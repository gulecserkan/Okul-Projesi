from __future__ import annotations

from datetime import datetime, timezone

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
)

from api import loans as loan_api
from core.utils import response_error_message
from ui.entity_manager_dialog import normalize_entity_text

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

            resp = loan_api.update_loan_status(
                loan_id,
                durum=status,
                teslim_tarihi=teslim_iso,
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

        self.resolved_count = len(actions)
        self.accept()
