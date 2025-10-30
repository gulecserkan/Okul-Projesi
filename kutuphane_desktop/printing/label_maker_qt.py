from PyQt5.QtGui import QImage, QPainter, QColor, QFont, QTransform
from PyQt5.QtCore import Qt, QRect

# Label size (mm)
MM_WIDTH = 57
MM_HEIGHT = 40


def _mm_to_px(mm, dpi):
    return int(round((mm / 25.4) * dpi))


# Code 128 patterns: index 0..106 -> widths string e.g., '212222'
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


def _code128_encode_b(text: str):
    codes = [104]  # Start Code B
    for ch in text:
        o = ord(ch)
        if 32 <= o <= 126:
            codes.append(o - 32)
        else:
            # unsupported char: replace with space
            codes.append(0)  # space
    checksum = 104
    for i, code in enumerate(codes[1:], start=1):
        checksum += code * i
    checksum %= 103
    codes.append(checksum)
    codes.append(106)  # Stop
    return codes


def _draw_code128(p: QPainter, x: int, y: int, height: int, module_w: int, codes):
    cur_x = x
    for idx, val in enumerate(codes):
        pattern = CODE128_PATTERNS[val]
        # pattern digits alternate bar/space widths, starting with bar
        black = True
        for d in pattern:
            w = int(d) * module_w
            if black:
                p.fillRect(QRect(cur_x, y - height, w, height), QColor(0, 0, 0))
            cur_x += w
            black = not black
        # After stop (106) pattern '2331112', add one final 2-module bar per spec
        if val == 106:
            w = 2 * module_w
            p.fillRect(QRect(cur_x, y - height, w, height), QColor(0, 0, 0))
            cur_x += w


def render_label_png(path: str, title: str, author: str, category: str,
                     barcode_text: str, dpi: int = 300):
    w = _mm_to_px(MM_WIDTH, dpi)
    h = _mm_to_px(MM_HEIGHT, dpi)
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor(255, 255, 255))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Margins
    m = int(0.04 * w)
    content_rect = QRect(m, m, w - 2 * m - _mm_to_px(10, dpi), h - 2 * m)
    barcode_rect = QRect(content_rect.right() + int(0.02 * w), m, w - m - (content_rect.right() + int(0.02 * w)), h - 2 * m)

    # Fonts (base ~ 8pt scaled)
    def font_pt(mult):
        base = 8
        return int(base * mult)

    # Header (2x)
    f = QFont()
    f.setPointSize(font_pt(2))
    f.setBold(True)
    painter.setFont(f)
    header = "S.B.Daniş Tunalıgil MTAL. Kütüphanesi"
    painter.drawText(content_rect, Qt.AlignTop | Qt.AlignLeft, header)

    # Title (4x)
    f = QFont()
    f.setPointSize(font_pt(4))
    f.setBold(True)
    painter.setFont(f)
    r = QRect(content_rect.left(), content_rect.top() + int(0.22 * h), content_rect.width(), int(0.28 * h))
    painter.drawText(r, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, title)

    # Author (2x)
    f = QFont()
    f.setPointSize(font_pt(2))
    painter.setFont(f)
    r2 = QRect(content_rect.left(), r.bottom() + int(0.02 * h), content_rect.width(), int(0.18 * h))
    painter.drawText(r2, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, author)

    # Category (2x)
    r3 = QRect(content_rect.left(), r2.bottom() + int(0.01 * h), content_rect.width(), int(0.14 * h))
    painter.drawText(r3, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, category)

    # Barcode text (4x)
    f = QFont()
    f.setPointSize(font_pt(4))
    f.setBold(True)
    painter.setFont(f)
    r4 = QRect(content_rect.left(), r3.bottom() + int(0.02 * h), content_rect.width(), int(0.16 * h))
    painter.drawText(r4, Qt.AlignLeft | Qt.AlignVCenter, barcode_text)

    # Code 128 (Set B) on right, rotated 90 degrees (upwards)
    codes = _code128_encode_b(barcode_text)
    # Draw into a small image then rotate
    bw = barcode_rect.width()
    bh = barcode_rect.height()
    if bw < 10:
        bw = _mm_to_px(10, dpi)
    tmp = QImage(bw, bh, QImage.Format_ARGB32)
    tmp.fill(QColor(255, 255, 255))
    p2 = QPainter(tmp)
    p2.setRenderHint(QPainter.Antialiasing, False)
    # Compute total modules to fit width
    total_modules = 0
    for val in codes:
        total_modules += sum(int(d) for d in CODE128_PATTERNS[val])
        if val == 106:
            total_modules += 2  # final bar
    module_w = max(1, int(bw / (total_modules + 20)))
    bar_height = int(bh * 0.9)
    used_w = total_modules * module_w
    start_x = int((bw - used_w) / 2)
    base_y = int(bh * 0.95)
    _draw_code128(p2, start_x, base_y, bar_height, module_w, codes)
    p2.end()

    rot = QTransform()
    rot.rotate(-90)
    tmp_rot = tmp.transformed(rot)
    # place at right-bottom upwards
    bx = barcode_rect.left() + int((barcode_rect.width() - tmp_rot.width()) / 2)
    by = barcode_rect.bottom() - tmp_rot.height()
    painter.drawImage(bx, by, tmp_rot)

    painter.end()
    img.setDotsPerMeterX(int(dpi / 25.4 * 1000))
    img.setDotsPerMeterY(int(dpi / 25.4 * 1000))
    img.save(path, 'PNG')
