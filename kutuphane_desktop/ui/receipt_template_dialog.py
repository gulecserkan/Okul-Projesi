from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QPlainTextEdit,
    QWidget,
)


RECEIPT_PLACEHOLDERS = [
    ("operator_name", "İşlemi yapan personel"),
    ("receipt_date", "Fiş tarihi (örn. 10.11.2025)"),
    ("receipt_time", "Fiş saati (örn. 14:32)"),
    ("student_full_name", "Öğrencinin adı soyadı"),
    ("student_number", "Öğrenci numarası"),
    ("student_class", "Öğrencinin sınıfı"),
    ("student_role", "Öğrencinin rolü / statüsü"),
    ("student_phone", "Öğrenci telefonu"),
    ("student_email", "Öğrenci e-posta adresi"),
    ("payment_amount", "Ödenen ceza tutarı"),
    ("payment_currency", "Para birimi"),
    ("remaining_debt", "Öğrencinin kalan borcu"),
    ("debt_items", "Borç kalemleri listesini metin olarak ekler"),
    ("loan_count", "Aktif ödünç sayısı"),
    ("return_deadline", "En yakın iade tarihi"),
]


class ReceiptTemplateDialog(QDialog):
    """
    Ödeme / borç fişi şablonu için basit editör.
    Kullanıcıya kullanılabilir yer tutucuları listeler ve serbest metin düzenlemeye izin verir.
    """

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        template_name: str,
        template_body: str,
        placeholders: list[tuple[str, str]] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Fiş Şablonu - {template_name}")
        self.resize(780, 520)

        self._template_name = template_name
        self._placeholders = placeholders or RECEIPT_PLACEHOLDERS

        root = QVBoxLayout(self)

        info = QLabel(
            "Şablon metninde {{ anahtar }} formatını kullanabilirsiniz. "
            "Aşağıdaki listeden anahtar seçip metne ekleyebilirsiniz."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        body = QHBoxLayout()

        self.list_placeholders = QListWidget()
        for key, desc in self._placeholders:
            item = QListWidgetItem(f"{key} — {desc}")
            item.setData(Qt.UserRole, key)
            self.list_placeholders.addItem(item)
        self.list_placeholders.itemDoubleClicked.connect(self._insert_placeholder_via_item)
        body.addWidget(self.list_placeholders, 0)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(template_body or "")
        body.addWidget(self.text_edit, 1)

        root.addLayout(body, 1)

        btn_row = QHBoxLayout()
        self.btn_insert_placeholder = QPushButton("Seçili Anahtarı Ekle")
        self.btn_insert_placeholder.clicked.connect(self._insert_selected_placeholder)
        btn_row.addWidget(self.btn_insert_placeholder)

        btn_row.addStretch(1)
        root.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    def template_text(self) -> str:
        return self.text_edit.toPlainText()

    # ------------------------------------------------------------------
    def _insert_placeholder_via_item(self, item: QListWidgetItem):
        if not item:
            return
        key = item.data(Qt.UserRole)
        if not key:
            return
        self._insert_text(f"{{{{ {key} }}}}")

    def _insert_selected_placeholder(self):
        item = self.list_placeholders.currentItem()
        if not item:
            QMessageBox.information(self, "Anahtar Seçimi", "Lütfen listeden bir anahtar seçin.")
            return
        self._insert_placeholder_via_item(item)

    def _insert_text(self, text: str):
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
