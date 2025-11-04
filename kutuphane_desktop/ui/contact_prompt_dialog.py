from __future__ import annotations

from PyQt5.QtCore import Qt
from decimal import Decimal

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QFont
from core.utils import format_date

from ui.student_manager_dialog import (
    _format_phone_display,
    _normalize_phone,
    _is_valid_phone,
    _is_valid_email,
)


class ContactReminderDialog(QDialog):
    RESULT_CANCEL = 0
    RESULT_SKIP = 1
    RESULT_UPDATE = 2

    def __init__(self, *, student: dict | None = None, missing_fields=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İletişim Bilgisi Eksik")
        self.setModal(True)
        self.resize(360, 200)

        self.result_code = self.RESULT_CANCEL
        self.student = student or {}
        missing = missing_fields or []

        layout = QVBoxLayout(self)
        info = QLabel(
            "Aşağıdaki öğrenci için {} bilgisi eksik.\n"
            "Kitap teslimi ve bildirimler için iletişim bilgilerini güncelleyebilirsiniz."
            .format(" ve ".join(missing) if missing else "iletisim")
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        sinif_info = self.student.get('sinif')
        if isinstance(sinif_info, dict):
            sinif_display = sinif_info.get('ad', '—')
        else:
            sinif_display = sinif_info or '—'
        number = self.student.get('ogrenci_no') or self.student.get('no') or '—'
        details = QLabel(
            f"<b>{self.student.get('ad','')} {self.student.get('soyad','')}</b><br/>"
            f"Numara: {number}<br/>"
            f"Sınıf: {sinif_display}"
        )
        details.setTextFormat(Qt.RichText)
        layout.addWidget(details)

        buttons = QDialogButtonBox()
        self.btn_update = buttons.addButton("Bilgileri Güncelle", QDialogButtonBox.AcceptRole)
        self.btn_continue = buttons.addButton("Girmeden Devam Et", QDialogButtonBox.DestructiveRole)
        self.btn_cancel = buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.clicked.connect(self._on_clicked)
        layout.addWidget(buttons)

    def _on_clicked(self, button):
        if button is self.btn_update:
            self.result_code = self.RESULT_UPDATE
            self.accept()
        elif button is self.btn_continue:
            self.result_code = self.RESULT_SKIP
            self.accept()
        else:
            self.result_code = self.RESULT_CANCEL
            self.reject()


class ContactEditDialog(QDialog):
    RESULT_CANCEL = 0
    RESULT_SKIP = 1
    RESULT_SAVE = 2

    def __init__(self, *, student: dict | None = None, missing_fields=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İletişim Bilgileri")
        self.setModal(True)
        self.resize(360, 200)

        self.student = student or {}
        self.missing_fields = missing_fields or []
        self.result_code = self.RESULT_CANCEL
        self.normalized_phone = None
        self.display_phone = ""
        self.email_value = None

        root = QVBoxLayout(self)
        info_label = QLabel(
            "Öğrencinin iletişim bilgileri eksik görünüyor.\n"
            "Kitap teslimi ve bildirimler için lütfen alanları doldurun."
        )
        info_label.setWordWrap(True)
        root.addWidget(info_label)

        form = QFormLayout()
        self.input_phone = QLineEdit()
        self.input_phone.setInputMask("(500) 000 00 00;_")
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("ornek@adres.com")

        phone = (self.student.get("telefon") or "").strip()
        email = (self.student.get("eposta") or "").strip()
        if phone:
            self.input_phone.setText(_format_phone_display(phone))
        if email:
            self.input_email.setText(email)

        form.addRow("Telefon", self.input_phone)
        form.addRow("E-posta", self.input_email)
        root.addLayout(form)

        self.buttons = QDialogButtonBox()
        self.btn_save = self.buttons.addButton("Kaydet ve Devam Et", QDialogButtonBox.AcceptRole)
        self.btn_skip = self.buttons.addButton("Girmeden Devam Et", QDialogButtonBox.DestructiveRole)
        self.btn_cancel = self.buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        self.buttons.clicked.connect(self._handle_clicked)
        root.addWidget(self.buttons)

    def _handle_clicked(self, button):
        if button is self.btn_save:
            phone_text = self.input_phone.text().strip()
            email_text = self.input_email.text().strip()

            if phone_text and not _is_valid_phone(phone_text):
                QMessageBox.warning(self, "Hatalı Telefon", "Telefon numarası '(5__) ___ __ __' formatında olmalıdır.")
                return
            if email_text and not _is_valid_email(email_text):
                QMessageBox.warning(self, "Hatalı E-posta", "Lütfen geçerli bir e-posta adresi girin.")
                return

            normalized = _normalize_phone(phone_text) if phone_text else None
            self.normalized_phone = normalized
            self.display_phone = _format_phone_display(normalized) if normalized else phone_text
            self.email_value = email_text or None

            self.result_code = self.RESULT_SAVE
            self.accept()
            return

        if button is self.btn_skip:
            self.result_code = self.RESULT_SKIP
            self.normalized_phone = None
            self.display_phone = ""
            self.email_value = None
            self.accept()
            return

        self.result_code = self.RESULT_CANCEL
        self.reject()


def _format_currency(value) -> str:
    try:
        quantized = Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return str(value)
    return f"{quantized:.2f} TL"


class PenaltyNoticeDialog(QDialog):
    RESULT_CANCEL = 0
    RESULT_SKIP = 1
    RESULT_PAID = 2

    def __init__(self, *, summary: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Öğrenci Borcu")
        self.setModal(True)
        self.resize(420, 260)

        self.summary = summary or {}
        self.result_code = self.RESULT_CANCEL

        student = self.summary.get("student") or {}
        total = self.summary.get("outstanding_total") or "0.00"

        layout = QVBoxLayout(self)
        info = QLabel(
            f"<b>{student.get('ad','')} {student.get('soyad','')}</b> öğrencisinin ödenmemiş ceza tutarı mevcut."
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        total_label = QLabel(f"Toplam borç: <b>{_format_currency(total)}</b>")
        total_label.setTextFormat(Qt.RichText)
        layout.addWidget(total_label)

        entries = self.summary.get("entries") or []
        table = QTableWidget(len(entries), 3)
        table.setHorizontalHeaderLabels(["Kitap", "Barkod", "Ceza"])
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        for row, entry in enumerate(entries):
            book = entry.get("kitap", "")
            barkod = entry.get("barkod", "")
            penalty = entry.get("gecikme_cezasi", "0")
            table.setItem(row, 0, QTableWidgetItem(book))
            table.setItem(row, 1, QTableWidgetItem(barkod))
            table.setItem(row, 2, QTableWidgetItem(_format_currency(penalty)))
            for col in range(3):
                item = table.item(row, col)
                if item:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(table)

        buttons = QDialogButtonBox()
        self.btn_paid = buttons.addButton("Ödeme Yapıldı", QDialogButtonBox.AcceptRole)
        self.btn_skip = buttons.addButton("Ödemeden Devam", QDialogButtonBox.DestructiveRole)
        self.btn_cancel = buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.clicked.connect(self._on_clicked)
        layout.addWidget(buttons)

    def _on_clicked(self, button):
        if button is self.btn_paid:
            self.result_code = self.RESULT_PAID
            self.accept()
        elif button is self.btn_skip:
            self.result_code = self.RESULT_SKIP
            self.accept()
        else:
            self.result_code = self.RESULT_CANCEL
            self.reject()


class CheckoutConfirmDialog(QDialog):
    def __init__(self, *, student: dict | None = None, copy: dict | None = None, book: dict | None = None, due_date=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ödünç Onayı")
        self.setModal(True)
        self.resize(400, 220)

        student = student or {}
        copy = copy or {}
        book = book or {}
        if not book:
            if isinstance(copy, dict):
                book = copy.get("kitap") or {}
                if not book and isinstance(copy.get("kitap_nusha"), dict):
                    book = (copy.get("kitap_nusha") or {}).get("kitap") or {}
        due_text = "—"
        if due_date is not None:
            if hasattr(due_date, "isoformat"):
                due_text = format_date(due_date.isoformat())
            else:
                due_text = str(due_date)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Aşağıdaki bilgilerle ödünç vermek üzeresiniz:"))

        student_label = QLabel(
            f"<b>Öğrenci:</b> {student.get('ad','')} {student.get('soyad','')}"
            f"<br/><b>Numara:</b> {student.get('ogrenci_no','—')}"
            f"<br/><b>Sınıf:</b> {student.get('sinif','—')}"
        )
        student_label.setTextFormat(Qt.RichText)
        layout.addWidget(student_label)

        book_label = QLabel(
            f"<b>Kitap:</b> {book.get('baslik','')}"
            f"<br/><b>Barkod:</b> {copy.get('barkod','―')}"
            f"<br/><b>İade Tarihi:</b> {due_text}"
        )
        book_label.setTextFormat(Qt.RichText)
        layout.addWidget(book_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Ödünç Ver")
        buttons.button(QDialogButtonBox.Cancel).setText("İptal")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MaxLoansDialog(QDialog):
    def __init__(self, *, student: dict | None = None, loans=None, limit: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ödünç Limiti Aşıldı")
        self.setModal(True)
        self.resize(420, 260)

        student = student or {}
        loans = loans or []

        layout = QVBoxLayout(self)
        info = QLabel(
            f"<b>{student.get('ad','')} {student.get('soyad','')}</b> öğrencisi halihazırda maksimum ödünç limitine ulaşmış durumda."
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        layout.addWidget(QLabel(f"Maksimum ödünç adedi: <b>{limit}</b>"))

        table = QTableWidget(len(loans), 3)
        table.setHorizontalHeaderLabels(["Kitap", "Barkod", "İade Tarihi"])
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        for row, loan in enumerate(loans):
            book = ((loan.get("kitap_nusha") or {}).get("kitap") or {}).get("baslik", loan.get("kitap", ""))
            barkod = (loan.get("kitap_nusha") or {}).get("barkod", loan.get("barkod", ""))
            due = loan.get("iade_tarihi") or loan.get("effective_iade_tarihi")
            table.setItem(row, 0, QTableWidgetItem(book))
            table.setItem(row, 1, QTableWidgetItem(barkod))
            table.setItem(row, 2, QTableWidgetItem(format_date(due)))
            for col in range(3):
                item = table.item(row, col)
                if item:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Tamam")
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
