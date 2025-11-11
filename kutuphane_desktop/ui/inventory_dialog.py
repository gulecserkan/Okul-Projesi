from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from api import inventory as inventory_api


class InventoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sayım Oturumları")
        self.resize(1100, 640)
        self.sessions = []
        self.current_session = None
        self.current_items = []
        self.current_filter = "unseen"
        self.current_search = ""

        self._build_ui()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._apply_search_filter)

        self._initializing = True
        self.refresh_sessions()
        self._initializing = False

    # ------------------------------------------------------------------
    def _build_ui(self):
        main = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("Yeni Sayım")
        self.btn_new.setObjectName("DialogPositiveButton")
        self.btn_refresh = QPushButton("Yenile")
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addStretch(1)
        main.addLayout(toolbar)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(self._on_session_selected)
        splitter.addWidget(self.session_list)

        self.detail_panel = QWidget()
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(10, 10, 10, 10)
        detail_layout.setSpacing(8)

        header_row = QHBoxLayout()
        self.label_session_title = QLabel("Sayım seçilmedi.")
        self.label_session_title.setStyleSheet("font-size:16px; font-weight:600;")
        header_row.addWidget(self.label_session_title, 2)
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(1000)
        header_row.addWidget(self.progress, 1)
        self.label_status = QLabel("")
        header_row.addWidget(self.label_status)
        detail_layout.addLayout(header_row)

        info_row = QHBoxLayout()
        self.label_counts = QLabel("")
        info_row.addWidget(self.label_counts)
        info_row.addStretch(1)
        self.label_filters = QLabel("")
        self.label_filters.setStyleSheet("color:#555;")
        info_row.addWidget(self.label_filters)
        detail_layout.addLayout(info_row)

        control_row = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Barkod okutun veya yazın")
        self.scan_input.returnPressed.connect(self.mark_from_input)
        control_row.addWidget(QLabel("Barkod:"))
        control_row.addWidget(self.scan_input, 2)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["Görülmeyen", "Görülen"])
        self.combo_status.currentIndexChanged.connect(self._status_changed)
        control_row.addWidget(QLabel("Liste:"))
        control_row.addWidget(self.combo_status)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara (barkod, kitap, raf)")
        self.search_input.textChanged.connect(self._search_changed)
        control_row.addWidget(self.search_input, 1)

        self.btn_complete = QPushButton("Sayımı Tamamla")
        self.btn_complete.setObjectName("DialogPositiveButton")
        self.btn_complete.clicked.connect(self.complete_session)
        self.btn_cancel = QPushButton("İptal Et")
        self.btn_cancel.setObjectName("DialogDangerButton")
        self.btn_cancel.clicked.connect(self.cancel_session)
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setObjectName("DialogNegativeButton")
        self.btn_delete.clicked.connect(self.delete_session)
        control_row.addWidget(self.btn_complete)
        control_row.addWidget(self.btn_cancel)
        control_row.addWidget(self.btn_delete)

        detail_layout.addLayout(control_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Barkod", "Kitap", "Raf", "Durum", "Görüldü", "Görülen", "Not"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._toggle_row_seen_state)
        detail_layout.addWidget(self.table, 1)

        self.empty_label = QLabel("Bir sayım oturumu seçin veya oluşturun.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(self.empty_label, 1)
        self.detail_panel.setVisible(False)

        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(1, 3)
        main.addWidget(splitter, 1)

        self.btn_new.clicked.connect(self.open_create_dialog)
        self.btn_refresh.clicked.connect(self.refresh_sessions)

    # ------------------------------------------------------------------
    def refresh_sessions(self, select_id=None):
        ok, sessions, error = inventory_api.list_sessions()
        if not ok:
            QMessageBox.warning(self, "Sayım", self._friendly_error(error) or "Sayım oturumları yüklenemedi.")
            return
        self.sessions = sessions or []
        self.session_list.blockSignals(True)
        self.session_list.clear()
        selected_row = 0
        for idx, session in enumerate(self.sessions):
            text = self._format_session_label(session)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, session)
            if session.get("status") != "active":
                item.setForeground(QColor("#777777"))
            self.session_list.addItem(item)
            if select_id and session.get("id") == select_id:
                selected_row = idx
        self.session_list.blockSignals(False)
        if self.sessions:
            self.session_list.setCurrentRow(selected_row)
        else:
            self.session_list.clearSelection()
            self._clear_current_session()

    # ------------------------------------------------------------------
    def _format_session_label(self, session):
        seen = session.get("seen_items") or 0
        total = session.get("total_items") or 0
        name = session.get("name") or "İsimsiz"
        status_text = session.get("status", "active")
        return f"{name}  ({seen}/{total})  [{status_text}]"

    # ------------------------------------------------------------------
    def _on_session_selected(self, current: QListWidgetItem, _previous: QListWidgetItem):
        session = current.data(Qt.UserRole) if current else None
        self.current_session = session
        if session:
            self._show_session(session)
        else:
            self.detail_panel.setVisible(False)
            self.empty_label.setVisible(True)
            self.btn_complete.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.scan_input.setEnabled(False)

    # ------------------------------------------------------------------
    def _show_session(self, session):
        if not session:
            self._clear_current_session()
            return
        self.detail_panel.setVisible(True)
        self.empty_label.setVisible(False)
        name = session.get("name") or "İsimsiz"
        status_value = session.get("status") or "active"
        seen = session.get("seen_items") or 0
        total = session.get("total_items") or 0
        percent = 0
        if total:
            percent = int(min(1000, (seen / float(total)) * 1000))
        self.progress.setValue(percent)
        self.label_session_title.setText(name)
        self.label_status.setText(f"Durum: {status_value}")
        self.label_counts.setText(f"Görülen: {seen} / {total}")
        self.label_filters.setText(self._format_filters(session.get("filters")))
        self.scan_input.setEnabled(status_value == "active")
        self.btn_complete.setEnabled(status_value == "active")
        self.btn_cancel.setEnabled(status_value == "active")
        self.btn_delete.setEnabled(True)
        self.refresh_items()

    # ------------------------------------------------------------------
    def _format_filters(self, filters):
        if not filters:
            return "Filtre: Tüm nüshalar"
        parts = []
        raf_query = filters.get("raf_query")
        if raf_query:
            parts.append(f"Raf contains '{raf_query}'")
        raf_prefix = filters.get("raf_prefix")
        if raf_prefix:
            parts.append(f"Raf startswith '{raf_prefix}'")
        durumlar = filters.get("durumlar")
        if durumlar:
            parts.append("Durum: " + ", ".join(durumlar))
        if not parts:
            return "Filtre: Tüm nüshalar"
        return "Filtre: " + " | ".join(parts)

    # ------------------------------------------------------------------
    def _status_changed(self):
        self.current_filter = "seen" if self.combo_status.currentIndex() == 1 else "unseen"
        self.refresh_items()

    # ------------------------------------------------------------------
    def _search_changed(self, text):
        self.current_search = text
        self._search_timer.start()

    def _apply_search_filter(self):
        self.refresh_items()

    # ------------------------------------------------------------------
    def refresh_items(self):
        session = self.current_session
        if not session:
            return
        if not session.get("id"):
            self._clear_current_session()
            return
        params = {"status": self.current_filter, "limit": 500}
        if self.current_search.strip():
            params["q"] = self.current_search.strip()
        ok, data, error = inventory_api.fetch_items(session.get("id"), params=params)
        if not ok:
            if self._is_missing_session_error(error):
                self._handle_missing_session()
                return
            QMessageBox.warning(self, "Sayım", self._friendly_error(error) or "Liste yüklenemedi.")
            return
        results = []
        if isinstance(data, dict):
            results = data.get("results") or []
            session_data = data.get("session")
            if session_data:
                self.current_session = session_data
                self._update_session_summary(session_data)
        elif isinstance(data, list):
            results = data
        self.current_items = results
        self._populate_table(results)

    # ------------------------------------------------------------------
    def _update_session_summary(self, session):
        self.label_counts.setText(f"Görülen: {session.get('seen_items', 0)} / {session.get('total_items', 0)}")
        self.label_filters.setText(self._format_filters(session.get("filters")))
        total = session.get("total_items") or 0
        seen = session.get("seen_items") or 0
        percent = 0
        if total:
            percent = int(min(1000, (seen / float(total)) * 1000))
        self.progress.setValue(percent)

    # ------------------------------------------------------------------
    def _populate_table(self, items):
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item.get("barkod") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("kitap_baslik") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(item.get("raf_kodu") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(item.get("durum") or ""))
            seen_text = "Evet" if item.get("seen") else "Hayır"
            self.table.setItem(row, 4, QTableWidgetItem(seen_text))
            seen_info = self._format_seen_info(item)
            self.table.setItem(row, 5, QTableWidgetItem(seen_info))
            note_item = QTableWidgetItem(item.get("note") or "")
            self.table.setItem(row, 6, note_item)

    # ------------------------------------------------------------------
    def _format_seen_info(self, item):
        if not item.get("seen"):
            return ""
        timestamp = item.get("seen_at")
        who = item.get("seen_by_name") or ""
        formatted = _format_datetime(timestamp)
        if who:
            return f"{formatted}\n{who}"
        return formatted

    # ------------------------------------------------------------------
    def mark_from_input(self):
        session = self.current_session
        if not session:
            return
        code = self.scan_input.text().strip()
        if not code:
            return
        ok, data, error = inventory_api.mark_item(
            session.get("id"),
            {"barkod": code, "seen": True},
        )
        if not ok:
            if self._is_missing_session_error(error):
                self._handle_missing_session()
                return
            QMessageBox.warning(self, "Sayım", self._friendly_error(error) or "Barkod bulunamadı.")
            return
        self.scan_input.clear()
        self._after_mark(data)

    # ------------------------------------------------------------------
    def _toggle_row_seen_state(self, row, _column):
        if row < 0 or row >= len(self.current_items):
            return
        session = self.current_session
        if not session or session.get("status") != "active":
            return
        item = self.current_items[row]
        new_state = not item.get("seen")
        payload = {"item_id": item.get("id"), "seen": new_state}
        ok, data, error = inventory_api.mark_item(session.get("id"), payload)
        if not ok:
            if self._is_missing_session_error(error):
                self._handle_missing_session()
                return
            QMessageBox.warning(self, "Sayım", self._friendly_error(error) or "İşlem gerçekleştirilemedi.")
            return
        self._after_mark(data)

    # ------------------------------------------------------------------
    def _after_mark(self, item_data):
        session_id = self.current_session.get("id") if self.current_session else None
        if session_id:
            ok, data, _ = inventory_api.get_session(session_id)
            if ok and isinstance(data, dict):
                self.current_session = data
                self._update_session_summary(data)
        self.refresh_items()

    # ------------------------------------------------------------------
    def open_create_dialog(self):
        dlg = InventorySessionCreateDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.created_session:
            self.refresh_sessions(select_id=dlg.created_session.get("id"))

    # ------------------------------------------------------------------
    def complete_session(self):
        self._close_session(status_value="completed")

    def cancel_session(self):
        self._close_session(status_value="canceled")

    def _close_session(self, status_value):
        session = self.current_session
        if not session:
            return
        confirm = QMessageBox.question(
            self,
            "Sayım",
            f"'{session.get('name')}' oturumunu {status_value} olarak işaretlemek istediğinize emin misiniz?",
        )
        if confirm != QMessageBox.Yes:
            return
        ok, data, error = inventory_api.complete_session(session.get("id"), status_value=status_value)
        if not ok:
            if self._is_missing_session_error(error):
                self._handle_missing_session()
                return
            QMessageBox.warning(self, "Sayım", self._friendly_error(error) or "İşlem tamamlanamadı.")
            return
        self.refresh_sessions(select_id=session.get("id"))

    def delete_session(self):
        session = self.current_session
        if not session:
            return
        confirm = QMessageBox.question(
            self,
            "Sayım",
            f"'{session.get('name')}' oturumunu silmek istediğinize emin misiniz? Bu işlem geri alınamaz.",
        )
        if confirm != QMessageBox.Yes:
            return
        ok, _, error = inventory_api.delete_session(session.get("id"))
        if not ok:
            if self._is_missing_session_error(error):
                self._handle_missing_session()
                return
            QMessageBox.warning(self, "Sayım", self._friendly_error(error) or "Sayım oturumu silinemedi.")
            return
        QMessageBox.information(self, "Sayım", "Oturum silindi.")
        self.refresh_sessions()

    def _friendly_error(self, message):
        if not message:
            return ""
        if "No InventorySession matches" in str(message):
            return (
                "Bu sayım oturumu bulunamadı. Oturum silinmiş veya tamamlanmış olabilir.\n"
                "Lütfen listeden farklı bir sayım seçin ya da yeni bir sayım oluşturun."
            )
        return str(message)

    def _is_missing_session_error(self, message):
        return bool(message) and "No InventorySession matches" in str(message)

    def _handle_missing_session(self):
        if (not getattr(self, "_initializing", False)) and self.current_session and self.current_session.get("id"):
            QMessageBox.information(
                self,
                "Sayım",
                "Bu sayım oturumu artık mevcut değil. Oturum listesi yenilenecek."
            )
        self._clear_current_session()
        self.session_list.clearSelection()
        self.refresh_sessions()

    def _clear_current_session(self):
        self.current_session = None
        self.current_items = []
        self.detail_panel.setVisible(False)
        self.empty_label.setVisible(True)
        self.table.setRowCount(0)
        self.label_session_title.setText("Sayım seçilmedi.")
        self.label_status.setText("")
        self.label_counts.setText("")
        self.label_filters.setText("")
        self.btn_complete.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.scan_input.setEnabled(False)

class InventorySessionCreateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Sayım")
        self.resize(460, 360)
        self.created_session = None
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.input_name = QLineEdit()
        self.input_desc = QTextEdit()
        self.input_desc.setFixedHeight(80)
        self.input_raf_query = QLineEdit()
        self.input_raf_prefix = QLineEdit()
        form.addRow("Adı*", self.input_name)
        form.addRow("Açıklama", self.input_desc)
        form.addRow("Raf (içeren)", self.input_raf_query)
        form.addRow("Raf (ile başlayan)", self.input_raf_prefix)
        layout.addLayout(form)

        self.status_checks = []
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Durum filtresi:"))
        for code, label in [("mevcut", "Mevcut"), ("oduncte", "Ödünçte"), ("kayip", "Kayıp"), ("hasarli", "Hasarlı")]:
            cb = QCheckBox(label)
            cb.setChecked(code in {"mevcut", "oduncte"})
            self.status_checks.append((code, cb))
            status_row.addWidget(cb)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _handle_accept(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Yeni Sayım", "Sayım adı zorunludur.")
            return
        filters = {}
        if self.input_raf_query.text().strip():
            filters["raf_query"] = self.input_raf_query.text().strip()
        if self.input_raf_prefix.text().strip():
            filters["raf_prefix"] = self.input_raf_prefix.text().strip()
        selected_statuses = [code for code, btn in self.status_checks if btn.isChecked()]
        if selected_statuses and len(selected_statuses) < 4:
            filters["durumlar"] = selected_statuses
        payload = {
            "name": name,
            "description": self.input_desc.toPlainText().strip(),
            "filters": filters,
        }
        ok, data, error = inventory_api.create_session(payload)
        if not ok:
            QMessageBox.warning(self, "Yeni Sayım", error or "Sayım oluşturulamadı.")
            return
        self.created_session = data
        self.accept()


def _format_datetime(value):
    if not value:
        return ""
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            text = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)
