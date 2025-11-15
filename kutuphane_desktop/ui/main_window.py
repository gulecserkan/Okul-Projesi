from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QToolButton, QMessageBox, QCheckBox,
    QPlainTextEdit, QTextEdit
)
from PyQt5.QtCore import Qt, QRect, QTimer, QEvent
from PyQt5.QtWidgets import QStyle
from PyQt5.QtGui import QIcon
from ui.detail_window import DetailWindow, BOOK_TAB_ICON, STUDENT_TAB_ICON, COPIES_TAB_ICON
from ui.entity_manager_dialog import AuthorManagerDialog, CategoryManagerDialog
from ui.book_manager_dialog import BookManagerDialog
from ui.label_editor_dialog import LabelEditorDialog
from ui.student_manager_dialog import StudentManagerDialog
from ui.inventory_dialog import InventoryDialog
from ui.side_menu import SideMenu, SideMenuEntry
from widgets.quick_result_panel import QuickResultPanel
from widgets.book_table import BookTable, HEADERS
import json, os, sys, subprocess, time
import sip
from core.config import SETTINGS_FILE, get_api_base_url, load_settings, save_settings
from core.utils import register_session_expired_handler
from PyQt5.QtPrintSupport import QPrinterInfo
from core.utils import api_request, format_date, response_error_message
from api import auth
from api import logs as log_api
from ui.settings_dialog import SettingsDialog
from core.log_helpers import build_log_detail


_active_login_window = None



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kütüphane Yönetim Sistemi")
        icon_path = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "icons", "library.png")
        )
        if os.path.exists(icon_path):
            app = QApplication.instance()
            icon = QIcon(icon_path)
            if app:
                app.setWindowIcon(icon)
            self.setWindowIcon(icon)
        self.last_quick_query = ""
        self._dlg_student = None
        self._dlg_author = None
        self._dlg_category = None
        self._scanner_buffer = []
        self._scanner_start_ts = 0.0
        self._scanner_capture = False
        self._scanner_timeout_s = 0.8
        self._scanner_lock_widget = None
        self._is_logging_out = False
        self._inactivity_timer = None
        self._inactivity_minutes = None
        self._inactivity_timeout_ms = None
        self._startup_jobs_run = False
        self._session_expired_warning_shown = False
        self.session_settings = {}
        role_value = auth.get_current_role()
        normalized_role = (role_value or "").strip().lower()
        self._current_role = normalized_role
        allowed_roles = {"admin", "superuser"}
        # Eğer rol bilgisi yoksa (eski token) erişimi kısıtlama
        self._settings_allowed = (not normalized_role) or (normalized_role in allowed_roles)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        layout = QVBoxLayout()

        # 🔹 Hızlı işlem kutusu
        self.quick_input = QLineEdit()
        self.quick_input.setPlaceholderText("Barkod veya Öğrenci No...")
        self.quick_input.setFixedWidth(300)
        self.quick_input.setAlignment(Qt.AlignCenter)
        self.quick_input.setObjectName("QuickInput")
        self.quick_input.returnPressed.connect(self.run_quick_search)
        self.quick_input.installEventFilter(self)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        self.menu_button = QToolButton()
        self.menu_button.setObjectName("HamburgerButton")
        self.menu_button.setText("☰")
        self.menu_button.setToolTip("Yönetim menüsü")
        self.menu_button.setFixedSize(46, 42)
        self.menu_button.clicked.connect(self.toggle_side_menu)
        top_row.addWidget(self.menu_button, 0, Qt.AlignLeft)
        top_row.addStretch(1)
        top_row.addWidget(self.quick_input, 0, Qt.AlignCenter)
        top_row.addStretch(1)

        layout.addLayout(top_row)

        self.quick_result = QWidget()
        self.quick_result.setVisible(False)
        self.quick_result_layout = QVBoxLayout()
        self.quick_result_layout.setContentsMargins(20, 10, 20, 10)
        self.quick_result.setLayout(self.quick_result_layout)

        # layout’a eklerken:
        layout.addWidget(self.quick_result)   # input genişliğiyle değil, pencere genişliğiyle gelir


        # Tablo (sağ tık menüsü BookTable içinde var)
        self.table = BookTable()
        layout.addWidget(self.table)

        # Ana container
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.side_menu = SideMenu(self)
        settings_desc = (
            "Genel tercihleri yönetin"
            if self._settings_allowed
            else "Bu alana yalnızca yönetici hesabı erişebilir"
        )
        menu_items = [
            SideMenuEntry(
                "Ayarlar",
                settings_desc,
                self._menu_icon("menu_settings.png", self.style().standardIcon(QStyle.SP_FileDialogDetailedView)),
                self.open_settings,
            ),
            SideMenuEntry(
                "Kitaplar",
                "Kitap kayıtlarını yönetin",
                self._menu_icon("menu_books.png", self.style().standardIcon(QStyle.SP_DirHomeIcon)),
                self.open_book_manager,
            ),
            SideMenuEntry(
                "Öğrenciler",
                "Öğrenci kayıtlarını yönetin",
                self._menu_icon("menu_student.png", self.style().standardIcon(QStyle.SP_ComputerIcon)),
                self.open_student_manager,
            ),
            SideMenuEntry(
                "Yazarlar",
                "Yazar kayıtlarını yönetin",
                self._menu_icon("menu_authors.png", self.style().standardIcon(QStyle.SP_FileIcon)),
                self.open_author_manager,
            ),
            SideMenuEntry(
                "Çıkış",
                "Oturumu kapatıp giriş ekranına dönün",
                self._menu_icon("menu_logout.png", self.style().standardIcon(QStyle.SP_DialogCloseButton)),
                self.logout_and_show_login,
            ),
        ]
        self.side_menu.set_items(menu_items)
        self.side_menu.update_geometry()

        # Ayarları yükle
        self.settings = self.load_settings()
        self.apply_window_settings()
        self._setup_inactivity_timer()
        QTimer.singleShot(0, self._trigger_startup_jobs)
        register_session_expired_handler(self._handle_session_expired)
        try:
            self._check_printers()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.KeyPress,
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.MouseMove,
            QEvent.Wheel,
        ):
            self._register_activity()

        if event.type() == QEvent.KeyPress:
            focus = QApplication.focusWidget()
            lock_widget = getattr(self, "_scanner_lock_widget", None)
            if lock_widget is not None:
                try:
                    if sip.isdeleted(lock_widget) or not lock_widget.isVisible():
                        self._scanner_lock_widget = None
                    elif focus is lock_widget:
                        return super().eventFilter(obj, event)
                except RuntimeError:
                    self._scanner_lock_widget = None

            if isinstance(focus, (QLineEdit, QTextEdit, QPlainTextEdit)) and focus not in (self.quick_input, lock_widget):
                return super().eventFilter(obj, event)

            modifiers = event.modifiers()
            if modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
                self._reset_scanner_capture()
                return super().eventFilter(obj, event)

            if focus is self.quick_input and not self._scanner_capture:
                return super().eventFilter(obj, event)

            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if self._scanner_capture and self._scanner_buffer:
                    elapsed = time.monotonic() - self._scanner_start_ts
                    if elapsed <= self._scanner_timeout_s:
                        text = "".join(self._scanner_buffer).strip()
                        self._reset_scanner_capture()
                        if text:
                            self._handle_scanner_input(text)
                            self.run_quick_search()
                            return True
                self._reset_scanner_capture()
                return super().eventFilter(obj, event)

            # Printable karakterler
            key = event.key()
            if key == Qt.Key_Shift:
                now = time.monotonic()
                if not self._scanner_capture or (now - self._scanner_start_ts) > self._scanner_timeout_s:
                    self._scanner_buffer = []
                    self._scanner_start_ts = now
                    self._scanner_capture = True
                    self.quick_input.clear()
                    self.quick_input.setFocus()
                return True

            text = event.text() or ""
            if (not text) and (Qt.Key_A <= key <= Qt.Key_Z) and event.modifiers() & Qt.ShiftModifier:
                text = chr(key)
            if (not text) and (Qt.Key_0 <= key <= Qt.Key_9) and event.modifiers() & Qt.ShiftModifier:
                text = chr(key)
            if text and text.isprintable():
                now = time.monotonic()
                if not self._scanner_capture or (now - self._scanner_start_ts) > self._scanner_timeout_s:
                    self._scanner_buffer = []
                    self._scanner_start_ts = now
                    self._scanner_capture = True
                    self.quick_input.clear()
                self._scanner_buffer.append(text)
                current = "".join(self._scanner_buffer)
                if current:
                    self.quick_input.setText(current)
                if not self.quick_input.hasFocus():
                    self.quick_input.setFocus()
                return True

            # Diğer tuşlar scanner senaryosu değil
            self._reset_scanner_capture()

        elif event.type() == QEvent.FocusIn and obj is self.quick_input:
            self._register_activity()
            if not self._scanner_capture:
                self._reset_scanner_capture()
            QTimer.singleShot(0, self.quick_input.selectAll)
        return super().eventFilter(obj, event)

    def _handle_scanner_input(self, text):
        self.quick_input.clear()
        self.quick_input.setText(text)
        self.quick_input.setFocus()

    def set_scanner_lock(self, widget):
        if widget is None:
            return
        self._scanner_lock_widget = widget

    def clear_scanner_lock(self, widget):
        if self._scanner_lock_widget is widget:
            self._scanner_lock_widget = None
        self._reset_scanner_capture()
        self.quick_input.setFocus()

    def _reset_scanner_capture(self):
        self._scanner_buffer = []
        self._scanner_capture = False
        self._scanner_start_ts = 0.0

    def _load_session_settings(self):
        data = load_settings() or {}
        session = data.get("session", {})
        enabled = session.get("auto_logout_enabled", True)
        minutes = session.get("auto_logout_minutes", 10)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 10
        minutes = min(max(minutes, 1), 30)
        self.session_settings = {
            "auto_logout_enabled": bool(enabled),
            "auto_logout_minutes": minutes,
        }

    def _ensure_inactivity_timer(self):
        """QTimer nesnesinin hala geçerli olduğundan emin olur; gerekirse yeniden oluşturur."""
        try:
            if sip.isdeleted(self):
                return None
        except Exception:
            return None
        timer = self._inactivity_timer
        if timer is not None:
            try:
                if sip.isdeleted(timer):
                    timer = None
            except Exception:
                timer = None
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._handle_inactivity_timeout)
        self._inactivity_timer = timer
        return timer

    def _setup_inactivity_timer(self):
        """Kullanıcı hareketsiz kaldığında otomatik oturumu kapatmak için zamanlayıcı kurar."""
        self._load_session_settings()
        enabled = self.session_settings.get("auto_logout_enabled", True)
        minutes = self.session_settings.get("auto_logout_minutes", 10)

        timer = self._ensure_inactivity_timer()
        if timer is None:
            return

        if enabled:
            self._inactivity_minutes = minutes
            self._inactivity_timeout_ms = self._inactivity_minutes * 60_000
            self._register_activity()
        else:
            self._inactivity_minutes = None
            self._inactivity_timeout_ms = None
            if timer and not sip.isdeleted(timer):
                timer.stop()

    def _register_activity(self):
        """Her kullanıcı etkileşiminde çağrılarak zamanlayıcıyı sıfırlar."""
        if (
            self._is_logging_out
            or self._inactivity_timeout_ms is None
        ):
            return
        timer = self._ensure_inactivity_timer()
        if timer and not sip.isdeleted(timer):
            timer.start(self._inactivity_timeout_ms)

    def _handle_inactivity_timeout(self):
        """Belirlenen süre boyunca etkinlik olmadığında çağrılır."""
        if self.session_settings.get("auto_logout_enabled", True):
            self.logout_and_show_login(reason="timeout")
    
    # Uygulama kapanırken ayarları kaydet
    def closeEvent(self, event):
        if self._is_logging_out:
            super().closeEvent(event)
            return
        # Geliştirme sürecinde doğrudan kapanmasına izin ver.
        self.side_menu.force_hide()
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self):
        geom: QRect = self.geometry()
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except Exception:
            settings = {}

        # Eski anahtarları temizle (geriye dönük temizlik)
        settings.pop("column_widths", None)
        settings.pop("window_geometry", None)

        settings["main_window"] = {
            "column_widths": [self.table.table.columnWidth(i) for i in range(len(HEADERS))],
            "window_geometry": {
                "x": geom.x(),
                "y": geom.y(),
                "w": geom.width(),
                "h": geom.height(),
            },
        }

        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                cfg = data.get("main_window")
                if not cfg and "window_geometry" in data and "column_widths" in data:
                    cfg = {
                        "window_geometry": data.get("window_geometry"),
                        "column_widths": data.get("column_widths")
                    }
                return cfg or {}
            except Exception:
                return {}
        return {}

    def apply_window_settings(self):
        geom = self.settings.get("window_geometry")
        if geom:
            self.setGeometry(
                geom.get("x", 300),
                geom.get("y", 100),
                geom.get("w", 1200),
                geom.get("h", 700)
            )
        else:
            self.setGeometry(300, 100, 1200, 700)

        # Kolon genişliklerini uygula
        widths = self.settings.get("column_widths", [])
        for i, w in enumerate(widths):
            if w > 0:
                self.table.table.setColumnWidth(i, w)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.side_menu.update_geometry()

    def mousePressEvent(self, event):
        if self.side_menu.is_visible() and event.pos().x() > self.side_menu.width():
            self.side_menu.hide_menu()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.side_menu.is_visible():
            self.side_menu.hide_menu()
        else:
            super().keyPressEvent(event)

    def run_quick_search(self):
        query = self.quick_input.text().strip()
        if not query:
            return
        self.perform_quick_search(query)

    def perform_quick_search(self, query):
        query = (query or "").strip()
        if not query:
            return

        self.last_quick_query = query
        resp = api_request("GET", self._api_url(f"fast-query/?q={query}"))
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                data["query"] = query
            self.show_quick_result(data)
        else:
            msg = response_error_message(resp, "Sunucu hatası")
            self.show_quick_result({
                "type": "error",
                "msg": msg,
                "query": query
            })
        self.quick_input.setFocus()
        self.quick_input.selectAll()

    def show_quick_result(self, data):
        for i in reversed(range(self.quick_result_layout.count())):
            w = self.quick_result_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        panel = QuickResultPanel(data)
        panel.detailStudentRequested.connect(self.show_detail_student)
        panel.editStudentRequested.connect(self.edit_student_from_quick)
        panel.detailBookRequested.connect(self.handle_detail_book_request)
        panel.returnProcessed.connect(self.on_quick_return_processed)
        panel.closed.connect(self.close_quick_result)

        self.quick_result_layout.addWidget(panel)
        self.quick_result.setVisible(True)

    def close_quick_result(self):
        """Hızlı arama panelini kapatır ve input kutusunu temizler."""
        self.quick_result.setVisible(False)
        self.quick_input.clear()

    def show_detail_student(self, ogr_no):
        resp = api_request("GET", self._api_url(f"student-history/{ogr_no}/"))
        if resp.status_code == 200:
            records = resp.json()
            rows = []
            for rec in records:
                # Tarih sütunu: teslim varsa teslim_tarihi, yoksa iade_tarihi
                if rec.get("teslim_tarihi"):
                    tarih = format_date(rec["teslim_tarihi"])
                else:
                    tarih = format_date(rec.get("iade_tarihi"))

                rows.append([
                    rec.get("durum", ""),   # önce durum
                    rec["kitap_nusha"]["kitap"]["baslik"],
                    tarih
                ])
            dlg = DetailWindow(
                "Öğrenci Geçmişi",
                ["Durum", "Kitap", "Tarih"],
                rows,
                settings_key="student_detail",
                main_tab_title="Öğrenci Geçmişi",
                main_tab_icon=STUDENT_TAB_ICON
            )
            dlg.exec_()

    def edit_student_from_quick(self, ogr_no: str):
        self.open_student_manager(student_no=ogr_no)

    def handle_detail_book_request(self, barkod, include_history):
        self.show_detail_book(barkod, include_history=include_history)

    def on_quick_return_processed(self):
        if hasattr(self.table, "reload_data"):
            self.table.reload_data()
        if self.last_quick_query:
            self.perform_quick_search(self.last_quick_query)

    def show_detail_book(self, barkod, include_history=True):
        """Kitap detay penceresini açar.

        include_history=True ise hem ilgili nüshanın geçmişi hem tüm nüshalar gösterilir,
        False olduğunda yalnızca "Tüm Nüshalar" sekmesi sunulur."""
        resp = api_request("GET", self._api_url(f"book-history/{barkod}/"))
        if resp.status_code != 200:
            print("Kitap geçmişi alınamadı:", resp.status_code)
            return

        data = resp.json()
        history = data.get("history", [])
        all_copies = data.get("all_copies", [])
        book = data.get("book", {})
        copy = data.get("copy", {})

        include_history_tab = include_history

        # 🔹 1. sekme: Bu nüshanın ödünç geçmişi
        rows_history = []
        if include_history_tab:
            for rec in history:
                if (rec.get("durum") or "").lower() == "iptal":
                    continue
                ogr = rec.get("ogrenci", {})
                rows_history.append([
                    f"{ogr.get('ad','')} {ogr.get('soyad','')}",
                    format_date(rec.get("odunc_tarihi")),
                    format_date(rec.get("iade_tarihi") or rec.get("teslim_tarihi")),
                    rec.get("durum", "")
                ])

        # 🔹 2. sekme: Aynı ISBN'e ait tüm nüshalar
        rows_copies = []
        for c in all_copies:
            barkod = c.get("barkod", "")
            raf = c.get("raf_kodu", "")

            durum = c.get("durum", "")
            son_islem = c.get("son_islem")

            # Eski API için geriye dönük uyumluluk
            son_odunc = c.get("son_odunc") or {}
            if not durum:
                durum = son_odunc.get("durum", "")
            if not son_islem:
                son_islem = son_odunc.get("teslim_tarihi") or son_odunc.get("iade_tarihi")

            son_islem = "" if son_islem is None else son_islem

            ogr_val = c.get("ogrenci", "")
            if isinstance(ogr_val, dict):
                ogrenci = f"{ogr_val.get('ad','')} {ogr_val.get('soyad','')}".strip()
            else:
                ogrenci = str(ogr_val or "")
            if not ogrenci and isinstance(son_odunc, dict):
                ogr = son_odunc.get("ogrenci", {}) or {}
                ogrenci = f"{ogr.get('ad','')} {ogr.get('soyad','')}".strip()

            aktif = "Aktif" if c.get("aktif") else ""

            rows_copies.append([
                aktif,
                barkod,
                raf,
                durum,
                son_islem,
                ogrenci
            ])

        # 🔹 Başlık bilgisi
        baslik = book.get("baslik", "")
        self.last_book_title = baslik

        # 🔹 Pencereyi oluştur
        if include_history_tab:
            dlg = DetailWindow(
                f"📖 {baslik} — Kitap Geçmişi",
                ["Öğrenci", "Ödünç Tarihi", "İade/Teslim", "Durum"],
                rows_history,
                settings_key="book_detail",
                main_tab_title="Bu Nüsha Geçmişi",
                main_tab_icon=BOOK_TAB_ICON
            )
        else:
            dlg = DetailWindow.single_tab(
                title=f"📚 {baslik} — Tüm Nüshalar",
                headers=["", "Barkod", "Raf", "Durum", "Son İşlem", "Öğrenci"],
                rows=rows_copies,
                settings_key="book_all_copies",
                icon_path=COPIES_TAB_ICON,
                tab_title="Tüm Nüshalar"
            )

        if include_history_tab and all_copies:
            dlg.add_tab(
                "Tüm Nüshalar",
                ["", "Barkod", "Raf", "Durum", "Son İşlem", "Öğrenci"],
                rows_copies,
                icon_path=COPIES_TAB_ICON
            )

        dlg.exec_()

    def open_author_manager(self):
        self.side_menu.force_hide()
        if self._dlg_author and self._dlg_author.isVisible():
            self._dlg_author.raise_(); self._dlg_author.activateWindow(); return
        dlg = AuthorManagerDialog(self)
        self._dlg_author = dlg
        dlg.finished.connect(lambda _: setattr(self, "_dlg_author", None))
        dlg.exec_()
        if hasattr(self.table, "reload_data"):
            self.table.reload_data()

    def open_category_manager(self):
        self.side_menu.force_hide()
        if self._dlg_category and self._dlg_category.isVisible():
            self._dlg_category.raise_(); self._dlg_category.activateWindow(); return
        dlg = CategoryManagerDialog(self)
        self._dlg_category = dlg
        dlg.finished.connect(lambda _: setattr(self, "_dlg_category", None))
        dlg.exec_()
        if hasattr(self.table, "reload_data"):
            self.table.reload_data()

    def open_label_editor(self):
        self.side_menu.force_hide()
        dlg = LabelEditorDialog(self)
        dlg.exec_()

    def open_printer_settings(self):
        self.open_settings(initial_tab="printers")

    def open_inventory_settings_tab(self):
        self.open_settings(initial_tab="inventory", require_admin=False)

    def open_password_settings(self):
        self.open_settings(initial_tab="password", require_admin=False)

    def open_settings(self, initial_tab: str | None = None, *, require_admin: bool = True):
        has_admin_access = bool(getattr(self, "_settings_allowed", True))
        limited_view = not has_admin_access
        if require_admin and limited_view:
            QMessageBox.information(
                self,
                "Sınırlı Erişim",
                "Bu hesap yönetici yetkisine sahip değil. Ayarlar penceresinde sadece şifre sekmesi görüntülenecek."
            )
            detail = build_log_detail(
                user=self._current_user_detail(),
                role=self._current_role,
                extra="Ayarlar menüsüne tam erişim isteği"
            )
            log_api.safe_send_log(
                "Sınırlı ayar erişimi",
                detay=detail or f"Rol: {self._current_role or 'bilinmiyor'}"
            )
        self.side_menu.force_hide()
        dlg = SettingsDialog(
            self,
            initial_tab=initial_tab,
            admin_access=has_admin_access,
            inventory_callback=self.open_inventory_manager,
        )
        dlg.exec_()
        self._setup_inactivity_timer()

    def _current_user_detail(self):
        name = auth.get_current_full_name() or auth.get_current_username() or "Bilinmeyen"
        return {"ad": name}
    
    def _check_label_printer(self):
        settings = load_settings() or {}
        prefs = settings.get("label_editor", {})
        name = prefs.get("default_printer")
        if not name:
            self._warn_no_printer("Varsayılan etiket yazıcısı belirlenmemiş.")
            return
        try:
            names = [p.printerName() for p in QPrinterInfo.availablePrinters()]
        except Exception:
            names = []
        if name not in names:
            self._warn_no_printer(f"'{name}' yazıcısı bağlı değil.")

    def _warn_no_printer(self, msg):
        box = QMessageBox(self)
        box.setWindowTitle("Yazıcı Uyarısı")
        box.setText(msg)
        btn_set = box.addButton("Yazıcı Ayarla", QMessageBox.AcceptRole)
        btn_close = box.addButton("Kapat", QMessageBox.RejectRole)
        box.setDefaultButton(btn_set)
        box.exec_()
        if box.clickedButton() == btn_set:
            self.open_printer_settings()

    # Yeni: Etiket ve Rapor yazıcılarını kontrol et, durumları bildir
    def _check_printers(self):
        st_all = load_settings() or {}
        notif = st_all.get("notification_settings", {})
        if not notif.get("printer_warning_enabled", True):
            return

        p = st_all.get("printing", {})
        le = st_all.get("label_editor", {})

        label_name = p.get("label_printer") or le.get("default_printer")
        report_name = p.get("report_printer")

        def _printer_status_text(name: str) -> str:
            name = (name or '').strip()
            if not name:
                return "tanımlanmadı"
            if sys.platform.startswith('win'):
                try:
                    import win32print
                    PR_ERR = (win32print.PRINTER_STATUS_ERROR |
                              win32print.PRINTER_STATUS_PAPER_OUT |
                              win32print.PRINTER_STATUS_OFFLINE |
                              getattr(win32print, 'PRINTER_STATUS_PAPER_JAM', 0) |
                              getattr(win32print, 'PRINTER_STATUS_DOOR_OPEN', 0))
                    h = win32print.OpenPrinter(name)
                    try:
                        info = win32print.GetPrinter(h, 2)
                        st = info.get('Status', 0) or 0
                        if st & PR_ERR:
                            return "hazır değil"
                        return "hazır"
                    finally:
                        win32print.ClosePrinter(h)
                except Exception:
                    return "bilinmiyor"
            else:
                # Linux/mac: CUPS dene, sonra lpstat'a düş
                try:
                    import cups
                    c = cups.Connection()
                    pinfo = c.getPrinters().get(name)
                    if not pinfo:
                        return "mevcut değil"
                    state = pinfo.get('printer-state')
                    reasons = pinfo.get('printer-state-reasons', [])
                    if state == 3 and (not reasons or 'none' in reasons):
                        return "hazır"
                    if state == 4:
                        return "yazdırıyor"
                    return "hazır değil"
                except Exception:
                    try:
                        r = subprocess.run(['lpstat','-p', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
                        if r.returncode != 0:
                            return "mevcut değil"
                        out = (r.stdout or '').lower()
                        if 'disabled' in out or 'stopped' in out or 'offline' in out:
                            return "hazır değil"
                        if 'is printing' in out or 'now printing' in out:
                            return "yazdırıyor"
                        if 'is idle' in out:
                            return "hazır"
                        return "bilinmiyor"
                    except Exception:
                        return "bilinmiyor"

        st_label = _printer_status_text(label_name)
        st_report = _printer_status_text(report_name)

        # Her ikisi de hazırsa uyarı verme
        if st_label == "hazır" and st_report == "hazır":
            return

        # Hatırlatma baskısı azaltma: kullanıcı daha önce 10 kez ertelediyse
        skip_count = int(p.get("reminder_skip_count", 0) or 0)
        if skip_count > 0:
            # Bir açılış daha düştü
            p["reminder_skip_count"] = max(0, skip_count - 1)
            st_all["printing"] = p
            try:
                save_settings(st_all)
            except Exception:
                pass
            return

        # Mesaj kutusu: iki durum birlikte gösterilsin
        msg = (
            "Yazıcı kontrolleri:\n"
            f"• Etiket yazıcısı: {st_label} {f'({label_name})' if label_name else ''}\n"
            f"• Rapor yazıcısı: {st_report} {f'({report_name})' if report_name else ''}\n\n"
            "Yazıcıları ayarlamak ister misiniz?"
        )
        box = QMessageBox(self)
        box.setWindowTitle("Yazıcı Durumu")
        box.setText(msg)
        btn_open = box.addButton("Yazıcıları Ayarla", QMessageBox.AcceptRole)
        btn_close = box.addButton("Kapat", QMessageBox.RejectRole)
        box.setDefaultButton(btn_open)
        # Sonraki 10 açılışta hatırlatma çeki
        chk = QCheckBox("Sonraki 10 açılışta hatırlatma")
        box.setCheckBox(chk)
        box.exec_()

        if box.clickedButton() == btn_open:
            self.open_printer_settings()

        if box.checkBox() and box.checkBox().isChecked():
            p["reminder_skip_count"] = 10
            st_all["printing"] = p
            try:
                save_settings(st_all)
            except Exception:
                pass

    def open_book_manager(self):
        self.side_menu.force_hide()
        if getattr(self, "_dlg_book", None) and self._dlg_book.isVisible():
            self._dlg_book.raise_(); self._dlg_book.activateWindow(); return
        dlg = BookManagerDialog(self)
        self._dlg_book = dlg
        dlg.finished.connect(lambda _: setattr(self, "_dlg_book", None))
        dlg.exec_()
        if hasattr(self.table, "reload_data"):
            self.table.reload_data()

    def open_student_manager(self, student_no: str | None = None):
        self.side_menu.force_hide()
        if self._dlg_student and self._dlg_student.isVisible():
            if student_no:
                QTimer.singleShot(0, lambda: self._dlg_student.focus_on_student(student_no))
            self._dlg_student.raise_()
            self._dlg_student.activateWindow()
            return
        dlg = StudentManagerDialog(self)
        self._dlg_student = dlg
        if student_no:
            QTimer.singleShot(0, lambda: dlg.focus_on_student(student_no))
        dlg.finished.connect(lambda _: setattr(self, "_dlg_student", None))
        dlg.exec_()
        if hasattr(self.table, "reload_data"):
            self.table.reload_data()

    def open_inventory_manager(self):
        self.side_menu.force_hide()
        dlg = InventoryDialog(self)
        dlg.exec_()

    def logout_and_show_login(self, reason=None):
        """Çıkış işlemini yapar ve giriş ekranını açar."""
        if self._is_logging_out:
            return
        self._is_logging_out = True
        register_session_expired_handler(None)
        self._session_expired_warning_shown = False

        if self._inactivity_timer:
            try:
                if not sip.isdeleted(self._inactivity_timer):
                    self._inactivity_timer.stop()
            except Exception:
                pass

        app = QApplication.instance()
        if app:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass

        if reason == "timeout":
            minutes = self.session_settings.get("auto_logout_minutes", self._inactivity_minutes or 0)
            QMessageBox.information(
                self,
                "Oturum Sonlandırıldı",
                f"{minutes} dakika işlem yapılmadığı için oturum kapatıldı.",
            )

        # Açık yöneticileri kapat
        for attr in ("_dlg_student", "_dlg_author", "_dlg_category", "_dlg_book"):
            dlg = getattr(self, attr, None)
            if dlg and hasattr(dlg, "close"):
                try:
                    dlg.close()
                except Exception:
                    pass
            setattr(self, attr, None)

        self.side_menu.force_hide()
        self.save_settings()
        try:
            display = auth.get_current_full_name() or auth.get_current_username() or "Bilinmeyen kullanıcı"
            if reason == "timeout":
                message = "Hareketsizlik nedeniyle oturum sonlandırıldı."
                action = "Oturum kapatma (pasiflik)"
            elif reason == "session_expired":
                message = "Oturum süresi sona erdi."
                action = "Oturum kapatma (oturum süresi)"
            else:
                message = "Kullanıcı isteğiyle çıkış yapıldı."
                action = "Oturum kapatma"
            detail = build_log_detail(
                user={"ad": display},
                role=self._current_role,
                extra=message,
            )
            log_api.safe_send_log(action, detay=detail or f"{display} çıkış yaptı.")
        except Exception:
            pass
        auth.logout()

        from ui.login_window import LoginWindow  # avoid circular import
        global _active_login_window

        _active_login_window = LoginWindow()
        _active_login_window.show()
        # Ana pencereyi anında kapatmak yerine güvenli kapatma
        QTimer.singleShot(0, self._close_safely)

    def _close_safely(self):
        register_session_expired_handler(None)
        try:
            self.hide()
        except Exception:
            pass
        try:
            self.deleteLater()
        except Exception:
            pass

    def toggle_side_menu(self):
        self.side_menu.toggle_menu()

    def _api_url(self, path):
        base = get_api_base_url().rstrip('/')
        path = path.lstrip('/')
        return f"{base}/{path}"

    def _trigger_startup_jobs(self):
        if self._startup_jobs_run:
            return
        self._startup_jobs_run = True
        QTimer.singleShot(0, self._run_startup_jobs)

    def _run_startup_jobs(self):
        try:
            resp = api_request("POST", self._api_url("jobs/update-overdue/"))
        except Exception as exc:
            print("[DBG] Overdue job failed:", exc)
            return
        status = getattr(resp, "status_code", None)
        if status != 200:
            print("[DBG] Overdue job response:", status)

    def _menu_icon(self, filename, fallback):
        path = os.path.join("resources", "icons", filename)
        if os.path.exists(path):
            return QIcon(path)
        return fallback

    def _handle_session_expired(self):
        if self._session_expired_warning_shown or self._is_logging_out:
            return
        self._session_expired_warning_shown = True
        QTimer.singleShot(0, self._show_session_expired_message)

    def _show_session_expired_message(self):
        if self._is_logging_out:
            return
        QMessageBox.warning(
            self,
            "Oturum Süresi Doldu",
            "Oturum süreniz doldu. Lütfen tekrar giriş yapın."
        )
        self.logout_and_show_login(reason="session_expired")
