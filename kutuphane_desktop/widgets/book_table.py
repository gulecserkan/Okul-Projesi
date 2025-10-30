from datetime import datetime, date, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QTableView, QMenu, QHBoxLayout, QComboBox
)
from PyQt5.QtCore import (
    Qt, QSortFilterProxyModel, QAbstractTableModel, QDate, QModelIndex, QPoint
)
from PyQt5.QtGui import QColor, QFont
from core.config import SETTINGS_FILE, get_api_base_url, load_settings
from core.utils import api_request, format_date
import json, os


HEADERS = [
    "Ad", "Soyad", "No", "Sınıf",
    "Kitap", "Yazar", "Kategori", "ISBN",
    "Barkod", "Raf",
    "Ödünç Tarihi", "İade Tarihi", "Teslim Tarihi",
    "Durum", "Ceza"
]


def safe_date(value):
    return format_date(value)


class LoanTableModel(QAbstractTableModel):
    def __init__(self, data, headers, raw_due_dates=None):
        super().__init__()
        self._data = data
        self._headers = headers
        self.selected_row = None   # seçili satır
        self._row_meta = raw_due_dates or []

    def update_data(self, data, raw_due_dates=None):
        self.beginResetModel()
        self._data = data
        self._row_meta = raw_due_dates or []
        self.selected_row = None
        self.endResetModel()

    def set_selected_row(self, row):
        # Hatalı indeksler çökermesin diye kapsam kontrolü
        row_count = self.rowCount()
        if row is not None and (row < 0 or row >= row_count):
            row = None

        old_row = self.selected_row
        if old_row is not None and (old_row < 0 or old_row >= row_count):
            old_row = None

        self.selected_row = row

        # Önceki seçimi temizle
        if old_row is not None:
            top_left = self.index(old_row, 0)
            bottom_right = self.index(old_row, self.columnCount() - 1)
            if top_left.isValid() and bottom_right.isValid():
                self.dataChanged.emit(top_left, bottom_right, [Qt.FontRole])

        # Yeni seçimi işaretle
        if row is not None:
            top_left = self.index(row, 0)
            bottom_right = self.index(row, self.columnCount() - 1)
            if top_left.isValid() and bottom_right.isValid():
                self.dataChanged.emit(top_left, bottom_right, [Qt.FontRole])

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role):
        if not index.isValid():
            return None
        value = self._data[index.row()][index.column()]

        if role == Qt.DisplayRole:
            return value

        if role == Qt.BackgroundRole:
            try:
                meta = self._get_row_meta(index.row())
                status = (meta.get("status") or "").lower()
                if status == "gecikmis":
                    return QColor(194, 57, 41)  # koyu kırmızı
                if meta.get("grace_alert"):
                    return QColor(255, 182, 193)  # pembe ton

                due_date = self.get_due_qdate(index.row())
                today = QDate.currentDate()
                if due_date.isValid():
                    if due_date < today:
                        return QColor(255, 100, 100)
                    elif due_date == today:
                        return QColor(255, 165, 0)
                    elif today.daysTo(due_date) <= 3:
                        return QColor(255, 255, 150)
                    else:
                        return QColor(200, 255, 200)
            except Exception:
                return None

        if role == Qt.FontRole and self.selected_row == index.row():
            font = QFont()
            font.setBold(True)
            #font.setItalic(True)
            font.setPointSize(11)
            return font
        return None
    
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
            return str(section)
        return None

    def get_due_qdate(self, row):
        meta = self._get_row_meta(row)
        if not meta:
            return QDate()
        effective = meta.get("effective_due_iso")
        raw_due = meta.get("due_iso")
        if effective:
            return self._parse_due_date(effective)
        if raw_due:
            return self._parse_due_date(raw_due)
        return QDate()

    def _parse_due_date(self, value):
        if value in (None, ""):
            return QDate()
        if isinstance(value, QDate):
            return value
        if isinstance(value, datetime):
            return QDate(value.year, value.month, value.day)
        if isinstance(value, date):
            return QDate(value.year, value.month, value.day)
        text = str(value).strip()
        if not text:
            return QDate()
        candidate = text.replace("Z", "+00:00")
        dt = None
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            try:
                dt = datetime.strptime(text[:10], "%Y-%m-%d")
            except ValueError:
                return QDate()
        return QDate(dt.year, dt.month, dt.day)

    def _get_row_meta(self, row):
        if row < 0 or row >= len(self._row_meta):
            return {}
        return self._row_meta[row] or {}

    def get_row_meta(self, row):
        return self._get_row_meta(row)


class LoanSortFilterProxyModel(QSortFilterProxyModel):
    """Tarih kolonlarını doğru sıralamak ve filtrelemek için özelleştirilmiş proxy"""

    def __init__(self):
        super().__init__()
        self._status_filter = "all"

    def set_status_filter(self, value: str):
        self._status_filter = value or "all"
        self.invalidateFilter()

    def lessThan(self, left, right):
        column = left.column()
        if self.sourceModel().headerData(column, Qt.Horizontal, Qt.DisplayRole) == "İade Tarihi":
            source = self.sourceModel()
            get_due = getattr(source, "get_due_qdate", None)
            if callable(get_due):
                left_date = get_due(left.row())
                right_date = get_due(right.row())
                if isinstance(left_date, QDate) and isinstance(right_date, QDate):
                    if left_date.isValid() and right_date.isValid():
                        return left_date < right_date
        return super().lessThan(left, right)
    
    # 🔹 Başlıkları doğrudan source model'den al
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.sourceModel().headerData(section, orientation, role)
        return super().headerData(section, orientation, role)

    def filterAcceptsRow(self, source_row, source_parent):
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._status_filter == "all":
            return True

        model = self.sourceModel()
        meta_getter = getattr(model, "get_row_meta", None)
        if not callable(meta_getter):
            return True
        meta = meta_getter(source_row) or {}

        if self._status_filter == "overdue":
            return bool(meta.get("is_overdue"))
        if self._status_filter == "grace":
            return bool(meta.get("grace_alert")) and not meta.get("is_overdue")
        if self._status_filter == "upcoming":
            return bool(meta.get("due_soon")) and not meta.get("is_overdue") and not meta.get("grace_alert")

        return True
    
    def _parse_due_date(self, value):
        if value in (None, ""):
            return QDate()  # invalid
        if isinstance(value, QDate):
            return value
        if isinstance(value, datetime):
            return QDate(value.year, value.month, value.day)
        if isinstance(value, date):
            return QDate(value.year, value.month, value.day)
        text = str(value).strip()
        if not text:
            return QDate()
        candidate = text.replace("Z", "+00:00")
        dt = None
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            try:
                dt = datetime.strptime(text[:10], "%Y-%m-%d")
            except ValueError:
                return QDate()
        return QDate(dt.year, dt.month, dt.day)


class BookTable(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # Arama + filtre satırı
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Arama yapın...")
        top_row.addWidget(self.search_box, 1)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Tüm kayıtlar", "all")
        self.filter_combo.addItem("Gecikenler", "overdue")
        self.filter_combo.addItem("Tolerans içindekiler", "grace")
        self.filter_combo.addItem("Yaklaşan iadeler", "upcoming")
        self.filter_combo.setMinimumWidth(160)
        top_row.addWidget(self.filter_combo, 0)
        layout.addLayout(top_row)

        # Veriyi yükle
        data, row_meta = self.fetch_data()

        # Tablo
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)

        # Model
        self.model = LoanTableModel(data, HEADERS, row_meta)

        # Proxy
        self.proxy = LoanSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)

        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(HEADERS.index("İade Tarihi"), Qt.AscendingOrder)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Stil: seçili satır rengini kapat
        self.table.setStyleSheet("""
            QTableView::item:selected {
                background: transparent;
                color: black;
            }
        """)

        # Seçim değiştiğinde modeli bilgilendir
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

        layout.addWidget(self.table)
        self.setLayout(layout)

        # Sağ tık menü → header
        header = self.table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)

        # Ayarları yükle
        self.hidden_columns = []
        self.saved_settings = self.load_settings()
        self.hidden_columns = self.saved_settings.get("hidden_columns", [])
        self.apply_settings()

        # Arama bağlama
        self.search_box.textChanged.connect(self.apply_filter)
        self.filter_combo.currentIndexChanged.connect(lambda _: self.apply_filter())
        self.apply_filter()

    def reload_data(self):
        data, row_meta = self.fetch_data()
        self.model.update_data(data, row_meta)
        self.apply_filter(self.search_box.text())

    def on_selection_changed(self, selected, deselected):
        try:
            if selected.indexes():
                proxy_index = selected.indexes()[0]
                if not proxy_index.isValid():
                    self.model.set_selected_row(None)
                    return
                source_index = self.proxy.mapToSource(proxy_index)
                if not source_index.isValid():
                    self.model.set_selected_row(None)
                    return
                row = source_index.row()
                if row < 0 or row >= self.model.rowCount():
                    self.model.set_selected_row(None)
                    return
                self.model.set_selected_row(row)
            else:
                self.model.set_selected_row(None)
        except Exception as e:
            print("Selection error:", e)
            self.model.set_selected_row(None)

    def show_header_menu(self, pos: QPoint):
        """Başlıkta sağ tık menüsü ile kolon gizle/göster"""
        header = self.table.horizontalHeader()
        menu = QMenu(self)

        for col, title in enumerate(HEADERS):
            action = menu.addAction(title)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(col))
            action.toggled.connect(lambda checked, c=col: self.toggle_column(c, checked))

        menu.exec_(header.mapToGlobal(pos))

    def toggle_column(self, col, checked):
        self.table.setColumnHidden(col, not checked)
        if not checked and col not in self.hidden_columns:
            self.hidden_columns.append(col)
        elif checked and col in self.hidden_columns:
            self.hidden_columns.remove(col)
        self.save_settings()

    def fetch_data(self):
        def _load_status(status):
            resp = api_request("GET", self._api_url(f"oduncler/?durum={status}"))
            if resp.status_code != 200:
                return []
            try:
                return resp.json() or []
            except ValueError:
                return []

        loans = []
        for status in ("oduncte", "gecikmis"):
            loans.extend(_load_status(status))

        settings = load_settings() or {}
        policy = settings.get("loans", {}) or {}
        grace_days = int(policy.get("delay_grace_days") or 0)
        shift_weekend = bool(policy.get("shift_weekend"))

        def _parse_datetime(value):
            if not value:
                return None
            text = str(value).strip()
            if not text:
                return None
            candidate = text.replace("Z", "+00:00")
            dt = None
            try:
                dt = datetime.fromisoformat(candidate)
            except ValueError:
                try:
                    dt = datetime.strptime(text[:10], "%Y-%m-%d")
                except ValueError:
                    return None
            if dt.tzinfo:
                return dt.astimezone()
            return dt

        def _shift_weekend(dt):
            if not dt:
                return None
            result = dt
            while shift_weekend and result.weekday() >= 5:
                result += timedelta(days=1)
            return result

        today = datetime.now().date()

        data = []
        row_meta = []
        for loan in loans:
            ogrenci = loan.get("ogrenci", {})
            sinif = ogrenci.get("sinif", {}) or {}
            nusha = loan.get("kitap_nusha", {})
            kitap = nusha.get("kitap", {})
            kategori = kitap.get("kategori", {}) or {}
            yazar = kitap.get("yazar", {}) or {}

            odunc_tarihi = loan.get("odunc_tarihi")
            iade_tarihi = loan.get("iade_tarihi")
            teslim_tarihi = loan.get("teslim_tarihi")
            durum = (loan.get("durum") or "").lower()

            due_dt = _parse_datetime(iade_tarihi)
            effective_due = due_dt
            if due_dt and grace_days:
                effective_due = due_dt + timedelta(days=grace_days)
            effective_due = _shift_weekend(effective_due)

            grace_alert = False
            if due_dt:
                original_date = due_dt.date()
                effective_date = effective_due.date() if effective_due else original_date
                if original_date < today <= effective_date and durum != "gecikmis":
                    grace_alert = True

            is_overdue = False
            if effective_due and effective_due.date() < today:
                is_overdue = True
            if durum == "gecikmis":
                is_overdue = True

            due_soon = False
            if not is_overdue and not grace_alert and effective_due:
                days_to = (effective_due.date() - today).days
                if 0 <= days_to <= 3:
                    due_soon = True

            row = [
                ogrenci.get("ad", ""),
                ogrenci.get("soyad", ""),
                ogrenci.get("ogrenci_no", ""),
                sinif.get("ad", ""),
                kitap.get("baslik", ""),
                yazar.get("ad_soyad", ""),
                kategori.get("ad", ""),
                kitap.get("isbn", ""),
                nusha.get("barkod", ""),
                nusha.get("raf_kodu", ""),
                safe_date(odunc_tarihi),
                safe_date(iade_tarihi),
                safe_date(teslim_tarihi),
                loan.get("durum", ""),
                loan.get("gecikme_cezasi", ""),
            ]
            data.append(row)
            row_meta.append(
                {
                    "due_iso": iade_tarihi,
                    "effective_due_iso": effective_due.isoformat() if effective_due else None,
                    "status": durum,
                    "grace_alert": grace_alert,
                    "is_overdue": is_overdue,
                    "due_soon": due_soon,
                }
            )

        return data, row_meta

    def apply_filter(self, text=None):
        if text is None:
            text = self.search_box.text()
        status = self.filter_combo.currentData()
        self.proxy.set_status_filter(status)
        self.proxy.setFilterFixedString(text)

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except Exception:
            settings = {}

        # Eski anahtarları temizle (geriye dönük temizlik)
        settings.pop("hidden_columns", None)
        settings.pop("column_widths", None)

        settings["book_table"] = {
            "hidden_columns": self.hidden_columns,
            "column_widths": [self.table.columnWidth(i) for i in range(len(HEADERS))]
        }

        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                cfg = data.get("book_table")
                if not cfg and "hidden_columns" in data and "column_widths" in data:
                    cfg = {
                        "hidden_columns": data.get("hidden_columns", []),
                        "column_widths": data.get("column_widths", [])
                    }
                return cfg or {"hidden_columns": [], "column_widths": []}
            except Exception:
                return {"hidden_columns": [], "column_widths": []}
        return {"hidden_columns": [], "column_widths": []}

    def apply_settings(self):
        # Sütun gizleme
        for col in self.hidden_columns:
            self.table.setColumnHidden(col, True)

        # Sütun genişlikleri
        widths = self.saved_settings.get("column_widths", [])
        for i, w in enumerate(widths):
            if w > 0:
                self.table.setColumnWidth(i, w)

    def get_settings(self):
        return {
            "hidden_columns": self.hidden_columns,
            "column_widths": [self.table.columnWidth(i) for i in range(len(HEADERS))]
        }

    def _api_url(self, path):
        base = get_api_base_url().rstrip('/')
        return f"{base}/{path.lstrip('/')}"
