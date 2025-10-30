from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinterInfo
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QScrollArea,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

from core.config import load_settings, save_settings
from core.utils import response_error_message
from ui.printer_settings_dialog import PrinterSettingsWidget
from ui.server_settings_dialog import ServerSettingsWidget
from ui.label_editor_dialog import LabelEditorDialog
from api import auth
from api import settings as settings_api


class LabelSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.default_label_printer = None
        self.default_label_is_thermal = False
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

        printer_row = QHBoxLayout()
        printer_row.addWidget(QLabel("Etiket yazıcısı:"))
        self.cmb_printer = QComboBox()
        self.cmb_printer.setMinimumWidth(180)
        printer_row.addWidget(self.cmb_printer, 1)
        self.btn_refresh_printers = QPushButton("Yenile")
        self.btn_refresh_printers.setMaximumWidth(90)
        printer_row.addWidget(self.btn_refresh_printers)
        self.chk_printer_thermal = QCheckBox("Termal")
        printer_row.addWidget(self.chk_printer_thermal)
        layout.addLayout(printer_row)

        self.chk_rotate = QCheckBox("90° döndür")
        layout.addWidget(self.chk_rotate)

        layout.addStretch(1)

        self.btn_open_editor = QPushButton("Etiket Editörünü Aç…")
        self.btn_open_editor.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_open_editor, alignment=Qt.AlignRight)

        self.btn_refresh_printers.clicked.connect(self.refresh_printers)
        self.btn_open_editor.clicked.connect(self._open_editor)
        self.cmb_printer.currentTextChanged.connect(self._on_printer_changed)
        self.chk_printer_thermal.toggled.connect(self._on_printer_thermal_toggled)

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

        self.default_label_printer = printing.get("label_printer") or label_prefs.get("default_printer")
        self.default_label_is_thermal = bool(
            printing.get("label_is_thermal", label_prefs.get("default_printer_is_thermal", False))
        )

        self.spin_width.setValue(self.mm_w)
        self.spin_height.setValue(self.mm_h)
        self.spin_dpi.setValue(self.dpi)
        self.spin_grid.setValue(self.grid_mm)
        self.chk_snap.setChecked(self.snap_enabled)
        self.chk_rotate.setChecked(self.rotate_print)
        self.refresh_printers()

    def save_preferences(self):
        st = load_settings() or {}
        label_prefs = st.setdefault("label_editor", {})
        printing = st.setdefault("printing", {})

        self.mm_w = float(self.spin_width.value())
        self.mm_h = float(self.spin_height.value())
        self.dpi = int(self.spin_dpi.value())
        self.grid_mm = float(self.spin_grid.value())
        self.snap_enabled = bool(self.chk_snap.isChecked())
        self.rotate_print = bool(self.chk_rotate.isChecked())

        self.default_label_printer = self.cmb_printer.currentText().strip() or None
        self.default_label_is_thermal = bool(self.chk_printer_thermal.isChecked())

        label_prefs.update(
            {
                "mm_w": self.mm_w,
                "mm_h": self.mm_h,
                "dpi": self.dpi,
                "grid_mm": self.grid_mm,
                "snap": self.snap_enabled,
                "rotate_print": self.rotate_print,
                "default_printer": self.default_label_printer,
                "default_printer_is_thermal": self.default_label_is_thermal,
            }
        )

        printing["label_printer"] = self.default_label_printer
        printing["label_is_thermal"] = self.default_label_is_thermal

        try:
            save_settings(st)
        except Exception:
            pass

        return True

    def _on_printer_changed(self, text: str):
        self.default_label_printer = text.strip() or None

    def _on_printer_thermal_toggled(self, checked: bool):
        self.default_label_is_thermal = bool(checked)

    # ------------------------------------------------------------------
    def refresh_printers(self):
        names = self._printers()
        prev = self.default_label_printer or self.cmb_printer.currentText().strip()
        self.cmb_printer.blockSignals(True)
        self.cmb_printer.clear()
        self.cmb_printer.addItems(names)
        if prev:
            idx = self.cmb_printer.findText(prev)
            if idx >= 0:
                self.cmb_printer.setCurrentIndex(idx)
        self.cmb_printer.blockSignals(False)
        if not names and prev:
            self.cmb_printer.addItem(prev)
            self.cmb_printer.setCurrentIndex(0)
        if self.default_label_printer:
            idx = self.cmb_printer.findText(self.default_label_printer)
            if idx >= 0:
                self.cmb_printer.setCurrentIndex(idx)
        self.chk_printer_thermal.setChecked(self.default_label_is_thermal)

    def _printers(self):
        try:
            return [p.printerName() for p in QPrinterInfo.availablePrinters()]
        except Exception:
            return []

    def _open_editor(self):
        dlg = LabelEditorDialog(self)
        dlg.exec_()
        # editörden çıkınca tercihleri yeniden yükleyelim
        self.load_preferences()


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
        layout.addStretch(1)

        tip = QLabel("Şifre değişikliği sonrası tekrar giriş yapmanız gerekebilir.")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self._refresh_user_label()

    def save_preferences(self):
        username = auth.get_current_username()
        if not username:
            QMessageBox.warning(self, "Şifre Değiştirme", "Oturum bilgisi bulunamadı. Önce giriş yapın.")
            return False
        current = self.current_password.text().strip()
        new1 = self.new_password.text().strip()
        new2 = self.new_password_again.text().strip()

        if not any([current, new1, new2]):
            return True

        if new1 != new2:
            QMessageBox.warning(self, "Hata", "Yeni şifre alanları birbiriyle uyuşmuyor.")
            return False

        ok, message = auth.change_password(current, new1, new2)
        if ok:
            QMessageBox.information(self, "Şifre Değiştirme", message)
            self.current_password.clear()
            self.new_password.clear()
            self.new_password_again.clear()
            return True

        QMessageBox.warning(self, "Şifre Değiştirme", message or "Şifre güncellenemedi.")
        return False

    def _refresh_user_label(self):
        username = auth.get_current_username() or "(bilinmiyor)"
        self.lbl_user.setText(username)


class LoansSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.defaults = {
            "default_duration": 14,
            "default_max_items": 3,
            "delay_grace_days": 0,
            "auto_extend_enabled": False,
            "auto_extend_days": 7,
            "auto_extend_limit": 1,
            "penalty_delay_days": 0,
            "shift_weekend": True,
            "quarantine_days": 0,
            "require_damage_note": True,
            "require_shelf_code": True,
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        }
        self.current_policy = dict(self.defaults)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        form = QFormLayout()

        self.spin_default_duration = QSpinBox()
        self.spin_default_duration.setRange(1, 90)
        self.spin_default_duration.setMaximumWidth(120)
        form.addRow(
            self._with_help(
                QLabel("Varsayılan ödünç süresi (gün)"),
                "Sunucudan ayarlanan standart ödünç verme süresi. Rolde farklı süre yoksa kullanılır.",
            ),
            self.spin_default_duration,
        )

        self.spin_default_max = QSpinBox()
        self.spin_default_max.setRange(1, 20)
        self.spin_default_max.setMaximumWidth(120)
        form.addRow(
            self._with_help(
                QLabel("Maks. ödünç sayısı"),
                "Bir öğrencinin aynı anda alabileceği ödünç sayısının genel limiti.",
            ),
            self.spin_default_max,
        )

        self.spin_grace = QSpinBox()
        self.spin_grace.setRange(0, 10)
        self.spin_grace.setMaximumWidth(120)
        form.addRow(
            self._with_help(
                QLabel("Gecikme toleransı (gün)"),
                "İade tarihi aşıldıktan sonra öğrenciyi gecikmiş saymadan önce verilen ek süre.",
            ),
            self.spin_grace,
        )

        self.chk_auto_extend = QCheckBox("Bitiş tarihine yaklaşınca otomatik uzat")
        form.addRow("", self._with_help(self.chk_auto_extend, "Bu özellik henüz devrede değil."))

        self.spin_auto_extend_days = QSpinBox()
        self.spin_auto_extend_days.setRange(1, 30)
        self.spin_auto_extend_days.setMaximumWidth(120)
        form.addRow(
            self._with_help(QLabel("Uzatma süresi (gün)"),
                            "Otomatik uzatma aktif olduğunda eklenmesi planlanan gün sayısı."),
            self.spin_auto_extend_days,
        )

        self.spin_auto_extend_limit = QSpinBox()
        self.spin_auto_extend_limit.setRange(1, 10)
        self.spin_auto_extend_limit.setMaximumWidth(120)
        form.addRow(
            self._with_help(QLabel("Maks. uzatma sayısı"),
                            "Bir ödünç kaydına otomatik uzatma kaç defa uygulanabilir."),
            self.spin_auto_extend_limit,
        )

        self.spin_penalty_delay = QSpinBox()
        self.spin_penalty_delay.setRange(0, 30)
        self.spin_penalty_delay.setMaximumWidth(120)
        form.addRow(
            self._with_help(
                QLabel("Ceza başlangıç gecikmesi (gün)"),
                (
                    "İade tarihine tanınan ek tolerans (ör. 2 gün) bittikten sonra ceza başlamadan önce beklenen süre.\n"
                    "Örnek: İade tarihi 10 Temmuz, tolerans 2 gün ise ceza 12 Temmuz'dan sonra başlar. "
                    "Burada girilen değer (örn. 1 gün) ceza başlamasını 13 Temmuz'a ertelemeye yarar."
                ),
            ),
            self.spin_penalty_delay,
        )

        self.chk_shift_weekend = QCheckBox("İade tarihi hafta sonuna denk gelirse bir sonraki iş gününe kaydır")
        form.addRow("", self.chk_shift_weekend)

        self.spin_quarantine = QSpinBox()
        self.spin_quarantine.setRange(0, 30)
        self.spin_quarantine.setMaximumWidth(120)
        form.addRow(
            self._with_help(QLabel("İade sonrası bekleme süresi (gün)"),
                            "Bu özellik henüz devrede değil."),
            self.spin_quarantine,
        )

        self.chk_damage_note = QCheckBox("İade sırasında hasar notu zorunlu")
        form.addRow("", self._with_help(self.chk_damage_note, "Bu özellik henüz devrede değil."))

        self.chk_shelf_required = QCheckBox("Ödünç verirken raf kodu zorunlu")
        form.addRow("", self._with_help(self.chk_shelf_required, "Bu özellik henüz devrede değil."))

        self.chk_quiet_hours = QCheckBox("Belirli saatlerde işlem yapılmasın")
        form.addRow("", self._with_help(self.chk_quiet_hours, "Bu özellik henüz devrede değil."))

        quiet_row = QHBoxLayout()
        quiet_row.setSpacing(6)
        self.time_quiet_start = QLineEdit()
        self.time_quiet_start.setPlaceholderText("22:00")
        self.time_quiet_start.setMaximumWidth(80)
        self.time_quiet_end = QLineEdit()
        self.time_quiet_end.setPlaceholderText("08:00")
        self.time_quiet_end.setMaximumWidth(80)
        quiet_row.addWidget(QLabel("Başlangıç"))
        quiet_row.addWidget(self.time_quiet_start)
        quiet_row.addWidget(QLabel("Bitiş"))
        quiet_row.addWidget(self.time_quiet_end)
        quiet_row.addStretch(1)
        form.addRow(
            self._with_help(QLabel("Sessiz saat"), "Bu özellik henüz devrede değil."),
            quiet_row,
        )

        layout.addLayout(form)

        layout.addWidget(QLabel("Rol bazlı sınırlar"))
        self.table_roles = QTableWidget(0, 3)
        self.table_roles.setHorizontalHeaderLabels(["Rol", "Süre (gün)", "Maks. ödünç"])
        header = self.table_roles.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table_roles)

        layout.addStretch(1)

        info = QLabel("Bu alanlar gelecekte ödünç modülünde kullanılmak üzere saklanır.")
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        self.load_preferences()
        self._mark_reserved_fields()

    def _mark_reserved_fields(self):
        """Şimdilik kullanılmayan alanları pasifleştir ve bilgi ver."""
        reserved_controls = [
            (self.chk_auto_extend, "Bu özellik henüz devrede değil."),
            (self.spin_auto_extend_days, "Bu özellik henüz devrede değil."),
            (self.spin_auto_extend_limit, "Bu özellik henüz devrede değil."),
            (self.spin_quarantine, "Bu özellik henüz devrede değil."),
            (self.chk_damage_note, "Bu özellik henüz devrede değil."),
            (self.chk_shelf_required, "Bu özellik henüz devrede değil."),
            (self.chk_quiet_hours, "Bu özellik henüz devrede değil."),
            (self.time_quiet_start, "Bu özellik henüz devrede değil."),
            (self.time_quiet_end, "Bu özellik henüz devrede değil."),
        ]
        for widget, tip in reserved_controls:
            widget.setEnabled(False)
            widget.setToolTip(tip)

    def _with_help(self, widget, message):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if isinstance(widget, QLabel):
            layout.addWidget(widget)
        else:
            layout.addWidget(widget)

        btn = QPushButton("?")
        btn.setFixedSize(20, 20)
        btn.setObjectName("HelpButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Açıklamayı görüntüle")

        def show_message():
            QMessageBox.information(self, "Açıklama", message)

        btn.clicked.connect(show_message)
        layout.addWidget(btn)
        layout.addStretch(1)

        return container

    def load_preferences(self):
        server_policy = None
        resp = settings_api.fetch_loan_policy()
        if resp is not None and getattr(resp, "status_code", None) == 200:
            try:
                server_policy = resp.json() or {}
            except ValueError:
                server_policy = {}
            # yerel önbelleği güncelle
            st = load_settings() or {}
            st["loans"] = server_policy
            try:
                save_settings(st)
            except Exception:
                pass
        else:
            st = load_settings() or {}
            server_policy = st.get("loans", {})
            if resp is not None and getattr(resp, "status_code", None) not in (None, 0, 200):
                QMessageBox.warning(
                    self,
                    "Sunucuya erişilemiyor",
                    response_error_message(resp, "Ayarlar alınamadı. Yerel değerler gösteriliyor."),
                )

        payload = dict(self.defaults)
        if server_policy:
            payload.update(server_policy)

        self.current_policy = payload

        self.spin_default_duration.setValue(int(payload.get("default_duration", self.defaults["default_duration"])))
        self.spin_default_max.setValue(int(payload.get("default_max_items", self.defaults["default_max_items"])))
        self.spin_grace.setValue(int(payload.get("delay_grace_days", self.defaults["delay_grace_days"])))
        self.chk_auto_extend.setChecked(bool(payload.get("auto_extend_enabled", self.defaults["auto_extend_enabled"])))
        self.spin_auto_extend_days.setValue(int(payload.get("auto_extend_days", self.defaults["auto_extend_days"])))
        self.spin_auto_extend_limit.setValue(int(payload.get("auto_extend_limit", self.defaults["auto_extend_limit"])))
        self.spin_penalty_delay.setValue(int(payload.get("penalty_delay_days", self.defaults["penalty_delay_days"])))
        self.chk_shift_weekend.setChecked(bool(payload.get("shift_weekend", self.defaults["shift_weekend"])))
        self.spin_quarantine.setValue(int(payload.get("quarantine_days", self.defaults["quarantine_days"])))
        self.chk_damage_note.setChecked(bool(payload.get("require_damage_note", self.defaults["require_damage_note"])))
        self.chk_shelf_required.setChecked(bool(payload.get("require_shelf_code", self.defaults["require_shelf_code"])))
        self.chk_quiet_hours.setChecked(bool(payload.get("quiet_hours_enabled", self.defaults["quiet_hours_enabled"])))
        self.time_quiet_start.setText(str(payload.get("quiet_hours_start", self.defaults["quiet_hours_start"])))
        self.time_quiet_end.setText(str(payload.get("quiet_hours_end", self.defaults["quiet_hours_end"])))

        role_limits = payload.get("role_limits", []) or []
        self.table_roles.setRowCount(len(role_limits))
        for row, entry in enumerate(role_limits):
            role = str(entry.get("role", ""))
            dur = str(entry.get("duration", ""))
            max_items = str(entry.get("max_items", ""))
            self.table_roles.setItem(row, 0, QTableWidgetItem(role))
            self.table_roles.setItem(row, 1, QTableWidgetItem(dur))
            self.table_roles.setItem(row, 2, QTableWidgetItem(max_items))

    def save_preferences(self):
        payload = self._collect_payload()

        resp = settings_api.update_loan_policy(payload)
        if resp is None or getattr(resp, "status_code", None) != 200:
            QMessageBox.warning(
                self,
                "Kaydedilemedi",
                response_error_message(resp, "Sunucuya kaydedilemedi."),
            )
            return False

        self.current_policy = payload

        st = load_settings() or {}
        st["loans"] = payload
        try:
            save_settings(st)
        except Exception:
            pass

        return True

    def _collect_payload(self):
        payload = {
            "default_duration": int(self.spin_default_duration.value()),
            "default_max_items": int(self.spin_default_max.value()),
            "delay_grace_days": int(self.spin_grace.value()),
            "auto_extend_enabled": bool(self.chk_auto_extend.isChecked()),
            "auto_extend_days": int(self.spin_auto_extend_days.value()),
            "auto_extend_limit": int(self.spin_auto_extend_limit.value()),
            "penalty_delay_days": int(self.spin_penalty_delay.value()),
            "shift_weekend": bool(self.chk_shift_weekend.isChecked()),
            "quarantine_days": int(self.spin_quarantine.value()),
            "require_damage_note": bool(self.chk_damage_note.isChecked()),
            "require_shelf_code": bool(self.chk_shelf_required.isChecked()),
            "quiet_hours_enabled": bool(self.chk_quiet_hours.isChecked()),
            "quiet_hours_start": self.time_quiet_start.text().strip() or self.defaults["quiet_hours_start"],
            "quiet_hours_end": self.time_quiet_end.text().strip() or self.defaults["quiet_hours_end"],
        }

        role_limits = []
        for row in range(self.table_roles.rowCount()):
            role_item = self.table_roles.item(row, 0)
            dur_item = self.table_roles.item(row, 1)
            max_item = self.table_roles.item(row, 2)
            role = role_item.text().strip() if role_item else ""
            if not role:
                continue
            try:
                duration = int(dur_item.text().strip()) if dur_item else 0
            except ValueError:
                duration = 0
            try:
                max_items = int(max_item.text().strip()) if max_item else 0
            except ValueError:
                max_items = 0
            role_limits.append(
                {
                    "role": role,
                    "duration": duration,
                    "max_items": max_items,
                }
            )

        payload["role_limits"] = role_limits
        return payload


class PlaceholderPage(QWidget):
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)

    def save_preferences(self):
        return True


class SettingsDialog(QDialog):
    TAB_MAP = {
        "printers": 0,
        "labels": 1,
        "server": 2,
        "password": 3,
        "notifications": 4,
        "loans": 5,
        "penalties": 6,
    }

    def __init__(self, parent=None, initial_tab: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.resize(560, 300)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.printer_page = PrinterSettingsWidget(self)
        self.label_page = LabelSettingsWidget(self)
        self.server_page = ServerSettingsWidget(self)
        self.password_page = PasswordSettingsWidget(self)
        self.notification_page = PlaceholderPage("Bildirim ayarları burada yer alacak.", self)
        self.loans_page = LoansSettingsWidget(self)
        self.penalties_page = PlaceholderPage("Ceza ayarları burada yer alacak.", self)

        self.tabs.addTab(self.printer_page, "Yazıcılar")
        self.tabs.addTab(self.label_page, "Etiket")
        self.tabs.addTab(self.server_page, "Sunucu")
        self.tabs.addTab(self.password_page, "Şifre")
        self.tabs.addTab(self.notification_page, "Bildirim")
        self.tabs.addTab(self.loans_page, "Ödünç")
        self.tabs.addTab(self.penalties_page, "Ceza")

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

        if initial_tab and initial_tab in self.TAB_MAP:
            self.tabs.setCurrentIndex(self.TAB_MAP[initial_tab])

    def _on_apply_clicked(self):
        current_index = self.tabs.currentIndex()
        page = self.tabs.currentWidget()
        tab_name = self.tabs.tabText(current_index)

        if hasattr(page, "save_preferences"):
            result = page.save_preferences()
        else:
            result = True

        if result is False:
            return

        if self._status_timer:
            self._status_timer.stop()
            self._status_timer.deleteLater()
        self.status_label.setText(f"{tab_name} ayarları kaydedildi.")
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
        if key in self.TAB_MAP:
            self.tabs.setCurrentIndex(self.TAB_MAP[key])
