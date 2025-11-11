from __future__ import annotations

from PyQt5.QtCore import Qt, QDateTime, pyqtSignal
from decimal import Decimal, InvalidOperation

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
    QWidget,
)
from PyQt5.QtGui import QFont, QColor, QBrush
from functools import partial
from core.config import get_api_base_url
from core.utils import format_date, api_request
from api import logs as log_api
from core.log_helpers import build_log_detail, format_currency
from printing.receipt_printer import (
    print_fine_payment_receipt,
    ReceiptPrintError,
    check_receipt_printer_status,
)

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
        self.btn_update.setObjectName("DialogPositiveButton")
        self.btn_continue.setObjectName("DialogWarnButton")
        self.btn_cancel.setObjectName("DialogDangerButton")
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
        self.btn_save.setObjectName("DialogPositiveButton")
        self.btn_skip.setObjectName("DialogWarnButton")
        self.btn_cancel.setObjectName("DialogDangerButton")
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


def _plain_amount(value) -> str:
    if value in (None, "", False):
        return "0"
    try:
        dec = Decimal(str(value).replace(",", "."))
        dec = dec.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return "0"
    text = format(dec, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _build_receipt_warning_widget(parent=None):
    ok, reason = check_receipt_printer_status()
    if ok:
        return None
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 4, 0, 0)
    layout.setSpacing(6)
    label = QLabel("Fiş yazıcısı hazır değil. Fiş basılamayabilir.")
    label.setStyleSheet("color:#c0392b; font-weight:600;")
    button = QPushButton("?")
    button.setFixedWidth(28)
    button.setCursor(Qt.PointingHandCursor)

    def _show():
        QMessageBox.information(parent, "Fiş Yazdırma", reason)

    button.clicked.connect(_show)
    layout.addWidget(label)
    layout.addWidget(button)
    layout.addStretch(1)
    return container


def _attach_warning_to_message_box(box):
    ok, reason = check_receipt_printer_status()
    if ok:
        return
    layout = box.layout()
    if layout is None:
        return
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    label = QLabel("Fiş yazıcısı hazır değil. Fiş basılamayabilir.")
    label.setStyleSheet("color:#c0392b; font-weight:600;")
    btn = QPushButton("?")
    btn.setFixedWidth(28)
    btn.setCursor(Qt.PointingHandCursor)

    def _show():
        QMessageBox.information(box, "Fiş Yazdırma", reason)

    btn.clicked.connect(_show)
    row.addWidget(label)
    row.addWidget(btn)
    row.addStretch(1)
    try:
        row_index = layout.rowCount()
        col_span = layout.columnCount()
        layout.addWidget(widget, row_index, 0, 1, max(1, col_span))
    except AttributeError:
        layout.addWidget(widget)


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
        self.updated_summary = None
        self._base_url = get_api_base_url().rstrip("/")

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
        self.btn_paid.setObjectName("DialogPositiveButton")
        self.btn_skip.setObjectName("DialogWarnButton")
        self.btn_cancel.setObjectName("DialogDangerButton")
        layout.addWidget(buttons)
        warning = _build_receipt_warning_widget(self)
        if warning:
            layout.addWidget(warning)

    def _on_clicked(self, button):
        if button is self.btn_paid:
            if self._pay_all_entries():
                self.result_code = self.RESULT_PAID
                self.accept()
        elif button is self.btn_skip:
            self.result_code = self.RESULT_SKIP
            self.accept()
        else:
            self.result_code = self.RESULT_CANCEL
            self.reject()

    def _pay_all_entries(self):
        entries = self.summary.get("entries") or []
        payable = [e for e in entries if self._parse_decimal(e.get("gecikme_cezasi")) > Decimal("0") and not e.get("gecikme_cezasi_odendi")]
        if not payable:
            QMessageBox.information(self, "Ceza Ödemesi", "Ödenecek ceza bulunamadı.")
            return True

        last_summary = None
        paid_total = Decimal("0")
        for entry in payable:
            loan_id = entry.get("id")
            if not loan_id:
                continue
            amount = self._parse_decimal(entry.get("gecikme_cezasi"))
            url = f"{self._base_url}/penalties/{loan_id}/pay/"
            payload = {"amount": format(amount.quantize(Decimal('0.01')), '.2f')}
            resp = api_request("POST", url, json=payload)
            if resp is None or getattr(resp, "status_code", None) != 200:
                message = getattr(resp, "error_message", None)
                if not message and resp is not None:
                    try:
                        data = resp.json()
                        message = data.get("error") if isinstance(data, dict) else str(data)
                    except Exception:
                        message = resp.text or "Ödeme kaydedilemedi."
                QMessageBox.warning(self, "Ceza Ödemesi", message or "Ödeme kaydedilemedi.")
                return False
            try:
                data = resp.json() if resp is not None else {}
            except ValueError:
                data = {}
            last_summary = data.get("summary") or last_summary
            paid_total += amount

        if last_summary:
            self.summary = last_summary
            self.updated_summary = last_summary
        if payable:
            student = (self.summary or {}).get("student") or {}
            base_detail = build_log_detail(
                student=student,
                amount=paid_total,
                amount_label="Toplam ödeme",
                extra=f"Ödenen ceza sayısı: {len(payable)}",
            )
            log_api.safe_send_log("Ceza ödemesi", detay=base_detail or "Ceza ödemesi tamamlandı.")
            if paid_total > Decimal("0"):
                log_api.safe_send_log("Tahsilat", detay=_plain_amount(paid_total))
            self._print_receipt(paid_total)
        QMessageBox.information(self, "Ceza Ödemesi", "Ödeme kaydedildi.")
        return True

    def _parse_decimal(self, value):
        if value in (None, "", False):
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            try:
                return Decimal(str(value).replace(",", "."))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal("0")

    def _print_receipt(self, amount):
        amount_dec = self._parse_decimal(amount)
        if amount_dec <= Decimal("0"):
            return
        summary = dict(self.summary or {})
        if "entries" not in summary or not summary.get("entries"):
            summary["entries"] = (self.summary or {}).get("entries") or []
        if "outstanding_total" not in summary:
            summary["outstanding_total"] = (self.summary or {}).get("outstanding_total")
        try:
            print_fine_payment_receipt(summary, amount_dec)
        except ReceiptPrintError as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", str(exc))
        except Exception as exc:  # pragma: no cover - GUI warning
            QMessageBox.warning(self, "Fiş Yazdırma", f"Fiş yazdırma başarısız:\n{exc}")

class PenaltyDetailDialog(QDialog):
    penaltyPaid = pyqtSignal(dict)

    def __init__(self, *, summary: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ceza Detayı")
        self.setModal(True)
        self.resize(560, 320)
        self.summary = summary or {}
        self._base_url = get_api_base_url().rstrip("/")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.label_total = QLabel()
        self.label_total.setStyleSheet("font-weight:600;")
        layout.addWidget(self.label_total)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Kitap", "Barkod", "Durum", "Teslim", "Ceza", ""])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(self.table)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color:#7f8c8d;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_rows()
        warning = _build_receipt_warning_widget(self)
        if warning:
            layout.insertWidget(layout.count() - 1, warning)

    def _parse_decimal(self, value) -> Decimal:
        if value in (None, "", False):
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            try:
                return Decimal(str(value).replace(",", "."))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal("0")

    def _format_currency(self, amount) -> str:
        decimal_value = self._parse_decimal(amount)
        try:
            decimal_value = decimal_value.quantize(Decimal("0.01"))
        except InvalidOperation:
            decimal_value = Decimal("0.00")
        return f"{format(decimal_value, '.2f')} ₺"

    def _load_rows(self):
        entries = self.summary.get("entries") or []
        self.table.setRowCount(len(entries))

        total = self._parse_decimal(self.summary.get("outstanding_total"))
        if total > Decimal("0"):
            self.label_total.setText(f"Toplam bekleyen ceza: {self._format_currency(total)}")
            self.info_label.setText("Teslim edilen kitapların cezalarını tek tek tahsil edebilirsiniz.")
        else:
            self.label_total.setText("Bekleyen ceza bulunmuyor.")
            self.info_label.setText("Tüm cezalar tahsil edilmiş görünüyor.")

        for row, entry in enumerate(entries):
            amount = self._parse_decimal(entry.get("gecikme_cezasi"))
            paid = bool(entry.get("gecikme_cezasi_odendi"))
            durum = (entry.get("durum") or "").lower()
            teslim = entry.get("teslim_tarihi")

            self.table.setItem(row, 0, QTableWidgetItem(entry.get("kitap", "")))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("barkod", "")))
            self.table.setItem(row, 2, QTableWidgetItem(durum.title()))
            self.table.setItem(row, 3, QTableWidgetItem(format_date(teslim)))
            self.table.setItem(row, 4, QTableWidgetItem(self._format_currency(amount)))
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            can_pay = (
                not paid
                and amount > Decimal("0")
                and teslim is not None
                and durum != "oduncte"
            )

            if paid:
                brush = QBrush(QColor(226, 250, 236))
            elif amount > Decimal("0") and can_pay:
                brush = QBrush(QColor(255, 243, 243))
            else:
                brush = None

            if brush:
                for col in range(5):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(brush)

            if can_pay:
                btn_pay = QPushButton("Öde")
                btn_pay.setCursor(Qt.PointingHandCursor)
                btn_pay.clicked.connect(partial(self._handle_payment, entry))
                self.table.setCellWidget(row, 5, btn_pay)
            else:
                label = QLabel("Ödendi" if paid else "—")
                label.setAlignment(Qt.AlignCenter)
                if paid:
                    label.setStyleSheet("color:#27ae60;font-weight:600;")
                self.table.setCellWidget(row, 5, label)

    def _handle_payment(self, entry):
        loan_id = entry.get("id")
        if not loan_id:
            return
        amount = self._parse_decimal(entry.get("gecikme_cezasi"))
        if amount <= Decimal("0"):
            return

        book = entry.get("kitap", "")
        barkod = entry.get("barkod", "")

        msg = QMessageBox(self)
        msg.setWindowTitle("Ceza Ödemesi")
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"\"{book}\" ({barkod}) için gecikme cezası tahsil edilsin mi?")
        msg.setInformativeText(f"Tutar: {self._format_currency(amount)}")
        btn_yes = msg.addButton("Ödeme Kaydet", QMessageBox.AcceptRole)
        btn_no = msg.addButton("Vazgeç", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_yes)
        _attach_warning_to_message_box(msg)
        msg.exec_()
        if msg.clickedButton() != btn_yes:
            return

        url = f"{self._base_url}/penalties/{loan_id}/pay/"
        amount_q = amount.quantize(Decimal("0.01"))
        payload = {"amount": format(amount_q, ".2f")}
        resp = api_request("POST", url, json=payload)
        if resp is None or resp.status_code != 200:
            error_text = getattr(resp, "error_message", None) if resp is not None else None
            detail = ""
            if resp is not None:
                try:
                    detail = resp.json().get("error")
                except Exception:
                    detail = resp.text or ""
            message = error_text or detail or "Ödeme kaydedilemedi."
            QMessageBox.warning(self, "Ceza Ödemesi", message)
            return

        try:
            data = resp.json() or {}
        except ValueError:
            data = {}

        summary = data.get("summary") or {}
        if summary:
            self.summary = summary
        student = (self.summary or {}).get("student") or {}
        detail = build_log_detail(
            student=student,
            book={"baslik": book} if book else None,
            barcode=barkod,
            amount=amount,
            amount_label="Tahsilat",
            extra="Kaynak: Ceza detayı üzerinden ödeme",
        )
        log_api.safe_send_log("Ceza ödemesi", detay=detail or "Ceza ödemesi kaydedildi.")
        log_api.safe_send_log("Tahsilat", detay=_plain_amount(amount))
        self._load_rows()
        self.penaltyPaid.emit(self.summary)
        self._print_receipt(amount)
        QMessageBox.information(self, "Ceza Ödemesi", "Ödeme başarıyla kaydedildi.")


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
