from __future__ import annotations

import os
import subprocess
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtPrintSupport import QPrinterInfo
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.config import load_settings, save_settings


class PrinterSettingsWidget(QWidget):
    """Reusable printer settings panel used by both the dialog and settings tab."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.default_label_printer = None
        self.default_label_is_thermal = False
        self.default_report_printer = None

        root = QVBoxLayout(self)

        # Etiket yazıcısı grubu
        grp_label = QFrame()
        grp_label.setObjectName("ToolbarGroup")
        lab_lay = QVBoxLayout(grp_label)
        lab_lay.setContentsMargins(10, 10, 10, 10)
        lab_lay.addWidget(QLabel("Etiket Yazıcısı"))

        row1 = QHBoxLayout()
        self.cmb_label = QComboBox()
        self.btn_refresh1 = QToolButton()
        self.chk_label_thermal = QCheckBox("Termal")
        self._apply_refresh_icon(self.btn_refresh1)
        self.btn_refresh1.setAutoRaise(True)
        self.btn_refresh1.setFixedSize(32, 32)
        row1.addWidget(self.cmb_label, 1)
        row1.addWidget(self.btn_refresh1)
        row1.addWidget(self.chk_label_thermal)
        lab_lay.addLayout(row1)

        self.lbl_label_status = QLabel("")
        self.lbl_label_status.setAlignment(Qt.AlignLeft)
        lab_lay.addWidget(self.lbl_label_status)

        # Rapor yazıcısı grubu
        grp_report = QFrame()
        grp_report.setObjectName("ToolbarGroup")
        rep_lay = QVBoxLayout(grp_report)
        rep_lay.setContentsMargins(10, 10, 10, 10)
        rep_lay.addWidget(QLabel("Rapor Yazıcısı (A4)"))

        row2 = QHBoxLayout()
        self.cmb_report = QComboBox()
        self.btn_refresh2 = QToolButton()
        self._apply_refresh_icon(self.btn_refresh2)
        self.btn_refresh2.setAutoRaise(True)
        self.btn_refresh2.setFixedSize(32, 32)
        row2.addWidget(self.cmb_report, 1)
        row2.addWidget(self.btn_refresh2)
        rep_lay.addLayout(row2)

        self.lbl_report_status = QLabel("")
        self.lbl_report_status.setAlignment(Qt.AlignLeft)
        rep_lay.addWidget(self.lbl_report_status)

        root.addWidget(grp_label)
        root.addWidget(grp_report)
        root.addStretch(1)

        # Sinyaller
        self.btn_refresh1.clicked.connect(self.refresh_printers)
        self.btn_refresh2.clicked.connect(self.refresh_printers)
        self.cmb_label.currentIndexChanged.connect(self._update_status_labels)
        self.cmb_report.currentIndexChanged.connect(self._update_status_labels)

        # İlk yükleme
        self.load_preferences()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_preferences(self):
        self._load_prefs()
        self.refresh_printers()
        self._apply_current_to_ui()
        self._update_status_labels()

    def save_preferences(self):
        self._save_prefs()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def refresh_printers(self):
        names = self._printers()
        for cmb in (self.cmb_label, self.cmb_report):
            prev = cmb.currentText().strip()
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItems(names)
            if prev:
                idx = cmb.findText(prev)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)
        self._update_status_labels()

    # ------------------------------------------------------------------
    def _apply_refresh_icon(self, button: QToolButton):
        try:
            custom_icon = os.path.join("resources", "icons", "yinele.png")
            if os.path.exists(custom_icon):
                button.setIcon(QIcon(custom_icon))
            else:
                button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        except Exception:
            pass

    def _printers(self):
        try:
            return [p.printerName() for p in QPrinterInfo.availablePrinters()]
        except Exception:
            return []

    def _apply_current_to_ui(self):
        if self.default_label_printer:
            idx = self.cmb_label.findText(self.default_label_printer)
            if idx >= 0:
                self.cmb_label.setCurrentIndex(idx)
        self.chk_label_thermal.setChecked(bool(self.default_label_is_thermal))

        if self.default_report_printer:
            idx = self.cmb_report.findText(self.default_report_printer)
            if idx >= 0:
                self.cmb_report.setCurrentIndex(idx)

    def _printer_status_text(self, name: str) -> str:
        name = (name or "").strip()
        if not name:
            return "mevcut değil"
        if sys.platform.startswith('win'):
            try:
                import win32print

                PR_ERR = (
                    win32print.PRINTER_STATUS_ERROR
                    | win32print.PRINTER_STATUS_PAPER_OUT
                    | win32print.PRINTER_STATUS_OFFLINE
                    | getattr(win32print, 'PRINTER_STATUS_PAPER_JAM', 0)
                    | getattr(win32print, 'PRINTER_STATUS_DOOR_OPEN', 0)
                )
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
            try:
                import cups

                conn = cups.Connection()
                p_info = conn.getPrinters().get(name)
                if not p_info:
                    return "mevcut değil"
                state = p_info.get('printer-state')
                reasons = p_info.get('printer-state-reasons', [])
                if state == 3 and (not reasons or 'none' in reasons):
                    return "hazır"
                if state == 4:
                    return "yazdırıyor"
                return "hazır değil"
            except Exception:
                try:
                    r = subprocess.run(
                        ['lpstat', '-p', name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=1.5,
                    )
                    if r.returncode != 0:
                        return "mevcut değil"
                    out = (r.stdout or '').lower()
                    if 'disabled' in out or 'stopped' in out:
                        return "hazır değil"
                    if 'is printing' in out or 'now printing' in out:
                        return "yazdırıyor"
                    if 'is idle' in out:
                        return "hazır"
                    return "bilinmiyor"
                except Exception:
                    return "bilinmiyor"

    def _update_status_labels(self):
        self.lbl_label_status.setText(self._printer_status_text(self.cmb_label.currentText()))
        self.lbl_report_status.setText(self._printer_status_text(self.cmb_report.currentText()))

    def _load_prefs(self):
        st = load_settings() or {}
        printing = st.get("printing", {})
        label_prefs = st.get("label_editor", {})
        self.default_label_printer = printing.get("label_printer") or label_prefs.get("default_printer")
        self.default_label_is_thermal = bool(
            printing.get("label_is_thermal", label_prefs.get("default_printer_is_thermal", False))
        )
        self.default_report_printer = printing.get("report_printer")

    def _save_prefs(self):
        st = load_settings() or {}
        printing = st.setdefault("printing", {})

        self.default_label_printer = self.cmb_label.currentText().strip() or None
        self.default_report_printer = self.cmb_report.currentText().strip() or None
        self.default_label_is_thermal = bool(self.chk_label_thermal.isChecked())

        printing["label_printer"] = self.default_label_printer
        printing["label_is_thermal"] = self.default_label_is_thermal
        printing["report_printer"] = self.default_report_printer

        label_prefs = st.setdefault("label_editor", {})
        label_prefs["default_printer"] = self.default_label_printer
        label_prefs["default_printer_is_thermal"] = self.default_label_is_thermal

        try:
            save_settings(st)
        except Exception:
            pass


class PrinterSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yazıcı Ayarları")
        self.resize(520, 320)

        layout = QVBoxLayout(self)
        self.page = PrinterSettingsWidget(self)
        layout.addWidget(self.page)

        buttons = QDialogButtonBox()
        btn_save = buttons.addButton("Kaydet", QDialogButtonBox.ApplyRole)
        btn_save.setObjectName("DialogPositiveButton")
        btn_close = buttons.addButton("Kapat", QDialogButtonBox.RejectRole)
        btn_close.setObjectName("DialogNeutralButton")
        btn_save.clicked.connect(self._on_save)
        btn_close.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self):
        self.page.save_preferences()
