import sys
from PyQt5.QtWidgets import QApplication
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from api import auth
from api.system import health_check

def main():
    app = QApplication(sys.argv)
    # 🔹 Stil dosyasını yükle
    try:
        with open("resources/style.qss", "r") as f:   # dosya yolunu kendi yapına göre ayarla
            qss = f.read()
            app.setStyleSheet(qss)
    except Exception as e:
        print("QSS yüklenemedi:", e)

    auth.load_tokens()

    health = health_check()
    server_ok = health[0]

    window = None

    if server_ok and auth.get_access_token():
        window = MainWindow()

    if window is None:
        initial = None if server_ok else health
        window = LoginWindow(initial_health=initial)

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
