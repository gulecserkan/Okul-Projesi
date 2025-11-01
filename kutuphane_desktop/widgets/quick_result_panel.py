from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, InvalidOperation

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox, QInputDialog, QLineEdit, QDialogButtonBox, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.config import get_api_base_url, load_settings
from core.utils import format_date, api_request
from ui.loan_status_dialog import LoanStatusDialog
from ui.detail_window import DetailWindow


class QuickResultPanel(QWidget):
    detailStudentRequested = pyqtSignal(str)            # öğrenci_no
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
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        self._return_in_progress = False
        self._checkout_in_progress = False
        self.penalty_summary = data.get("penalty_summary") if isinstance(data, dict) else None
        if not isinstance(self.penalty_summary, dict):
            self.penalty_summary = None

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
            self._inject_penalty_info(info_inner_card, summary)
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
            for loan in active_loans:
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

            if student_cards:
                lbl_active = QLabel("📚 Aktif Ödünç Kayıtları")
                lbl_active.setStyleSheet("font-size:19px; font-weight:bold;")
                hist_box.addWidget(lbl_active)
                for card in student_cards:
                    contents = card.layout()
                    if contents:
                        contents.setContentsMargins(8, 6, 8, 6)
                    hist_box.addWidget(card, 0, Qt.AlignTop)
            else:
                hist_box.addWidget(
                    self.create_card(None, ["Bu öğrencinin aktif ödünç kaydı bulunmamaktadır."], "HistoryCard")
                )

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
                btn_checkout.clicked.connect(lambda _, cp=copy: self.prompt_checkout(cp))
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
                if status_current == "gecikmis":
                    lines.append(("⚠️ Gecikme", f"Ceza: {penalty_preview or '—'}"))
                outstanding_total = self._parse_decimal((self.penalty_summary or {}).get("outstanding_total"))
                if outstanding_total > Decimal("0"):
                    entry_amount = Decimal("0")
                    entries = (self.penalty_summary or {}).get("entries") or []
                    for entry in entries:
                        if entry.get("id") == loan.get("id"):
                            entry_amount = self._parse_decimal(entry.get("gecikme_cezasi"))
                            break
                    if entry_amount == Decimal("0") and penalty_preview:
                        entry_amount = self._parse_decimal(penalty_preview)
                    lines.append(("Toplam ceza", self._format_currency(outstanding_total)))
                    remaining = outstanding_total - entry_amount
                    if remaining > Decimal("0"):
                        lines.append(("Diğer cezalar", self._format_currency(remaining)))
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
        button = self.sender()
        if isinstance(button, QPushButton):
            button.setEnabled(False)

        if expected_no:
            entered, ok = self._prompt_student_code(expected_no)
            if not ok:
                if isinstance(button, QPushButton):
                    button.setEnabled(True)
                return
            if entered.strip() != str(expected_no).strip():
                QMessageBox.warning(self, "Onay Hatası", "Öğrenci numarası eşleşmiyor.")
                if isinstance(button, QPushButton):
                    button.setEnabled(True)
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
        outstanding_other = outstanding_total - entry_amount
        if outstanding_other < Decimal("0"):
            outstanding_other = Decimal("0")

        penalty_override = None
        if current_penalty > Decimal("0"):
            alert = QMessageBox(self)
            alert.setWindowTitle("Gecikme Cezası")
            alert.setIcon(QMessageBox.Warning)
            lines = [f"Bu iade için gecikme cezası: {self._format_currency(current_penalty)}"]
            if outstanding_other > Decimal("0"):
                lines.append(f"Diğer ödenmemiş cezalar: {self._format_currency(outstanding_other)}")
            alert.setText("\n".join(lines))
            alert.setInformativeText("Ödeme alındıysa 'Ceza Ödendi'yi seçin.")
            btn_paid = alert.addButton("Ceza Ödendi", QMessageBox.AcceptRole)
            btn_unpaid = alert.addButton("Ödenmedi", QMessageBox.DestructiveRole)
            btn_cancel = alert.addButton("Vazgeç", QMessageBox.RejectRole)
            self._apply_dialog_style(alert)
            alert.exec_()
            clicked = alert.clickedButton()
            if clicked == btn_cancel:
                if isinstance(button, QPushButton):
                    button.setEnabled(True)
                return
            if clicked == btn_paid:
                penalty_override = Decimal("0")
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
                    button.setEnabled(True)
                return
            elif choice == "loan_cancel":
                mode = "cancel"
            # else remain "return"
        success = self.process_return(loan, mode=mode, penalty_override=penalty_override)
        if not success and isinstance(button, QPushButton):
            button.setEnabled(True)

    def process_return(self, loan, mode="return", penalty_override=None):
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
                QMessageBox.information(self, "Ödünç İptal", "Ödünç işlemi iptal edildi.")
            else:
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
            entered, ok = self._prompt_student_code(expected_no)
            if not ok or entered.strip() != str(expected_no).strip():
                if ok:
                    QMessageBox.warning(self, "Onay Hatası", "Öğrenci numarası eşleşmiyor.")
                return

        self.open_loan_status_dialog(
            [loan],
            require_resolution=False,
            allowed_statuses={"kayip", "hasarli"},
        )

    def prompt_checkout(self, copy_info):
        if self._checkout_in_progress:
            return
        barkod = (copy_info or {}).get("barkod")
        if not barkod:
            QMessageBox.warning(self, "İşlem Başarısız", "Nüsha barkodu bulunamadı.")
            return

        button = self.sender()
        if isinstance(button, QPushButton):
            button.setEnabled(False)

        ogr_no, ok = QInputDialog.getText(
            self,
            "Ödünç Ver",
            "Öğrenci numarasını girin:",
            QLineEdit.Normal
        )
        if not ok or not ogr_no.strip():
            if isinstance(button, QPushButton):
                button.setEnabled(True)
            return

        ogr_no = ogr_no.strip()
        stu_resp = api_request("GET", self._api_url(f"fast-query/?q={ogr_no}"))
        if stu_resp.status_code != 200:
            QMessageBox.warning(self, "İşlem Başarısız", f"Öğrenci doğrulanamadı ({stu_resp.status_code}).")
            if isinstance(button, QPushButton):
                button.setEnabled(True)
            return

        stu_data = {}
        try:
            stu_data = stu_resp.json() or {}
        except Exception:
            stu_data = {}

        if stu_data.get("type") != "student":
            QMessageBox.warning(self, "İşlem Başarısız", "Girilen numaraya ait öğrenci bulunamadı.")
            if isinstance(button, QPushButton):
                button.setEnabled(True)
            return

        stu = stu_data.get("student") or {}
        adsoyad = f"{stu.get('ad','')} {stu.get('soyad','')}".strip()
        sinif = stu.get("sinif") or "—"
        phone = (stu.get("telefon") or "").strip()
        email = (stu.get("eposta") or "").strip()
        missing = []
        if not phone:
            missing.append("telefon")
        if not email:
            missing.append("e-posta")
        if missing:
            box = QMessageBox(self)
            box.setWindowTitle("Eksik Bilgi")
            box.setIcon(QMessageBox.Warning)
            box.setText(
                "Bu öğrenci için {} bilgisi eksik.".format(" ve ".join(missing))
            )
            box.setInformativeText(
                "Devam etmeden önce öğrenci kartını güncelleyebilirsiniz."
            )
            btn_update = box.addButton("Öğrenciyi Güncelle", QMessageBox.AcceptRole)
            btn_continue = box.addButton("Devam Et", QMessageBox.DestructiveRole)
            btn_cancel = box.addButton("Vazgeç", QMessageBox.RejectRole)
            box.setDefaultButton(btn_update)
            self._apply_dialog_style(box)
            box.exec_()

            clicked = box.clickedButton()
            if clicked == btn_cancel:
                if isinstance(button, QPushButton):
                    button.setEnabled(True)
                return
            if clicked == btn_update:
                self.detailStudentRequested.emit(stu.get("ogrenci_no") or ogr_no)
            # Devam Et seçildiyse hiçbir şey yapmayıp akışı sürdürüyoruz.
        aktif_sayi = len(stu_data.get("active_loans", []))
        if isinstance(stu_data, dict):
            self.data["policy"] = stu_data.get("policy") or {}
        self._loan_prefs_cache = None
        loan_prefs = self._get_loan_preferences()
        max_allowed = int(loan_prefs.get("default_max_items", 0) or 0)
        if max_allowed and aktif_sayi >= max_allowed:
            QMessageBox.warning(
                self,
                "İşlem Engellendi",
                f"Öğrencinin aktif ödünç sayısı {aktif_sayi}. Maksimum izin verilen değer {max_allowed}."
            )
            if isinstance(button, QPushButton):
                button.setEnabled(True)
            return
        msg = (
            f"Öğrenci: {adsoyad} ({stu.get('no') or stu.get('ogrenci_no')})\n"
            f"Sınıf: {sinif}\n"
            f"Aktif ödünç sayısı: {aktif_sayi}\n\n"
            "Bu öğrenciye kitap ödünç verilsin mi?"
        )

        if not self._confirm_checkout(msg):
            if isinstance(button, QPushButton):
                button.setEnabled(True)
            return

        due_date = self._compute_due_date(loan_prefs)
        success = self.process_checkout(ogr_no, barkod, due_date, loan_prefs, button)
        if not success and isinstance(button, QPushButton):
            button.setEnabled(True)

    def process_checkout(self, ogr_no, barkod, due_date, loan_prefs, button=None):
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
            QMessageBox.information(
                self,
                "Ödünç Verildi",
                f"İşlem tamamlandı. İade tarihi: {due_text or '—'}"
            )
            self.returnProcessed.emit()
            if isinstance(button, QPushButton):
                button.setEnabled(True)
            return True
        finally:
            self._checkout_in_progress = False

    def _confirm_checkout(self, message):
        box = QMessageBox(self)
        box.setWindowTitle("Ödünç Onayı")
        box.setText(message)
        btn_yes = box.addButton("Evet", QMessageBox.AcceptRole)
        btn_yes.setObjectName("DialogReturnButton")
        btn_no = box.addButton("Vazgeç", QMessageBox.RejectRole)
        btn_no.setObjectName("DialogCancelButton")
        box.setDefaultButton(btn_yes)
        self._apply_dialog_style(box)
        box.exec_()
        return box.clickedButton() == btn_yes

    def _get_loan_preferences(self):
        if not hasattr(self, "_loan_prefs_cache"):
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

            prefs = base if isinstance(base, dict) else {}
            if role_override:
                prefs = _merge(prefs, {
                    "default_duration": role_override.get("duration"),
                    "default_max_items": role_override.get("max_items"),
                    "delay_grace_days": role_override.get("delay_grace_days"),
                    "penalty_delay_days": role_override.get("penalty_delay_days"),
                    "shift_weekend": role_override.get("shift_weekend"),
                })
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

    def _prompt_student_code(self, expected_no):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("İade Onayı")
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
        accepted = dialog.exec_() == QDialog.Accepted
        return dialog.textValue(), accepted

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

    def _format_decimal_for_payload(self, value):
        if value is None:
            return None
        amount = self._parse_decimal(value)
        try:
            quantized = amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            quantized = Decimal("0.00")
        return format(quantized, ".2f")

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
        return summary

    def open_penalty_detail(self):
        if not self.student_no:
            QMessageBox.information(self, "Bilgi", "Öğrenci seçili değil.")
            return
        payload = self.fetch_penalty_summary(self.student_no)
        if not payload:
            QMessageBox.information(self, "Bilgi", "Ceza detayları alınamadı.")
            return
        entries = payload.get("entries") or []
        if not entries:
            QMessageBox.information(self, "Bilgi", "Bu öğrenciye ait bekleyen ceza bulunmuyor.")
            return

        rows = []
        for entry in entries:
            rows.append([
                entry.get("kitap", ""),
                entry.get("barkod", ""),
                format_date(entry.get("odunc_tarihi")),
                format_date(entry.get("iade_tarihi")),
                format_date(entry.get("teslim_tarihi")),
                entry.get("durum", ""),
                self._format_currency(entry.get("gecikme_cezasi")),
            ])

        dialog = DetailWindow.single_tab(
            "Gecikme Cezaları",
            ["Kitap", "Barkod", "Ödünç", "İade", "Teslim", "Durum", "Ceza"],
            rows,
            settings_key="penalty_detail",
            icon_path=None,
            tab_title="Ceza Detayı"
        )
        dialog.exec_()

    def _inject_penalty_info(self, card_widget, summary):
        if not isinstance(summary, dict):
            return
        total = self._parse_decimal(summary.get("outstanding_total"))
        if total <= Decimal("0"):
            return
        layout = card_widget.layout()
        if layout is None:
            return
        layout.addSpacing(4)
        row = QHBoxLayout()
        label = QLabel(f"Toplam ceza: {self._format_currency(total)}")
        label.setStyleSheet("color:#c0392b; font-weight:bold;")
        row.addWidget(label)
        row.addStretch(1)
        btn_detail = QPushButton("Ceza Detayı")
        btn_detail.setObjectName("SecondaryButton")
        btn_detail.setCursor(Qt.PointingHandCursor)
        btn_detail.clicked.connect(self.open_penalty_detail)
        row.addWidget(btn_detail)
        layout.addLayout(row)

    def _expected_student_no(self, loan):
        if self.student_no:
            return self.student_no
        if isinstance(loan, dict):
            ogr = loan.get("ogrenci") or {}
            if isinstance(ogr, dict):
                return ogr.get("ogrenci_no") or ogr.get("no")
        return None

    def _api_url(self, path):
        base = get_api_base_url().rstrip('/')
        return f"{base}/{path.lstrip('/')}"
