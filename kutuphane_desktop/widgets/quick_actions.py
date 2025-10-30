from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QTextEdit, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.config import get_api_base_url
from core.utils import api_request, format_date


class QuickActions(QWidget):
    resultReady = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # 🔹 Giriş kutusu HER ZAMAN görünsün
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("⚡ Hızlı İşlem: Barkod / ISBN / Öğrenci No girin...")
        self.input_box.returnPressed.connect(self.run_query)
        layout.addWidget(self.input_box)

        # 🔹 Sonuç alanı başlangıçta gizli
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setVisible(False)
        layout.addWidget(self.result_area)

        # 🔹 Kapat butonu başlangıçta gizli
        self.btn_close = QPushButton("Kapat")
        self.btn_close.clicked.connect(self.close_panel)
        self.btn_close.setVisible(False)
        layout.addWidget(self.btn_close)

        self.setLayout(layout)

    def run_query(self):
        query = self.input_box.text().strip()
        if not query:
            return
        resp = api_request("GET", self._api_url(f"fast-query/?q={query}"))
        if resp.status_code != 200:
            self.result_area.setText("❌ Sunucu hatası")
            self.result_area.setVisible(True)
            self.btn_close.setVisible(True)
            return

        data = resp.json()
        self.show_result(data)
        self.resultReady.emit(data)
        self.result_area.setVisible(True)
        self.btn_close.setVisible(True)

    def show_result(self, data):
        t = data.get("type")
        txt = ""

        if t == "book_copy":
            book = data.get("book", {})
            copy = data.get("copy", {})
            loan = data.get("loan")
            txt = f"📖 {book.get('baslik')} ({book.get('isbn')})\n"
            txt += f"Barkod: {copy.get('barkod')} | Raf: {copy.get('raf_kodu')}\nDurum: {copy.get('durum')}\n"
            if loan:
                o = loan.get("ogrenci", {})
                due = format_date(loan.get("iade_tarihi"))
                due_text = f" → iade: {due}" if due else ""
                txt += f"\n🔒 Ödünçte{due_text}\n"
                txt += f"{o.get('ad')} {o.get('soyad')} ({o.get('ogrenci_no')})\n"
            else:
                txt += "\n✅ Kütüphanede mevcut."

        elif t == "isbn":
            if data.get("exists"):
                book = data.get("book", {})
                txt = f"ISBN kayıtlı: {book.get('baslik')} - {book.get('yazar')}"
            else:
                txt = "❗ Bu ISBN kayıtlı değil. Kitap eklemek ister misiniz?"

        elif t == "student":
            stu = data.get("student", {})
            txt = f"👤 {stu.get('ad')} {stu.get('soyad')} ({stu.get('no')})\nSınıf: {stu.get('sinif')}\n\n"
            txt += "📚 Aktif ödünçler:\n"
            for od in data.get("active_loans", []):
                due = format_date(od.get("iade_tarihi"))
                txt += f"- {od.get('kitap')} ({od.get('barkod')}) → iade: {due}\n"

        elif t == "not_found":
            txt = "❓ Kayıt bulunamadı."

        else:
            txt = "⚠️ Bilinmeyen yanıt."

        self.result_area.setText(txt)

    def close_panel(self):
        self.input_box.clear()
        self.result_area.clear()
        self.result_area.setVisible(False)
        self.btn_close.setVisible(False)

    def _api_url(self, path):
        base = get_api_base_url().rstrip('/')
        return f"{base}/{path.lstrip('/')}"
