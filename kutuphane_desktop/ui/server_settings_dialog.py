from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
    QScrollArea,
)
from PyQt5.QtCore import Qt

from core.config import get_api_base_url, set_api_base_url
from api.system import health_check
from ui.rich_label import RichLabel


class ServerSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._saved = False
        self.new_url = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Sunucu adresi (ör. http://127.0.0.1:8000/api)"))

        self.url_input = QLineEdit(get_api_base_url())
        self.url_input.setClearButtonEnabled(True)
        layout.addWidget(self.url_input)

        test_row = QHBoxLayout()
        self.status_container = QScrollArea()
        self.status_container.setWidgetResizable(True)
        self.status_container.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_container.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.status_container.setFixedHeight(100)
        self.status_label = RichLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_container.setWidget(self.status_label)
        self.status_container.setVisible(False)
        test_button = QPushButton("Bağlantıyı Test Et")
        test_button.clicked.connect(self.test_connection)
        test_row.addWidget(test_button, 0, Qt.AlignLeft)
        test_row.addStretch(1)
        layout.addLayout(test_row)
        layout.addWidget(self.status_container)

        layout.addStretch(1)

    def test_connection(self):
        url = self.url_input.text().strip()
        if not url:
            self._set_status("Sunucu adresi boş olamaz.", color="#e74c3c")
            return False

        ok, data = health_check(url)
        if ok:
            self._set_status("Bağlantı başarılı.", detail=f"Adres: {url}", color="#27ae60")
        else:
            message = data.get("error") if isinstance(data, dict) else str(data)
            self._set_status("Bağlantı hatası.", detail=message, color="#e74c3c")
        return ok

    def save_preferences(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Uyarı", "Sunucu adresi boş olamaz.")
            return False

        ok, data = health_check(url)
        if not ok:
            message = data.get("error") if isinstance(data, dict) else str(data)
            QMessageBox.warning(self, "Bağlantı Hatası", f"Sunucuya ulaşamadık.\n\nDetay: {message}")
            return False

        set_api_base_url(url)
        self.new_url = url
        self._saved = True
        return True

    def _set_status(self, summary, detail=None, color="#27ae60"):
        if detail:
            text = (
                f"<span style='color:{color};'><b>{summary}</b><br/>"
                f"<small>{detail}</small></span>"
            )
        else:
            text = f"<span style='color:{color};'><b>{summary}</b></span>"
        self.status_label.setText(text)
        self.status_container.setVisible(True)


class ServerSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sunucu Ayarları")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        self.page = ServerSettingsWidget(self)
        layout.addWidget(self.page)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_save = button_box.button(QDialogButtonBox.Save)
        if btn_save:
            btn_save.setText("Kaydet")
        btn_cancel = button_box.button(QDialogButtonBox.Cancel)
        if btn_cancel:
            btn_cancel.setText("Vazgeç")
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_save(self):
        if self.page.save_preferences():
            self.accept()
