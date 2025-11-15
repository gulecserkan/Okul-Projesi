import os
import sys
import tempfile
from PyQt5.QtCore import QLockFile
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from api import auth
from api.system import health_check

LOCK_FILENAME = "kutuphane_desktop.lock"

def main():
    # WM_CLASS ve launcher eşleşmesi için
    os.environ.setdefault("QT_WMCLASS", "kutuphane")
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", os.environ.get("QT_QPA_PLATFORMTHEME", "gtk3"))
    app = QApplication(sys.argv)
    app.setApplicationName("kutuphane")
    app.setApplicationDisplayName("Kütüphane")
    app.setDesktopFileName("kutuphane.desktop")

    lock_path = os.path.join(tempfile.gettempdir(), LOCK_FILENAME)
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(0)
    if not lock.tryLock():
        QMessageBox.warning(
            None,
            "Kütüphane Programı",
            "Program zaten çalışıyor.",
        )
        return 0

    exit_code = 0
    try:
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
        exit_code = app.exec_()
    finally:
        lock.unlock()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
