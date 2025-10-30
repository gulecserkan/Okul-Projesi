import re

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QFormLayout, QMessageBox, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt

from core.config import get_api_base_url
from api import books
from core.utils import api_request, response_error_message


class EntityManagerDialog(QDialog):
    """
    Basit CRUD ekranı için temel diyalog.
    """

    def __init__(self, title, endpoint, fields, parent=None):
        """
        :param title: Pencere başlığı
        :param endpoint: REST endpoint (ör: 'yazarlar/')
        :param fields: [{'name': 'ad_soyad', 'label': 'Ad Soyad'}]
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(620, 400)

        self.endpoint = endpoint.rstrip('/') + '/'
        self.fields = fields
        self.current_id = None

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Liste
        header_label = self.fields[0]["label"] if self.fields else "Ad"
        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels([header_label])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setStretchLastSection(True)
        header.setSortIndicator(0, Qt.AscendingOrder)
        self.table.setSortingEnabled(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.table, 2)

        # Form
        right = QVBoxLayout()
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.inputs = {}
        for field in self.fields:
            line = QLineEdit()
            form.addRow(field["label"], line)
            self.inputs[field["name"]] = line
        right.addWidget(form_widget)
        right.addStretch(1)

        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("Yeni")
        self.btn_new.setObjectName("DialogNeutralButton")
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setObjectName("DialogPositiveButton")
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setObjectName("DialogNegativeButton")
        self.btn_close = QPushButton("Kapat")
        self.btn_close.setAutoDefault(False)
        self.btn_close.setDefault(False)

        # Tüm butonlarda default/autoDefault kapalı
        for _b in (self.btn_new, self.btn_save, self.btn_delete, self.btn_close):
            _b.setAutoDefault(False)
            _b.setDefault(False)

        self.btn_new.clicked.connect(self.reset_form)
        self.btn_save.clicked.connect(self.save_record)
        self.btn_delete.clicked.connect(self.delete_record)
        # Sade: tek tıkta doğrudan accept
        self.btn_close.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_close)

        right.addLayout(btn_row)
        layout.addLayout(right, 3)

        self.setLayout(layout)
        try:
            self.setModal(True)
        except Exception:
            pass
        self.load_data()

    # Helpers
    def _api_url(self, path=""):
        base = get_api_base_url().rstrip('/')
        if path:
            path = path.lstrip('/')
            return f"{base}/{self.endpoint}{path}"
        return f"{base}/{self.endpoint}"

    def load_data(self):
        self.table.setSortingEnabled(False)
        resp = api_request("GET", self._api_url())
        if resp.status_code != 200:
            detail = response_error_message(resp, "Kayıtlar alınamadı")
            QMessageBox.warning(self, "Hata", detail)
            self.table.setSortingEnabled(True)
            return
        try:
            data = resp.json()
        except ValueError:
            QMessageBox.warning(self, "Hata", "Sunucudan geçersiz yanıt alındı.")
            self.table.setSortingEnabled(True)
            return
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            display = self._display_text(item)
            cell = QTableWidgetItem(display)
            cell.setData(Qt.UserRole, item)
            self.table.setItem(row, 0, cell)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    # Sade kapatma akışına geçildi – ekstra eventFilter/queued-close ve debug logları kaldırıldı

    def _display_text(self, item):
        # İlk alanı göster
        name_field = self.fields[0]["name"]
        value = str(item.get(name_field, "")) or ""
        if not value:
            return "(İsimsiz)"
        return self._normalize_text(value)

    def reset_form(self):
        self.current_id = None
        for widget in self.inputs.values():
            widget.clear()
        self.table.clearSelection()

    def on_row_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        data = selected[0].data(Qt.UserRole)
        self.current_id = data.get("id")
        for field in self.fields:
            name = field["name"]
            self.inputs[name].setText(str(data.get(name, "") or ""))

    def _collect_data(self):
        payload = {}
        for field in self.fields:
            value = self.inputs[field["name"]].text().strip()
            if not value:
                QMessageBox.warning(self, "Uyarı", f"{field['label']} alanı boş olamaz.")
                return None
            payload[field["name"]] = self._normalize_text(value)
        return payload

    def save_record(self):
        data = self._collect_data()
        if data is None:
            return

        primary_field = self.fields[0]["name"] if self.fields else None
        if primary_field:
            existing = self._normalized_existing_values(primary_field, exclude_id=self.current_id)
            candidate = data.get(primary_field, "")
            if candidate and candidate in existing:
                QMessageBox.warning(self, "Uyarı", f"Aynı {self.fields[0]['label']} değeri zaten kayıtlı.")
                return

        if self.current_id:
            url = self._api_url(str(self.current_id) + "/")
            resp = api_request("PUT", url, json=data)
            action = "güncelleme"
        else:
            url = self._api_url()
            resp = api_request("POST", url, json=data)
            action = "ekleme"

        if resp.status_code in (200, 201):
            QMessageBox.information(self, "Başarılı", f"Kayıt {action} işlemi tamamlandı.")
            self.load_data()
            self.reset_form()
        else:
            detail = safe_error_text(resp)
            header = response_error_message(resp, f"Kayıt {action} işlemi başarısız")
            QMessageBox.warning(self, "Hata", f"{header}.\n\nDetay: {detail}")

    def delete_record(self):
        if not self.current_id:
            QMessageBox.warning(self, "Uyarı", "Silinecek kayıt seçmediniz.")
            return
        if not self._confirm_delete():
            return
        url = self._api_url(str(self.current_id) + "/")
        resp = api_request("DELETE", url)
        if resp.status_code in (200, 204):
            QMessageBox.information(self, "Başarılı", "Kayıt silindi.")
            self.load_data()
            self.reset_form()
        else:
            detail = safe_error_text(resp)
            header = response_error_message(resp, "Kayıt silinemedi")
            QMessageBox.warning(self, "Hata", f"{header}.\n\nDetay: {detail}")

    def _normalized_existing_values(self, field_name, exclude_id=None):
        values = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item:
                continue
            record = item.data(Qt.UserRole) or {}
            if exclude_id is not None and record.get("id") == exclude_id:
                continue
            normalized = self._normalize_text(record.get(field_name, ""))
            if normalized:
                values.add(normalized)
        return values

    def _normalize_text(self, value):
        return normalize_entity_text(value)

    def _confirm_delete(self):
        return self._ask_confirmation(
            "Kaydı silmek istediğinize emin misiniz?",
            yes_style="DialogNegativeButton",
            no_style="DialogNeutralButton"
        )

    def _ask_confirmation(self, message, detail=None, yes_text="Evet", no_text="Vazgeç",
                           yes_style="DialogPositiveButton", no_style="DialogNeutralButton"):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Onay")
        dialog.setText(message)
        if detail:
            dialog.setInformativeText(detail)
        btn_yes = dialog.addButton(yes_text, QMessageBox.YesRole)
        btn_no = dialog.addButton(no_text, QMessageBox.NoRole)
        btn_yes.setObjectName(yes_style)
        btn_no.setObjectName(no_style)
        btn_yes.setStyleSheet(self._button_style_for(yes_style))
        btn_no.setStyleSheet(self._button_style_for(no_style))
        dialog.setDefaultButton(btn_no)
        dialog.exec_()
        return dialog.clickedButton() == btn_yes

    def _button_style_for(self, style_name):
        if style_name == "DialogNegativeButton":
            return "background-color:#e74c3c;color:white;border:none;border-radius:4px;padding:4px 12px;"
        if style_name == "DialogNeutralButton":
            return "background-color:#bdc3c7;color:#2c3e50;border:none;border-radius:4px;padding:4px 12px;"
        if style_name == "DialogPositiveButton":
            return "background-color:#27ae60;color:white;border:none;border-radius:4px;padding:4px 12px;"
        return ""


TURKISH_LOWER_MAP = str.maketrans("IİŞĞÜÇÖ", "ıişğüçö")
TURKISH_UPPER_SPECIAL = {
    "i": "İ",
    "ı": "I",
    "ğ": "Ğ",
    "ü": "Ü",
    "ş": "Ş",
    "ö": "Ö",
    "ç": "Ç",
}


def _lower_tr(text: str) -> str:
    return text.translate(TURKISH_LOWER_MAP).lower()


def _capitalize_tr(token: str) -> str:
    token = _lower_tr(token)
    if not token:
        return token
    first = token[0]
    first = TURKISH_UPPER_SPECIAL.get(first, first.upper())
    return first + token[1:]


def normalize_entity_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    parts = re.split(r'(\s+)', text)
    normalized = []
    for part in parts:
        if not part.strip():
            normalized.append(part)
            continue
        segments = part.split('-')
        normalized_segments = []
        for segment in segments:
            sub_segments = segment.split("'")
            normalized_sub = [_capitalize_tr(sub) for sub in sub_segments]
            normalized_segments.append("'".join(normalized_sub))
        normalized.append("-".join(normalized_segments))
    return "".join(normalized)


def safe_error_text(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("detail") or data.get("error") or str(data)
        return str(data)
    except Exception:
        return response.text.strip() or "Bilinmeyen hata"


class AuthorManagerDialog(EntityManagerDialog):
    def __init__(self, parent=None):
        fields = [{"name": "ad_soyad", "label": "Ad Soyad"}]
        super().__init__("Yazar Yönetimi", "yazarlar/", fields, parent)

    def _confirm_delete(self):
        if not self.current_id:
            return False
        count = books.count_books_by_author(self.current_id)
        if count > 0:
            detail = f"Bu yazara bağlı {count} kitap kaydı bulunuyor. Yine de silmek ister misiniz?"
            return self._ask_confirmation(
                "Bağlı kitap kayıtları bulundu",
                detail=detail,
                yes_style="DialogNegativeButton",
                no_style="DialogNeutralButton"
            )
        return super()._confirm_delete()


class CategoryManagerDialog(EntityManagerDialog):
    def __init__(self, parent=None):
        fields = [{"name": "ad", "label": "Kategori Adı"}]
        super().__init__("Kategori Yönetimi", "kategoriler/", fields, parent)

    def _confirm_delete(self):
        if not self.current_id:
            return False
        count = books.count_books_by_category(self.current_id)
        if count > 0:
            detail = f"Bu kategoriye bağlı {count} kitap kaydı bulunuyor. Yine de silmek ister misiniz?"
            return self._ask_confirmation(
                "Bağlı kitap kayıtları bulundu",
                detail=detail,
                yes_style="DialogNegativeButton",
                no_style="DialogNeutralButton"
            )
        return super()._confirm_delete()
