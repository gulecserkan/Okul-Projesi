from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QHeaderView,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
)

from api import loans as loan_api
from api import logs as log_api
from core.utils import response_error_message
from ui.entity_manager_dialog import normalize_entity_text
from core.log_helpers import build_log_detail, format_currency

STATUS_OPTIONS = [
    ("", "Seçiniz..."),
    ("teslim", "Teslim Alındı"),
    ("kayip", "Kayıp"),
    ("hasarli", "Hasarlı"),
    ("iptal", "İptal"),
]

COPY_STATUS_MAP = {
    "teslim": "mevcut",
    "iptal": "mevcut",
    "kayip": "kayip",
    "hasarli": "hasarli",
}


class LossPenaltyDialog(QDialog):
    def __init__(self, *, status_label: str, student=None, book=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{status_label} Durumu")
        self.setModal(True)
        self.resize(360, 200)
        self._amount = Decimal("0")
        self._paid = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        student = student or {}
        book = book or {}

        full_name = " ".join(part for part in [(student.get("ad") or "").strip(), (student.get("soyad") or "").strip()] if part)
        ogr_no = (student.get("ogrenci_no") or student.get("no") or "").strip()
        book_title = book.get("baslik") if isinstance(book, dict) else str(book or "")
        book_title = normalize_entity_text(book_title)
        info_lines = [
            f"Bu kayıt '{status_label.lower()}' olarak işaretlenecek.",
            "Gerekli ise ceza tutarını girin ve ödemenin alınıp alınmadığını seçin.",
        ]
        if full_name or ogr_no:
            detail = full_name or "—"
            if ogr_no:
                detail = f"{detail} (No: {ogr_no})"
            info_lines.append(f"Öğrenci: {detail}")
        if book_title:
            info_lines.append(f"Kitap: {book_title}")

        info_label = QLabel("\n".join(info_lines))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.input_amount = QLineEdit(self)
        self.input_amount.setPlaceholderText("0,00")
        self.input_amount.setText("0,00")
        form.addRow("Ceza tutarı", self.input_amount)

        self.chk_paid = QCheckBox("Ödeme hemen alındı", self)
        form.addRow("", self.chk_paid)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.button(QDialogButtonBox.Ok).setText("Onayla")
        buttons.button(QDialogButtonBox.Cancel).setText("Vazgeç")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        text = (self.input_amount.text() or "").strip()
        if not text:
            text = "0"
        normalized_text = text.replace(",", ".")
        try:
            value = Decimal(normalized_text).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            value = Decimal("0.00")
        self._amount = value
        self._paid = self.chk_paid.isChecked()
        super().accept()

    def get_result(self):
        return {"amount": self._amount, "paid": self._paid}


class LoanStatusDialog(QDialog):
    def __init__(
        self,
        student_id=None,
        loans=None,
        require_resolution=False,
        parent=None,
        title="Ödünç Durumu Güncelle",
        allowed_statuses=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 420)
        self.student_id = student_id
        self.require_resolution = require_resolution
        self._loans = loans[:] if loans else None
        self.resolved_count = 0
        self.allowed_statuses = set(allowed_statuses or [])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        info_label = QLabel(
            "Aşağıdaki listeden her ödünç kaydı için yeni durum seçin. "
            "Kayıtları kaydetmek için tüm satırların bir seçim yapması gerekir."
            if require_resolution
            else "Durumunu değiştirmek istediğiniz kayıtları seçin."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ["Kitap", "Barkod", "İade Tarihi", "Mevcut Durum", "Yeni Durum"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        layout.addWidget(self.table, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.btn_cancel = QPushButton("Vazgeç", self)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("Kaydet", self)
        self.btn_apply.setObjectName("DialogPositiveButton")
        self.btn_apply.clicked.connect(self.apply_changes)
        button_row.addWidget(self.btn_cancel)
        button_row.addWidget(self.btn_apply)
        layout.addLayout(button_row)

        self._populate()

    def _populate(self):
        loans = self._loans
        if loans is None and self.student_id:
            loans = loan_api.list_student_open_loans(self.student_id)
        loans = loans or []
        self._loans = loans

        self.table.setRowCount(len(loans))
        self._row_controls = []

        for row, loan in enumerate(loans):
            copy = loan.get("kitap_nusha") or {}
            book = copy.get("kitap") or loan.get("kitap") or {}
            title = book.get("baslik") if isinstance(book, dict) else str(book or "")
            title = normalize_entity_text(title)
            barkod = copy.get("barkod") or loan.get("barkod") or ""
            due = loan.get("iade_tarihi") or ""
            # Mevcut durum fast-query aktif kayıtlarında boş olabilir; iade tarihine göre türet
            cur_status = (loan.get("durum") or "").lower().strip()
            if not cur_status:
                # gecikmiş/ödünçte kestirimi
                try:
                    from datetime import datetime
                    d = str(due).replace("Z", "+00:00")
                    due_dt = datetime.fromisoformat(d) if d else None
                except Exception:
                    due_dt = None
                if due_dt and due_dt.date() < datetime.utcnow().date():
                    cur_status = "gecikmis"
                else:
                    cur_status = "oduncte"

            display_status = {
                "oduncte": "Ödünçte",
                "gecikmis": "Gecikmiş",
                "teslim": "Teslim",
                "kayip": "Kayıp",
                "hasarli": "Hasarlı",
                "iptal": "İptal",
            }.get(cur_status, cur_status.title())

            self.table.setItem(row, 0, QTableWidgetItem(title))
            self.table.setItem(row, 1, QTableWidgetItem(str(barkod or "")))
            self.table.setItem(row, 2, QTableWidgetItem((due or "")[:16]))
            self.table.setItem(row, 3, QTableWidgetItem(display_status))

            combo = QComboBox(self.table)
            for value, label in STATUS_OPTIONS:
                if value and self.allowed_statuses and value not in self.allowed_statuses:
                    continue
                combo.addItem(label, value or None)
            self.table.setCellWidget(row, 4, combo)

            self._row_controls.append(
                {
                    "loan": loan,
                    "combo": combo,
                }
            )

        if not loans:
            empty = QLabel("Bu öğrenciye ait açık ödünç kaydı bulunamadı.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#777; padding:16px;")
            self.table.setRowCount(0)
            self.table.setDisabled(True)
            self.btn_apply.setDisabled(True)
            self.layout().addWidget(empty)

    def apply_changes(self):
        if not self._row_controls:
            self.accept()
            return

        actions = []
        for row_data in self._row_controls:
            combo = row_data["combo"]
            status = combo.currentData()
            if status is None:
                if self.require_resolution:
                    QMessageBox.warning(
                        self,
                        "Eksik Seçim",
                        "Lütfen tüm kayıtlar için yeni durum seçin.",
                    )
                    return
                continue
            actions.append({"loan": row_data["loan"], "status": status})

        if not actions:
            QMessageBox.information(self, "Bilgi", "Herhangi bir değişiklik yapılmadı.")
            self.reject()
            return

        for action in actions:
            loan = action["loan"]
            loan_id = loan.get("id")
            if not loan_id:
                continue

            status = action["status"]
            teslim_iso = datetime.now(timezone.utc).isoformat()
            if status == "iptal":
                teslim_iso = None

            penalty_info = {"amount": Decimal("0"), "paid": False}
            extra_payload = {}
            if status in ("kayip", "hasarli"):
                status_label = "Kayıp" if status == "kayip" else "Hasarlı"
                student = loan.get("ogrenci") or {}
                copy = loan.get("kitap_nusha") or {}
                book = copy.get("kitap") or loan.get("kitap") or {}
                penalty_dialog = LossPenaltyDialog(
                    status_label=status_label,
                    student=student,
                    book=book,
                    parent=self,
                )
                if penalty_dialog.exec_() != QDialog.Accepted:
                    return
                penalty_info = penalty_dialog.get_result() or penalty_info
                amount = penalty_info.get("amount", Decimal("0"))
                if not isinstance(amount, Decimal):
                    try:
                        amount = Decimal(str(amount))
                    except (InvalidOperation, ValueError):
                        amount = Decimal("0")
                try:
                    amount = amount.quantize(Decimal("0.01"))
                except InvalidOperation:
                    amount = Decimal("0")
                penalty_info["amount"] = amount
                if not penalty_info.get("paid") and amount > Decimal("0"):
                    existing_amount = self._parse_decimal(loan.get("gecikme_cezasi"))
                    if loan.get("gecikme_cezasi_odendi"):
                        existing_amount = Decimal("0")
                    payload_amount = existing_amount + amount
                    extra_payload.update(
                        {
                            "gecikme_cezasi": format(payload_amount, ".2f"),
                            "gecikme_cezasi_odendi": False,
                            "gecikme_odeme_tarihi": None,
                            "gecikme_odeme_tutari": None,
                        }
                    )
                    penalty_info["recorded_total"] = payload_amount

            resp = loan_api.update_loan_status(
                loan_id,
                durum=status,
                teslim_tarihi=teslim_iso,
                extra_payload=extra_payload or None,
            )

            if resp.status_code not in (200, 202):
                detail = loan_api.extract_error(resp)
                header = response_error_message(resp, "Ödünç kaydı güncellenemedi")
                QMessageBox.warning(
                    self,
                    "İşlem Başarısız",
                    f"{header}.\n\nDetay: {detail}",
                )
                return

            copy = loan.get("kitap_nusha") or {}
            copy_id = copy.get("id")
            new_copy_status = COPY_STATUS_MAP.get(status)
            if copy_id and new_copy_status:
                copy_resp = loan_api.update_copy_status(copy_id, new_copy_status)
                if copy_resp is not None and copy_resp.status_code not in (200, 202):
                    header = response_error_message(copy_resp, "Nüsha durumu güncellenemedi")
                    detail = loan_api.extract_error(copy_resp)
                    QMessageBox.warning(
                        self,
                        "Uyarı",
                        f"{header}.\n\nDetay: {detail}",
                    )

            if status in ("kayip", "hasarli"):
                status_label = "Kayıp" if status == "kayip" else "Hasarlı"
                student = loan.get("ogrenci") or {}
                copy_data = copy or {}
                barkod = (copy_data.get("barkod") or loan.get("barkod") or "").strip()
                book = copy_data.get("kitap") or loan.get("kitap") or {}
                if isinstance(book, dict):
                    title = book.get("baslik") or book.get("title") or ""
                    book_payload = {"baslik": normalize_entity_text(title)}
                else:
                    book_payload = {"baslik": normalize_entity_text(str(book or ""))}
                due_date = loan.get("iade_tarihi") or ""
                amount_entered = penalty_info.get("amount", Decimal("0"))
                recorded_total = penalty_info.get("recorded_total")
                penalty_status = None
                if amount_entered > Decimal("0"):
                    penalty_status = "Ödendi" if penalty_info.get("paid") else "Ödenmedi"
                extra_lines = [f"Yeni durum: {status_label}"]
                if recorded_total and recorded_total != amount_entered:
                    extra_lines.append(f"Kayıtlı toplam ceza: {format_currency(recorded_total)}")
                detail = build_log_detail(
                    student={"ad": student.get("ad"), "soyad": student.get("soyad"), "ogrenci_no": student.get("ogrenci_no") or student.get("no")},
                    book=book_payload,
                    barcode=barkod,
                    date=due_date,
                    date_label="Planlanan iade",
                    penalty=amount_entered if amount_entered > Decimal("0") else None,
                    penalty_status=penalty_status,
                    extra=extra_lines,
                )
                log_api.safe_send_log(
                    f"Kitap {status_label.lower()} olarak işaretlendi",
                    detay=detail or f"Kitap {status_label.lower()} olarak işaretlendi",
                )
                if penalty_info.get("paid") and amount_entered > Decimal("0"):
                    log_api.safe_send_log("Tahsilat", detay=self._numeric_amount(amount_entered))

        self.resolved_count = len(actions)
        self.accept()

    def _parse_decimal(self, value):
        if isinstance(value, Decimal):
            return value
        if value in (None, "", False):
            return Decimal("0")
        if isinstance(value, (int, float)):
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return Decimal("0")
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    def _format_currency(self, amount):
        dec = self._parse_decimal(amount)
        try:
            dec = dec.quantize(Decimal("0.01"))
        except InvalidOperation:
            dec = Decimal("0.00")
        return f"{format(dec, '.2f')} ₺"

    def _numeric_amount(self, amount):
        dec = self._parse_decimal(amount)
        if dec == Decimal("0"):
            return "0"
        try:
            dec = dec.quantize(Decimal("0.01"))
        except InvalidOperation:
            dec = Decimal("0.00")
        text = format(dec, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"
