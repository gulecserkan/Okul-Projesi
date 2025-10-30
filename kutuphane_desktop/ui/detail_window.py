import json, os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView,
    QSizePolicy, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QIcon
from core.config import SETTINGS_FILE
from core.utils import format_date

ICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "icons"))
BOOK_TAB_ICON = os.path.join(ICON_DIR, "tab_book.svg")
COPIES_TAB_ICON = os.path.join(ICON_DIR, "tab_copies.svg")
STUDENT_TAB_ICON = os.path.join(ICON_DIR, "tab_student.svg")

class DetailWindow(QDialog):
    def __init__(
        self,
        title,
        headers,
        rows,
        settings_key="detail",
        other_copies=None,
        main_tab_title=None,
        main_tab_icon=None,
        create_main_tab=True
    ):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(400, 200, 800, 450)

        self.settings_key = settings_key
        self.other_copies = other_copies or []  # diğer nüshalar listesi (dict listesi)
        self.main_tab_title = main_tab_title or "Bu Nüsha Geçmişi"
        self.main_tab_icon = main_tab_icon
        self.create_main_tab = create_main_tab

        # === Ana layout ===
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # === Sekme yapısı ===
        self.tabs = QTabWidget()
        self.tab_current = None
        if create_main_tab:
            self.tab_current = self.create_table_tab("Bu Nüsha Geçmişi", headers, rows)
            icon = self._load_icon(self.main_tab_icon)
            if icon:
                self.tabs.addTab(self.tab_current, icon, self.main_tab_title)
            else:
                self.tabs.addTab(self.tab_current, self.main_tab_title)

        # Eğer diğer nüshalar varsa, ikinci sekme
        if create_main_tab and self.other_copies:
            copy_headers = ["Barkod", "Raf", "Durum", "Son İşlem"]
            self.tab_copies = self.create_table_tab("Diğer Nüshalar", copy_headers, [
                [
                    c.get("barkod", ""),
                    c.get("raf_kodu", ""),
                    c.get("durum", ""),
                    c.get("son_islem", "")
                ]
                for c in self.other_copies
            ])
            copies_icon = self._load_icon(COPIES_TAB_ICON)
            if copies_icon:
                self.tabs.addTab(self.tab_copies, copies_icon, "Diğer Nüshalar")
            else:
                self.tabs.addTab(self.tab_copies, "Diğer Nüshalar")

        layout.addWidget(self.tabs)

        # === Kapat Butonu ===
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

        self.setLayout(layout)
        self.apply_settings()

    @classmethod
    def single_tab(cls, title, headers, rows, settings_key="detail", icon_path=None, tab_title=None):
        dlg = cls(
            title,
            headers=[],
            rows=[],
            settings_key=settings_key,
            other_copies=None,
            main_tab_title="",
            main_tab_icon=None,
            create_main_tab=False
        )
        dlg.add_tab(tab_title or title, headers, rows, icon_path=icon_path)
        dlg.apply_settings()
        dlg.tabs.setCurrentIndex(dlg.tabs.count() - 1)
        return dlg

    # ============================================================
    # Yardımcı metotlar
    # ============================================================
    def create_table_tab(self, title, headers, rows):
        """Sekme içinde tablo oluşturur."""
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

        # Veri doldurma
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else "")
                table.setItem(r, c, item)

            # 🔹 Durum bazlı satır renklendirme
            try:
                durum_index = [h.lower() for h in headers].index("durum")
                durum = str(row[durum_index]).lower()
                color = None
                if "teslim" in durum:
                    color = QColor(200, 255, 200)
                elif "odunc" in durum:
                    color = QColor(255, 200, 200)
                elif "kayip" in durum or "hasar" in durum:
                    color = QColor(215, 215, 215)
                if color:
                    for cc in range(len(headers)):
                        it = table.item(r, cc)
                        if not it:
                            it = QTableWidgetItem("")
                            table.setItem(r, cc, it)
                        it.setBackground(color)
            except ValueError:
                pass

        table.itemSelectionChanged.connect(lambda: self.on_selection_changed(table))
        return table

    def on_selection_changed(self, table):
        selected = table.selectionModel().selectedRows()
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if not item:
                    continue
                font = QFont(item.font())
                font.setBold(any(r == idx.row() for idx in selected))
                item.setFont(font)

    # ============================================================
    # Ayar kaydetme / yükleme
    # ============================================================
    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self):
        settings = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                try:
                    settings = json.load(f)
                except Exception:
                    settings = {}

        out = {}

        if hasattr(self, "tabs"):
            # Her sekme için ayrı sütun genişlikleri
            for i in range(self.tabs.count()):
                key = f"{self.settings_key}_tab{i}"
                tab_widget = self.tabs.widget(i)
                # Sekmedeki tabloyu bul (sekme doğrudan QTableWidget olabilir
                # veya içinde layout ile gömülü olabilir)
                table = tab_widget if isinstance(tab_widget, QTableWidget) else tab_widget.findChild(QTableWidget)
                widths = [table.columnWidth(x) for x in range(table.columnCount())] if table else []
                out[key] = widths
        else:
            # Sekmesiz tek tablo modu (eski yapı ile uyum)
            out[f"{self.settings_key}_single"] = [
                self.table.columnWidth(x) for x in range(self.table.columnCount())
            ]

        settings[self.settings_key] = out
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)


    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                try:
                    return json.load(f)
                except:
                    return {}
        return {}

    def apply_settings(self):
        cfg_all = self.load_settings().get(self.settings_key, {})

        if hasattr(self, "tabs"):
            for i in range(self.tabs.count()):
                key = f"{self.settings_key}_tab{i}"
                widths = cfg_all.get(key, [])
                tab_widget = self.tabs.widget(i)
                table = tab_widget if isinstance(tab_widget, QTableWidget) else tab_widget.findChild(QTableWidget)
                if not table:
                    continue
                for j, w in enumerate(widths):
                    if w > 0:
                        table.setColumnWidth(j, w)
        else:
            widths = cfg_all.get(f"{self.settings_key}_single", [])
            for j, w in enumerate(widths):
                if w > 0:
                    self.table.setColumnWidth(j, w)


    # sınıf içinde (örneğin apply_settings'in hemen altına ekle)
    def add_tab(self, title, headers, rows, icon_path=None):
        """Yeni bir sekme ekler (örneğin Tüm Nüshalar sekmesi)."""
        # Eğer daha önce sekme yoksa, tab widget'ı oluştur
        if not hasattr(self, "tabs"):
            self.tabs = QTabWidget()
            # Mevcut tabloyu (self.table) ana sekme olarak ekle
            tab_main = QWidget()
            vbox = QVBoxLayout(tab_main)
            vbox.addWidget(self.table)
            self.tabs.addTab(tab_main, "Geçmiş")
            # Kapat butonunu sekmelerin altına taşı
            self.layout().insertWidget(0, self.tabs)

        # Yeni tablo
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                display_val = self._format_value(headers[c], val)
                table.setItem(r, c, QTableWidgetItem(display_val))

            # Renklendirme (isteğe bağlı)
            durum_index = None
            for i, h in enumerate(headers):
                if h.lower() == "durum":
                    durum_index = i
                    break
            if durum_index is not None:
                durum = str(row[durum_index]).lower()
                for cc in range(len(headers)):
                    item = table.item(r, cc)
                    if item is None:
                        continue
                    if "odunc" in durum:
                        item.setBackground(QColor(255, 230, 230))  # açık pembe
                    elif "teslim" in durum or "mevcut" in durum:
                        item.setBackground(QColor(220, 255, 220))  # açık yeşil
                    elif "kayip" in durum or "hasar" in durum:
                        item.setBackground(QColor(215, 215, 215))  # gri

        # Tablo ayarları
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)

        # Sekme oluştur
        tab = QWidget()
        vbox = QVBoxLayout(tab)
        vbox.addWidget(table)
        icon = self._load_icon(icon_path)
        if icon:
            self.tabs.addTab(tab, icon, title)
        else:
            self.tabs.addTab(tab, title)

    def _load_icon(self, path):
        if path and os.path.exists(path):
            return QIcon(path)
        return None

    def _format_value(self, header, value):
        """Sekme tablosu hücre değerini kullanıcı dostu hale getirir."""
        key = self._normalize_header(header)
        if key == "son_islem":
            return format_date(value)
        return "" if value is None else str(value)

    def _normalize_header(self, header):
        text = (header or "").strip().lower()
        text = text.replace("i̇", "i")  # Türkçe büyük İ -> i̇ uzaklaştır
        replacements = {
            "ı": "i",
            "ş": "s",
            "ğ": "g",
            "ö": "o",
            "ü": "u",
            "ç": "c",
        }
        for src, target in replacements.items():
            text = text.replace(src, target)
        text = text.replace(" ", "_")
        return text
