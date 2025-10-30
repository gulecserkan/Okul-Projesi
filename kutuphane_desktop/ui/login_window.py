from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QScrollArea
)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QAction

from api import auth
from api.system import health_check
from core.config import get_api_base_url
from ui.main_window import MainWindow
from ui.rich_label import RichLabel
from ui.server_settings_dialog import ServerSettingsDialog


class LoginWindow(QWidget):
    def __init__(self, initial_health=None):
        super().__init__()
        self.setWindowTitle("Kütüphane Giriş")
        self.setFixedSize(460, 420)

        # ekran ortasına al
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        # Logo
        logo = QLabel()
        pixmap = QPixmap("resources/icons/library_large.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        # Başlık
        title = QLabel("Kütüphane Yönetim Sistemi")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Kullanıcı adı
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Kullanıcı adı")
        self.username_input.setFocus()
        layout.addWidget(self.username_input)

        # Parola alanı
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Parola")
        self.password_input.setEchoMode(QLineEdit.Password)

        # Göster/Gizle ikonu (textbox içine)
        self.toggle_action = QAction(QIcon("resources/icons/eye.png"), "Göster", self)
        self.toggle_action.setCheckable(True)
        self.toggle_action.toggled.connect(self.toggle_password_visibility)
        self.password_input.addAction(self.toggle_action, QLineEdit.TrailingPosition)

        layout.addWidget(self.password_input)

        # Giriş butonu
        self.login_button = QPushButton("Giriş Yap")
        self.login_button.setObjectName("loginButton")
        self.login_button.clicked.connect(self.check_login)
        layout.addWidget(self.login_button)

        # Sunucu durumu
        self.status_container = QScrollArea()
        self.status_container.setWidgetResizable(True)
        self.status_container.setFrameStyle(QScrollArea.NoFrame)
        self.status_container.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_container.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.status_container.setFixedHeight(90)
        self.status_label = RichLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_container.setWidget(self.status_label)
        self.status_container.setVisible(False)
        layout.addWidget(self.status_container)

        # Sunucu ayarları butonu
        button_row = QHBoxLayout()
        button_row.addStretch()
        self.server_button = QPushButton("Sunucu Ayarları")
        self.server_button.clicked.connect(self.open_server_settings)
        self.server_button.setVisible(False)
        button_row.addWidget(self.server_button)
        layout.addLayout(button_row)

        self.setLayout(layout)
        # Enter → password alanına geç
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        # Password alanında Enter → login dene
        self.password_input.returnPressed.connect(self.check_login)

        self.server_ready = False
        self.last_server_error = ""
        self._logging_in = False
        if initial_health is not None:
            self.update_server_status(initial_health)
        else:
            self.update_server_status()

    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_action.setIcon(QIcon("resources/icons/eye-off.png"))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_action.setIcon(QIcon("resources/icons/eye.png"))

    def check_login(self):
        if self._logging_in:
            return
        username = self.username_input.text()
        password = self.password_input.text()

        if not self.server_ready:
            self.update_server_status()
            if not self.server_ready:
                detail = self.last_server_error or "Sunucuya ulaşılamadı."
                QMessageBox.warning(self, "Sunucu", f"Sunucuya bağlanılamadı.\n\nDetay: {detail}")
                return

        self._logging_in = True
        result = auth.login(username, password)
        if result:
            self.accept_login()
        else:
            QMessageBox.warning(self, "Hata", "Kullanıcı adı veya parola yanlış!")
            self._logging_in = False

    def accept_login(self):
        # Ana pencereyi bir sonraki event loop turunda aç – Login şimdilik görünür kalsın
        QTimer.singleShot(50, self._open_main_async)
        # Not: _active_login_window referansını hemen temizlemiyoruz; deleteLater sonrası zaten kalkacak

    def _open_main_async(self):
        try:
            self.main_window = MainWindow()
            self.main_window.show()
        except Exception as exc:
            # İsteğe bağlı: hatayı stdout'a yazmadan kullanıcıya gösterme
            pass
        finally:
            # Login penceresini güvenli şekilde sıradaki döngüde kapat/temizle
            try:
                self.hide()
            except Exception:
                pass
            QTimer.singleShot(0, self.deleteLater)
            self._logging_in = False

    def update_server_status(self, health_result=None):
        if health_result is None:
            health_result = health_check()
        ok, info = health_result
        if ok:
            self.server_ready = True
            self.last_server_error = ""
            self.server_button.setVisible(False)
            self.status_label.clear()
            self.status_container.setVisible(False)
        else:
            self.server_ready = False
            message = ""
            if isinstance(info, dict):
                message = info.get("error") or info.get("detail") or str(info)
            else:
                message = str(info)
            self.last_server_error = message
            html = (
                "<span style='color:#e74c3c;'>"
                "<b>Sunucuya ulaşılamadı.</b><br/>"
                f"<small>{message}</small>"
                "</span>"
            )
            self.status_label.setText(html)
            self.status_container.setVisible(True)
            self.server_button.setVisible(True)

    def open_server_settings(self):
        current_url = get_api_base_url()
        dialog = ServerSettingsDialog(self)
        if dialog.exec_() == dialog.Accepted and dialog.saved:
            new_url = dialog.new_url or get_api_base_url()
            if new_url.rstrip('/') != current_url.rstrip('/'):
                auth.logout()
            self.update_server_status()
