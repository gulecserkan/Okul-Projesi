from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, InvalidOperation

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox, QInputDialog, QLineEdit, QDialogButtonBox, QDialog,
    QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.config import get_api_base_url, load_settings
from core.utils import format_date, api_request
from ui.contact_prompt_dialog import (
    ContactReminderDialog,
    ContactEditDialog,
    PenaltyNoticeDialog,
    PenaltyDetailDialog,
    CheckoutConfirmDialog,
    MaxLoansDialog,
)
from api import students as student_api
from api import logs as log_api
from PyQt5 import sip
from ui.loan_status_dialog import LoanStatusDialog
from ui.detail_window import DetailWindow
from core.log_helpers import build_log_detail, format_currency
from printing.receipt_printer import (
    print_fine_payment_receipt,
    ReceiptPrintError,
    check_receipt_printer_status,
    print_receipt_from_template,
    build_receipt_context,
)


class QuickResultPanel(QWidget):
    MAX_ACTIVE_LOAN_CARDS = 5
    LOAN_CARD_HEIGHT_HINT = 120
    LOAN_CARD_VISIBLE_ROWS = 2.0
    detailStudentRequested = pyqtSignal(str)            # öğrenci_no
    editStudentRequested = pyqtSignal(str)              # öğrenci_no
    detailBookRequested = pyqtSignal(str, bool)         # barkod, include_history
    returnProcessed = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.student_no = None
        self.student_id = None
        self.book_barkod = None
        self.isbn_value = None
        self._return_in_progress = False
        self._active_loans_count = 0
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        self._return_in_progress = False
        self._checkout_in_progress = False
        self.penalty_summary = data.get("penalty_summary") if isinstance(data, dict) else None
        if not isinstance(self.penalty_summary, dict):
            self.penalty_summary = None
        self.penalty_total_label = None
        self.penalty_detail_button = None
        self.general_receipt_button = None
        self._penalty_action_mode = "detail"
        self._pending_penalty_entries = []

        # üst: info + history
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        t = data.get("type")

        # ---- ÖĞRENCİ ----

        if t == "student":
            stu = data.get("student") or data.get("ogrenci") or {}
            no = stu.get("no") or stu.get("ogrenci_no") or ""
            self.student_id = stu.get("id") if isinstance(stu, dict) else None
            sinif = stu.get("sinif")
            sinif_ad = sinif.get("ad") if isinstance(sinif, dict) else (sinif or "")
            is_active = self._is_student_active(stu)

            # Sol info card (küçük, sabit genişlik)
            summary = data.get("penalty_summary") if isinstance(data, dict) else None
            if isinstance(summary, dict):
                self.penalty_summary = summary
            else:
                summary = self.penalty_summary

            info_lines = [
                (f"{stu.get('ad','')} {stu.get('soyad','')}", ""),
                (f"No: {no}", f"Sınıf: {sinif_ad}")
            ]
            # Başlık: pasif ise sol başlık yanında kırmızı etiket
            info_inner_card = self.create_card(None, info_lines, "InfoCard")
            if not is_active:
                header = QWidget()
                hb = QHBoxLayout(header)
                hb.setContentsMargins(0, 0, 0, 0)
                hb.setSpacing(8)
                lbl_title = QLabel("👤 Öğrenci")
                lbl_title.setStyleSheet("font-size:19px; font-weight:bold;")
                lbl_badge = QLabel("❌ Pasif öğrenci")
                lbl_badge.setStyleSheet("color:#e74c3c; font-weight:600;")
                hb.addWidget(lbl_title)
                hb.addWidget(lbl_badge)
                hb.addStretch(1)
                header.setLayout(hb)
                info_card = self.create_card_group(header, [info_inner_card])
            else:
                info_card = self.create_card_group("👤 Öğrenci", [info_inner_card])
            top_layout.addWidget(info_card, 0, alignment=Qt.AlignTop)

            # Sağ tarafta ödünç kartları
            hist_box = QVBoxLayout()
            student_cards = []

            active_loans = sorted(
                data.get("active_loans", []),
                key=lambda x: x.get("iade_tarihi") or "",
            )

            today = datetime.now().date()
            loan_prefs = self._get_loan_preferences()
            grace_days = int((loan_prefs or {}).get("delay_grace_days") or 0)
            self._active_loans_count = len(active_loans)
            self._pending_penalty_entries = self._collect_pending_penalties(active_loans)
            display_loans = active_loans[: self.MAX_ACTIVE_LOAN_CARDS] if self.MAX_ACTIVE_LOAN_CARDS else active_loans
            hidden_count = max(0, len(active_loans) - len(display_loans))
            for loan in display_loans:
                title = ((loan.get("kitap_nusha") or {}).get("kitap") or {}).get("baslik") \
                        or loan.get("kitap") or ""
                barkod = (loan.get("kitap_nusha") or {}).get("barkod") or loan.get("barkod") or ""
                raw_due = loan.get("iade_tarihi")
                tarih_str = format_date(raw_due)
                status = (loan.get("durum") or "").lower()
                status_text_map = {
                    "kayip": "Kayıp",
                    "hasarli": "Hasarlı",
                    "oduncte": "Ödünçte",
                    "gecikmis": "Gecikmiş",
                }

                if status in ("kayip", "hasarli"):
                    style = "HistoryCardDisabled"
                    sag = f"Durum: {status_text_map.get(status, status.title())}"
                else:
                    due_date = self._parse_date(raw_due)
                    effective_due = due_date + timedelta(days=grace_days) if due_date else None
                    kalan = (effective_due - today).days if effective_due else None

                    if kalan is None:
                        style = "HistoryCard"
                    elif kalan < 0:
                        style = "HistoryCardExpired"
                    elif kalan <= 2:
                        style = "HistoryCardWarning"
                    else:
                        style = "HistoryCardActive"

                    if status in status_text_map and status not in ("oduncte", "gecikmis"):
                        sag = f"Durum: {status_text_map.get(status)}"
                    else:
                        sag = f"İade: {tarih_str or '—'}"

                    sol = f"{title} ({barkod})"
                    lines = [(sol, sag)]
                    card = self.create_card(None, lines, style)
                    loan_id = loan.get("id")
                    if loan_id:
                        btn_update = QPushButton("Kayıp/Hasarlı")
                        btn_update.setObjectName("SecondaryButton")
                        btn_update.setCursor(Qt.PointingHandCursor)
                        btn_update.clicked.connect(lambda _, ln=loan: self.handle_issue_report(ln))
                        btn_return = QPushButton("İade Al")
                        btn_return.setObjectName("ReturnButton")
                        btn_return.clicked.connect(lambda _, ln=loan: self.prompt_return(ln))
                        btn_return.setCursor(Qt.PointingHandCursor)
                        btn_return.setMinimumHeight(38)
                        btn_return.setMinimumHeight(40)
                        action_row = QHBoxLayout()
                        action_row.addStretch(1)
                        action_row.addWidget(btn_update)
                        action_row.addWidget(btn_return)
                        card.layout().addLayout(action_row)
                    student_cards.append(card)

            lbl_active = QLabel("📚 Aktif Ödünç Kayıtları")
            lbl_active.setStyleSheet("font-size:19px; font-weight:bold;")
            hist_box.addWidget(lbl_active)

            cards_host = QWidget()
            cards_layout = QVBoxLayout(cards_host)
            cards_layout.setContentsMargins(0, 0, 0, 0)
            cards_layout.setSpacing(8)

            if student_cards:
                for card in student_cards:
                    contents = card.layout()
                    if contents:
                        contents.setContentsMargins(8, 6, 8, 6)
                    cards_layout.addWidget(card, 0, Qt.AlignTop)
            else:
                self._active_loans_count = 0
                empty_card = self.create_card(
                    None,
                    ["Bu öğrencinin aktif ödünç kaydı bulunmamaktadır."],
                    "HistoryCard"
                )
                cards_layout.addWidget(empty_card, 0, Qt.AlignTop)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(cards_host)
            cards_count = len(student_cards) if student_cards else 1
            visible_rows = min(self.LOAN_CARD_VISIBLE_ROWS, cards_count if cards_count > 0 else 1)
            height_hint = int(self.LOAN_CARD_HEIGHT_HINT * visible_rows)
            scroll.setFixedHeight(max(80, height_hint))
            hist_box.addWidget(scroll)

            if student_cards and hidden_count > 0:
                lbl_hidden = QLabel(
                    f"+{hidden_count} kayıt daha var (ilk {self.MAX_ACTIVE_LOAN_CARDS} kayıt gösterilir)."
                )
                lbl_hidden.setStyleSheet("color:#7f8c8d; font-size:12px;")
                hist_box.addWidget(lbl_hidden)

            self._active_loans_count = len(active_loans)
            self._inject_penalty_info(info_inner_card, summary)
            top_layout.addLayout(hist_box, 1)
            self.student_no = no

        # if t == "student":
        #     stu = data.get("student") or data.get("ogrenci") or {}
        #     no = stu.get("no") or stu.get("ogrenci_no") or ""
        #     sinif = stu.get("sinif")
        #     sinif_ad = sinif.get("ad") if isinstance(sinif, dict) else (sinif or "")

        #     # Sol info card (küçük, sabit genişlik)
        #     info_lines = [
        #         (f"{stu.get('ad','')} {stu.get('soyad','')}",""),(f"No: {no}",f"Sınıf: {sinif_ad}"),
        #         #f"Rol: {stu.get('rol',{}).get('ad','') if isinstance(stu.get('rol'), dict) else ''}"
        #     ]

        #     info_card = self.create_card_group("👤 Öğrenci", [self.create_card(None, info_lines, "InfoCard"),])
        #     #info_card.setFixedWidth(200)
        #     top_layout.addWidget(info_card, 0,Qt.AlignTop)

        #     # Sağ history cards (max 2 satır)
        #     loans = data.get("active_loans", [])
        #     hist_box = QVBoxLayout()
        #     cards=[]
        #     for loan in loans[:5]:
        #         title = ((loan.get("kitap_nusha") or {}).get("kitap") or {}).get("baslik") \
        #                 or loan.get("kitap") or ""
        #         tarih = str(loan.get("iade_tarihi") or "")[:10]
        #         #durum = loan.get("durum", "")
        #         lines = [(f"{title}",f"İade: {tarih}")]
        #         cards.append(self.create_card(None, lines, "HistoryCard"))

        #     hist_box.addWidget(self.create_card_group("📚 Aktif Ödünç Kayıtları",cards),0,Qt.AlignTop)
        #     top_layout.addLayout(hist_box, 1)

        #     self.student_no = no

        # ---- KİTAP NÜSHA ----
        if t == "book_copy":
            book = data.get("book", {}) or {}
            copy = data.get("copy", {}) or {}
            barkod = copy.get("barkod", "")
            kategori = book.get("kategori")
            loan=data.get("loan")
            copy_status = (copy.get("durum") or "").lower()
            status_text_map = {
                "mevcut": "Mevcut",
                "oduncte": "Ödünçte",
                "kayip": "Kayıp",
                "hasarli": "Hasarlı",
                "gecikmis": "Gecikmiş",
            }

            if isinstance(kategori, dict):
                kategori_ad=kategori.get("ad", "")
            else:
                kategori_ad = str(kategori or "")

            # Sol info card
            info_lines = [
                (f"{book.get('baslik','')}",""),
                (f"Yazar: {book.get('yazar',{}).get('ad_soyad','') if isinstance(book.get('yazar'), dict) else book.get('yazar','')}",""),
                (f"Kategori: {kategori_ad}", ""),
                (f"Barkod: {copy.get('barkod','')}",f"Raf: {copy.get('raf_kodu','')}")
            ]
            history = data.get("history", []) or []
            latest_history_status = (
                (history[0].get("durum") or "") if history else ""
            ).lower()

            effective_status = copy_status
            if loan:
                effective_status = (loan.get("durum") or "oduncte").lower()
            elif effective_status in ("", "mevcut") and latest_history_status in {"kayip", "hasarli"}:
                effective_status = latest_history_status
            elif effective_status in ("", None) and latest_history_status:
                effective_status = latest_history_status

            status_label = status_text_map.get(effective_status)
            if status_label:
                info_lines.append((f"Durum: {status_label}", ""))

            info_card_widget = self.create_card(None, info_lines, "InfoCard")
            can_checkout = (not loan) and effective_status in ("", "mevcut")
            if can_checkout:
                btn_checkout = QPushButton("Ödünç Ver")
                btn_checkout.setObjectName("CheckoutButton")
                btn_checkout.setCursor(Qt.PointingHandCursor)
                btn_checkout.clicked.connect(lambda _, cp=copy, bk=book: self.prompt_checkout(cp, book_info=bk))
                info_card_widget.layout().addWidget(btn_checkout, alignment=Qt.AlignRight)

            info_card = self.create_card_group("📖 Kitap", [info_card_widget])
            #info_card.setFixedWidth(200)
            top_layout.addWidget(info_card, 0,Qt.AlignTop)

            # Sağ history cards
            hist_box = QVBoxLayout()
            history = data.get("history", []) or []
            history_cards = []
            active_id = loan.get("id") if loan else None

            if loan:
                ogr = loan.get("ogrenci", {}) or {}
                adsoyad = f"{ogr.get('ad','')} {ogr.get('soyad','')}".strip()
                ogr_no = ogr.get("ogrenci_no") or ogr.get("no")
                if ogr_no:
                    self.student_no = ogr_no
                if isinstance(data.get("penalty_summary"), dict):
                    self.penalty_summary = data.get("penalty_summary")
                if not self._is_student_active(ogr):
                    adsoyad = f"{adsoyad}   ❌ Pasif öğrenci"
                donus = format_date(loan.get("iade_tarihi"))
                lines = [(f"{adsoyad}", f"🕓 Dönüş: {donus or '—'}")]
                status_current = (loan.get("durum") or "").lower()
                penalty_preview = loan.get("penalty_preview") or loan.get("gecikme_cezasi")
                outstanding_total = self._parse_decimal((self.penalty_summary or {}).get("outstanding_total"))
                entry_amount = Decimal("0")
                if outstanding_total > Decimal("0"):
                    entries = (self.penalty_summary or {}).get("entries") or []
                    for entry in entries:
                        if entry.get("id") == loan.get("id"):
                            entry_amount = self._parse_decimal(entry.get("gecikme_cezasi"))
                            break
                if status_current == "gecikmis":
                    penalty_amount = entry_amount
                    if penalty_amount == Decimal("0") and penalty_preview not in (None, ""):
                        penalty_amount = self._parse_decimal(penalty_preview)
                    penalty_text = self._format_currency(penalty_amount) if penalty_amount > Decimal("0") else "—"
                    lines.append(("⚠️ Gecikme", f"Ceza: {penalty_text}"))
                if outstanding_total > Decimal("0"):
                    lines.append(("Toplam ceza", self._format_currency(outstanding_total)))
                active_style = "HistoryCardExpired" if status_current == "gecikmis" else "HistoryCardWarning"
                active_card = self.create_card(None, lines, active_style)
                if loan.get("id"):
                    btn_update = QPushButton("Kayıp\nHasarlı")
                    btn_update.setObjectName("SecondaryButton")
                    btn_update.setCursor(Qt.PointingHandCursor)
                    btn_update.clicked.connect(lambda _, ln=loan: self.handle_issue_report(ln))
                    btn_return = QPushButton("İade Al")
                    btn_return.setMinimumWidth(100)
                    btn_return.setObjectName("ReturnButton")
                    btn_return.setCursor(Qt.PointingHandCursor)
                    btn_return.clicked.connect(lambda _, ln=loan: self.prompt_return(ln))
                    btn_return.setMinimumHeight(40)
                    button_row = QHBoxLayout()
                    button_row.addStretch(1)
                    button_row.addWidget(btn_update)
                    button_row.addWidget(btn_return)
                    active_card.layout().addLayout(button_row)
                history_cards.append(active_card)

            for rec in history[:5]:
                if active_id and rec.get("id") == active_id:
                    continue
                ogr = rec.get("ogrenci", {}) or {}
                adsoyad = f"{ogr.get('ad','')} {ogr.get('soyad','')}"
                durum = (rec.get("durum") or "").lower()
                label_text = {
                    "teslim": "✅ Teslim",
                    "kayip": "⚠️ Kayıp",
                    "hasarli": "⚠️ Hasarlı",
                    "gecikmis": "⚠️ Gecikmiş",
                    "iptal": "⛔ İptal",
                }.get(durum, "📘 Kayıt")

                tarih = format_date(rec.get("teslim_tarihi") or rec.get("iade_tarihi")) or "—"

                if durum in ("kayip", "hasarli"):
                    card_style = "HistoryCardDisabled"
                elif durum == "gecikmis":
                    card_style = "HistoryCardExpired"
                elif durum == "oduncte":
                    card_style = "HistoryCardWarning"
                else:
                    card_style = "HistoryCard"

                lines = [(f"{adsoyad}", f"{label_text}: {tarih}")]
                history_cards.append(self.create_card(None, lines, card_style))
            if history_cards:    
                hist_box.addWidget(self.create_card_group("👥 Kimler almış?",history_cards),0,Qt.AlignTop)
                #print(cards.__len__())
            else:
                hist_box.addWidget(self.create_card(None,["Bu kitap için herhangi bir ödünç işlemi olmamıştır.",],"HistoryCardActive"))
            top_layout.addLayout(hist_box, 1)

            self.book_barkod = barkod

        # ---- ISBN ----
        if t == "isbn":
            if data.get("exists"):
                book = data.get("book", {}) or {}
                baslik = book.get("baslik", "")
                yazar = book.get("yazar", {})
                if isinstance(yazar, dict):
                    yazar = yazar.get("ad_soyad") or ""
                kategori = book.get("kategori", "")
                if isinstance(kategori, dict):
                    kategori = kategori.get("ad") or ""
                isbn = book.get("isbn") or data.get("query") or ""

                self.isbn_value = isbn
                summary = data.get("copy_summary") or {}
                if not summary:
                    summary = self.fetch_isbn_summary(isbn)
                else:
                    summary = {
                        "count": summary.get("count", 0),
                        "loaned": summary.get("loaned", 0),
                        "available": summary.get("available", 0),
                        "first_barkod": summary.get("first_barkod"),
                    }
                self.isbn_summary = summary
                if summary.get("first_barkod"):
                    self.book_barkod = summary["first_barkod"]

                info_lines = [
                    (baslik or "—", f"ISBN: {isbn or '—'}"),
                    (f"Yazar: {yazar or '—'}", f"Kategori: {kategori or '—'}")
                ]
                info_lines.append((f"Nüsha sayısı: {summary.get('count', 0)}", f"Rafta: {summary.get('available', 0)}"))
                info_lines.append(("", f"Ödünçte: {summary.get('loaned', 0)}"))
                info_card = self.create_card("📘 Kitap", info_lines, "InfoCardWide")
            else:
                info = [("Bu ISBN kayıtlı değil.",""),("", "Kitap eklemek ister misiniz?")]
                info_card = self.create_card("ISBN", info, "InfoCard")
            #info_card.setFixedWidth(200)
            top_layout.addWidget(info_card, 0, alignment=Qt.AlignTop)

        if t == "error":
            msg = data.get("msg") or "Beklenmeyen bir hata oluştu."
            info_card = self.create_card("Hata", [(msg, "")], "InfoCard")
            top_layout.addWidget(info_card, 0, alignment=Qt.AlignTop)

        # ---- NOT FOUND ----
        if t == "not_found":
            info_card = self.create_card("Sonuç", [("Kayıt bulunamadı.","")], "InfoCard")
            info_card.setFixedWidth(200)
            top_layout.addWidget(info_card)

        layout.addLayout(top_layout)

        # Alt aksiyon butonları
        actions = QHBoxLayout()
        if t == "student" and getattr(self, "student_no", None):
            btn_detail = QPushButton("Detaylı Geçmiş")
            btn_detail.clicked.connect(lambda: self.detailStudentRequested.emit(self.student_no))
            actions.addWidget(btn_detail)
        elif t == "book_copy" and getattr(self, "book_barkod", None):
            btn_detail = QPushButton("Detaylı Geçmiş")
            btn_detail.clicked.connect(lambda: self.detailBookRequested.emit(self.book_barkod, True))
            actions.addWidget(btn_detail)
        elif t == "isbn" and getattr(self, "book_barkod", None):
            btn_detail = QPushButton("Detaylı Görünüm")
            btn_detail.clicked.connect(lambda: self.detailBookRequested.emit(self.book_barkod, False))
            actions.addWidget(btn_detail)

        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.closed.emit)
        actions.addWidget(btn_close)

        layout.addLayout(actions)
        self.setLayout(layout)

    def _is_student_active(self, stu: dict) -> bool:
        try:
            if not isinstance(stu, dict):
                return True
            if "aktif" in stu:
                val = stu.get("aktif")
                # Doğrudan bool
                if isinstance(val, bool):
                    return val
                # Sayısal 0/1
                if isinstance(val, (int, float)):
                    return bool(val)
                # Metin: "false", "0" vs.
                txt = str(val).strip().lower()
                if txt in {"false", "hayır", "hayırlı", "no", "0", "pasif"}:
                    return False
                if txt in {"true", "evet", "yes", "1", "aktif"}:
                    return True
            # pasif_tarihi varsa pasif say
            if stu.get("pasif_tarihi"):
                return False
            return True
        except Exception:
            return True

    def create_card(self, title, lines, style_class="HistoryCard"):
        frame = QFrame()
        frame.setObjectName(style_class)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(3,3,3,1)
        vbox.setSpacing(2)
        if style_class == "InfoCardWide":
            frame.setMinimumWidth(320)
            frame.setMaximumWidth(420)
        # Başlık
        if title:
            label = QLabel(title)
            label.setStyleSheet("font-weight:bold;")
            vbox.addWidget(label)
        ilk=True
        for l in lines:
            if isinstance(l, (tuple, list)) and len(l) == 2:
                # İki kolonlu satır: sol & sağ
                hbox = QHBoxLayout()
                left = QLabel(l[0])
                if ilk:
                    left.setStyleSheet("font-weight:bold;")
                    ilk=False
                right = QLabel(l[1])
                hbox.addWidget(left, alignment=Qt.AlignLeft)
                hbox.addWidget(right, alignment=Qt.AlignRight)
                vbox.addLayout(hbox)
            else:
                vbox.addWidget(QLabel(str(l)))
        
        frame.setLayout(vbox)
        return frame


    def create_card_group(self, group_title, cards):
        frame = QFrame()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)
        # Başlık string ise QLabel oluştur; QWidget ise doğrudan ekle
        if isinstance(group_title, str):
            label = QLabel(group_title)
            label.setStyleSheet("font-size:19px; font-weight:bold;")
            vbox.addWidget(label)
        else:
            try:
                vbox.addWidget(group_title)
            except Exception:
                label = QLabel(str(group_title))
                label.setStyleSheet("font-size:19px; font-weight:bold;")
                vbox.addWidget(label)
        
        for c in cards:
            vbox.addWidget(c,0,Qt.AlignTop)
        
        frame.setLayout(vbox)
        return frame

    def open_loan_status_dialog(self, loans, require_resolution=False, allowed_statuses=None):
        if not loans:
            return
        first = loans[0] or {}
        ogr = first.get("ogrenci") if isinstance(first, dict) else None
        student_id = None
        if isinstance(ogr, dict):
            student_id = ogr.get("id")
        if not student_id:
            student_id = self.student_id

        dialog = LoanStatusDialog(
            student_id=student_id,
            loans=loans,
            require_resolution=require_resolution,
            parent=self,
            title="Ödünç Durumunu Güncelle",
            allowed_statuses=allowed_statuses,
        )
        if dialog.exec_() == QDialog.Accepted and dialog.resolved_count:
            QMessageBox.information(self, "İşlem Tamamlandı", "Ödünç kaydı güncellendi.")
            self.returnProcessed.emit()

    def prompt_return(self, loan):
        if self._return_in_progress:
            return
        loan_id = loan.get("id")
        if not loan_id:
            QMessageBox.warning(self, "İşlem Başarısız", "Bu kaydın kimliği bulunamadı.")
            return

        expected_no = self._expected_student_no(loan)
        expected_barkod = self._expected_barkod(loan)
        verify_mode = "student"
        expected_value = expected_no
        if self.student_no and expected_barkod:
            verify_mode = "barcode"
            expected_value = expected_barkod
        button = self.sender()
        self._set_button_enabled(button, False)

        if expected_value:
            entered, ok = self._prompt_student_code(expected_value, mode=verify_mode)
            if not ok:
                self._set_button_enabled(button, True)
                return
            expected_str = str(expected_value).strip()
            if entered.strip() != expected_str:
                message = "Barkod eşleşmiyor." if verify_mode == "barcode" else "Öğrenci numarası eşleşmiyor."
                QMessageBox.warning(self, "Onay Hatası", message)
                if isinstance(button, QPushButton):
                    self._set_button_enabled(button, True)
                return

        if expected_no:
            self.fetch_penalty_summary(expected_no)
        else:
            self.fetch_penalty_summary()

        penalty_preview = loan.get("penalty_preview") or loan.get("gecikme_cezasi")
        current_penalty = self._parse_decimal(penalty_preview)
        summary_dict = self.penalty_summary or {}
        outstanding_total = self._parse_decimal(summary_dict.get("outstanding_total"))
        entry_amount = current_penalty
        entries = summary_dict.get("entries") or []
        for entry in entries:
            if entry.get("id") == loan_id:
                entry_amount = self._parse_decimal(entry.get("gecikme_cezasi"))
                break
        previous_outstanding = outstanding_total
        if previous_outstanding < Decimal("0"):
            previous_outstanding = Decimal("0")

        penalty_override = None
        penalty_payment_amount = None
        if current_penalty > Decimal("0"):
            alert = QMessageBox(self)
            alert.setWindowTitle("Gecikme Cezası")
            alert.setIcon(QMessageBox.Warning)
            lines = [f"Bu iade için gecikme cezası: {self._format_currency(current_penalty)}"]
            if previous_outstanding > Decimal("0"):
                lines.append(f"Diğer ödenmemiş cezalar: {self._format_currency(previous_outstanding)}")
            alert.setText("\n".join(lines))
            alert.setInformativeText("Ödeme alındıysa 'Ceza Ödendi'yi seçin.")
            btn_paid = alert.addButton("Ceza Ödendi", QMessageBox.AcceptRole)
            btn_unpaid = alert.addButton("Ödenmedi", QMessageBox.DestructiveRole)
            btn_cancel = alert.addButton("Vazgeç", QMessageBox.RejectRole)
            btn_paid.setObjectName("DialogPositiveButton")
            btn_unpaid.setObjectName("DialogWarnButton")
            btn_cancel.setObjectName("DialogDangerButton")
            self._apply_dialog_style(alert)
            self._attach_receipt_warning_to_box(alert)
            alert.exec_()
            clicked = alert.clickedButton()
            if clicked == btn_cancel:
                if isinstance(button, QPushButton):
                    self._set_button_enabled(button, True)
                return
            if clicked == btn_paid:
                penalty_override = Decimal("0")
                penalty_payment_amount = entry_amount if entry_amount > Decimal("0") else current_penalty
        elif outstanding_total > Decimal("0"):
            info = QMessageBox(self)
            info.setWindowTitle("Bekleyen Ceza")
            info.setIcon(QMessageBox.Information)
            info.setText("Bu öğrencinin ödenmemiş ceza bakiyesi bulunuyor.")
            info.setInformativeText(f"Toplam tutar: {self._format_currency(outstanding_total)}")
            info.addButton("Tamam", QMessageBox.AcceptRole)
            btn_detail = info.addButton("Ceza Detayı", QMessageBox.ActionRole)
            self._apply_dialog_style(info)
            info.exec_()
            if info.clickedButton() == btn_detail:
                self.open_penalty_detail()

        mode = "return"
        if self._is_same_day_loan(loan):
            choice = self._ask_return_mode()
            if choice == "cancel_operation":
                if isinstance(button, QPushButton):
                    self._set_button_enabled(button, True)
                return
            elif choice == "loan_cancel":
                mode = "cancel"
            # else remain "return"
        success = self.process_return(
            loan,
            mode=mode,
            penalty_override=penalty_override,
            penalty_payment_amount=penalty_payment_amount,
        )
        if success and penalty_payment_amount is not None:
            summary = self.fetch_penalty_summary(self.student_no)
            self._attempt_penalty_receipt(summary, penalty_payment_amount)
        if not success and isinstance(button, QPushButton):
            self._set_button_enabled(button, True)

    def process_return(self, loan, mode="return", penalty_override=None, penalty_payment_amount=None):
        loan_id = loan.get("id")
        if not loan_id:
            return False
        self._return_in_progress = True
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            if mode == "cancel":
                payload = {
                    "durum": "iptal",
                    "teslim_tarihi": None,
                    "gecikme_cezasi": 0
                }
            else:
                payload = {
                    "durum": "teslim",
                    "teslim_tarihi": now_iso
                }
                if penalty_override is not None:
                    payload["gecikme_cezasi"] = self._format_decimal_for_payload(penalty_override)
                    paid = penalty_payment_amount is not None and penalty_payment_amount > Decimal("0")
                    payload["gecikme_cezasi_odendi"] = paid
                    if paid:
                        payload["gecikme_odeme_tarihi"] = now_iso
                        payload["gecikme_odeme_tutari"] = self._format_decimal_for_payload(penalty_payment_amount)
                    else:
                        payload["gecikme_odeme_tarihi"] = None
                        payload["gecikme_odeme_tutari"] = None
            resp = api_request("PATCH", self._api_url(f"oduncler/{loan_id}/"), json=payload)
            if resp.status_code not in (200, 202):
                QMessageBox.warning(self, "İşlem Başarısız", f"İade kaydedilemedi ({resp.status_code}).")
                return False

            updated = {}
            try:
                updated = resp.json() or {}
            except Exception:
                updated = {}

            copy = updated.get("kitap_nusha") or loan.get("kitap_nusha") or {}
            copy_id = copy.get("id")
            if copy_id:
                try:
                    copy_resp = api_request("PATCH", self._api_url(f"nushalar/{copy_id}/"), json={"durum": "mevcut"})
                    if copy_resp.status_code not in (200, 202):
                        print("Nüsha durumu güncellenemedi:", copy_resp.status_code)
                except Exception as exc:
                    print("Nüsha durumu güncellenirken hata:", exc)

            if mode == "cancel":
                log_action = "Ödünç iptali"
                ogrenci = (updated or {}).get("ogrenci") or loan.get("ogrenci") or {}
                copy = (updated or {}).get("kitap_nusha") or loan.get("kitap_nusha") or {}
                barkod = copy.get("barkod") or loan.get("barkod")
                kitap = copy.get("kitap") or loan.get("kitap") or {}
                detail = build_log_detail(
                    student=self._student_log_payload(ogrenci),
                    book=self._book_log_payload(kitap),
                    barcode=barkod,
                    extra="İşlem: Ödünç iptal edildi",
                )
                log_api.safe_send_log(log_action, detay=detail or "Ödünç işlemi iptal edildi.")
                QMessageBox.information(self, "Ödünç İptal", "Ödünç işlemi iptal edildi.")
            else:
                log_action = "İade alma"
                ogrenci = (updated or {}).get("ogrenci") or loan.get("ogrenci") or {}
                copy = (updated or {}).get("kitap_nusha") or loan.get("kitap_nusha") or {}
                barkod = copy.get("barkod") or loan.get("barkod")
                kitap = copy.get("kitap") or loan.get("kitap") or {}
                due_text = ""
                raw_due = (updated or {}).get("iade_tarihi") or loan.get("iade_tarihi")
                if raw_due:
                    due_text = format_date(raw_due)
                penalty_value = None
                penalty_status = None
                if penalty_override is not None:
                    paid_amount = self._parse_decimal(penalty_payment_amount) if penalty_payment_amount is not None else Decimal("0")
                    override_amount = self._parse_decimal(penalty_override)
                    penalty_value = paid_amount if paid_amount > Decimal("0") else override_amount
                    penalty_status = "Ödendi" if paid_amount > Decimal("0") else "Ödenmedi"
                elif loan.get("gecikme_cezasi"):
                    unpaid_amount = self._parse_decimal(loan.get("gecikme_cezasi"))
                    if unpaid_amount > Decimal("0"):
                        penalty_value = unpaid_amount
                        penalty_status = "Ödendi" if loan.get("gecikme_cezasi_odendi") else "Ödenmedi"
                detail = build_log_detail(
                    student=self._student_log_payload(ogrenci),
                    book=self._book_log_payload(kitap),
                    barcode=barkod,
                    date=due_text or raw_due,
                    date_label="Asıl iade",
                    penalty=penalty_value,
                    penalty_status=penalty_status,
                )
                log_api.safe_send_log(log_action, detay=detail or "Kitap iadesi kaydedildi.")
                if penalty_payment_amount and self._parse_decimal(penalty_payment_amount) > Decimal("0"):
                    log_api.safe_send_log("Tahsilat", detay=self._numeric_amount(penalty_payment_amount))
                QMessageBox.information(self, "İade Alındı", "Kitap iadesi başarıyla kaydedildi.")
            self.returnProcessed.emit()
            return True
        finally:
            self._return_in_progress = False
        return False

    def handle_issue_report(self, loan):
        if not isinstance(loan, dict):
            return
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Warning)
        confirm.setWindowTitle("Durum Güncelle")
        confirm.setText("Bu işlem sadece kitap geri gelemiyorsa kullanılmalıdır.")
        confirm.setInformativeText("Kitap kayıp ya da hasarlıysa devam edin.")
        btn_continue = confirm.addButton("Devam", QMessageBox.AcceptRole)
        btn_cancel = confirm.addButton("İptal", QMessageBox.RejectRole)
        confirm.setDefaultButton(btn_cancel)
        confirm.exec_()
        if confirm.clickedButton() != btn_continue:
            return

        expected_no = self._expected_student_no(loan)
        if expected_no:
            entered, ok = self._prompt_student_code(expected_no, mode="student")
            if not ok or entered.strip() != str(expected_no).strip():
                if ok:
                    QMessageBox.warning(self, "Onay Hatası", "Öğrenci numarası eşleşmiyor.")
                return

        self.open_loan_status_dialog(
            [loan],
            require_resolution=False,
            allowed_statuses={"kayip", "hasarli"},
        )

    def prompt_checkout(self, copy_info, *, book_info=None):
        if self._checkout_in_progress:
            return
        barkod = (copy_info or {}).get("barkod")
        if not barkod:
            QMessageBox.warning(self, "İşlem Başarısız", "Nüsha barkodu bulunamadı.")
            return

        button = self.sender()
        self._set_button_enabled(button, False)

        ogr_no, ok = QInputDialog.getText(
            self,
            "Ödünç Ver",
            "Öğrenci numarasını girin:",
            QLineEdit.Normal
        )
        if not ok or not ogr_no.strip():
            self._set_button_enabled(button, True)
            return

        ogr_no = ogr_no.strip()
        stu_resp = api_request("GET", self._api_url(f"fast-query/?q={ogr_no}"))
        if stu_resp.status_code != 200:
            QMessageBox.warning(self, "İşlem Başarısız", f"Öğrenci doğrulanamadı ({stu_resp.status_code}).")
            self._set_button_enabled(button, True)
            return

        stu_data = {}
        try:
            stu_data = stu_resp.json() or {}
        except Exception:
            stu_data = {}

        if stu_data.get("type") != "student":
            QMessageBox.warning(self, "İşlem Başarısız", "Girilen numaraya ait öğrenci bulunamadı.")
            self._set_button_enabled(button, True)
            return

        stu = stu_data.get("student") or {}
        adsoyad = f"{stu.get('ad','')} {stu.get('soyad','')}".strip()
        sinif_info = stu.get("sinif")
        if isinstance(sinif_info, dict):
            sinif = sinif_info.get("ad", "—")
        else:
            sinif = sinif_info or "—"
        if not self._is_student_active(stu):
            QMessageBox.warning(
                self,
                "Ödünç Verilemez",
                "Bu öğrenci pasif durumda olduğu için ödünç işlemi yapılamaz."
            )
            detail = build_log_detail(
                student=self._student_log_payload(stu),
                extra="Pasif öğrenci için ödünç verme girişimi"
            )
            log_api.safe_send_log("Pasif öğrenci engeli", detay=detail or "Pasif öğrenciye ödünç verme denemesi.")
            if isinstance(button, QPushButton):
                self._set_button_enabled(button, True)
            return
        phone = (stu.get("telefon") or "").strip()
        email = (stu.get("eposta") or "").strip()
        missing = []
        if not phone:
            missing.append("telefon")
        if not email:
            missing.append("e-posta")
        if missing:
            display_student = stu.copy()
            display_student["sinif"] = sinif
            reminder = ContactReminderDialog(student=display_student, missing_fields=missing, parent=self.window())
            reminder.setWindowModality(Qt.ApplicationModal)
            reminder.exec_()
            if reminder.result_code == ContactReminderDialog.RESULT_CANCEL:
                if isinstance(button, QPushButton):
                    self._set_button_enabled(button, True)
                return
            if reminder.result_code == ContactReminderDialog.RESULT_UPDATE:
                edit_dlg = ContactEditDialog(student=display_student, missing_fields=missing, parent=self.window())
                edit_dlg.setWindowModality(Qt.ApplicationModal)
                edit_dlg.exec_()
                if edit_dlg.result_code == ContactEditDialog.RESULT_CANCEL:
                    self._set_button_enabled(button, True)
                    return
                if edit_dlg.result_code == ContactEditDialog.RESULT_SAVE:
                    student_id = stu.get("id")
                    payload = {}
                    if edit_dlg.normalized_phone is not None:
                        payload["telefon"] = edit_dlg.normalized_phone
                    if edit_dlg.email_value is not None:
                        payload["eposta"] = edit_dlg.email_value
                    if payload and student_id:
                        resp = student_api.patch_student(student_id, payload)
                        if resp.status_code not in (200, 202):
                            QMessageBox.warning(
                                self,
                                "Güncelleme Başarısız",
                                f"İletişim bilgileri kaydedilemedi ({resp.status_code})."
                            )
                            if isinstance(button, QPushButton):
                                self._set_button_enabled(button, True)
                            return
                        if edit_dlg.normalized_phone is not None:
                            phone = edit_dlg.display_phone
                            stu["telefon"] = edit_dlg.normalized_phone
                        if edit_dlg.email_value is not None:
                            email = edit_dlg.email_value
                            stu["eposta"] = edit_dlg.email_value
                        stu_data["student"] = stu
                    else:
                        if edit_dlg.normalized_phone is not None:
                            phone = edit_dlg.display_phone
                        if edit_dlg.email_value is not None:
                            email = edit_dlg.email_value
                # Skip durumunda mevcut bilgilerle devam edilir.
        summary = self.fetch_penalty_summary(ogr_no)
        outstanding_total = self._parse_decimal((summary or {}).get("outstanding_total"))
        loan_prefs = self._get_loan_preferences()
        if outstanding_total > Decimal("0"):
            penalty_dialog = PenaltyNoticeDialog(summary=summary, parent=self.window(), receipt_callback=self._print_penalty_receipt)
            penalty_dialog.setWindowModality(Qt.ApplicationModal)
            penalty_dialog.exec_()
            if penalty_dialog.result_code == PenaltyNoticeDialog.RESULT_CANCEL:
                if isinstance(button, QPushButton):
                    self._set_button_enabled(button, True)
                return
            if penalty_dialog.result_code == PenaltyNoticeDialog.RESULT_PAID:
                summary = penalty_dialog.updated_summary or self.fetch_penalty_summary(ogr_no)
                self._update_penalty_info(summary or {})
                outstanding_total = self._parse_decimal((summary or {}).get("outstanding_total"))
            else:
                summary = penalty_dialog.updated_summary or summary
            self.penalty_summary = summary if isinstance(summary, dict) else self.penalty_summary
        if not self._maybe_show_student_status_alert(stu_data, summary, loan_prefs):
            if isinstance(button, QPushButton):
                self._set_button_enabled(button, True)
            return

        aktif_sayi = len(stu_data.get("active_loans", []))
        if isinstance(stu_data, dict):
            self.data["policy"] = stu_data.get("policy") or {}
        self._loan_prefs_cache = None
        loan_prefs = self._get_loan_preferences()
        if loan_prefs.get("loan_blocked"):
            QMessageBox.warning(
                self,
                "Ödünç Verilemez",
                "Bu rol için ödünç işlemi yapılamıyor."
            )
            if isinstance(button, QPushButton):
                self._set_button_enabled(button, True)
            return
        max_allowed = int(loan_prefs.get("default_max_items", 0) or 0)
        if max_allowed and aktif_sayi >= max_allowed:
            loans = stu_data.get("active_loans", [])
            dlg = MaxLoansDialog(
                student={
                    "ad": stu.get("ad"),
                    "soyad": stu.get("soyad"),
                    "ogrenci_no": stu.get("ogrenci_no") or stu.get("no"),
                    "sinif": sinif,
                },
                loans=loans,
                limit=max_allowed,
                parent=self.window(),
            )
            dlg.setWindowModality(Qt.ApplicationModal)
            dlg.exec_()
            if isinstance(button, QPushButton):
                self._set_button_enabled(button, True)
            return
        due_date = self._compute_due_date(loan_prefs)
        student_payload = {
            "ad": stu.get("ad"),
            "soyad": stu.get("soyad"),
            "ogrenci_no": stu.get("ogrenci_no") or stu.get("no"),
            "sinif": sinif,
        }
        raw_copy = copy_info if isinstance(copy_info, dict) else {}
        book_info = book_info if isinstance(book_info, dict) else {}
        copy_payload = dict(raw_copy) if isinstance(raw_copy, dict) else {}
        if book_info:
            copy_payload.setdefault("kitap", book_info)
        if "barkod" not in copy_payload and isinstance(raw_copy, dict):
            copy_payload["barkod"] = raw_copy.get("barkod")
        kit = copy_payload.get("kitap")
        if not kit and isinstance(copy_payload.get("kitap_nusha"), dict):
            nested = copy_payload.get("kitap_nusha") or {}
            copy_payload = dict(nested) if isinstance(nested, dict) else {}
            if book_info:
                copy_payload.setdefault("kitap", book_info)
        kit = copy_payload.get("kitap")
        confirm_dialog = CheckoutConfirmDialog(
            student=student_payload,
            copy=copy_payload,
            book=book_info or kit,
            due_date=due_date,
            parent=self.window(),
        )
        confirm_dialog.setWindowModality(Qt.ApplicationModal)
        if confirm_dialog.exec_() != QDialog.Accepted:
            if isinstance(button, QPushButton):
                self._set_button_enabled(button, True)
            return

        summary_payload = {
            "student": student_payload,
            "book": {
                "title": (book_info.get("baslik") if isinstance(book_info, dict) else None)
                         or ((kit or {}).get("baslik") if isinstance(kit, dict) else None)
                         or (raw_copy.get("book") or {}).get("baslik", "")
                         or (copy_payload.get("kitap") or {}).get("baslik", ""),
                "barkod": copy_payload.get("barkod") or raw_copy.get("barkod"),
            },
        }

        success = self.process_checkout(ogr_no, barkod, due_date, loan_prefs, button, summary=summary_payload)
        if not success and isinstance(button, QPushButton):
            self._set_button_enabled(button, True)

    def process_checkout(self, ogr_no, barkod, due_date, loan_prefs, button=None, *, summary=None):
        payload = {"ogrenci_no": ogr_no, "barkod": barkod}
        if due_date is not None:
            payload["iade_tarihi"] = due_date.isoformat()
        max_allowed = int(loan_prefs.get("default_max_items", 0) or 0)
        if max_allowed:
            payload["max_allowed"] = max_allowed
        self._checkout_in_progress = True
        try:
            resp = api_request("POST", self._api_url("checkout/"), json=payload)
            if resp.status_code not in (200, 201):
                QMessageBox.warning(self, "İşlem Başarısız", f"Ödünç verme kaydedilemedi ({resp.status_code}).")
                return False

            data = {}
            try:
                data = resp.json() or {}
            except Exception:
                data = {}

            due = data.get("iade_tarihi") or (due_date.isoformat() if due_date else None)
            due_text = format_date(due)
            message_lines = ["İşlem tamamlandı."]
            book_info = (summary or {}).get("book") or {}
            student_info = (summary or {}).get("student") or {}
            book_title = book_info.get("title")
            book_barcode = book_info.get("barkod")
            student_name = f"{student_info.get('ad','')} {student_info.get('soyad','')}".strip()
            student_no = student_info.get("ogrenci_no")
            if book_title or book_barcode or student_name:
                message_lines.append("")
            if book_title:
                message_lines.append(f"Kitap: {book_title}")
            if book_barcode:
                message_lines.append(f"Barkod: {book_barcode}")
            if student_name:
                message_lines.append(f"Öğrenci: {student_name}")
            if student_no:
                message_lines.append(f"Numara: {student_no}")
            message_lines.append(f"İade Tarihi: {due_text or '—'}")

            log_detail = build_log_detail(
                student={"ad": student_info.get("ad"), "soyad": student_info.get("soyad"), "ogrenci_no": student_no},
                book={"baslik": book_title} if book_title else None,
                barcode=book_barcode,
                date=due_text,
                date_label="İade Tarihi",
            )
            log_api.safe_send_log(
                "Ödünç verme",
                detay=log_detail or "Ödünç işlemi tamamlandı."
            )

            QMessageBox.information(
                self,
                "Ödünç Verildi",
                "\n".join(message_lines)
            )
            self.returnProcessed.emit()
            if isinstance(button, QPushButton):
                self._set_button_enabled(button, True)
            return True
        finally:
            self._checkout_in_progress = False
            self._set_button_enabled(button, True)

    def _set_button_enabled(self, button, enabled):
        if isinstance(button, QPushButton) and button is not None:
            try:
                if not sip.isdeleted(button):
                    button.setEnabled(enabled)
            except RuntimeError:
                pass

    def _get_loan_preferences(self):
        if not hasattr(self, "_loan_prefs_cache") or self._loan_prefs_cache is None:
            base = {}
            if isinstance(self.data, dict):
                base = (self.data.get("policy") or {}).copy()
            if not base:
                settings = load_settings() or {}
                base = settings.get("loans", {}) or {}

            role_override = None
            if isinstance(base, dict):
                role_override = base.get("role")

            def _merge(prefs, override):
                if not isinstance(prefs, dict):
                    prefs = {}
                if not isinstance(override, dict):
                    return prefs
                merged = prefs.copy()
                merged.update({k: v for k, v in override.items() if v is not None})
                return merged

            def _parse_bool(value, default=True):
                if isinstance(value, bool):
                    return value
                if value in (None, "", "None"):
                    return default
                if isinstance(value, (int, float)):
                    return value != 0
                if isinstance(value, str):
                    text = value.strip().lower()
                    if text in ("true", "1", "evet", "on", "yes"):
                        return True
                    if text in ("false", "0", "hayır", "hayir", "off", "no"):
                        return False
                return default

            prefs = base if isinstance(base, dict) else {}
            base_shift_default = _parse_bool((base or {}).get("shift_weekend"), True) if isinstance(base, dict) else True
            if role_override:
                prefs = _merge(prefs, {
                    "default_duration": role_override.get("duration"),
                    "default_max_items": role_override.get("max_items"),
                    "delay_grace_days": role_override.get("delay_grace_days"),
                    "penalty_delay_days": role_override.get("penalty_delay_days"),
                    "shift_weekend": role_override.get("shift_weekend"),
                    "loan_blocked": role_override.get("loan_blocked"),
                })
            def _is_zero(value):
                if value in (None, ""):
                    return False
                try:
                    return int(value) == 0
                except (TypeError, ValueError):
                    return False

            prefs["shift_weekend"] = _parse_bool(prefs.get("shift_weekend"), base_shift_default)
            blocked = bool(prefs.get("loan_blocked"))
            if not blocked:
                if _is_zero(prefs.get("default_duration")) or _is_zero(prefs.get("default_max_items")):
                    blocked = True
            prefs["loan_blocked"] = blocked
            self._loan_prefs_cache = prefs or {}
        return self._loan_prefs_cache

    def _compute_due_date(self, prefs):
        days = int((prefs or {}).get("default_duration") or 0)
        if days <= 0:
            days = 15
        due_date = datetime.now(timezone.utc) + timedelta(days=days)
        if (prefs or {}).get("shift_weekend", True):
            while due_date.weekday() >= 5:
                due_date += timedelta(days=1)
        return due_date

    def _is_same_day_loan(self, loan):
        if not loan:
            return False
        odunc_val = loan.get("odunc_tarihi")
        if not odunc_val:
            kit_nusha = loan.get("kitap_nusha")
            if isinstance(kit_nusha, dict):
                odunc_val = kit_nusha.get("odunc_tarihi")
        loan_date = self._parse_date(odunc_val)
        if not loan_date:
            return False
        return loan_date == datetime.now().date()

    def _ask_return_mode(self):
        box = QMessageBox(self)
        box.setWindowTitle("İşlem Seçimi")
        box.setText("Bu ödünç işlemi bugün gerçekleşmiş görünüyor. Ne yapmak istersiniz?")
        btn_cancel = box.addButton("Vazgeç", QMessageBox.RejectRole)
        btn_cancel.setObjectName("DialogCancelButton")
        btn_cancel_loan = box.addButton("Ödünç İptal", QMessageBox.DestructiveRole)
        btn_cancel_loan.setObjectName("DialogCancelLoanButton")
        btn_return = box.addButton("İade Al", QMessageBox.AcceptRole)
        btn_return.setObjectName("DialogReturnButton")
        box.setDefaultButton(btn_return)
        self._apply_dialog_style(box)
        box.exec_()
        clicked = box.clickedButton()
        if clicked == btn_cancel:
            return "cancel_operation"
        if clicked == btn_cancel_loan:
            return "loan_cancel"
        return "return"

    def _prompt_student_code(self, expected_value, mode="student"):
        dialog = QInputDialog(self)
        if mode == "barcode":
            dialog.setWindowTitle("Barkod Onayı")
            dialog.setLabelText("Kitap barkodunu okutun veya yazın:")
        else:
            dialog.setWindowTitle("Öğrenci Onayı")
            dialog.setLabelText("Öğrenci numarasını girin:")
        dialog.setTextValue("")
        dialog.setOkButtonText("Onayla")
        dialog.setCancelButtonText("Vazgeç")
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box:
            btn_ok = button_box.button(QDialogButtonBox.Ok)
            if btn_ok:
                btn_ok.setText("Onayla")
                btn_ok.setObjectName("DialogReturnButton")
            btn_cancel = button_box.button(QDialogButtonBox.Cancel)
            if btn_cancel:
                btn_cancel.setText("Vazgeç")
                btn_cancel.setObjectName("DialogCancelButton")
        self._apply_dialog_style(dialog)
        line_edit = dialog.findChild(QLineEdit)
        if line_edit:
            line_edit.setFocus()
        main_window = self.window()
        if line_edit and hasattr(main_window, "set_scanner_lock"):
            main_window.set_scanner_lock(line_edit)
        try:
            accepted = dialog.exec_() == QDialog.Accepted
            return dialog.textValue(), accepted
        finally:
            if line_edit and hasattr(main_window, "clear_scanner_lock"):
                main_window.clear_scanner_lock(line_edit)

    def _apply_dialog_style(self, box):
        style = """
        QPushButton#DialogCancelButton {
            background-color: #95a5a6;
            color: #2c3e50;
            padding: 4px 12px;
            border-radius: 4px;
        }
        QPushButton#DialogCancelButton:hover {
            background-color: #7f8c8d;
        }
        QPushButton#DialogCancelLoanButton {
            background-color: #e67e22;
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 4px;
        }
        QPushButton#DialogCancelLoanButton:hover {
            background-color: #d35400;
        }
        QPushButton#DialogReturnButton {
            background-color: #27ae60;
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 4px;
        }
        QPushButton#DialogReturnButton:hover {
            background-color: #1f8a4c;
        }
        """
        existing = box.styleSheet()
        box.setStyleSheet((existing + "\n" if existing else "") + style)

    def fetch_isbn_summary(self, isbn):
        summary = {"count": 0, "loaned": 0, "available": 0, "first_barkod": None}
        if not isbn:
            return summary
        try:
            resp = api_request("GET", self._api_url(f"nushalar/?kitap__isbn={isbn}"))
            if resp.status_code == 200:
                try:
                    payload = resp.json() or []
                except ValueError:
                    return summary

                if isinstance(payload, dict):
                    copies = payload.get("results") or payload.get("items") or []
                else:
                    copies = payload

                if not isinstance(copies, list):
                    copies = []

                summary["count"] = len(copies)
                loaned = 0
                available = 0
                for copy in copies:
                    barkod = copy.get("barkod")
                    if barkod and not summary["first_barkod"]:
                        summary["first_barkod"] = barkod

                    status = str(copy.get("durum") or "").lower()
                    if not status:
                        son_odunc = copy.get("son_odunc") or {}
                        status = str(son_odunc.get("durum") or "").lower()

                    aktif = copy.get("aktif")
                    if aktif is None:
                        aktif = True

                    if status in {"oduncte", "gecikmis"}:
                        loaned += 1
                    elif status in {"kayip", "hasarli", "iptal"} or not aktif:
                        continue
                    else:
                        available += 1

                summary["loaned"] = loaned
                summary["available"] = available
            else:
                print("Kitap nüsha listesi alınamadı:", resp.status_code)
        except Exception as exc:
            print("ISBN özet alınamadı:", exc)
        return summary

    def _parse_date(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        if not text:
            return None
        candidate = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            try:
                return datetime.strptime(text[:10], "%Y-%m-%d").date()
            except ValueError:
                return None

    def _parse_decimal(self, value):
        if value in (None, "", False):
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            try:
                cleaned = str(value).replace(",", ".")
                return Decimal(cleaned)
            except (InvalidOperation, ValueError, TypeError):
                return Decimal("0")

    def _format_currency(self, amount: Decimal):
        if not isinstance(amount, Decimal):
            amount = self._parse_decimal(amount)
        try:
            quantized = amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            quantized = Decimal("0.00")
        return f"{format(quantized, '.2f')} ₺"

    def _numeric_amount(self, amount):
        dec = self._parse_decimal(amount)
        if dec is None:
            return "0"
        try:
            normalized = dec.quantize(Decimal("0.01"))
        except InvalidOperation:
            normalized = Decimal("0.00")
        text = format(normalized, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"

    def _format_decimal_for_payload(self, value):
        if value is None:
            return None
        amount = self._parse_decimal(value)
        try:
            quantized = amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            quantized = Decimal("0.00")
        return format(quantized, ".2f")

    def _student_log_payload(self, student):
        if not isinstance(student, dict):
            return student
        return {
            "ad": student.get("ad"),
            "soyad": student.get("soyad"),
            "ogrenci_no": student.get("ogrenci_no") or student.get("no"),
        }

    def _book_log_payload(self, book):
        if isinstance(book, dict):
            title = book.get("baslik") or book.get("title")
            if title:
                return {"baslik": title}
            return book
        if isinstance(book, str):
            return {"baslik": book}
        return {}

    def fetch_penalty_summary(self, student_no=None):
        code = student_no or self.student_no
        if not code:
            return None
        try:
            resp = api_request("GET", self._api_url(f"student-penalties/{code}/"))
        except Exception as exc:
            print("Ceza özeti alınamadı:", exc)
            return None
        if resp.status_code != 200:
            print("Ceza özeti alınamadı:", resp.status_code)
            return None
        summary = resp.json() or {}
        summary_data = {k: v for k, v in summary.items() if k != "student"}
        if isinstance(summary_data, dict):
            self.penalty_summary = summary_data
            self._update_penalty_info(summary_data)
        return summary

    def _maybe_show_student_status_alert(self, student_data, penalty_summary, loan_prefs=None):
        if not isinstance(student_data, dict):
            return True
        active_loans = student_data.get("active_loans") or []
        overdue_titles = []
        issue_titles = []
        due_soon = []
        today = datetime.now().date()
        active_count = len(active_loans)
        for loan in active_loans:
            status = (loan.get("durum") or "").lower()
            copy = loan.get("kitap_nusha") or {}
            book = copy.get("kitap") or {}
            title = book.get("baslik") or loan.get("kitap") or "(Bilgi yok)"
            if status == "gecikmis":
                overdue_titles.append(title)
            copy_status = (copy.get("durum") or "").lower()
            if copy_status in {"kayip", "hasarli"} or status in {"kayip", "hasarli"}:
                issue_titles.append(title)
            raw_due = loan.get("iade_tarihi")
            due_date = self._parse_date(raw_due)
            if due_date and due_date >= today:
                days_left = (due_date - today).days
                if days_left <= 2:
                    due_soon.append((title, days_left))

        limit = None
        if isinstance(loan_prefs, dict):
            limit = loan_prefs.get("default_max_items")
        if limit in (None, ""):
            policy_role = student_data.get("policy", {}).get("role", {}) if isinstance(student_data.get("policy"), dict) else {}
            limit = policy_role.get("max_items")
        try:
            limit = int(limit) if limit not in (None, "") else None
        except (TypeError, ValueError):
            limit = None

        total_penalty = self._parse_decimal((penalty_summary or {}).get("outstanding_total"))
        primary_warnings = []
        if overdue_titles:
            primary_warnings.append(f"• Gecikmiş iade: {', '.join(self._summarize_titles(overdue_titles))}")
        if issue_titles:
            primary_warnings.append(f"• Kayıp/hasarlı kayıt: {', '.join(self._summarize_titles(issue_titles))}")
        if due_soon:
            formatted = []
            for title, days_left in due_soon[:3]:
                if days_left <= 0:
                    formatted.append(f"{title} (bugün)")
                else:
                    formatted.append(f"{title} ({days_left} gün içinde)")
            if len(due_soon) > 3:
                formatted.append(f"+{len(due_soon) - 3} daha")
            primary_warnings.append(f"• Yaklaşan iade: {', '.join(formatted)}")
        if total_penalty > Decimal("0"):
            primary_warnings.append(f"• Toplam ceza: {self._format_currency(total_penalty)}")

        limit_warning = None
        if active_count and limit and limit > 0 and active_count >= limit:
            limit_warning = f"• Aktif ödünç: {active_count} / {limit}"

        if not primary_warnings and not limit_warning:
            return True

        warnings = list(primary_warnings)
        if limit_warning:
            warnings.insert(0, limit_warning)
        elif active_count and primary_warnings:
            if limit and limit > 0:
                warnings.insert(0, f"• Aktif ödünç: {active_count} / {limit}")
            else:
                warnings.insert(0, f"• Aktif ödünç: {active_count}")

        box = QMessageBox(self)
        box.setWindowTitle("Öğrenci Durumu")
        box.setIcon(QMessageBox.Warning)
        box.setText("Bu öğrencinin mevcut durumu:\n\n" + "\n".join(warnings))
        btn_continue = box.addButton("Ödünçe Devam Et", QMessageBox.AcceptRole)
        btn_cancel = box.addButton("İptal", QMessageBox.RejectRole)
        btn_continue.setObjectName("DialogPositiveButton")
        btn_cancel.setObjectName("DialogDangerButton")
        box.setDefaultButton(btn_cancel if overdue_titles or issue_titles else btn_continue)
        box.exec_()
        return box.clickedButton() == btn_continue

    def _summarize_titles(self, titles, limit=3):
        unique = []
        for title in titles:
            if title and title not in unique:
                unique.append(title)
        if len(unique) <= limit:
            return unique
        return unique[:limit] + [f"+{len(unique) - limit} daha"]

    def open_penalty_detail(self):
        if not self.student_no:
            QMessageBox.information(self, "Bilgi", "Öğrenci seçili değil.")
            return
        payload = self.fetch_penalty_summary(self.student_no)
        if not payload:
            QMessageBox.information(self, "Bilgi", "Ceza detayları alınamadı.")
            return
        summary = self._attach_pending_penalties(self.penalty_summary or {})
        entries = summary.get("entries") or []
        if not entries:
            QMessageBox.information(self, "Bilgi", "Bu öğrenciye ait bekleyen ceza bulunmuyor.")
            return
        dialog = PenaltyDetailDialog(summary=summary, parent=self, receipt_callback=self._print_penalty_receipt)
        dialog.penaltyPaid.connect(self._on_penalty_paid)
        dialog.exec_()

    def _on_penalty_paid(self, summary):
        if isinstance(summary, dict):
            self._update_penalty_info(summary)
            self.penalty_summary = summary

    def _print_penalty_receipt(self, summary, amount):
        amount_dec = self._parse_decimal(amount)
        if amount_dec <= Decimal("0"):
            return
        summary = self._prepare_receipt_summary(summary)
        print("[DBG] QuickResultPanel receipt student:", summary.get("student"))
        try:
            print_fine_payment_receipt(summary, amount_dec)
        except ReceiptPrintError as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", f"Fiş yazdırma başarısız:\n{exc}")

    def _handle_penalty_action_button(self):
        if self._penalty_action_mode == "debt_free":
            self._print_debt_statement_receipt()
        else:
            self.open_penalty_detail()

    def _handle_general_notice(self):
        if not self._can_print_general_notice():
            QMessageBox.information(self, "Bilgi", "Öğrenci seçili değil.")
            return
        self._print_general_notice_receipt()

    def _can_print_general_notice(self):
        return bool(self.student_no or self.student_id)

    def _can_print_debt_statement(self):
        return bool(self.student_no or self.student_id)

    def _latest_summary_for_receipt(self, *, force_refresh=False):
        summary_payload = None
        if force_refresh or not isinstance(self.penalty_summary, dict):
            fetched = self.fetch_penalty_summary()
            if isinstance(fetched, dict):
                summary_payload = dict(fetched)
        if summary_payload is None:
            if isinstance(self.penalty_summary, dict):
                summary_payload = dict(self.penalty_summary)
            else:
                summary_payload = {}
        if not summary_payload and not self._can_print_general_notice():
            return None
        return self._prepare_receipt_summary(summary_payload)

    def _print_general_notice_receipt(self):
        summary = self._latest_summary_for_receipt(force_refresh=True)
        if not summary:
            QMessageBox.warning(self, "Fiş Yazdırma", "Öğrenci özeti alınamadı.")
            return
        context = build_receipt_context(summary, pending_entries=self._pending_penalty_entries)
        try:
            print_receipt_from_template("general_notice", context)
        except ReceiptPrintError as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", f"Fiş yazdırma başarısız:\n{exc}")

    def _print_debt_statement_receipt(self):
        if not self._can_print_debt_statement():
            QMessageBox.information(self, "Bilgi", "Öğrenci seçili değil.")
            return
        summary = self._latest_summary_for_receipt(force_refresh=True)
        if not summary:
            QMessageBox.warning(self, "Fiş Yazdırma", "Öğrenci özeti alınamadı.")
            return
        context = build_receipt_context(summary)
        try:
            print_receipt_from_template("debt_statement", context)
        except ReceiptPrintError as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", f"Fiş yazdırma başarısız:\n{exc}")

    def _should_show_debt_free_button(self, total=None):
        if total is None:
            total = self._parse_decimal((self.penalty_summary or {}).get("outstanding_total"))
        try:
            return total <= Decimal("0") and self._active_loans_count == 0
        except Exception:
            return self._active_loans_count == 0

    def _collect_pending_penalties(self, loans):
        result = []
        for loan in loans or []:
            status = (loan.get("durum") or "").lower()
            if status not in {"oduncte", "gecikmis"}:
                continue
            penalty_preview = loan.get("penalty_preview") or loan.get("gecikme_cezasi")
            amount = self._parse_decimal(penalty_preview)
            if amount <= Decimal("0"):
                continue
            copy = loan.get("kitap_nusha") or {}
            book = copy.get("kitap") or {}
            title = book.get("baslik") or loan.get("kitap") or ""
            barkod = copy.get("barkod") or loan.get("barkod") or ""
            try:
                formatted_amount = amount.quantize(Decimal("0.01"))
            except InvalidOperation:
                formatted_amount = Decimal("0.00")
            result.append({
                "kitap": title,
                "barkod": barkod,
                "durum": status,
                "teslim_tarihi": None,
                "gecikme_cezasi": format(formatted_amount, ".2f"),
                "gecikme_cezasi_odendi": False,
                "id": loan.get("id"),
                "pending_return": True,
            })
        return result

    def _attach_pending_penalties(self, summary):
        merged = dict(summary or {})
        entries = list(merged.get("entries") or [])
        pending = list(self._pending_penalty_entries or [])
        if not pending:
            merged["entries"] = entries
            return merged
        existing_ids = {entry.get("id") for entry in entries if entry.get("id")}
        for entry in pending:
            entry_id = entry.get("id")
            if entry_id and entry_id in existing_ids:
                continue
            entries.append(dict(entry))
        merged["entries"] = entries
        merged["pending_notice"] = True
        return merged

    def _button_style_sheet(self, color, disabled="#95a5a6"):
        return (
            "QPushButton {"
            "border-radius:6px;"
            "padding:5px 12px;"
            "font-weight:600;"
            "font-size:12px;"
            "color:white;"
            f"background-color:{color};"
            "}"
            "QPushButton:disabled {"
            f"background-color:{disabled};"
            "color:#ecf0f1;"
            "}"
        )

    def _apply_penalty_button_style(self):
        button = getattr(self, "penalty_detail_button", None)
        if not button:
            return
        color = "#27ae60" if self._penalty_action_mode == "debt_free" else "#e67e22"
        button.setStyleSheet(self._button_style_sheet(color))

    def _apply_general_notice_style(self):
        button = getattr(self, "general_receipt_button", None)
        if not button:
            return
        button.setStyleSheet(self._button_style_sheet("#2980b9"))

    def _inject_penalty_info(self, card_widget, summary):
        self.penalty_total_label = None
        self.penalty_detail_button = None
        layout = card_widget.layout()
        if layout is None:
            return
        layout.addSpacing(6)
        label_row = QHBoxLayout()
        label = QLabel("Toplam ceza: 0.00 ₺")
        label_row.addWidget(label)
        label_row.addStretch(1)
        layout.addLayout(label_row)

        buttons_row = QHBoxLayout()
        btn_notice = QPushButton("Bilgilendirme Fişi")
        btn_notice.setCursor(Qt.PointingHandCursor)
        btn_notice.clicked.connect(self._handle_general_notice)
        buttons_row.addWidget(btn_notice)
        buttons_row.addStretch(1)
        btn_detail = QPushButton("Ceza Detayı")
        btn_detail.setCursor(Qt.PointingHandCursor)
        btn_detail.clicked.connect(self._handle_penalty_action_button)
        buttons_row.addWidget(btn_detail)
        layout.addLayout(buttons_row)
        self.penalty_total_label = label
        self.penalty_detail_button = btn_detail
        self.general_receipt_button = btn_notice
        self._apply_general_notice_style()
        self._update_penalty_info(summary if isinstance(summary, dict) else {})

    def _update_penalty_info(self, summary):
        if not isinstance(summary, dict):
            summary = {}
        self.penalty_summary = summary
        label = getattr(self, "penalty_total_label", None)
        button = getattr(self, "penalty_detail_button", None)
        general_button = getattr(self, "general_receipt_button", None)
        total = self._parse_decimal(summary.get("outstanding_total"))
        if label:
            if total > Decimal("0"):
                label.setText(f"Toplam ceza: {self._format_currency(total)}")
                label.setStyleSheet("color:#c0392b; font-weight:bold;")
            else:
                label.setText("Toplam ceza: 0.00 ₺")
                label.setStyleSheet("color:#27ae60; font-weight:bold;")
        if button:
            show_debt_free = self._should_show_debt_free_button(total)
            if show_debt_free:
                button.setText("Borcu Yoktur Fişi")
                self._penalty_action_mode = "debt_free"
                button.setEnabled(self._can_print_debt_statement())
            else:
                button.setText("Ceza Detayı")
                entries = summary.get("entries") or []
                button.setEnabled(bool(entries))
                self._penalty_action_mode = "detail"
            self._apply_penalty_button_style()
        if general_button:
            general_button.setEnabled(self._can_print_general_notice())
            self._apply_general_notice_style()

    def _attempt_penalty_receipt(self, summary, amount):
        amount_dec = self._parse_decimal(amount)
        if amount_dec <= Decimal("0"):
            return
        summary_data = self._prepare_receipt_summary(summary)
        print("[DBG] QuickResultPanel (attempt) receipt student:", summary_data.get("student"))
        try:
            print_fine_payment_receipt(summary_data, amount_dec)
        except ReceiptPrintError as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "Fiş Yazdırma", f"Fiş yazdırma başarısız:\n{exc}")

    def _prepare_receipt_summary(self, summary):
        summary_data = dict(summary) if isinstance(summary, dict) else {}
        if "entries" not in summary_data or not summary_data.get("entries"):
            entries = (self.penalty_summary or {}).get("entries") or []
            summary_data["entries"] = entries
        if "outstanding_total" not in summary_data or summary_data.get("outstanding_total") is None:
            summary_data["outstanding_total"] = (self.penalty_summary or {}).get("outstanding_total")
        if not summary_data.get("student"):
            student = (self.data or {}).get("student") or (self.data or {}).get("ogrenci")
            if isinstance(student, dict):
                summary_data["student"] = student
        if not summary_data.get("student") and isinstance(self.penalty_summary, dict):
            fallback_student = (self.penalty_summary or {}).get("student")
            if isinstance(fallback_student, dict):
                summary_data["student"] = fallback_student
        return summary_data

    def _attach_receipt_warning_to_box(self, box):
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

    def _expected_student_no(self, loan):
        if self.student_no:
            return self.student_no
        if isinstance(loan, dict):
            ogr = loan.get("ogrenci") or {}
            if isinstance(ogr, dict):
                return ogr.get("ogrenci_no") or ogr.get("no")
        return None

    def _expected_barkod(self, loan):
        if not isinstance(loan, dict):
            return None
        copy = loan.get("kitap_nusha")
        if isinstance(copy, dict):
            barkod = copy.get("barkod")
            if barkod:
                return barkod
        return loan.get("barkod")

    def _api_url(self, path):
        base = get_api_base_url().rstrip('/')
        return f"{base}/{path.lstrip('/')}"
