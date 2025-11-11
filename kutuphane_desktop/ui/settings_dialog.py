from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt5.QtCore import Qt, QTime
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import load_settings, save_settings
from core.utils import response_error_message
from ui.printer_settings_dialog import PrinterSettingsWidget
from ui.server_settings_dialog import ServerSettingsWidget
from ui.label_editor_dialog import LabelEditorDialog
from ui.notification_template_dialog import NotificationTemplateDialog
from ui.receipt_template_dialog import ReceiptTemplateDialog
from core.receipt_templates import RECEIPT_SCENARIOS, DEFAULT_RECEIPT_TEMPLATES, RECEIPT_PLACEHOLDERS
from api import auth
from api import settings as settings_api
from api import roles as roles_api


class LabelSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.mm_w = 55.0
        self.mm_h = 40.0
        self.dpi = 203
        self.grid_mm = 2.0
        self.snap_enabled = False
        self.rotate_print = False

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(10.0, 200.0)
        self.spin_width.setSingleStep(0.5)
        self.spin_width.setMaximumWidth(120)
        form.addRow("Genişlik (mm)", self.spin_width)

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(10.0, 200.0)
        self.spin_height.setSingleStep(0.5)
        self.spin_height.setMaximumWidth(120)
        form.addRow("Yükseklik (mm)", self.spin_height)

        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(96, 600)
        self.spin_dpi.setMaximumWidth(100)
        form.addRow("DPI", self.spin_dpi)

        self.chk_snap = QCheckBox("Izgaraya yapıştır")
        form.addRow("", self.chk_snap)

        self.spin_grid = QDoubleSpinBox()
        self.spin_grid.setRange(0.5, 10.0)
        self.spin_grid.setSingleStep(0.5)
        self.spin_grid.setMaximumWidth(120)
        form.addRow("Izgara (mm)", self.spin_grid)

        layout.addLayout(form)

        self.lbl_printer_info = QLabel()
        self.lbl_printer_info.setWordWrap(True)
        layout.addWidget(self.lbl_printer_info)

        self.chk_rotate = QCheckBox("90° döndür")
        layout.addWidget(self.chk_rotate)

        layout.addStretch(1)

        self.btn_open_editor = QPushButton("Etiket Editörünü Aç…")
        self.btn_open_editor.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_open_editor, alignment=Qt.AlignRight)

        self.btn_open_editor.clicked.connect(self._open_editor)

        self.load_preferences()

    # ------------------------------------------------------------------
    def load_preferences(self):
        st = load_settings() or {}
        label_prefs = st.get("label_editor", {})
        printing = st.get("printing", {})

        self.mm_w = float(label_prefs.get("mm_w", self.mm_w))
        self.mm_h = float(label_prefs.get("mm_h", self.mm_h))
        self.dpi = int(label_prefs.get("dpi", self.dpi))
        self.grid_mm = float(label_prefs.get("grid_mm", self.grid_mm))
        self.snap_enabled = bool(label_prefs.get("snap", False))
        self.rotate_print = bool(label_prefs.get("rotate_print", False))

        self.spin_width.setValue(self.mm_w)
        self.spin_height.setValue(self.mm_h)
        self.spin_dpi.setValue(self.dpi)
        self.spin_grid.setValue(self.grid_mm)
        self.chk_snap.setChecked(self.snap_enabled)
        self.chk_rotate.setChecked(self.rotate_print)

        printer_name = printing.get("label_printer")
        info_parts = []
        if printer_name:
            info_parts.append(f"Varsayılan etiket yazıcısı: {printer_name}")
        else:
            info_parts.append("Varsayılan etiket yazıcısı seçilmemiş.")
        if printing.get("label_is_thermal"):
            info_parts.append("Termal mod etkin.")
        self.lbl_printer_info.setText(" ".join(info_parts) + " (Yazıcı seçimi Yazıcılar sekmesinden yapılır.)")

    def save_preferences(self):
        st = load_settings() or {}
        label_prefs = st.setdefault("label_editor", {})

        self.mm_w = float(self.spin_width.value())
        self.mm_h = float(self.spin_height.value())
        self.dpi = int(self.spin_dpi.value())
        self.grid_mm = float(self.spin_grid.value())
        self.snap_enabled = bool(self.chk_snap.isChecked())
        self.rotate_print = bool(self.chk_rotate.isChecked())

        label_prefs.update(
            {
                "mm_w": self.mm_w,
                "mm_h": self.mm_h,
                "dpi": self.dpi,
                "grid_mm": self.grid_mm,
                "snap": self.snap_enabled,
                "rotate_print": self.rotate_print,
            }
        )

        try:
            save_settings(st)
        except Exception:
            pass

        return True

    def _open_editor(self):
        dlg = LabelEditorDialog(self)
        dlg.exec_()
        # editörden çıkınca tercihleri yeniden yükleyelim
        self.load_preferences()



class ReceiptSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.mm_w = 80.0
        self.mm_h = 120.0
        self.dpi = 203
        self.rotate_print = False
        self.templates: dict[str, dict] = {}
        self.font_pt = 10  # Düz metin fişler için varsayılan yazı boyutu (termal ve masaüstü yazıcılar için dengeli).

        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        size_group = QGroupBox("Kağıt Ayarı")
        size_form = QFormLayout(size_group)

        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(40.0, 210.0)
        self.spin_width.setSingleStep(0.5)
        self.spin_width.setMaximumWidth(120)
        size_form.addRow("Genişlik (mm)", self.spin_width)

        root.addWidget(size_group)

        self.lbl_printer_info = QLabel()
        self.lbl_printer_info.setWordWrap(True)
        root.addWidget(self.lbl_printer_info)

        template_group = QGroupBox("Şablonlar")
        template_layout = QVBoxLayout(template_group)

        self.template_views: dict[str, QPlainTextEdit] = {}
        for key, title in RECEIPT_SCENARIOS:
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            preview = QPlainTextEdit()
            preview.setReadOnly(True)
            preview.setLineWrapMode(QPlainTextEdit.NoWrap)
            preview.setFixedHeight(140)
            self.template_views[key] = preview
            box_layout.addWidget(preview)
            btn_row = QHBoxLayout()
            btn_edit = QPushButton("Şablonu Düzenle…")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(lambda _, slug=key, caption=title: self._edit_template(slug, caption))
            btn_row.addStretch(1)
            btn_row.addWidget(btn_edit)
            box_layout.addLayout(btn_row)
            template_layout.addWidget(box)

        template_layout.addStretch(1)
        root.addWidget(template_group)

        root.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.load_preferences()

    # ------------------------------------------------------------------
    def load_preferences(self):
        settings = load_settings() or {}
        receipts = settings.get("receipts", {})
        printing = settings.get("printing", {})

        self.mm_w = float(receipts.get("mm_w", self.mm_w))
        self.mm_h = float(receipts.get("mm_h", self.mm_h))
        self.dpi = int(receipts.get("dpi", self.dpi))
        self.font_pt = int(receipts.get("font_pt", self.font_pt or 10))
        self.rotate_print = bool(receipts.get("rotate_print", False))

        raw_templates = receipts.get("templates", {})
        if isinstance(raw_templates, dict):
            self.templates = {
                key: {
                    "title": value.get("title", key) if isinstance(value, dict) else str(key),
                    "body": value.get("body", "") if isinstance(value, dict) else str(value),
                }
                for key, value in raw_templates.items()
            }
        else:
            self.templates = {}

        if not self.templates:
            self.templates = {k: v.copy() for k, v in DEFAULT_RECEIPT_TEMPLATES.items()}
        else:
            for key, value in DEFAULT_RECEIPT_TEMPLATES.items():
                self.templates.setdefault(key, value.copy())

        self.spin_width.setValue(self.mm_w)
        self._refresh_template_previews()

        self._refresh_printer_info(printing)

    # ------------------------------------------------------------------
    def save_preferences(self):
        settings = load_settings() or {}
        receipts = settings.setdefault("receipts", {})

        self.mm_w = float(self.spin_width.value())
        self.mm_h = float(self.mm_h)
        self.dpi = int(self.dpi)
        self.rotate_print = bool(self.rotate_print)

        receipts.update(
            {
                "mm_w": self.mm_w,
                "mm_h": self.mm_h,
                "dpi": self.dpi,
                "rotate_print": self.rotate_print,
                "font_pt": self.font_pt,
                "templates": self.templates,
            }
        )

        try:
            save_settings(settings)
        except Exception as exc:
            QMessageBox.warning(self, "Kayıt Hatası", f"Ayarlar kaydedilemedi.\n{exc}")
            return False
        return True

    # ------------------------------------------------------------------
    def _refresh_printer_info(self, printing: dict):
        printer_name = printing.get("receipt_printer") or printing.get("label_printer")
        parts = []
        if printer_name:
            parts.append(f"Varsayılan fiş yazıcısı: {printer_name}")
        else:
            parts.append("Varsayılan fiş yazıcısı seçilmemiş.")
        if printing.get("receipt_is_thermal"):
            parts.append("Termal mod etkin.")
        info = " ".join(parts) + " (Yazıcı seçimi Yazıcılar sekmesinden yapılır.)"
        self.lbl_printer_info.setText(info)

    def _refresh_template_previews(self):
        for slug, view in self.template_views.items():
            tmpl = self.templates.get(slug) or {}
            body = tmpl.get("body", "").strip()
            view.setPlainText(body)

    def _edit_template(self, slug: str, title: str):
        data = self.templates.get(slug) or {}
        dialog = ReceiptTemplateDialog(
            parent=self,
            template_name=title,
            template_body=data.get("body", ""),
            placeholders=RECEIPT_PLACEHOLDERS,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        self.templates[slug] = {
            "title": title,
            "body": dialog.template_text(),
        }
        self._refresh_template_previews()

class PasswordSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()

        self.lbl_user = QLabel("")
        form.addRow("Kullanıcı", self.lbl_user)

        self.current_password = QLineEdit()
        self.current_password.setEchoMode(QLineEdit.Password)
        form.addRow("Mevcut şifre", self.current_password)

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        form.addRow("Yeni şifre", self.new_password)

        self.new_password_again = QLineEdit()
        self.new_password_again.setEchoMode(QLineEdit.Password)
        form.addRow("Yeni şifre (tekrar)", self.new_password_again)

        layout.addLayout(form)

        session_group = QGroupBox("Oturum")
        session_form = QFormLayout(session_group)
        self.chk_auto_logout = QCheckBox("Hareketsizlikte otomatik çıkış")
        session_form.addRow(self.chk_auto_logout)
        self.spin_auto_logout = QSpinBox()
        self.spin_auto_logout.setRange(1, 30)
        self.spin_auto_logout.setSuffix(" dk")
        session_form.addRow("Süre", self.spin_auto_logout)
        layout.addWidget(session_group)
        self.chk_auto_logout.toggled.connect(self.spin_auto_logout.setEnabled)

        layout.addStretch(1)

        tip = QLabel("Şifre değişikliği sonrası tekrar giriş yapmanız gerekebilir.")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self._refresh_user_label()
        self._load_session_preferences()

    def save_preferences(self):
        current = self.current_password.text().strip()
        new1 = self.new_password.text().strip()
        new2 = self.new_password_again.text().strip()
        has_password_input = any([current, new1, new2])

        if has_password_input:
            username = auth.get_current_username()
            if not username:
                QMessageBox.warning(self, "Şifre Değiştirme", "Oturum bilgisi bulunamadı. Önce giriş yapın.")
                return False
            if not all([current, new1, new2]):
                QMessageBox.warning(self, "Hata", "Şifre değiştirmek için tüm alanları doldurun.")
                return False
            if new1 != new2:
                QMessageBox.warning(self, "Hata", "Yeni şifre alanları birbiriyle uyuşmuyor.")
                return False

            ok, message = auth.change_password(current, new1, new2)
            if ok:
                QMessageBox.information(self, "Şifre Değiştirme", message)
                self.current_password.clear()
                self.new_password.clear()
                self.new_password_again.clear()
            else:
                QMessageBox.warning(self, "Şifre Değiştirme", message or "Şifre güncellenemedi.")
                return False

        if not self._save_session_preferences():
            return False

        dialog = self.window()
        parent_window = dialog.parent() if dialog else None
        if parent_window and hasattr(parent_window, "_setup_inactivity_timer"):
            try:
                parent_window._setup_inactivity_timer()
            except Exception:
                pass

        changed = bool(has_password_input)
        return True, ("Şifre güncellendi." if changed else "Oturum ayarları kaydedildi.")

    def _refresh_user_label(self):
        username = auth.get_current_username() or "(bilinmiyor)"
        self.lbl_user.setText(username)

    def _load_session_preferences(self):
        settings = load_settings() or {}
        session = settings.get("session", {})
        enabled = bool(session.get("auto_logout_enabled", True))
        minutes = session.get("auto_logout_minutes", 10)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 10
        minutes = min(max(minutes, 1), 30)
        self.chk_auto_logout.setChecked(enabled)
        self.spin_auto_logout.setValue(minutes)
        self.spin_auto_logout.setEnabled(enabled)

    def _save_session_preferences(self):
        settings = load_settings() or {}
        session = settings.setdefault("session", {})
        session["auto_logout_enabled"] = bool(self.chk_auto_logout.isChecked())
        session["auto_logout_minutes"] = int(self.spin_auto_logout.value())
        try:
            save_settings(settings)
        except Exception as exc:
            QMessageBox.warning(self, "Oturum Ayarları", f"Ayarlar kaydedilemedi.\n{exc}")
            return False
        return True


class LoansSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roles = []
        self.role_policies = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        title = QLabel("Rol bazlı ödünç ayarları")
        title.setStyleSheet("font-weight:600;font-size:14px;")
        root_layout.addWidget(title)

        helper = QHBoxLayout()
        helper.setSpacing(12)
        helper.addSpacing(60)
        for text, tip in [
            ("Süre (gün)", "Bu rol için ödünç verilen kitabın başlangıç süresi."),
            ("Maks. ödünç", "Bu rol aynı anda en fazla kaç kitabı ödünç alabilir."),
            ("Gecikme toleransı", "İade tarihi aşıldıktan sonra gecikmiş sayılmadan önce tanınan ek gün."),
            ("Ceza gecikmesi", "Gecikme tespit edildiğinde cezanın başlamadan önce beklenen süre."),
            ("Hafta sonu", "İade tarihi hafta sonuna denk gelirse bir sonraki iş gününe kaydır."),
        ]:
            helper.addWidget(self._header_with_help(text, tip))
        helper.addStretch(1)
        root_layout.addLayout(helper)

        self.table_roles = QTableWidget(0, 6)
        self.table_roles.setHorizontalHeaderLabels([
            "Rol",
            "Süre (gün)",
            "Maks. ödünç",
            "Gecikme toleransı",
            "Ceza gecikmesi",
            "Hafta sonu kaydır",
        ])
        header = self.table_roles.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        root_layout.addWidget(self.table_roles)

        warning = QLabel(
            "Süre veya maks. ödünç değerlerinden herhangi biri 0 olursa bu rol için ödünç verme işlemi devre dışı bırakılır."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#ff0000;")
        root_layout.addWidget(warning)

        self.load_preferences()

    def _header_with_help(self, text, message):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(text)
        layout.addWidget(label)
        btn = QPushButton("?")
        btn.setFixedSize(20, 20)
        btn.setObjectName("HelpButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Açıklamayı görüntüle")

        def show_message():
            QMessageBox.information(self, "Açıklama", message)

        btn.clicked.connect(show_message)
        layout.addWidget(btn)
        return container

    def load_preferences(self):
        roles_resp = roles_api.list_roles()
        try:
            roles = roles_resp.json() if roles_resp and roles_resp.status_code == 200 else []
        except Exception:
            roles = []
        self.roles = roles or []

        role_policies = {}
        role_resp = settings_api.fetch_role_loan_policies()
        if role_resp is not None and getattr(role_resp, "status_code", None) == 200:
            try:
                data = role_resp.json() or []
            except ValueError:
                data = []
            for item in data:
                rid = item.get("role_id")
                if rid is None:
                    continue
                role_policies[rid] = item
            st = load_settings() or {}
            st["role_loans"] = {str(k): v for k, v in role_policies.items()}
            try:
                save_settings(st)
            except Exception:
                pass
        else:
            st = load_settings() or {}
            cached = st.get("role_loans", {}) or {}
            role_policies = {int(k): v for k, v in cached.items() if k is not None}

        self.role_policies = role_policies

        self.table_roles.setRowCount(len(self.roles))
        for row, role in enumerate(self.roles):
            role_id = role.get("id")
            name = role.get("ad", "")
            item_role = QTableWidgetItem(name)
            item_role.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_role.setData(Qt.UserRole, role)
            self.table_roles.setItem(row, 0, item_role)

            overrides = role_policies.get(role_id, {})

            def _int_text(value):
                if value in (None, ""):
                    return ""
                try:
                    iv = int(value)
                except (TypeError, ValueError):
                    return ""
                return str(iv)

            dur_item = QTableWidgetItem(_int_text(overrides.get("duration")))
            max_item = QTableWidgetItem(_int_text(overrides.get("max_items")))
            grace_item = QTableWidgetItem(_int_text(overrides.get("delay_grace_days")))
            penalty_item = QTableWidgetItem(_int_text(overrides.get("penalty_delay_days")))
            for itm in (dur_item, max_item, grace_item, penalty_item):
                itm.setTextAlignment(Qt.AlignCenter)
            self.table_roles.setItem(row, 1, dur_item)
            self.table_roles.setItem(row, 2, max_item)
            self.table_roles.setItem(row, 3, grace_item)
            self.table_roles.setItem(row, 4, penalty_item)

            shift_item = QTableWidgetItem()
            shift_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            shift = overrides.get("shift_weekend")
            if isinstance(shift, bool):
                shift_item.setCheckState(Qt.Checked if shift else Qt.Unchecked)
            else:
                shift_item.setCheckState(Qt.PartiallyChecked)
            self.table_roles.setItem(row, 5, shift_item)

    def save_preferences(self):
        overrides = self._collect_role_overrides()
        role_resp = settings_api.update_role_loan_policies(overrides)
        if role_resp is None or getattr(role_resp, "status_code", None) not in (200, 202):
            QMessageBox.warning(
                self,
                "Rol ayarları",
                response_error_message(role_resp, "Rol bazlı ayarlar kaydedilemedi."),
            )
            return False

        try:
            data = role_resp.json() or []
        except Exception:
            data = []
        st = load_settings() or {}
        st["role_loans"] = {str(item.get("role_id")): item for item in data if item.get("role_id") is not None}
        self.role_policies = {item.get("role_id"): item for item in data if item.get("role_id") is not None}
        try:
            save_settings(st)
        except Exception:
            pass

        self.load_preferences()
        return True

    def _collect_role_overrides(self):
        overrides = []
        for row in range(self.table_roles.rowCount()):
            role_item = self.table_roles.item(row, 0)
            if not role_item:
                continue
            role_data = role_item.data(Qt.UserRole) or {}
            role_id = role_data.get("id")
            if role_id is None:
                continue

            def _parse_int(item):
                if not item or not item.text().strip():
                    return None
                try:
                    return int(item.text().strip())
                except ValueError:
                    return None

            duration = _parse_int(self.table_roles.item(row, 1))
            max_items = _parse_int(self.table_roles.item(row, 2))
            grace_days = _parse_int(self.table_roles.item(row, 3))
            penalty_delay = _parse_int(self.table_roles.item(row, 4))

            shift_item = self.table_roles.item(row, 5)
            if shift_item and shift_item.checkState() != Qt.PartiallyChecked:
                shift_weekend = shift_item.checkState() == Qt.Checked
            else:
                shift_weekend = None

            existing = self.role_policies.get(role_id, {})
            penalty_max_per_loan = existing.get("penalty_max_per_loan")
            penalty_max_per_student = existing.get("penalty_max_per_student")
            daily_penalty_rate = existing.get("daily_penalty_rate")

            overrides.append({
                "role_id": role_id,
                "duration": duration,
                "max_items": max_items,
                "delay_grace_days": grace_days,
                "penalty_delay_days": penalty_delay,
                "shift_weekend": shift_weekend,
                "penalty_max_per_loan": penalty_max_per_loan,
                "penalty_max_per_student": penalty_max_per_student,
                "daily_penalty_rate": daily_penalty_rate,
            })
        return overrides

class PenaltySettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roles = []
        self.role_policies = {}
        self.default_penalty_max_per_loan = 0.0
        self.default_penalty_max_per_student = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        title = QLabel("Rol bazlı ceza ayarları")
        title.setStyleSheet("font-weight:600;font-size:14px;")
        root.addWidget(title)

        info = QLabel(
            "Her rol için günlük gecikme cezası ve üst limitleri tanımlayın."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#555;")
        root.addWidget(info)

        self.table_roles = QTableWidget(0, 4)
        self.table_roles.setHorizontalHeaderLabels(
            ["Rol", "Günlük ceza (TL)", "Ödünç başına azami (TL)", "Kişi başına azami (TL)"]
        )
        header = self.table_roles.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for idx in range(1, 4):
            header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
        self.table_roles.verticalHeader().setVisible(False)
        root.addWidget(self.table_roles, 1)

        tip = QLabel("Tüm limit alanları zorunludur. 0 değeri sınırsız anlamına gelir.")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#ff0000;")
        root.addWidget(tip)

        self.load_preferences()

    # ------------------------------------------------------------------
    def _format_decimal(self, value, fallback):
        target = value if value not in (None, "") else fallback
        try:
            val = Decimal(str(target))
        except (InvalidOperation, ValueError):
            val = Decimal("0")
        return f"{val:.2f}"

    def _parse_decimal_item(self, item):
        if item is None:
            return None, "Değer gereklidir."
        text = (item.text() or "").strip().replace(",", ".")
        if not text:
            return None, "Bu alan boş bırakılamaz."
        try:
            value = Decimal(text)
        except (InvalidOperation, ValueError):
            return None, "Geçerli bir sayı girin."
        if value < 0:
            return None, "Negatif değer girilemez."
        return f"{value.quantize(Decimal('0.01'))}", None

    # ------------------------------------------------------------------
    def load_preferences(self):
        policy = {}
        resp = settings_api.fetch_loan_policy()
        if resp is not None and getattr(resp, "status_code", None) == 200:
            try:
                policy = resp.json() or {}
            except ValueError:
                policy = {}

            st = load_settings() or {}
            st.setdefault("loans", {}).update(policy)
            try:
                save_settings(st)
            except Exception:
                pass
        else:
            st = load_settings() or {}
            policy = st.get("loans", {}) or {}

        self.default_penalty_max_per_loan = float(policy.get("penalty_max_per_loan", 0) or 0)
        self.default_penalty_max_per_student = float(policy.get("penalty_max_per_student", 0) or 0)

        role_policies = {}
        role_resp = settings_api.fetch_role_loan_policies()
        if role_resp is not None and getattr(role_resp, "status_code", None) == 200:
            try:
                data = role_resp.json() or []
            except ValueError:
                data = []
            for item in data:
                rid = item.get("role_id")
                if rid is None:
                    continue
                role_policies[rid] = item
            st = load_settings() or {}
            st["role_loans"] = {str(k): v for k, v in role_policies.items()}
            try:
                save_settings(st)
            except Exception:
                pass
        else:
            st = load_settings() or {}
            cached = st.get("role_loans", {}) or {}
            role_policies = {int(k): v for k, v in cached.items() if k is not None}

        self.role_policies = role_policies

        roles_resp = roles_api.list_roles()
        try:
            roles = roles_resp.json() if roles_resp and roles_resp.status_code == 200 else []
        except Exception:
            roles = []
        self.roles = roles or []

        self.table_roles.setRowCount(len(self.roles))
        for row, role in enumerate(self.roles):
            role_id = role.get("id")
            role_info = role_policies.get(role_id, {})

            name_item = QTableWidgetItem(role.get("ad", ""))
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            name_item.setData(Qt.UserRole, role)
            self.table_roles.setItem(row, 0, name_item)

            rate_text = self._format_decimal(role_info.get("daily_penalty_rate"), Decimal("0"))
            rate_item = QTableWidgetItem(rate_text)
            rate_item.setTextAlignment(Qt.AlignCenter)
            rate_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.table_roles.setItem(row, 1, rate_item)

            loan_cap = self._format_decimal(
                role_info.get("penalty_max_per_loan"),
                self.default_penalty_max_per_loan,
            )
            loan_item = QTableWidgetItem(loan_cap)
            loan_item.setTextAlignment(Qt.AlignCenter)
            loan_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.table_roles.setItem(row, 2, loan_item)

            student_cap = self._format_decimal(
                role_info.get("penalty_max_per_student"),
                self.default_penalty_max_per_student,
            )
            student_item = QTableWidgetItem(student_cap)
            student_item.setTextAlignment(Qt.AlignCenter)
            student_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            self.table_roles.setItem(row, 3, student_item)

    # ------------------------------------------------------------------
    def save_preferences(self):
        invalid_values = []

        overrides = []
        for row in range(self.table_roles.rowCount()):
            role_item = self.table_roles.item(row, 0)
            rate_item = self.table_roles.item(row, 1)
            loan_item = self.table_roles.item(row, 2)
            student_item = self.table_roles.item(row, 3)
            if not role_item:
                continue
            role_data = role_item.data(Qt.UserRole) or {}
            role_id = role_data.get("id")
            if not role_id:
                continue

            rate_value, rate_err = self._parse_decimal_item(rate_item)
            loan_cap, loan_err = self._parse_decimal_item(loan_item)
            student_cap, student_err = self._parse_decimal_item(student_item)
            if rate_err or loan_err or student_err:
                invalid_values.append(role_data.get("ad", "Rol"))
                continue

            existing = self.role_policies.get(role_id, {})
            override_entry = {
                "role_id": role_id,
                "duration": existing.get("duration"),
                "max_items": existing.get("max_items"),
                "delay_grace_days": existing.get("delay_grace_days"),
                "penalty_delay_days": existing.get("penalty_delay_days"),
                "shift_weekend": existing.get("shift_weekend"),
                "daily_penalty_rate": rate_value,
                "penalty_max_per_loan": loan_cap,
                "penalty_max_per_student": student_cap,
            }
            overrides.append(override_entry)

        if invalid_values:
            QMessageBox.warning(
                self,
                "Geçersiz değer",
                "Şu roller için ceza limitleri boş bırakılamaz veya hatalı: " + ", ".join(invalid_values),
            )
            return False

        role_resp = settings_api.update_role_loan_policies(overrides)
        if role_resp is None or getattr(role_resp, "status_code", None) not in (200, 202):
            QMessageBox.warning(
                self,
                "Kaydedilemedi",
                response_error_message(role_resp, "Rol bazlı ceza limitleri kaydedilemedi."),
            )
            return False

        try:
            data = role_resp.json() or []
        except Exception:
            data = []
        self.role_policies = {item.get("role_id"): item for item in data if item.get("role_id") is not None}

        st = load_settings() or {}
        st["role_loans"] = {str(k): v for k, v in self.role_policies.items()}
        try:
            save_settings(st)
        except Exception:
            pass

        self.load_preferences()
        return True


class NotificationSettingsWidget(QWidget):
    PLACEHOLDERS = [
        ("ogrenci_ad", "Öğrencinin adı"),
        ("ogrenci_soyad", "Öğrencinin soyadı"),
        ("ogrenci_no", "Öğrenci numarası"),
        ("rol", "Öğrencinin rolü"),
        ("kitap_baslik", "Kitap adı"),
        ("kitap_barkod", "Kitap barkodu"),
        ("iade_tarihi", "Planlanan iade tarihi"),
        ("odunc_tarihi", "Ödünç tarihi"),
        ("gecikme_gun", "Gecikme gün sayısı"),
        ("kutuphane_adi", "Kütüphane adı"),
        ("sunucu_tarihi", "Bildirim gönderim tarihi"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setContentsMargins(0, 0, 0, 12)
        scroll_layout.setSpacing(12)

        general_box = QGroupBox("Genel bildirimler")
        general_layout = QFormLayout(general_box)
        general_layout.setLabelAlignment(Qt.AlignLeft)

        self.chk_printer_warning = QCheckBox("Açılışta yazıcı bağlantısını kontrol et")
        general_layout.addRow(self.chk_printer_warning)

        reminder_row = QHBoxLayout()
        self.chk_due_reminder = QCheckBox("İade tarihi yaklaşınca hatırlatma gönder")
        reminder_row.addWidget(self.chk_due_reminder)
        reminder_row.addStretch(1)
        general_layout.addRow(reminder_row)

        reminder_channels_layout = QHBoxLayout()
        self.chk_due_reminder_email = QCheckBox("E-posta")
        reminder_channels_layout.addWidget(self.chk_due_reminder_email)
        self.chk_due_reminder_sms = QCheckBox("SMS")
        reminder_channels_layout.addWidget(self.chk_due_reminder_sms)
        self.chk_due_reminder_mobile = QCheckBox("Mobil")
        reminder_channels_layout.addWidget(self.chk_due_reminder_mobile)
        reminder_channels_layout.addStretch(1)
        reminder_channels_widget = QWidget()
        reminder_channels_widget.setLayout(reminder_channels_layout)
        general_layout.addRow("Kanallar", reminder_channels_widget)

        self.spin_reminder_days = QSpinBox()
        self.spin_reminder_days.setRange(0, 60)
        self.spin_reminder_days.setSuffix(" gün önce")
        general_layout.addRow("Gönderim zamanı", self.spin_reminder_days)

        overdue_row = QHBoxLayout()
        self.chk_due_overdue = QCheckBox("İade geciktiğinde bildirim gönder")
        overdue_row.addWidget(self.chk_due_overdue)
        overdue_row.addStretch(1)
        general_layout.addRow(overdue_row)

        overdue_channels_layout = QHBoxLayout()
        self.chk_overdue_email = QCheckBox("E-posta")
        overdue_channels_layout.addWidget(self.chk_overdue_email)
        self.chk_overdue_sms = QCheckBox("SMS")
        overdue_channels_layout.addWidget(self.chk_overdue_sms)
        self.chk_overdue_mobile = QCheckBox("Mobil")
        overdue_channels_layout.addWidget(self.chk_overdue_mobile)
        overdue_channels_layout.addStretch(1)
        overdue_channels_widget = QWidget()
        overdue_channels_widget.setLayout(overdue_channels_layout)
        general_layout.addRow("Kanallar", overdue_channels_widget)

        self.spin_overdue_days = QSpinBox()
        self.spin_overdue_days.setRange(0, 60)
        self.spin_overdue_days.setSuffix(" gün sonra")
        general_layout.addRow("Gecikme bildirimi", self.spin_overdue_days)

        scroll_layout.addWidget(general_box)

        email_box = QGroupBox("E-posta bildirimleri")
        email_layout = QFormLayout(email_box)
        self.chk_email_enabled = QCheckBox("E-posta gönder")
        email_layout.addRow(self.chk_email_enabled)
        self.edit_email_sender = QLineEdit()
        email_layout.addRow("Gönderen adres", self.edit_email_sender)
        self.edit_email_host = QLineEdit()
        email_layout.addRow("SMTP sunucusu", self.edit_email_host)
        self.spin_email_port = QSpinBox()
        self.spin_email_port.setRange(1, 65535)
        email_layout.addRow("Port", self.spin_email_port)
        self.chk_email_tls = QCheckBox("TLS kullan")
        email_layout.addRow(self.chk_email_tls)
        self.edit_email_username = QLineEdit()
        email_layout.addRow("Kullanıcı adı", self.edit_email_username)
        self.edit_email_password = QLineEdit()
        self.edit_email_password.setEchoMode(QLineEdit.Password)
        email_layout.addRow("Parola", self.edit_email_password)

        email_schedule_layout = QHBoxLayout()
        self.chk_email_schedule = QCheckBox("Belirli saatte gönder")
        email_schedule_layout.addWidget(self.chk_email_schedule)
        self.time_email_schedule = QTimeEdit()
        self.time_email_schedule.setDisplayFormat("HH:mm")
        email_schedule_layout.addWidget(self.time_email_schedule)
        self.edit_email_timezone = QLineEdit()
        self.edit_email_timezone.setPlaceholderText("Zaman dilimi (örn. Europe/Istanbul)")
        email_schedule_layout.addWidget(self.edit_email_timezone)
        email_schedule_layout.addStretch(1)
        email_schedule_widget = QWidget()
        email_schedule_widget.setLayout(email_schedule_layout)
        email_layout.addRow("Planlama", email_schedule_widget)
        scroll_layout.addWidget(email_box)

        sms_box = QGroupBox("SMS bildirimleri")
        sms_layout = QFormLayout(sms_box)
        self.chk_sms_enabled = QCheckBox("SMS gönder")
        sms_layout.addRow(self.chk_sms_enabled)
        self.edit_sms_provider = QLineEdit()
        sms_layout.addRow("Servis sağlayıcı", self.edit_sms_provider)
        self.edit_sms_url = QLineEdit()
        sms_layout.addRow("API adresi", self.edit_sms_url)
        self.edit_sms_key = QLineEdit()
        self.edit_sms_key.setEchoMode(QLineEdit.Password)
        sms_layout.addRow("API anahtarı", self.edit_sms_key)

        sms_schedule_layout = QHBoxLayout()
        self.chk_sms_schedule = QCheckBox("Belirli saatte gönder")
        sms_schedule_layout.addWidget(self.chk_sms_schedule)
        self.time_sms_schedule = QTimeEdit()
        self.time_sms_schedule.setDisplayFormat("HH:mm")
        sms_schedule_layout.addWidget(self.time_sms_schedule)
        self.edit_sms_timezone = QLineEdit()
        self.edit_sms_timezone.setPlaceholderText("Zaman dilimi")
        sms_schedule_layout.addWidget(self.edit_sms_timezone)
        sms_schedule_layout.addStretch(1)
        sms_schedule_widget = QWidget()
        sms_schedule_widget.setLayout(sms_schedule_layout)
        sms_layout.addRow("Planlama", sms_schedule_widget)
        scroll_layout.addWidget(sms_box)

        mobile_box = QGroupBox("Mobil bildirimler")
        mobile_layout = QFormLayout(mobile_box)
        self.chk_mobile_enabled = QCheckBox("Mobil uygulama bildirimlerini gönder")
        mobile_layout.addRow(self.chk_mobile_enabled)

        mobile_schedule_layout = QHBoxLayout()
        self.chk_mobile_schedule = QCheckBox("Belirli saatte gönder")
        mobile_schedule_layout.addWidget(self.chk_mobile_schedule)
        self.time_mobile_schedule = QTimeEdit()
        self.time_mobile_schedule.setDisplayFormat("HH:mm")
        mobile_schedule_layout.addWidget(self.time_mobile_schedule)
        self.edit_mobile_timezone = QLineEdit()
        self.edit_mobile_timezone.setPlaceholderText("Zaman dilimi")
        mobile_schedule_layout.addWidget(self.edit_mobile_timezone)
        mobile_schedule_layout.addStretch(1)
        mobile_schedule_widget = QWidget()
        mobile_schedule_widget.setLayout(mobile_schedule_layout)
        mobile_layout.addRow("Planlama", mobile_schedule_widget)
        scroll_layout.addWidget(mobile_box)

        template_box = QGroupBox("Mesaj şablonları")
        template_layout = QFormLayout(template_box)

        self.edit_reminder_subject = QLineEdit()
        self.btn_edit_reminder_subject = QPushButton("Şablonu Düzenle…")
        self.btn_edit_reminder_subject.clicked.connect(lambda: self._open_template_editor("reminder_subject", multiline=False))
        subject_container = QHBoxLayout()
        subject_container.addWidget(self.edit_reminder_subject, 1)
        subject_container.addWidget(self.btn_edit_reminder_subject)
        subject_widget = QWidget()
        subject_widget.setLayout(subject_container)
        template_layout.addRow("Hatırlatma konusu", subject_widget)

        self.edit_reminder_body = QPlainTextEdit()
        self.edit_reminder_body.setPlaceholderText("Hatırlatma mesajı gövdesi…")
        self.edit_reminder_body.setFixedHeight(100)
        self.btn_edit_reminder_body = QPushButton("Şablonu Düzenle…")
        self.btn_edit_reminder_body.clicked.connect(lambda: self._open_template_editor("reminder_body", multiline=True))
        body_container = QVBoxLayout()
        body_container.addWidget(self.edit_reminder_body)
        btn_body_container = QHBoxLayout()
        btn_body_container.addStretch(1)
        btn_body_container.addWidget(self.btn_edit_reminder_body)
        body_container.addLayout(btn_body_container)
        body_widget = QWidget()
        body_widget.setLayout(body_container)
        template_layout.addRow("Hatırlatma metni", body_widget)

        self.edit_overdue_subject = QLineEdit()
        self.btn_edit_overdue_subject = QPushButton("Şablonu Düzenle…")
        self.btn_edit_overdue_subject.clicked.connect(lambda: self._open_template_editor("overdue_subject", multiline=False))
        overdue_subject_layout = QHBoxLayout()
        overdue_subject_layout.addWidget(self.edit_overdue_subject, 1)
        overdue_subject_layout.addWidget(self.btn_edit_overdue_subject)
        overdue_subject_widget = QWidget()
        overdue_subject_widget.setLayout(overdue_subject_layout)
        template_layout.addRow("Gecikme konusu", overdue_subject_widget)

        self.edit_overdue_body = QPlainTextEdit()
        self.edit_overdue_body.setPlaceholderText("Gecikme bildirimi gövdesi…")
        self.edit_overdue_body.setFixedHeight(100)
        self.btn_edit_overdue_body = QPushButton("Şablonu Düzenle…")
        self.btn_edit_overdue_body.clicked.connect(lambda: self._open_template_editor("overdue_body", multiline=True))
        overdue_body_layout = QVBoxLayout()
        overdue_body_layout.addWidget(self.edit_overdue_body)
        overdue_body_btn_layout = QHBoxLayout()
        overdue_body_btn_layout.addStretch(1)
        overdue_body_btn_layout.addWidget(self.btn_edit_overdue_body)
        overdue_body_layout.addLayout(overdue_body_btn_layout)
        overdue_body_widget = QWidget()
        overdue_body_widget.setLayout(overdue_body_layout)
        template_layout.addRow("Gecikme metni", overdue_body_widget)

        scroll_layout.addWidget(template_box)
        scroll_layout.addStretch(1)

        scroll.setWidget(container)
        root.addWidget(scroll)

        self.chk_due_reminder.toggled.connect(self._sync_reminder_fields)
        self.chk_due_overdue.toggled.connect(self._sync_overdue_fields)
        self.chk_email_enabled.toggled.connect(self._sync_email_fields)
        self.chk_email_schedule.toggled.connect(self._sync_email_schedule_fields)
        self.chk_sms_enabled.toggled.connect(self._sync_sms_fields)
        self.chk_sms_schedule.toggled.connect(self._sync_sms_schedule_fields)
        self.chk_mobile_enabled.toggled.connect(self._sync_mobile_fields)
        self.chk_mobile_schedule.toggled.connect(self._sync_mobile_schedule_fields)

        self.load_preferences()

    def load_preferences(self):
        response = settings_api.fetch_notification_settings()
        if response is not None and getattr(response, "status_code", None) == 200:
            try:
                self.data = response.json() or {}
            except ValueError:
                self.data = {}
            cache = load_settings() or {}
            cache["notification_settings"] = self.data
            try:
                save_settings(cache)
            except Exception:
                pass
        else:
            cache = load_settings() or {}
            self.data = cache.get("notification_settings", {})

        data = self.data or {}

        self.chk_printer_warning.setChecked(bool(data.get("printer_warning_enabled", True)))
        self.chk_due_reminder.setChecked(bool(data.get("due_reminder_enabled", True)))
        self.spin_reminder_days.setValue(int(data.get("due_reminder_days_before", 1) or 0))
        self.chk_due_reminder_email.setChecked(bool(data.get("due_reminder_email_enabled", True)))
        self.chk_due_reminder_sms.setChecked(bool(data.get("due_reminder_sms_enabled", True)))
        self.chk_due_reminder_mobile.setChecked(bool(data.get("due_reminder_mobile_enabled", True)))
        self.chk_due_overdue.setChecked(bool(data.get("due_overdue_enabled", True)))
        self.spin_overdue_days.setValue(int(data.get("due_overdue_days_after", 0) or 0))
        self.chk_overdue_email.setChecked(bool(data.get("overdue_email_enabled", True)))
        self.chk_overdue_sms.setChecked(bool(data.get("overdue_sms_enabled", True)))
        self.chk_overdue_mobile.setChecked(bool(data.get("overdue_mobile_enabled", True)))

        self.chk_email_enabled.setChecked(bool(data.get("email_enabled", False)))
        self.edit_email_sender.setText(data.get("email_sender", ""))
        self.edit_email_host.setText(data.get("email_smtp_host", ""))
        self.spin_email_port.setValue(int(data.get("email_smtp_port", 587) or 587))
        self.chk_email_tls.setChecked(bool(data.get("email_use_tls", True)))
        self.edit_email_username.setText(data.get("email_username", ""))
        self.edit_email_password.setText(data.get("email_password", ""))
        self.chk_email_schedule.setChecked(bool(data.get("email_schedule_enabled", False)))
        email_hour = int(data.get("email_schedule_hour", 9) or 0)
        email_minute = int(data.get("email_schedule_minute", 0) or 0)
        self.time_email_schedule.setTime(QTime(email_hour % 24, email_minute % 60))
        self.edit_email_timezone.setText(data.get("email_schedule_timezone", ""))

        self.chk_sms_enabled.setChecked(bool(data.get("sms_enabled", False)))
        self.edit_sms_provider.setText(data.get("sms_provider", ""))
        self.edit_sms_url.setText(data.get("sms_api_url", ""))
        self.edit_sms_key.setText(data.get("sms_api_key", ""))
        self.chk_sms_schedule.setChecked(bool(data.get("sms_schedule_enabled", False)))
        sms_hour = int(data.get("sms_schedule_hour", 9) or 0)
        sms_minute = int(data.get("sms_schedule_minute", 0) or 0)
        self.time_sms_schedule.setTime(QTime(sms_hour % 24, sms_minute % 60))
        self.edit_sms_timezone.setText(data.get("sms_schedule_timezone", ""))

        self.chk_mobile_enabled.setChecked(bool(data.get("mobile_enabled", False)))
        self.chk_mobile_schedule.setChecked(bool(data.get("mobile_schedule_enabled", False)))
        mobile_hour = int(data.get("mobile_schedule_hour", 9) or 0)
        mobile_minute = int(data.get("mobile_schedule_minute", 0) or 0)
        self.time_mobile_schedule.setTime(QTime(mobile_hour % 24, mobile_minute % 60))
        self.edit_mobile_timezone.setText(data.get("mobile_schedule_timezone", ""))

        self.edit_reminder_subject.setText(data.get("reminder_subject", ""))
        self.edit_reminder_body.setPlainText(data.get("reminder_body", ""))
        self.edit_overdue_subject.setText(data.get("overdue_subject", ""))
        self.edit_overdue_body.setPlainText(data.get("overdue_body", ""))

        self._sync_reminder_fields()
        self._sync_overdue_fields()
        self._sync_email_fields()
        self._sync_sms_fields()
        self._sync_mobile_fields()

    def save_preferences(self):
        payload = {
            "printer_warning_enabled": bool(self.chk_printer_warning.isChecked()),
            "due_reminder_enabled": bool(self.chk_due_reminder.isChecked()),
            "due_reminder_days_before": int(self.spin_reminder_days.value()),
            "due_reminder_email_enabled": bool(self.chk_due_reminder_email.isChecked()),
            "due_reminder_sms_enabled": bool(self.chk_due_reminder_sms.isChecked()),
            "due_reminder_mobile_enabled": bool(self.chk_due_reminder_mobile.isChecked()),
            "due_overdue_enabled": bool(self.chk_due_overdue.isChecked()),
            "due_overdue_days_after": int(self.spin_overdue_days.value()),
            "overdue_email_enabled": bool(self.chk_overdue_email.isChecked()),
            "overdue_sms_enabled": bool(self.chk_overdue_sms.isChecked()),
            "overdue_mobile_enabled": bool(self.chk_overdue_mobile.isChecked()),
            "email_enabled": bool(self.chk_email_enabled.isChecked()),
            "email_sender": self.edit_email_sender.text().strip(),
            "email_smtp_host": self.edit_email_host.text().strip(),
            "email_smtp_port": int(self.spin_email_port.value()),
            "email_use_tls": bool(self.chk_email_tls.isChecked()),
            "email_username": self.edit_email_username.text().strip(),
            "email_password": self.edit_email_password.text(),
            "email_schedule_enabled": bool(self.chk_email_schedule.isChecked()),
            "email_schedule_hour": int(self.time_email_schedule.time().hour()),
            "email_schedule_minute": int(self.time_email_schedule.time().minute()),
            "email_schedule_timezone": self.edit_email_timezone.text().strip(),
            "sms_enabled": bool(self.chk_sms_enabled.isChecked()),
            "sms_provider": self.edit_sms_provider.text().strip(),
            "sms_api_url": self.edit_sms_url.text().strip(),
            "sms_api_key": self.edit_sms_key.text(),
            "sms_schedule_enabled": bool(self.chk_sms_schedule.isChecked()),
            "sms_schedule_hour": int(self.time_sms_schedule.time().hour()),
            "sms_schedule_minute": int(self.time_sms_schedule.time().minute()),
            "sms_schedule_timezone": self.edit_sms_timezone.text().strip(),
            "mobile_enabled": bool(self.chk_mobile_enabled.isChecked()),
            "mobile_schedule_enabled": bool(self.chk_mobile_schedule.isChecked()),
            "mobile_schedule_hour": int(self.time_mobile_schedule.time().hour()),
            "mobile_schedule_minute": int(self.time_mobile_schedule.time().minute()),
            "mobile_schedule_timezone": self.edit_mobile_timezone.text().strip(),
            "reminder_subject": self.edit_reminder_subject.text(),
            "reminder_body": self.edit_reminder_body.toPlainText(),
            "overdue_subject": self.edit_overdue_subject.text(),
            "overdue_body": self.edit_overdue_body.toPlainText(),
        }

        response = settings_api.update_notification_settings(payload, partial=False)
        if response is None or getattr(response, "status_code", None) not in (200, 202):
            QMessageBox.warning(self, "Bildirim Ayarları", response_error_message(response, "Ayarlar kaydedilemedi."))
            return False

        try:
            self.data = response.json() or payload
        except Exception:
            self.data = payload

        cache = load_settings() or {}
        cache["notification_settings"] = self.data
        try:
            save_settings(cache)
        except Exception:
            pass

        return True

    # ------------------------------------------------------------------
    def _sync_reminder_fields(self):
        enabled = self.chk_due_reminder.isChecked()
        self.spin_reminder_days.setEnabled(enabled)
        self._sync_reminder_channels(enabled)

    def _sync_overdue_fields(self):
        enabled = self.chk_due_overdue.isChecked()
        self.spin_overdue_days.setEnabled(enabled)
        self._sync_overdue_channels(enabled)

    def _sync_email_fields(self):
        enabled = self.chk_email_enabled.isChecked()
        for widget in (
            self.edit_email_sender,
            self.edit_email_host,
            self.spin_email_port,
            self.chk_email_tls,
            self.edit_email_username,
            self.edit_email_password,
        ):
            widget.setEnabled(enabled)
        self.chk_email_schedule.setEnabled(enabled)
        if not enabled:
            self.chk_email_schedule.setChecked(False)
        self._sync_email_schedule_fields()
        self._sync_reminder_channels(self.chk_due_reminder.isChecked())
        self._sync_overdue_channels(self.chk_due_overdue.isChecked())

    def _sync_sms_fields(self):
        enabled = self.chk_sms_enabled.isChecked()
        for widget in (
            self.edit_sms_provider,
            self.edit_sms_url,
            self.edit_sms_key,
        ):
            widget.setEnabled(enabled)
        self.chk_sms_schedule.setEnabled(enabled)
        if not enabled:
            self.chk_sms_schedule.setChecked(False)
        self._sync_sms_schedule_fields()
        self._sync_reminder_channels(self.chk_due_reminder.isChecked())
        self._sync_overdue_channels(self.chk_due_overdue.isChecked())

    def _sync_mobile_fields(self):
        enabled = self.chk_mobile_enabled.isChecked()
        self.chk_mobile_schedule.setEnabled(enabled)
        if not enabled:
            self.chk_mobile_schedule.setChecked(False)
        self._sync_mobile_schedule_fields()
        self._sync_reminder_channels(self.chk_due_reminder.isChecked())
        self._sync_overdue_channels(self.chk_due_overdue.isChecked())

    def _sync_email_schedule_fields(self):
        enabled = self.chk_email_enabled.isChecked() and self.chk_email_schedule.isChecked()
        self.time_email_schedule.setEnabled(enabled)
        self.edit_email_timezone.setEnabled(enabled)

    def _sync_sms_schedule_fields(self):
        enabled = self.chk_sms_enabled.isChecked() and self.chk_sms_schedule.isChecked()
        self.time_sms_schedule.setEnabled(enabled)
        self.edit_sms_timezone.setEnabled(enabled)

    def _sync_mobile_schedule_fields(self):
        enabled = self.chk_mobile_enabled.isChecked() and self.chk_mobile_schedule.isChecked()
        self.time_mobile_schedule.setEnabled(enabled)
        self.edit_mobile_timezone.setEnabled(enabled)

    def _sync_reminder_channels(self, enabled=None):
        if enabled is None:
            enabled = self.chk_due_reminder.isChecked()
        email_enabled = enabled and self.chk_email_enabled.isChecked()
        sms_enabled = enabled and self.chk_sms_enabled.isChecked()
        mobile_enabled = enabled and self.chk_mobile_enabled.isChecked()
        self.chk_due_reminder_email.setEnabled(email_enabled)
        self.chk_due_reminder_sms.setEnabled(sms_enabled)
        self.chk_due_reminder_mobile.setEnabled(mobile_enabled)

    def _sync_overdue_channels(self, enabled=None):
        if enabled is None:
            enabled = self.chk_due_overdue.isChecked()
        email_enabled = enabled and self.chk_email_enabled.isChecked()
        sms_enabled = enabled and self.chk_sms_enabled.isChecked()
        mobile_enabled = enabled and self.chk_mobile_enabled.isChecked()
        self.chk_overdue_email.setEnabled(email_enabled)
        self.chk_overdue_sms.setEnabled(sms_enabled)
        self.chk_overdue_mobile.setEnabled(mobile_enabled)

    def _open_template_editor(self, key: str, *, multiline: bool):
        if key == "reminder_subject":
            current = self.edit_reminder_subject.text()
        elif key == "reminder_body":
            current = self.edit_reminder_body.toPlainText()
        elif key == "overdue_subject":
            current = self.edit_overdue_subject.text()
        else:
            current = self.edit_overdue_body.toPlainText()

        dialog = NotificationTemplateDialog("Şablon Düzenleyici", current, self.PLACEHOLDERS, self)
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.template_text()
            if key == "reminder_subject":
                self.edit_reminder_subject.setText(text)
            elif key == "reminder_body":
                self.edit_reminder_body.setPlainText(text)
            elif key == "overdue_subject":
                self.edit_overdue_subject.setText(text)
            else:
                self.edit_overdue_body.setPlainText(text)
class SettingsDialog(QDialog):
    def __init__(self, parent=None, initial_tab: str | None = None, *, admin_access: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.resize(560, 300)
        self.admin_access = bool(admin_access)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        tab_bar = self.tabs.tabBar()
        if tab_bar is not None:
            tab_bar.setUsesScrollButtons(False)
        # Scroll butonlarının ayırdığı boşluğu da gizle
        self.tabs.setStyleSheet(
            """
            QTabBar::scroller { width: 0px; }
            QTabBar QToolButton { width: 0px; height: 0px; margin: 0; padding: 0; border: none; }
            """
        )
        self.printer_page = PrinterSettingsWidget(self)
        self.label_page = LabelSettingsWidget(self)
        self.receipt_page = ReceiptSettingsWidget(self)
        self.server_page = ServerSettingsWidget(self)
        self.password_page = PasswordSettingsWidget(self)
        self.notification_page = NotificationSettingsWidget(self)
        self.loans_page = LoansSettingsWidget(self)
        self.penalties_page = PenaltySettingsWidget(self)

        self._tab_map: dict[str, int] = {}
        tab_definitions = [
            ("printers", self.printer_page, "Yazıcılar"),
            ("labels", self.label_page, "Etiket"),
            ("receipts", self.receipt_page, "Fiş"),
            ("server", self.server_page, "Sunucu"),
            ("password", self.password_page, "Şifre"),
            ("notifications", self.notification_page, "Bildirim"),
            ("loans", self.loans_page, "Ödünç"),
            ("penalties", self.penalties_page, "Ceza"),
        ]

        for key, widget, title in tab_definitions:
            if not self.admin_access and key != "password":
                continue

            index = self.tabs.addTab(widget, title)
            self._tab_map[key] = index

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox()
        self.btn_apply = buttons.addButton("Kaydet", QDialogButtonBox.ApplyRole)
        self.btn_apply.setObjectName("DialogPositiveButton")
        self.btn_close = buttons.addButton("Kapat", QDialogButtonBox.RejectRole)
        self.btn_close.setObjectName("DialogNeutralButton")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        self.btn_close.clicked.connect(self.reject)

        footer = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        footer.addWidget(self.status_label, 1, Qt.AlignCenter)
        footer.addWidget(buttons, 0, Qt.AlignRight)
        layout.addLayout(footer)
        self._status_timer = None

        if initial_tab and initial_tab in self._tab_map:
            self.tabs.setCurrentIndex(self._tab_map[initial_tab])
        elif not self.admin_access and "password" in self._tab_map:
            self.tabs.setCurrentIndex(self._tab_map["password"])

    def _on_apply_clicked(self):
        current_index = self.tabs.currentIndex()
        page = self.tabs.currentWidget()
        tab_name = self.tabs.tabText(current_index)

        save_message = None
        if hasattr(page, "save_preferences"):
            result = page.save_preferences()
            if isinstance(result, tuple):
                result, save_message = result
        else:
            result = True

        if result is False:
            return

        # Sadece bilgilendirici sekme olduğunda status çubuğunu kullanma
        if self._status_timer:
            self._status_timer.stop()
            self._status_timer.deleteLater()
        message = save_message or f"{tab_name} ayarları kaydedildi."
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #27ae60;")
        from PyQt5.QtCore import QTimer

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.setInterval(2500)
        self._status_timer.timeout.connect(self._clear_status_label)
        self._status_timer.start()

    def _clear_status_label(self):
        self.status_label.setText("")
        self.status_label.setStyleSheet("")
        if self._status_timer:
            self._status_timer.deleteLater()
            self._status_timer = None

    def open_tab(self, key: str):
        if key in self._tab_map:
            self.tabs.setCurrentIndex(self._tab_map[key])
