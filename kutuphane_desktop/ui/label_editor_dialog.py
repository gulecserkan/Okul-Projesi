from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from PyQt5.QtCore import (
    QPointF,
    QRect,
    QRectF,
    QSize,
    QSizeF,
    Qt,
    QTimer,
)
import sys

from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QIcon,
    QPainter,
    QPixmap,
    QTextOption,
    QTransform,
)
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
    QFontComboBox,
)

from core.config import load_settings, save_settings
from printing.template_renderer import (
    FIELD_PLACEHOLDERS,
    get_default_template_path,
    mm_to_px,
    print_label_batch,
    render_template_to_image,
)


FIELD_NAMES = ["title", "author", "category", "barcode", "isbn", "shelf_code"]


def px_to_mm(px: float, dpi: int) -> float:
    return (float(px) / dpi) * 25.4 if dpi else 0.0


class SnapTextItem(QGraphicsTextItem):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            scene = self.scene()
            if scene and getattr(scene, "snap_enabled", False):
                grid = getattr(scene, "grid_px", 0)
                if grid:
                    x = round(value.x() / grid) * grid
                    y = round(value.y() / grid) * grid
                    return QPointF(x, y)
        return super().itemChange(change, value)


class Code128GraphicsItem(QGraphicsItem):
    CODE128_PATTERNS = [
        "212222",
        "222122",
        "222221",
        "121223",
        "121322",
        "131222",
        "122213",
        "122312",
        "132212",
        "221213",
        "221312",
        "231212",
        "112232",
        "122132",
        "122231",
        "113222",
        "123122",
        "123221",
        "223211",
        "221132",
        "221231",
        "213212",
        "223112",
        "312131",
        "311222",
        "321122",
        "321221",
        "312212",
        "322112",
        "322211",
        "212123",
        "212321",
        "232121",
        "111323",
        "131123",
        "131321",
        "112313",
        "132113",
        "132311",
        "211313",
        "231113",
        "231311",
        "112133",
        "112331",
        "132131",
        "113123",
        "113321",
        "133121",
        "313121",
        "211331",
        "231131",
        "213113",
        "213311",
        "213131",
        "311123",
        "311321",
        "331121",
        "312113",
        "312311",
        "332111",
        "314111",
        "221411",
        "431111",
        "111224",
        "111422",
        "121124",
        "121421",
        "141122",
        "141221",
        "112214",
        "112412",
        "122114",
        "122411",
        "142112",
        "142211",
        "241211",
        "221114",
        "413111",
        "241112",
        "134111",
        "111242",
        "121142",
        "121241",
        "114212",
        "124112",
        "124211",
        "411212",
        "421112",
        "421211",
        "212141",
        "214121",
        "412121",
        "111143",
        "111341",
        "131141",
        "114113",
        "114311",
        "411113",
        "411311",
        "113141",
        "114131",
        "311141",
        "411131",
        "211412",
        "211214",
        "211232",
        "2331112",
    ]

    def __init__(self, text="KIT000001", height_px=160, module_px=2, font_family=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._module = max(1, int(module_px))
        self._height = max(10, int(height_px))
        self._human_visible = True
        self._human_font_px = 12
        self._human_font_family = font_family or QFont().family()
        self._bounds = QRectF()
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
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

    def setText(self, text: str):
        self._text = text or ""
        self._update_geometry()
        self.update()

    def text(self) -> str:
        return self._text

    def setModule(self, px: int):
        self._module = max(1, int(px))
        self._update_geometry()
        self.update()

    def module(self) -> int:
        return self._module

    def setBarHeight(self, px: int):
        self._height = max(10, int(px))
        self.prepareGeometryChange()
        self._update_geometry()
        self.update()

    def barHeight(self) -> int:
        return self._height

    def setHumanTextVisible(self, visible: bool):
        self._human_visible = bool(visible)
        self._update_geometry()
        self.update()

    def humanTextVisible(self) -> bool:
        return self._human_visible

    def setHumanTextSize(self, px: int):
        self._human_font_px = max(6, int(px))
        self._update_geometry()
        self.update()

    def humanTextSize(self) -> int:
        return self._human_font_px

    def setHumanFontFamily(self, family: str):
        if family:
            self._human_font_family = family
            self._update_geometry()
            self.update()

    def humanFontFamily(self) -> str:
        return self._human_font_family

    def _update_geometry(self):
        codes = self.code128_encode_b(self._text)
        total = self.code128_total_modules(codes)
        width = total * self._module
        extra_h = (self._human_font_px + 6) if self._human_visible else 0
        self._bounds = QRectF(0, 0, width, self._height + extra_h)

    def boundingRect(self) -> QRectF:
        return self._bounds

    def paint(self, painter: QPainter, option, widget=None):
        codes = self.code128_encode_b(self._text)
        curr_x = 0
        for val in codes:
            pattern = self.CODE128_PATTERNS[val]
            black = True
            for d in pattern:
                w = int(d) * self._module
                if black:
                    painter.fillRect(QRect(curr_x, 0, w, self._height), QColor(0, 0, 0))
                curr_x += w
                black = not black
            if val == 106:
                w = 2 * self._module
                painter.fillRect(QRect(curr_x, 0, w, self._height), QColor(0, 0, 0))
                curr_x += w
        if self._human_visible:
            font = painter.font()
            font.setPointSize(self._human_font_px)
            font.setBold(False)
            font.setFamily(self._human_font_family)
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))
            rect = QRect(0, int(self._height), int(self._bounds.width()), int(self._human_font_px + 6))
            painter.drawText(rect, int(Qt.AlignHCenter | Qt.AlignVCenter), self._text)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            scene = self.scene()
            if scene and getattr(scene, "snap_enabled", False):
                grid = getattr(scene, "grid_px", 0)
                if grid:
                    x = round(value.x() / grid) * grid
                    y = round(value.y() / grid) * grid
                    return QPointF(x, y)
        return super().itemChange(change, value)


class LabelScene(QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_px = 0
        self.snap_enabled = False

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        if self.grid_px and self.grid_px > 0:
            painter.save()
            painter.setPen(QColor(220, 220, 220))
            r = self.sceneRect()
            x = 0
            while x <= r.width():
                painter.drawLine(int(x), 0, int(x), int(r.height()))
                x += self.grid_px
            y = 0
            while y <= r.height():
                painter.drawLine(0, int(y), int(r.width()), int(y))
                y += self.grid_px
            painter.restore()


@dataclass
class TemplateItem:
    type: str
    text: str
    field: Optional[str]
    x_mm: float
    y_mm: float
    rotation: float
    w_px: float
    font_pt: int
    bold: bool
    align: str
    module_px: int = 2
    bar_h_px: int = 160
    bar_text_visible: bool = True
    bar_text_px: int = 12
    font_family: Optional[str] = None
    human_font_family: Optional[str] = None


class _SampleDataDialog(QDialog):
    def __init__(self, data: Dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Örnek Veriyi Düzenle")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.in_title = QLineEdit(data.get("title", ""))
        self.in_author = QLineEdit(data.get("author", ""))
        self.in_category = QLineEdit(data.get("category", ""))
        self.in_barcode = QLineEdit(data.get("barcode", ""))
        self.in_isbn = QLineEdit(data.get("isbn", ""))
        self.in_shelf = QLineEdit(data.get("shelf_code", ""))
        form.addRow("Kitap Adı", self.in_title)
        form.addRow("Yazar", self.in_author)
        form.addRow("Kategori", self.in_category)
        form.addRow("Barkod", self.in_barcode)
        form.addRow("ISBN", self.in_isbn)
        form.addRow("Raf Kodu", self.in_shelf)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def data(self) -> Dict[str, str]:
        return {
            "title": self.in_title.text().strip(),
            "author": self.in_author.text().strip(),
            "category": self.in_category.text().strip(),
            "barcode": self.in_barcode.text().strip(),
            "isbn": self.in_isbn.text().strip(),
            "shelf_code": self.in_shelf.text().strip(),
        }


class _ImagePreviewDialog(QDialog):
    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Önizleme")
        self.resize(900, 650)
        v = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        btn_fit = QPushButton("Sığdır")
        btn_100 = QPushButton("100%")
        btn_minus = QPushButton("–")
        btn_plus = QPushButton("+")
        toolbar.addWidget(btn_fit)
        toolbar.addWidget(btn_100)
        toolbar.addStretch(1)
        toolbar.addWidget(btn_minus)
        toolbar.addWidget(btn_plus)
        v.addLayout(toolbar)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.label)
        v.addWidget(self.scroll, 1)

        self._orig = QPixmap.fromImage(image)
        self._zoom = 1.0
        self._update_pixmap()

        btn_fit.clicked.connect(self._fit)
        btn_100.clicked.connect(self._reset)
        btn_minus.clicked.connect(lambda: self._change_zoom(1 / 1.2))
        btn_plus.clicked.connect(lambda: self._change_zoom(1.2))

    def _update_pixmap(self):
        if self._orig.isNull():
            return
        target = self._orig.scaled(
            self._orig.size() * self._zoom,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.label.setPixmap(target)

    def _change_zoom(self, factor: float):
        self._zoom = max(0.1, min(8.0, self._zoom * factor))
        self._update_pixmap()

    def _fit(self):
        if self._orig.isNull():
            return
        area = self.scroll.viewport().size()
        size = self._orig.size()
        if size.width() == 0 or size.height() == 0:
            return
        self._zoom = min(area.width() / size.width(), area.height() / size.height())
        self._update_pixmap()

    def _reset(self):
        self._zoom = 1.0
        self.label.setPixmap(self._orig)


class LabelEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Etiket Editörü")
        self.resize(960, 640)

        self.dpi = 300
        self.mm_w = 57.0
        self.mm_h = 40.0
        self.template_path = os.path.join("label_templates", "default.json")
        self.default_template = None
        self.default_printer = None
        self.default_printer_is_thermal = False
        self.rotate_print_pref = False
        self.auto_save_pref = False
        self.default_font_family = QFont().family()

        self.sample_context = {
            "title": "Kitap Adı Örneği",
            "author": "Yazar Adı",
            "category": "Kategori Adı",
            "barcode": "KIT000001",
            "isbn": "9786050000000",
            "shelf_code": "A-01",
        }
        self.sample_file = None
        self.sample_live = False
        self._live_cache: Dict[int, str] = {}
        self._loading_template = False
        self._suspend_auto_save = 0

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setInterval(750)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.timeout.connect(self._auto_save_template)

        self._load_prefs()
        self._build_ui()
        self._apply_preferences()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        toolbar_widget = QWidget()
        toolbar1 = QHBoxLayout(toolbar_widget)
        toolbar1.setContentsMargins(0, 0, 0, 0)
        toolbar1.addWidget(QLabel("Genişlik (mm):"))
        self.sp_w = QDoubleSpinBox()
        self.sp_w.setRange(10, 200)
        self.sp_w.setValue(self.mm_w)
        toolbar1.addWidget(self.sp_w)
        toolbar1.addWidget(QLabel("Yükseklik (mm):"))
        self.sp_h = QDoubleSpinBox()
        self.sp_h.setRange(10, 200)
        self.sp_h.setValue(self.mm_h)
        toolbar1.addWidget(self.sp_h)
        toolbar1.addWidget(QLabel("DPI:"))
        self.sp_dpi = QSpinBox()
        self.sp_dpi.setRange(96, 600)
        self.sp_dpi.setValue(self.dpi)
        toolbar1.addWidget(self.sp_dpi)
        self.chk_snap = QCheckBox("Izgaraya Yapıştır")
        toolbar1.addWidget(self.chk_snap)
        toolbar1.addWidget(QLabel("Izgara (mm):"))
        self.spin_grid = QDoubleSpinBox()
        self.spin_grid.setRange(0.5, 10.0)
        self.spin_grid.setSingleStep(0.5)
        self.spin_grid.setValue(2.0)
        toolbar1.addWidget(self.spin_grid)
        toolbar1.addStretch(1)

        root.addWidget(toolbar_widget)
        toolbar_widget.setVisible(False)

        # Printer toolbar
        printer_frame = QFrame()
        printer_frame.setObjectName("ToolbarGroup")
        printer_bar = QHBoxLayout(printer_frame)
        printer_bar.setContentsMargins(8, 6, 8, 6)
        printer_bar.setSpacing(8)
        printer_bar.setAlignment(Qt.AlignLeft)
        printer_bar.addWidget(QLabel("Yazıcı:"))
        self.lbl_printer_name = QLabel("—")
        printer_bar.addWidget(self.lbl_printer_name)
        self.btn_printer_settings = QPushButton("Yazıcı Seç…")
        self.btn_printer_settings.setObjectName("ToolbarButton")
        printer_bar.addWidget(self.btn_printer_settings)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setFrameShadow(QFrame.Sunken)
        sep2.setFixedHeight(28)
        printer_bar.addWidget(sep2)
        self.chk_rotate_print = QCheckBox("90° Döndür")
        printer_bar.addWidget(self.chk_rotate_print)

        root.addWidget(printer_frame)
        printer_frame.setVisible(False)

        # Object toolbar
        bar_objects_frame = QFrame()
        bar_objects_frame.setObjectName("ToolbarGroup")
        bar_objects = QHBoxLayout(bar_objects_frame)
        bar_objects.setContentsMargins(8, 6, 8, 6)
        bar_objects.setSpacing(8)
        bar_objects.addWidget(QLabel("Alan:"))
        self.cmb_field = QComboBox()
        self.cmb_field.addItems(FIELD_NAMES)
        bar_objects.addWidget(self.cmb_field)
        btn_add_field = QPushButton("Alan Ekle")
        bar_objects.addWidget(btn_add_field)
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setFixedHeight(28)
        bar_objects.addWidget(sep)
        btn_add_text = QPushButton("Metin Ekle")
        btn_add_bar = QPushButton("Barkod Ekle")
        btn_delete = QPushButton("Seçiliyi Sil")
        for b in (btn_add_field, btn_add_text, btn_add_bar, btn_delete):
            b.setObjectName("ToolbarButton")
        bar_objects.addWidget(btn_add_text)
        bar_objects.addWidget(btn_add_bar)
        bar_objects.addWidget(btn_delete)
        bar_objects.addWidget(QLabel("Font:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setEditable(False)
        self.font_combo.setFontFilters(QFontComboBox.AllFonts)
        bar_objects.addWidget(self.font_combo)
        self.font_combo.blockSignals(True)
        self.font_combo.setCurrentFont(QFont(self.default_font_family))
        self.font_combo.blockSignals(False)

        root.addWidget(bar_objects_frame)

        # Template toolbar
        bar_template_frame = QFrame()
        bar_template_frame.setObjectName("ToolbarGroup")
        bar_template = QHBoxLayout(bar_template_frame)
        bar_template.setContentsMargins(8, 6, 8, 6)
        bar_template.setSpacing(8)
        btn_load = QPushButton("Şablon Yükle")
        btn_save = QPushButton("Şablon Kaydet")
        btn_new_tpl = QPushButton("Yeni Şablon")
        btn_set_default = QPushButton("Varsayılan Yap")
        for b in (btn_load, btn_save, btn_new_tpl, btn_set_default):
            b.setObjectName("ToolbarButton")
        bar_template.addWidget(btn_load)
        bar_template.addWidget(btn_save)
        bar_template.addWidget(btn_new_tpl)
        bar_template.addWidget(btn_set_default)
        self.chk_auto_save = QCheckBox("Otomatik kaydet")
        bar_template.addWidget(self.chk_auto_save)
        bar_template.addStretch(1)

        root.addWidget(bar_template_frame)

        # Output toolbar
        bar_output_frame = QFrame()
        bar_output_frame.setObjectName("ToolbarGroup")
        bar_output = QHBoxLayout(bar_output_frame)
        bar_output.setContentsMargins(8, 6, 8, 6)
        bar_output.setSpacing(8)
        btn_preview = QPushButton("Önizleme PNG")
        btn_print = QPushButton("Test Yazdır")
        btn_edit_sample = QPushButton("Örnek Veriyi Düzenle")
        for b in (btn_preview, btn_print, btn_edit_sample):
            b.setObjectName("ToolbarButton")
        self.chk_sample_live = QCheckBox("Örnek veriyi göster")
        bar_output.addWidget(btn_preview)
        bar_output.addWidget(btn_print)
        bar_output.addWidget(self.chk_sample_live)
        bar_output.addWidget(btn_edit_sample)
        bar_output.addStretch(1)

        root.addWidget(bar_output_frame)

        # Graphics view + properties
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        self.scene = LabelScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_box = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_box)
        left_box.addWidget(self.view, 1)
        zoom_bar = QHBoxLayout()
        btn_zoom_out = QPushButton("–")
        btn_fit = QPushButton("Sığdır")
        btn_zoom_in = QPushButton("+")
        for b in (btn_zoom_out, btn_fit, btn_zoom_in):
            b.setObjectName("ToolbarButton")
        zoom_bar.addWidget(btn_zoom_out)
        zoom_bar.addWidget(btn_fit)
        zoom_bar.addWidget(btn_zoom_in)
        zoom_widget = QWidget()
        zoom_widget.setLayout(zoom_bar)
        left_box.addWidget(zoom_widget, 0)
        splitter.addWidget(left_widget)

        prop_widget = QWidget()
        prop_widget.setFixedWidth(300)
        prop_layout = QFormLayout(prop_widget)
        prop_layout.setSpacing(8)
        prop_layout.setContentsMargins(10, 10, 10, 10)

        self.lbl_prop_type = QLabel("—")
        prop_layout.addRow(QLabel("Seçim:"), self.lbl_prop_type)
        self.prop_text = QLineEdit()
        self.prop_text.setEnabled(False)
        prop_layout.addRow(QLabel("Metin:"), self.prop_text)
        self.prop_rotation = QDoubleSpinBox()
        self.prop_rotation.setRange(-360.0, 360.0)
        self.prop_rotation.setSingleStep(1.0)
        self.prop_rotation.setDecimals(1)
        self.prop_rotation.setEnabled(False)
        prop_layout.addRow(QLabel("Döndür (°):"), self.prop_rotation)

        self.prop_font = QSpinBox()
        self.prop_font.setRange(6, 96)
        self.prop_font.setValue(14)
        self.prop_bold = QCheckBox("Kalın")
        self.prop_align = QComboBox()
        self.prop_align.addItems(["Sola", "Ortala", "Sağa"])
        self.prop_text_width = QDoubleSpinBox()
        self.prop_text_width.setRange(5.0, 500.0)
        self.prop_text_width.setSingleStep(1.0)
        self.prop_text_width.setDecimals(1)
        self.prop_text_width.setEnabled(False)

        self.prop_module = QSpinBox()
        self.prop_module.setRange(1, 8)
        self.prop_module.setValue(2)
        self.prop_height = QSpinBox()
        self.prop_height.setRange(20, 600)
        self.prop_height.setValue(160)
        self.prop_target_w = QDoubleSpinBox()
        self.prop_target_w.setRange(5.0, 200.0)
        self.prop_target_w.setSingleStep(0.5)
        self.prop_target_w.setDecimals(1)
        self.prop_target_w.setEnabled(False)
        self.chk_bar_text = QCheckBox("Barkod Metni")
        self.chk_bar_text.setChecked(True)
        self.spin_bar_text_px = QSpinBox()
        self.spin_bar_text_px.setRange(6, 72)
        self.spin_bar_text_px.setValue(12)

        self._rows_common = [(self.prop_rotation,)]
        self._rows_text = [
            (self.prop_font,),
            (self.prop_bold,),
            (self.prop_align,),
            (self.prop_text_width,),
        ]
        self._rows_barcode = [
            (self.prop_module,),
            (self.prop_height,),
            (self.prop_target_w,),
            (self.chk_bar_text,),
            (self.spin_bar_text_px,),
        ]

        prop_layout.addRow(QLabel("Yazı Boyutu:"), self.prop_font)
        prop_layout.addRow(self.prop_bold)
        prop_layout.addRow(QLabel("Hizalama:"), self.prop_align)
        prop_layout.addRow(QLabel("Metin Genişliği (mm):"), self.prop_text_width)
        prop_layout.addRow(QLabel("Modül (px):"), self.prop_module)
        prop_layout.addRow(QLabel("Bar Yüksekliği (px):"), self.prop_height)
        prop_layout.addRow(QLabel("Barkod Genişliği (mm):"), self.prop_target_w)
        prop_layout.addRow(self.chk_bar_text)
        prop_layout.addRow(QLabel("Metin Boyutu (px):"), self.spin_bar_text_px)

        prop_scroll = QScrollArea()
        prop_scroll.setWidgetResizable(True)
        prop_scroll.setWidget(prop_widget)
        splitter.addWidget(prop_scroll)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        # Events
        self.sp_w.valueChanged.connect(lambda v: self._update_canvas(v, self.sp_h.value(), self.sp_dpi.value()))
        self.sp_h.valueChanged.connect(lambda v: self._update_canvas(self.sp_w.value(), v, self.sp_dpi.value()))
        self.sp_dpi.valueChanged.connect(lambda v: self._update_canvas(self.sp_w.value(), self.sp_h.value(), v))
        self.chk_snap.toggled.connect(self._on_snap_toggle)
        self.spin_grid.valueChanged.connect(lambda v: self._apply_grid(v))
        self.chk_rotate_print.toggled.connect(lambda _: self._save_prefs())
        self.chk_auto_save.toggled.connect(self._on_auto_save_toggled)
        self.chk_sample_live.toggled.connect(self._apply_sample_live)

        btn_add_text.clicked.connect(self.add_text_item)
        btn_add_field.clicked.connect(self.add_field_item)
        btn_add_bar.clicked.connect(self.add_barcode_item)
        btn_delete.clicked.connect(self.delete_selected)
        btn_load.clicked.connect(self.load_template)
        btn_save.clicked.connect(self.save_template)
        btn_new_tpl.clicked.connect(self.new_template)
        btn_set_default.clicked.connect(self.set_default_template)
        btn_preview.clicked.connect(self.export_png)
        btn_print.clicked.connect(self.print_test)
        btn_edit_sample.clicked.connect(self.edit_sample_data)
        btn_zoom_in.clicked.connect(lambda: self._zoom(1.2))
        btn_zoom_out.clicked.connect(lambda: self._zoom(1 / 1.2))
        btn_fit.clicked.connect(lambda: self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio))

        self.font_combo.currentFontChanged.connect(self._on_font_family_changed)
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.scene.changed.connect(self._on_scene_changed)
        self.btn_printer_settings.clicked.connect(self._open_printer_settings)

        self.prop_text.textChanged.connect(self._apply_prop_text)
        self.prop_font.valueChanged.connect(self._apply_prop_font)
        self.prop_bold.toggled.connect(self._apply_prop_bold)
        self.prop_align.currentIndexChanged.connect(self._apply_prop_alignment)
        self.prop_text_width.valueChanged.connect(self._apply_prop_text_width)
        self.prop_rotation.valueChanged.connect(self._apply_prop_rotation)
        self.prop_module.valueChanged.connect(self._apply_prop_module)
        self.prop_height.valueChanged.connect(self._apply_prop_height)
        self.prop_target_w.valueChanged.connect(self._apply_barcode_target_width)
        self.chk_bar_text.toggled.connect(self._apply_bar_text_visible)
        self.spin_bar_text_px.valueChanged.connect(self._apply_bar_text_size)

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------
    def _apply_preferences(self):
        self._loading_template = True
        self._update_canvas(self.mm_w, self.mm_h, self.dpi)
        self.chk_snap.setChecked(getattr(self, "_pref_snap", False))
        self.spin_grid.setValue(getattr(self, "_pref_grid_mm", 2.0))
        self.chk_auto_save.setChecked(self.auto_save_pref)
        self.chk_rotate_print.setChecked(self.rotate_print_pref)
        self._load_printer_settings()
        template = self.default_template or self.template_path
        if template and os.path.exists(template):
            self._load_template_from_path(template)
        self._loading_template = False
        self._auto_save_timer.stop()

    def _update_canvas(self, mm_w, mm_h, dpi):
        self.mm_w = float(mm_w)
        self.mm_h = float(mm_h)
        self.dpi = int(dpi)
        self.scene.setSceneRect(0, 0, mm_to_px(self.mm_w, self.dpi), mm_to_px(self.mm_h, self.dpi))
        for item in list(self.scene.items()):
            if isinstance(item, QGraphicsRectItem) and getattr(item, "_is_bg", False):
                self.scene.removeItem(item)
        bg = QGraphicsRectItem(0, 0, mm_to_px(self.mm_w, self.dpi), mm_to_px(self.mm_h, self.dpi))
        bg.setPen(QColor(180, 180, 180))
        bg.setZValue(-1000)
        bg._is_bg = True
        self.scene.addItem(bg)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self._apply_grid(self.spin_grid.value())
        self._save_prefs()

    # ------------------------------------------------------------------
    # Add / delete items
    # ------------------------------------------------------------------
    def add_text_item(self):
        item = SnapTextItem("Yeni Metin")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setFamily(self.default_font_family)
        item.setFont(font)
        item.setDefaultTextColor(Qt.black)
        item.setTextWidth(mm_to_px(self.mm_w * 0.6, self.dpi))
        item.setFlag(QGraphicsItem.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        item.setPos(10, 10)
        item.setData(1, None)
        self.scene.addItem(item)
        self._trigger_auto_save()

    def add_field_item(self):
        field = self.cmb_field.currentText()
        placeholder = FIELD_PLACEHOLDERS.get(field, FIELD_PLACEHOLDERS["title"])
        item = SnapTextItem(self._sub_placeholder(field, placeholder))
        font = QFont()
        font.setPointSize(14)
        font.setBold(field in ("title", "barcode"))
        font.setFamily(self.default_font_family)
        item.setFont(font)
        item.setDefaultTextColor(Qt.black)
        item.setTextWidth(mm_to_px(self.mm_w * 0.6, self.dpi))
        item.setFlag(QGraphicsItem.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        item.setPos(10, 10)
        item.setData(1, field)
        self.scene.addItem(item)
        self._trigger_auto_save()

    def add_barcode_item(self):
        code = Code128GraphicsItem("KIT000001", height_px=int(mm_to_px(15, self.dpi)), module_px=2, font_family=self.default_font_family)
        code.setPos(10, max(0, mm_to_px(self.mm_h - 20, self.dpi)))
        self.scene.addItem(code)
        self._trigger_auto_save()

    def delete_selected(self):
        removed = False
        for item in list(self.scene.selectedItems()):
            if isinstance(item, (SnapTextItem, Code128GraphicsItem)):
                self.scene.removeItem(item)
                removed = True
        if removed:
            self._trigger_auto_save()

    # ------------------------------------------------------------------
    # Selection / properties
    # ------------------------------------------------------------------
    def _on_selection_changed(self):
        items = self.scene.selectedItems()
        if not items:
            self._set_selection_none()
            return
        item = items[0]
        self.prop_rotation.blockSignals(True)
        self.prop_rotation.setValue(float(item.rotation()))
        self.prop_rotation.blockSignals(False)
        self.prop_rotation.setEnabled(True)

        if isinstance(item, QGraphicsTextItem):
            self._show_text_properties(item)
        elif isinstance(item, Code128GraphicsItem):
            self._show_barcode_properties(item)
        else:
            self._set_selection_none()

    def _set_selection_none(self):
        self.lbl_prop_type.setText("—")
        for widgets in self._rows_text + self._rows_barcode:
            for w in widgets:
                w.setEnabled(False)
        self.prop_text.setEnabled(False)
        self.prop_rotation.setEnabled(False)
        self.prop_text.clear()

    def _show_text_properties(self, item: QGraphicsTextItem):
        field = item.data(1)
        self.lbl_prop_type.setText("Alan" if field else "Metin")
        text = item.toPlainText()
        if field:
            text = FIELD_PLACEHOLDERS.get(field, text)
        self.prop_text.blockSignals(True)
        self.prop_text.setText(text)
        self.prop_text.blockSignals(False)
        self.prop_text.setEnabled(not field)

        font = item.font()
        self.prop_font.blockSignals(True)
        self.prop_font.setValue(font.pointSize())
        self.prop_font.blockSignals(False)
        self.prop_bold.blockSignals(True)
        self.prop_bold.setChecked(font.bold())
        self.prop_bold.blockSignals(False)

        align_idx = self._get_text_alignment_index(item)
        self.prop_align.blockSignals(True)
        self.prop_align.setCurrentIndex(align_idx)
        self.prop_align.blockSignals(False)
        width_mm = px_to_mm(item.textWidth(), self.dpi)
        self.prop_text_width.blockSignals(True)
        self.prop_text_width.setValue(max(self.prop_text_width.minimum(), min(width_mm, self.prop_text_width.maximum())))
        self.prop_text_width.blockSignals(False)
        for widgets in self._rows_text:
            for w in widgets:
                w.setEnabled(True)
        for widgets in self._rows_barcode:
            for w in widgets:
                w.setEnabled(False)

    def _show_barcode_properties(self, item: Code128GraphicsItem):
        self.lbl_prop_type.setText("Code128 Barkod")
        self.prop_text.blockSignals(True)
        self.prop_text.setText(item.text())
        self.prop_text.blockSignals(False)
        self.prop_text.setEnabled(True)
        self.prop_module.blockSignals(True)
        self.prop_module.setValue(item.module())
        self.prop_module.blockSignals(False)
        self.prop_height.blockSignals(True)
        self.prop_height.setValue(item.barHeight())
        self.prop_height.blockSignals(False)
        total_modules = Code128GraphicsItem.code128_total_modules(Code128GraphicsItem.code128_encode_b(item.text()))
        actual_mm = px_to_mm(total_modules * item.module(), self.dpi)
        self.prop_target_w.blockSignals(True)
        self.prop_target_w.setValue(actual_mm)
        self.prop_target_w.blockSignals(False)
        self.chk_bar_text.blockSignals(True)
        self.chk_bar_text.setChecked(item.humanTextVisible())
        self.chk_bar_text.blockSignals(False)
        self.spin_bar_text_px.blockSignals(True)
        self.spin_bar_text_px.setValue(item.humanTextSize())
        self.spin_bar_text_px.blockSignals(False)
        for widgets in self._rows_text:
            for w in widgets:
                w.setEnabled(False)
        for widgets in self._rows_barcode:
            for w in widgets:
                w.setEnabled(True)

    def _apply_prop_text(self, text: str):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, QGraphicsTextItem):
            if item.data(1):
                return
            item.setPlainText(text)
        elif isinstance(item, Code128GraphicsItem):
            item.setText(text)
        self._trigger_auto_save()

    def _apply_prop_font(self, value: int):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, QGraphicsTextItem):
            font = item.font()
            font.setPointSize(int(value))
            item.setFont(font)
            self._trigger_auto_save()

    def _apply_prop_bold(self, checked: bool):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, QGraphicsTextItem):
            font = item.font()
            font.setBold(bool(checked))
            item.setFont(font)
            self._trigger_auto_save()

    def _apply_prop_alignment(self, index: int):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, QGraphicsTextItem):
            doc = item.document()
            option = QTextOption(doc.defaultTextOption())
            option.setAlignment([Qt.AlignLeft, Qt.AlignHCenter, Qt.AlignRight][index])
            doc.setDefaultTextOption(option)
            self._trigger_auto_save()

    def _apply_prop_text_width(self, mm_val: float):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, QGraphicsTextItem):
            px = mm_to_px(float(mm_val), self.dpi)
            item.setTextWidth(px)
            self._trigger_auto_save()

    def _apply_prop_rotation(self, angle: float):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        item.setRotation(float(angle))
        self._trigger_auto_save()

    def _apply_prop_module(self, value: int):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, Code128GraphicsItem):
            item.setModule(int(value))
            total = Code128GraphicsItem.code128_total_modules(Code128GraphicsItem.code128_encode_b(item.text()))
            actual_mm = px_to_mm(total * item.module(), self.dpi)
            self.prop_target_w.blockSignals(True)
            self.prop_target_w.setValue(actual_mm)
            self.prop_target_w.blockSignals(False)
            self._trigger_auto_save()

    def _apply_prop_height(self, value: int):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, Code128GraphicsItem):
            item.setBarHeight(int(value))
            self._trigger_auto_save()

    def _apply_barcode_target_width(self, mm_val: float):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if not isinstance(item, Code128GraphicsItem):
            return
        try:
            mm = float(mm_val)
            if mm <= 0:
                return
            codes = Code128GraphicsItem.code128_encode_b(item.text())
            total = Code128GraphicsItem.code128_total_modules(codes)
            desired_px = mm_to_px(mm, self.dpi)
            module_px = max(1, int(round(desired_px / total)))
            item.setModule(module_px)
            self.prop_module.blockSignals(True)
            self.prop_module.setValue(module_px)
            self.prop_module.blockSignals(False)
            actual_mm = px_to_mm(total * module_px, self.dpi)
            self.prop_target_w.blockSignals(True)
            self.prop_target_w.setValue(actual_mm)
            self.prop_target_w.blockSignals(False)
            self._trigger_auto_save()
        except Exception:
            pass

    def _apply_bar_text_visible(self, checked: bool):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, Code128GraphicsItem):
            item.setHumanTextVisible(bool(checked))
            if self.chk_sample_live.isChecked():
                self._apply_sample_live(True)
            item.update()
            self.scene.update()
            self._trigger_auto_save()

    def _apply_bar_text_size(self, value: int):
        items = self.scene.selectedItems()
        if not items:
            return
        item = items[0]
        if isinstance(item, Code128GraphicsItem):
            item.setHumanTextSize(int(value))
            self._trigger_auto_save()

    # ------------------------------------------------------------------
    # Sample data & auto live preview
    # ------------------------------------------------------------------
    def _substitute(self, text: str) -> str:
        if not text:
            return ""
        result = text
        for key, placeholder in FIELD_PLACEHOLDERS.items():
            result = result.replace(placeholder, self.sample_context.get(key, ""))
        return result

    def _sub_placeholder(self, field: str, placeholder: str) -> str:
        value = self.sample_context.get(field, "")
        return value if self.chk_sample_live.isChecked() else placeholder

    def _apply_sample_live(self, on: bool):
        self.sample_live = bool(on)
        self._suspend_auto_save += 1
        try:
            if self.sample_live:
                for item in self.scene.items():
                    if isinstance(item, QGraphicsTextItem) and not isinstance(item, Code128GraphicsItem):
                        field = item.data(1)
                        key = id(item)
                        if key not in self._live_cache:
                            self._live_cache[key] = item.toPlainText()
                        if field:
                            item.setPlainText(self.sample_context.get(field, ""))
                        else:
                            item.setPlainText(self._live_cache[key])
                    elif isinstance(item, Code128GraphicsItem):
                        key = id(item)
                        if key not in self._live_cache:
                            self._live_cache[key] = item.text()
                        item.setText(self.sample_context.get("barcode", item.text()))
            else:
                for item in self.scene.items():
                    key = id(item)
                    if isinstance(item, QGraphicsTextItem) and not isinstance(item, Code128GraphicsItem):
                        field = item.data(1)
                        if field:
                            item.setPlainText(FIELD_PLACEHOLDERS.get(field, item.toPlainText()))
                        elif key in self._live_cache:
                            item.setPlainText(self._live_cache[key])
                    elif isinstance(item, Code128GraphicsItem):
                        if key in self._live_cache:
                            item.setText(self._live_cache[key])
                self._live_cache.clear()
        finally:
            self._suspend_auto_save = max(0, self._suspend_auto_save - 1)
            self.scene.update()

    # ------------------------------------------------------------------
    # Template load/save
    # ------------------------------------------------------------------
    def _gather_template_data(self) -> Dict:
        items: List[TemplateItem] = []
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem) and getattr(item, "_is_bg", False):
                continue
            if isinstance(item, QGraphicsTextItem) and not isinstance(item, Code128GraphicsItem):
                field = item.data(1)
                text = item.toPlainText()
                align = ["left", "center", "right"][self._get_text_alignment_index(item)]
                ti = TemplateItem(
                    type="field" if field else "text",
                    text="" if field else text,
                    field=field,
                    x_mm=px_to_mm(item.pos().x(), self.dpi),
                    y_mm=px_to_mm(item.pos().y(), self.dpi),
                    rotation=float(item.rotation()),
                    w_px=float(item.textWidth()),
                    font_pt=item.font().pointSize(),
                    bold=item.font().bold(),
                    align=align,
                    font_family=item.font().family(),
                )
                items.append(ti)
            elif isinstance(item, Code128GraphicsItem):
                ti = TemplateItem(
                    type="code128",
                    text=item.text(),
                    field=None,
                    x_mm=px_to_mm(item.pos().x(), self.dpi),
                    y_mm=px_to_mm(item.pos().y(), self.dpi),
                    rotation=float(item.rotation()),
                    w_px=0,
                    font_pt=0,
                    bold=False,
                    align="left",
                    module_px=item.module(),
                    bar_h_px=item.barHeight(),
                    bar_text_visible=item.humanTextVisible(),
                    bar_text_px=item.humanTextSize(),
                    human_font_family=item.humanFontFamily(),
                )
                items.append(ti)
        data = {
            "mm_w": self.mm_w,
            "mm_h": self.mm_h,
            "dpi": self.dpi,
            "items": [],
        }
        for ti in items:
            base = {
                "x_mm": ti.x_mm,
                "y_mm": ti.y_mm,
                "rotation": ti.rotation,
                "w_px": ti.w_px,
                "font_pt": ti.font_pt,
                "bold": ti.bold,
                "align": ti.align,
                "font_family": ti.font_family,
            }
            if ti.type == "field":
                item = {
                    "type": FIELD_PLACEHOLDERS.get(ti.field, f"{{{ti.field}}}"),
                    "field": ti.field,
                }
                item.update(base)
                data["items"].append(item)
            elif ti.type == "text":
                item = {"type": "text", "text": ti.text}
                item.update(base)
                data["items"].append(item)
            elif ti.type == "code128":
                item = {
                    "type": "code128",
                    "text": ti.text,
                    "module_px": ti.module_px,
                    "bar_h_px": ti.bar_h_px,
                    "bar_text_visible": ti.bar_text_visible,
                    "bar_text_px": ti.bar_text_px,
                    "human_font_family": ti.human_font_family,
                }
                item.update(base)
                data["items"].append(item)
        return data

    def _write_template_to_path(self, path: str, show_message: bool = False) -> bool:
        if not path:
            return False
        data = self._gather_template_data()
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.template_path = path
            self._save_prefs()
            if show_message:
                QMessageBox.information(self, "Kaydedildi", "Şablon kaydedildi.")
            return True
        except Exception as exc:
            if show_message:
                QMessageBox.warning(self, "Hata", f"Kaydedilemedi: {exc}")
            else:
                print("[WARN] Şablon otomatik kaydedilemedi:", exc)
            return False

    def save_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Şablon Kaydet", self.template_path, "JSON (*.json)")
        if not path:
            return
        if self._write_template_to_path(path, show_message=True):
            self._auto_save_timer.stop()

    def load_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "Şablon Yükle", self.template_path, "JSON (*.json)")
        if not path:
            return
        self._load_template_from_path(path)

    def _load_template_from_path(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.warning(self, "Hata", f"Şablon okunamadı: {exc}")
            return
        self._auto_save_timer.stop()
        self._loading_template = True
        try:
            self.scene.clear()
            self._update_canvas(data.get("mm_w", self.mm_w), data.get("mm_h", self.mm_h), data.get("dpi", self.dpi))
            for item in data.get("items", []):
                t = item.get("type")
                x = mm_to_px(float(item.get("x_mm", 0)), self.dpi)
                y = mm_to_px(float(item.get("y_mm", 0)), self.dpi)
                rot = float(item.get("rotation", 0))
                field_name = item.get("field")
                if isinstance(t, str) and t.startswith("{") and t.endswith("}"):
                    field_name = field_name or t.strip("{}")
                    t = "field"
                elif t == "text":
                    candidate = item.get("text", "")
                    if isinstance(candidate, str):
                        for key, placeholder in FIELD_PLACEHOLDERS.items():
                            if candidate == placeholder:
                                field_name = key
                                t = "field"
                                break
                if t == "field" and not field_name:
                    t = "text"
                if t == "text":
                    snap = SnapTextItem(item.get("text", ""))
                    font = QFont()
                    font.setPointSize(int(item.get("font_pt", 14)))
                    font.setBold(bool(item.get("bold", False)))
                    font.setFamily(item.get("font_family", self.default_font_family))
                    snap.setFont(font)
                    snap.setDefaultTextColor(Qt.black)
                    snap.setTextWidth(float(item.get("w_px", mm_to_px(self.mm_w * 0.6, self.dpi))))
                    snap.setFlag(QGraphicsItem.ItemIsMovable, True)
                    snap.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    snap.setPos(x, y)
                    snap.setRotation(rot)
                    align_name = str(item.get("align", "left")).lower()
                    idx = 0 if align_name == "left" else 1 if align_name == "center" else 2
                    self._set_text_alignment(snap, idx)
                    snap.setData(1, None)
                    self.scene.addItem(snap)
                elif t == "field":
                    placeholder = FIELD_PLACEHOLDERS.get(field_name, f"{{{field_name}}}")
                    text = self.sample_context.get(field_name, "") if self.sample_live else placeholder
                    snap = SnapTextItem(text)
                    font = QFont()
                    font.setPointSize(int(item.get("font_pt", 14)))
                    font.setBold(bool(item.get("bold", False)))
                    font.setFamily(item.get("font_family", self.default_font_family))
                    snap.setFont(font)
                    snap.setDefaultTextColor(Qt.black)
                    snap.setTextWidth(float(item.get("w_px", mm_to_px(self.mm_w * 0.6, self.dpi))))
                    snap.setFlag(QGraphicsItem.ItemIsMovable, True)
                    snap.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    snap.setPos(x, y)
                    snap.setRotation(rot)
                    align_name = str(item.get("align", "left")).lower()
                    idx = 0 if align_name == "left" else 1 if align_name == "center" else 2
                    self._set_text_alignment(snap, idx)
                    snap.setData(1, field_name)
                    self.scene.addItem(snap)
                elif t == "code128":
                    code = Code128GraphicsItem(
                        item.get("text", "KIT000001"),
                        height_px=int(item.get("bar_h_px", 160)),
                        module_px=int(item.get("module_px", 2)),
                        font_family=item.get("human_font_family", self.default_font_family),
                    )
                    code.setFlag(QGraphicsItem.ItemIsMovable, True)
                    code.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    code.setPos(x, y)
                    code.setRotation(rot)
                    code.setHumanTextVisible(bool(item.get("bar_text_visible", True)))
                    code.setHumanTextSize(int(item.get("bar_text_px", 12)))
                    self.scene.addItem(code)
        finally:
            self._loading_template = False
        self.template_path = path
        self._save_prefs()
        self.font_combo.blockSignals(True)
        self.font_combo.setCurrentFont(QFont(self.default_font_family))
        self.font_combo.blockSignals(False)
        self._apply_font_family_to_scene(self.default_font_family, trigger_save=False)

    def new_template(self):
        self.scene.clear()
        self._update_canvas(self.mm_w, self.mm_h, self.dpi)
        self.template_path = os.path.join("label_templates", "untitled.json")
        self._save_prefs()
        self._trigger_auto_save()

    def set_default_template(self):
        if not self.template_path or not os.path.exists(self.template_path):
            ret = QMessageBox.question(
                self,
                "Varsayılan Şablon",
                "Şablonu önce kaydetmek ister misiniz?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.Yes:
                self.save_template()
        if not self.template_path or not os.path.exists(self.template_path):
            QMessageBox.warning(self, "Varsayılan Şablon", "Lütfen önce şablonu kaydedin.")
            return
        settings = load_settings() or {}
        settings.setdefault("label_editor", {})["default_template"] = os.path.abspath(self.template_path)
        save_settings(settings)
        QMessageBox.information(self, "Varsayılan", "Varsayılan şablon güncellendi.")

    # ------------------------------------------------------------------
    # Printing / preview
    # ------------------------------------------------------------------
    def export_png(self):
        image = render_template_to_image(self._gather_template_data(), self.sample_context, self.default_font_family)
        dlg = _ImagePreviewDialog(image, self)
        dlg.exec_()

    def print_test(self):
        template_path = self.template_path
        if not template_path or not os.path.exists(template_path):
            template_path = get_default_template_path()
        if not template_path:
            QMessageBox.warning(self, "Etiket", "Şablon bulunamadı. Lütfen önce kaydedin.")
            return
        context = dict(self.sample_context)
        try:
            print_label_batch(template_path, [context])
        except Exception as exc:
            QMessageBox.warning(self, "Etiket", f"Yazdırma başarısız:\n{exc}")

    # ------------------------------------------------------------------
    # Sample data editing
    # ------------------------------------------------------------------
    def edit_sample_data(self):
        dlg = _SampleDataDialog(self.sample_context, self)
        if dlg.exec_() == QDialog.Accepted:
            self.sample_context.update(dlg.data())
            if not self.sample_file:
                path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Örnek Veri Kaydet",
                    os.path.join("label_templates", "sample_data.json"),
                    "JSON (*.json)",
                )
                if not path:
                    return
                self.sample_file = path
            try:
                os.makedirs(os.path.dirname(self.sample_file) or ".", exist_ok=True)
                with open(self.sample_file, "w", encoding="utf-8") as f:
                    json.dump(self.sample_context, f, ensure_ascii=False, indent=2)
                self._save_prefs()
            except Exception as exc:
                QMessageBox.warning(self, "Örnek Veri", f"Kaydedilemedi:\n{exc}")
            if self.chk_sample_live.isChecked():
                self._apply_sample_live(True)

    # ------------------------------------------------------------------
    # Auto save support
    # ------------------------------------------------------------------
    def _on_auto_save_toggled(self, checked: bool):
        self.auto_save_pref = bool(checked)
        self._save_prefs()
        if checked:
            self._trigger_auto_save()
        else:
            self._auto_save_timer.stop()

    def _trigger_auto_save(self):
        if not self.auto_save_pref:
            return
        if self._loading_template or self._suspend_auto_save:
            return
        if not self.template_path:
            return
        self._auto_save_timer.start()

    def _auto_save_template(self):
        if not self.auto_save_pref or self._loading_template or not self.template_path:
            return
        self._write_template_to_path(self.template_path, show_message=False)

    def _on_scene_changed(self, _regions):
        if not self.auto_save_pref or self._loading_template:
            return
        self._trigger_auto_save()

    # ------------------------------------------------------------------
    # Grid / snapping / zoom
    # ------------------------------------------------------------------
    def _on_snap_toggle(self, checked: bool):
        self.scene.snap_enabled = bool(checked)
        self._save_prefs()

    def _apply_grid(self, mm_val: float):
        try:
            px = int(max(1, mm_to_px(float(mm_val), self.dpi)))
        except Exception:
            px = 0
        self.scene.grid_px = px
        self.scene.update()
        self._save_prefs()

    def _zoom(self, factor: float):
        self.view.scale(factor, factor)

    # ------------------------------------------------------------------
    # Font management
    # ------------------------------------------------------------------
    def _apply_font_family_to_scene(self, family: str, trigger_save: bool = True):
        if not family:
            return
        self.default_font_family = family
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem) and not isinstance(item, Code128GraphicsItem):
                font = item.font()
                if font.family() != family:
                    font.setFamily(family)
                    item.setFont(font)
            elif isinstance(item, Code128GraphicsItem):
                item.setHumanFontFamily(family)
        self.scene.update()
        if trigger_save:
            self._trigger_auto_save()

    def _on_font_family_changed(self, font: QFont):
        if self._loading_template:
            return
        family = font.family()
        self._apply_font_family_to_scene(family)
        self._save_prefs()

    # ------------------------------------------------------------------
    # Printers
    # ------------------------------------------------------------------
    def _load_printer_settings(self):
        settings = load_settings() or {}
        printing = settings.get("printing", {})
        label_prefs = settings.get("label_editor", {})
        self.default_printer = printing.get("label_printer") or label_prefs.get("default_printer")
        self.default_printer_is_thermal = bool(
            printing.get("label_is_thermal", label_prefs.get("default_printer_is_thermal", False))
        )
        self.lbl_printer_name.setText(self.default_printer or "—")

    def _open_printer_settings(self):
        from ui.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self, initial_tab="printers")
        if dlg.exec_():
            self._load_printer_settings()
            self._load_prefs()
            self._apply_preferences()


    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def _load_prefs(self):
        try:
            settings = load_settings()
        except Exception:
            settings = {}
        prefs = settings.get("label_editor", {})
        self.mm_w = float(prefs.get("mm_w", self.mm_w))
        self.mm_h = float(prefs.get("mm_h", self.mm_h))
        self.dpi = int(prefs.get("dpi", self.dpi))
        self.template_path = prefs.get("last_template", self.template_path)
        self.default_template = prefs.get("default_template")
        self._pref_snap = bool(prefs.get("snap", False))
        self._pref_grid_mm = float(prefs.get("grid_mm", 2.0))
        self.sample_file = prefs.get("sample_file")
        if self.sample_file and os.path.exists(self.sample_file):
            try:
                with open(self.sample_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.sample_context.update({k: str(data.get(k, v)) for k, v in self.sample_context.items()})
            except Exception:
                pass
        self.default_printer = prefs.get("default_printer")
        self.default_printer_is_thermal = bool(prefs.get("default_printer_is_thermal", False))
        self.rotate_print_pref = bool(prefs.get("rotate_print", False))
        self.auto_save_pref = bool(prefs.get("auto_save", False))
        self.default_font_family = prefs.get("font_family", self.default_font_family)

        printing = settings.get("printing", {})
        if printing.get("label_printer"):
            self.default_printer = printing.get("label_printer")
            self.default_printer_is_thermal = bool(printing.get("label_is_thermal", self.default_printer_is_thermal))

    def _save_prefs(self):
        try:
            settings = load_settings()
        except Exception:
            settings = {}
        prefs = settings.setdefault("label_editor", {})
        prefs.update(
            {
                "mm_w": float(self.mm_w),
                "mm_h": float(self.mm_h),
                "dpi": int(self.dpi),
                "last_template": self.template_path,
                "snap": bool(self.chk_snap.isChecked()) if hasattr(self, "chk_snap") else self._pref_snap,
                "grid_mm": float(self.spin_grid.value()) if hasattr(self, "spin_grid") else self._pref_grid_mm,
                "default_template": self.default_template,
                "sample_file": self.sample_file,
                "default_printer": self.default_printer,
                "default_printer_is_thermal": self.default_printer_is_thermal,
                "rotate_print": bool(self.chk_rotate_print.isChecked()) if hasattr(self, "chk_rotate_print") else self.rotate_print_pref,
                "auto_save": bool(self.chk_auto_save.isChecked()) if hasattr(self, "chk_auto_save") else self.auto_save_pref,
                "font_family": self.default_font_family,
            }
        )
        printing = settings.setdefault("printing", {})
        printing["label_printer"] = self.default_printer
        printing["label_is_thermal"] = self.default_printer_is_thermal
        save_settings(settings)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _get_text_alignment_index(self, text_item: QGraphicsTextItem) -> int:
        option = text_item.document().defaultTextOption()
        align = option.alignment()
        if align & Qt.AlignHCenter:
            return 1
        if align & Qt.AlignRight:
            return 2
        return 0

    def _set_text_alignment(self, text_item: QGraphicsTextItem, index: int):
        option = QTextOption(text_item.document().defaultTextOption())
        if index == 1:
            option.setAlignment(Qt.AlignHCenter)
        elif index == 2:
            option.setAlignment(Qt.AlignRight)
        else:
            option.setAlignment(Qt.AlignLeft)
        text_item.document().setDefaultTextOption(option)

    def _on_scene_change_noop(self):
        pass

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self.mm_w = float(self.sp_w.value())
        self.mm_h = float(self.sp_h.value())
        self.dpi = int(self.sp_dpi.value())
        self._save_prefs()
        super().closeEvent(event)
