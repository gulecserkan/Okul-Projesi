from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from PyQt5.QtCore import QPointF, QSizeF, Qt, QRectF
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QTransform
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QGraphicsTextItem

from core.config import load_settings

FIELD_PLACEHOLDERS = {
    'title': '{title}',
    'author': '{author}',
    'category': '{category}',
    'barcode': '{barcode}',
    'isbn': '{isbn}',
    'shelf_code': '{shelf_code}',
}


def mm_to_px(mm: float, dpi: int) -> float:
    return (mm / 25.4) * dpi


class Code128GraphicsItem:
    CODE128_PATTERNS = [
        '212222','222122','222221','121223','121322','131222','122213','122312','132212','221213',
        '221312','231212','112232','122132','122231','113222','123122','123221','223211','221132',
        '221231','213212','223112','312131','311222','321122','321221','312212','322112','322211',
        '212123','212321','232121','111323','131123','131321','112313','132113','132311','211313',
        '231113','231311','112133','112331','132131','113123','113321','133121','313121','211331',
        '231131','213113','213311','213131','311123','311321','331121','312113','312311','332111',
        '314111','221411','431111','111224','111422','121124','121421','141122','141221','112214',
        '112412','122114','122411','142112','142211','241211','221114','413111','241112','134111',
        '111242','121142','121241','114212','124112','124211','411212','421112','421211','212141',
        '214121','412121','111143','111341','131141','114113','114311','411113','411311','113141',
        '114131','311141','411131','211412','211214','211232','2331112'
    ]

    def __init__(self, text="KIT000001", height_px=160, module_px=2, font_family=None):
        self._text = text
        self._module = max(1, int(module_px))
        self._height = max(10, int(height_px))
        self._human_visible = True
        self._human_font_px = 12
        self._human_font_family = font_family or QFont().family()
        self._bounds = QRectF()
        self._update_geometry()

    @staticmethod
    def code128_encode_b(text: str):
        codes = [104]
        for ch in text:
            o = ord(ch)
            if 32 <= o <= 126:
                codes.append(o - 32)
            else:
                codes.append(0)
        checksum = 104
        for i, code in enumerate(codes[1:], start=1):
            checksum += code * i
        checksum %= 103
        codes.append(checksum)
        codes.append(106)
        return codes

    @classmethod
    def code128_total_modules(cls, codes):
        total = 0
        for val in codes:
            total += sum(int(d) for d in cls.CODE128_PATTERNS[val])
            if val == 106:
                total += 2
        return total

    def _update_geometry(self):
        codes = self.code128_encode_b(self._text)
        total = self.code128_total_modules(codes)
        width = total * self._module
        extra_h = (self._human_font_px + 6) if self._human_visible else 0
        self._bounds = QRectF(0, 0, width, self._height + extra_h)

    def setText(self, text: str):
        self._text = text or ""
        self._update_geometry()

    def setModule(self, px: int):
        self._module = max(1, int(px))
        self._update_geometry()

    def setBarHeight(self, px: int):
        self._height = max(10, int(px))
        self._update_geometry()

    def setHumanTextVisible(self, on: bool):
        self._human_visible = bool(on)
        self._update_geometry()

    def setHumanTextSize(self, px: int):
        self._human_font_px = max(6, int(px))
        self._update_geometry()

    def setHumanFontFamily(self, family: str):
        if family:
            self._human_font_family = family
            self._update_geometry()

    def draw(self, painter: QPainter, pos: QPointF):
        painter.save()
        painter.translate(pos)
        codes = self.code128_encode_b(self._text)
        curr_x = 0
        for val in codes:
            pattern = self.CODE128_PATTERNS[val]
            black = True
            for d in pattern:
                w = int(d) * self._module
                if black:
                    painter.fillRect(curr_x, 0, w, self._height, QColor(0, 0, 0))
                curr_x += w
                black = not black
            if val == 106:
                w = 2 * self._module
                painter.fillRect(curr_x, 0, w, self._height, QColor(0, 0, 0))
                curr_x += w
        if self._human_visible:
            font = painter.font()
            font.setPointSize(self._human_font_px)
            font.setBold(False)
            font.setFamily(self._human_font_family)
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))
            text_rect_h = int(self._human_font_px + 6)
            painter.drawText(0, self._height, curr_x, text_rect_h, Qt.AlignHCenter, self._text)
        painter.restore()

    def bounding_rect(self) -> QRectF:
        return self._bounds


def _load_template(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def _build_scene(template: Dict, context: Dict[str, str], font_family: str) -> QGraphicsScene:
    dpi = int(template.get("dpi", 203))
    scene = QGraphicsScene()
    mm_w = float(template.get("mm_w", 55.0))
    mm_h = float(template.get("mm_h", 40.0))
    scene.setSceneRect(0, 0, mm_to_px(mm_w, dpi), mm_to_px(mm_h, dpi))

    for item in template.get("items", []):
        item_type = item.get("type")
        x = mm_to_px(float(item.get("x_mm", 0)), dpi)
        y = mm_to_px(float(item.get("y_mm", 0)), dpi)
        rot = float(item.get("rotation", 0))

        field_name = item.get("field")
        if isinstance(item_type, str) and item_type.startswith("{") and item_type.endswith("}"):
            field_name = field_name or item_type.strip("{}")
            item_type = "field"
        elif item_type == "text":
            candidate = item.get("text", "")
            if isinstance(candidate, str):
                for key, placeholder in FIELD_PLACEHOLDERS.items():
                    if candidate == placeholder:
                        field_name = key
                        item_type = "field"
                        break

        if item_type == "field":
            placeholder = FIELD_PLACEHOLDERS.get(field_name, f"{{{field_name}}}")
            text_val = str(context.get(field_name, ""))
            text_item = QGraphicsTextItem(text_val)
            font = QFont()
            font.setPointSize(int(item.get("font_pt", 14)))
            font.setBold(bool(item.get("bold", False)))
            font.setFamily(item.get("font_family", font_family) or font_family)
            text_item.setFont(font)
            text_item.setDefaultTextColor(Qt.black)
            width_px = float(item.get("w_px", mm_to_px(mm_w * 0.6, dpi)))
            text_item.setTextWidth(width_px)
            text_item.setPos(x, y)
            text_item.setRotation(rot)
            align_name = str(item.get("align", "left")).lower()
            idx = 0 if align_name == "left" else 1 if align_name == "center" else 2
            _set_text_alignment(text_item, idx)
            scene.addItem(text_item)
        elif item_type == "text":
            text_val = item.get("text", "")
            text_item = QGraphicsTextItem(text_val)
            font = QFont()
            font.setPointSize(int(item.get("font_pt", 14)))
            font.setBold(bool(item.get("bold", False)))
            font.setFamily(item.get("font_family", font_family) or font_family)
            text_item.setFont(font)
            text_item.setDefaultTextColor(Qt.black)
            width_px = float(item.get("w_px", mm_to_px(mm_w * 0.6, dpi)))
            text_item.setTextWidth(width_px)
            text_item.setPos(x, y)
            text_item.setRotation(rot)
            align_name = str(item.get("align", "left")).lower()
            idx = 0 if align_name == "left" else 1 if align_name == "center" else 2
            _set_text_alignment(text_item, idx)
            scene.addItem(text_item)
        elif item_type == "code128":
            text_val = str(context.get("barcode", item.get("text", "")))
            code = Code128GraphicsItem(
                text_val,
                height_px=int(item.get("bar_h_px", 160)),
                module_px=int(item.get("module_px", 2)),
                font_family=item.get("human_font_family", font_family) or font_family,
            )
            code.setHumanTextVisible(bool(item.get("bar_text_visible", True)))
            code.setHumanTextSize(int(item.get("bar_text_px", 12)))
            wrapper = _CodeItemWrapper(code)
            wrapper.setPos(x, y)
            wrapper.setRotation(rot)
            scene.addItem(wrapper)

    return scene


def _set_text_alignment(text_item: QGraphicsTextItem, idx: int) -> None:
    doc = text_item.document()
    option = doc.defaultTextOption()
    if idx == 1:
        option.setAlignment(Qt.AlignHCenter)
    elif idx == 2:
        option.setAlignment(Qt.AlignRight)
    else:
        option.setAlignment(Qt.AlignLeft)
    doc.setDefaultTextOption(option)


class _CodeItemWrapper(QGraphicsItem):
    def __init__(self, code_item: Code128GraphicsItem):
        super().__init__()
        self.code_item = code_item

    def boundingRect(self):
        return self.code_item.bounding_rect()

    def paint(self, painter: QPainter, option, widget=None):
        self.code_item.draw(painter, QPointF(0, 0))


def render_template_to_image(template: Dict, context: Dict[str, str], font_family: str) -> QImage:
    dpi = int(template.get("dpi", 203))
    mm_w = float(template.get("mm_w", 55.0))
    mm_h = float(template.get("mm_h", 40.0))
    scene = _build_scene(template, context, font_family)
    width = int(mm_to_px(mm_w, dpi))
    height = int(mm_to_px(mm_h, dpi))
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    scene.render(painter)
    painter.end()
    return image


def _configure_printer(printer: QPrinter, template: Dict, prefs: Dict) -> None:
    mm_w = float(template.get("mm_w", 55.0))
    mm_h = float(template.get("mm_h", 40.0))
    dpi = int(template.get("dpi", 203))
    rotate = bool(prefs.get("rotate_print", False))

    if rotate:
        printer.setOrientation(QPrinter.Landscape if mm_w >= mm_h else QPrinter.Portrait)
    else:
        printer.setOrientation(QPrinter.Portrait if mm_h >= mm_w else QPrinter.Landscape)

    printer.setPaperSize(QSizeF(mm_w, mm_h), QPrinter.Millimeter)
    printer.setFullPage(True)
    try:
        printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
    except Exception:
        pass

    if prefs.get("label_is_thermal", prefs.get("default_printer_is_thermal", False)):
        printer.setResolution(max(203, dpi))
        printer.setColorMode(QPrinter.GrayScale)
    else:
        printer.setResolution(dpi)
        printer.setColorMode(QPrinter.Color)


def print_label_batch(template_path: str, contexts: List[Dict[str, str]]) -> None:
    if not contexts:
        return
    settings = load_settings() or {}
    label_prefs = settings.get("label_editor", {})
    printing_prefs = settings.get("printing", {})
    template = _load_template(template_path)
    font_family = label_prefs.get("font_family", QFont().family())
    rotate = bool(label_prefs.get("rotate_print", False))

    printer = QPrinter(QPrinter.HighResolution)
    printer_name = printing_prefs.get("label_printer") or label_prefs.get("default_printer")
    if printer_name:
        printer.setPrinterName(printer_name)

    label_prefs["label_is_thermal"] = printing_prefs.get(
        "label_is_thermal", label_prefs.get("default_printer_is_thermal", False)
    )

    _configure_printer(printer, template, label_prefs)

    if not printer_name:
        dlg = QPrintDialog(printer)
        dlg.setWindowTitle("Etiket Yazdır")
        if dlg.exec_() != QPrintDialog.Accepted:
            return

    painter = QPainter(printer)
    if not painter.isActive():
        painter.end()
        raise RuntimeError("Yazıcıya bağlanılamadı.")

    for index, ctx in enumerate(contexts):
        image = render_template_to_image(template, ctx, font_family)
        if rotate:
            transform = QTransform()
            transform.rotate(-90)
            image = image.transformed(transform, Qt.FastTransformation)
        page_rect = printer.pageRect(QPrinter.DevicePixel)
        scale_x = page_rect.width() / image.width()
        scale_y = page_rect.height() / image.height()
        scale = min(scale_x, scale_y)
        painter.save()
        painter.translate(page_rect.left(), page_rect.top())
        painter.scale(scale, scale)
        painter.drawImage(QPointF(0, 0), image)
        painter.restore()
        if index < len(contexts) - 1:
            printer.newPage()
    painter.end()


def get_default_template_path() -> Optional[str]:
    settings = load_settings() or {}
    prefs = settings.get("label_editor", {})
    path = prefs.get("default_template") or prefs.get("last_template")
    if path and os.path.exists(path):
        return path
    return None
