from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from api import auth
from ui.main_window import MainWindow


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kütüphane Giriş")
        self.setFixedSize(400, 350)

        # ekran ortasına al
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        # Logo / resim
        logo = QLabel()
        pixmap = QPixmap("resources/icons/library.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        layout.addWidget(self.username_input)

        # Parola + göz butonu
        pw_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Parola")
        self.password_input.setEchoMode(QLineEdit.Password)
        pw_layout.addWidget(self.password_input)

        self.toggle_pw_btn = QPushButton("👁")
        self.toggle_pw_btn.setFixedWidth(40)
        self.toggle_pw_btn.setCheckable(True)
        self.toggle_pw_btn.clicked.connect(self.toggle_password_visibility)
        pw_layout.addWidget(self.toggle_pw_btn)

        layout.addLayout(pw_layout)

        # Giriş butonu
        login_button = QPushButton("Giriş Yap")
        login_button.setObjectName("loginButton")
        login_button.clicked.connect(self.check_login)
        layout.addWidget(login_button)

        self.setLayout(layout)

    def toggle_password_visibility(self):
        if self.toggle_pw_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

    def check_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        result = auth.login(username, password)
        if result:
            self.accept_login()
        else:
            QMessageBox.warning(self, "Hata", "Kullanıcı adı veya parola yanlış!")

    def accept_login(self):
        self.hide()
        self.main_window = MainWindow()
        self.main_window.show() 
