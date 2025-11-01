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
    QInputDialog,
)


class NotificationTemplateDialog(QDialog):
    """
    Basit bir şablon düzenleyicisi: kullanıcıya kullanılabilir anahtar kelimeleri gösterir,
    metin içindeki yer tutucuları hızlıca eklemeyi sağlar ve koşullu bloklar için yardımcı şablon sunar.
    """

    def __init__(self, title: str, text: str, placeholders: list[tuple[str, str]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 480)

        self._placeholders = placeholders or []

        root = QVBoxLayout(self)
        info = QLabel(
            "Şablon metninde {{ anahtar }} biçiminde yer tutucular kullanabilirsiniz. "
            "Koşullu ifadeler için 'Koşul Ekle' butonunu kullanın."
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
        self.text_edit.setPlainText(text or "")
        body.addWidget(self.text_edit, 1)
        root.addLayout(body, 1)

        btn_row = QHBoxLayout()
        self.btn_insert_placeholder = QPushButton("Seçili Anahtarı Ekle")
        self.btn_insert_placeholder.clicked.connect(self._insert_selected_placeholder)
        btn_row.addWidget(self.btn_insert_placeholder)

        self.btn_insert_condition = QPushButton("Koşul Ekle")
        self.btn_insert_condition.clicked.connect(self._insert_condition_snippet)
        btn_row.addWidget(self.btn_insert_condition)

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
        placeholder = item.data(Qt.UserRole)
        self._insert_text(f"{{{{ {placeholder} }}}}")

    def _insert_selected_placeholder(self):
        item = self.list_placeholders.currentItem()
        if not item:
            QMessageBox.information(self, "Anahtar Seçimi", "Lütfen listeden bir anahtar seçin.")
            return
        self._insert_placeholder_via_item(item)

    def _insert_condition_snippet(self):
        placeholder = "role"
        item = self.list_placeholders.currentItem()
        if item:
            placeholder = item.data(Qt.UserRole) or placeholder

        condition, ok = QInputDialog.getText(
            self,
            "Koşul İfadesi",
            "Koşul (örnek: role == \"Öğretmen\")",
            text=f'{placeholder} == "Öğretmen"',
        )
        if not ok or not condition.strip():
            return
        snippet = (
            f"{{{{#if {condition.strip()} }}}}\n"
            "    \n"
            "{{else}}\n"
            "    \n"
            "{{/if}}\n"
        )
        self._insert_text(snippet)

    def _insert_text(self, text: str):
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
