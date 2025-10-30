from __future__ import annotations

import re

from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QBrush, QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QApplication,
)
from PyQt5.QtCore import QSize

from api import students as student_api
from ui.loan_status_dialog import LoanStatusDialog
from ui.entity_manager_dialog import normalize_entity_text


TABLE_HEADERS = ["Ad", "Soyad", "No", "Sınıf", "Rol", "Telefon", "E-posta", "Durum"]


class StudentManagerDialog(QDialog):
    """Öğrenci kayıtlarını yönetmek için diyalog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Öğrenci Yönetimi")
        self.resize(900, 600)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.current_id = None
        self._students = []
        self._classes = []
        self._roles = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        self.toggle_form_button = QToolButton()
        self.toggle_form_button.setText("Formu Gizle")
        self.toggle_form_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_form_button.setArrowType(Qt.DownArrow)
        self.toggle_form_button.setCheckable(True)
        self.toggle_form_button.setChecked(False)
        self.toggle_form_button.clicked.connect(self.toggle_form_section)

        # ------------------------------------------------------------------ #
        # Form alanı
        self.form_container = QWidget()
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        self.input_first_name = QLineEdit()
        self.input_last_name = QLineEdit()
        self.input_first_name.setPlaceholderText("Ad")
        self.input_last_name.setPlaceholderText("Soyad")
        self.input_number = QLineEdit()
        self.input_number.setPlaceholderText("Öğrenci No")
        self.input_phone = QLineEdit()
        self.input_phone.setPlaceholderText("(5__) ___ __ __")
        self.input_phone.setInputMask("(500) 000 00 00;_")
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("E-posta")

        self.combo_class = QComboBox()
        self.combo_class.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_role = QComboBox()
        self.combo_role.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.check_active = QCheckBox("Aktif Öğrenci")
        self.check_active.setChecked(True)
        self._active_last_state = True
        self.check_active.toggled.connect(self.on_active_toggled)

        # Satır 1: Ad | Soyad
        row1 = QWidget()
        row1h = QHBoxLayout(row1)
        row1h.setContentsMargins(0, 0, 0, 0)
        row1h.setSpacing(8)
        row1h.addWidget(self.input_first_name)
        row1h.addWidget(self.input_last_name)
        row1h.setStretch(0, 1)
        row1h.setStretch(1, 1)
        form_layout.addWidget(row1)

        # Satır 2: No | Sınıf | Rol
        row2 = QWidget()
        row2h = QHBoxLayout(row2)
        row2h.setContentsMargins(0, 0, 0, 0)
        row2h.setSpacing(8)
        row2h.addWidget(self.input_number)
        row2h.addWidget(self.combo_class)
        row2h.addWidget(self.combo_role)
        row2h.setStretch(0, 1)
        row2h.setStretch(1, 1)
        row2h.setStretch(2, 1)
        form_layout.addWidget(row2)

        # Satır 3: Telefon | E‑posta
        row3 = QWidget()
        row3h = QHBoxLayout(row3)
        row3h.setContentsMargins(0, 0, 0, 0)
        row3h.setSpacing(8)
        row3h.addWidget(self.input_phone)
        row3h.addWidget(self.input_email)
        # Aktif/Pasif onayını aynı satıra taşı
        row3h.addWidget(self.check_active)
        row3h.setStretch(0, 1)
        row3h.setStretch(1, 1)
        form_layout.addWidget(row3)

        main_layout.addWidget(self.form_container)

        # ------------------------------------------------------------------ #
        # Butonlar
        self.button_row_widget = QWidget()
        button_row = QHBoxLayout(self.button_row_widget)
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)

        self.btn_new = QPushButton("Yeni")
        self.btn_new.setObjectName("DialogNeutralButton")
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setObjectName("DialogPositiveButton")
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setObjectName("DialogNegativeButton")
        self.btn_close = QPushButton("Kapat")
        self.btn_close.setAutoDefault(False)
        self.btn_close.setDefault(False)
        self.btn_close.setFocusPolicy(Qt.StrongFocus)


        self.btn_new.clicked.connect(self.reset_form)
        self.btn_save.clicked.connect(self.save_student)
        self.btn_delete.clicked.connect(self.delete_student)
        # Sade kapatma: tek tıkta close/accept yeterli
        self.btn_close.clicked.connect(self.accept)

        # Butonlar satıra yayılsın: Yeni x1, Kaydet x3, Sil x1
        self.btn_new.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_save.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_delete.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_row.addWidget(self.btn_new)
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_delete)
        button_row.setStretch(0, 1)
        button_row.setStretch(1, 3)
        button_row.setStretch(2, 1)

        main_layout.addWidget(self.button_row_widget)

        # ------------------------------------------------------------------ #
        # Arama & filtre + tablo
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Öğrenci ara (ad, soyad, numara, telefon, e-posta)...")
        self.search_box.textChanged.connect(self.apply_filter)

        self.filter_active_only = QCheckBox("Yalnızca aktif öğrenciler")
        self.filter_active_only.setChecked(True)
        self.filter_active_only.toggled.connect(lambda _: self.apply_filter(self.search_box.text()))

        self.control_row_widget = QWidget()
        control_row = QHBoxLayout(self.control_row_widget)
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(10)
        control_row.addWidget(self.toggle_form_button)
        control_row.addWidget(self.filter_active_only)
        control_row.addWidget(self.search_box, stretch=1)
        control_row.addWidget(self.btn_close)
        main_layout.addWidget(self.control_row_widget)

        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSortIndicatorShown(True)
        # İkon boyutu ve son sütun için merkezleyen delege
        try:
            self.table.setIconSize(QSize(16, 16))
        except Exception:
            pass

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.table.setSortingEnabled(True)
        # Seçili satır rengi yerine yazı stili vurgulansın (ana sayfa ile uyumlu)
        self.table.setStyleSheet(
            "QTableWidget::item:selected{background: transparent; color: black;}"
        )
        # Yazı tipi vurgusu için ayrı bir sinyal daha: selectionChanged
        try:
            self.table.selectionModel().selectionChanged.connect(self.on_table_selection_changed)
        except Exception:
            pass

        main_layout.addWidget(self.table, stretch=1)

        # Durum sütunu için ikonları merkezleyen delegeyi ayarla
        try:
            self._status_delegate = _CenteredIconDelegate(self.table, QSize(16, 16))
            self.table.setItemDelegateForColumn(len(TABLE_HEADERS) - 1, self._status_delegate)
        except Exception:
            pass

        # ------------------------------------------------------------------ #
        self.load_reference_data()
        self.load_students()

    # ------------------------------------------------------------------ #
    # Veri yükleme
    def load_reference_data(self):
        self._classes = student_api.list_classes()
        self.combo_class.blockSignals(True)
        self.combo_class.clear()
        if not self._classes:
            self.combo_class.addItem("Sınıf bulunamadı", None)
        else:
            for item in self._classes:
                self.combo_class.addItem(item.get("ad", ""), item.get("id"))
        self.combo_class.blockSignals(False)

        self._roles = student_api.list_roles()
        self.combo_role.blockSignals(True)
        self.combo_role.clear()
        self.combo_role.addItem("— Seçim Yok —", None)
        for item in self._roles:
            self.combo_role.addItem(item.get("ad", ""), item.get("id"))
        self.combo_role.blockSignals(False)

    def load_students(self):
        self.table.setSortingEnabled(False)
        data = student_api.list_students()
        self.table.setRowCount(len(data))
        self._students = []

        for row, raw in enumerate(data):
            student = dict(raw or {})

            sinif_display, sinif_id = self._resolve_class(student)
            rol_display, rol_id = self._resolve_role(student)

            phone_raw = student.get("telefon") or ""
            phone_display = _format_phone_display(phone_raw)
            email = student.get("eposta") or ""
            is_active = bool(student.get("aktif", True))
            # Durum sütunu için metin yerine ikon kullanacağız

            row_values = [
                normalize_entity_text(student.get("ad", "")),
                normalize_entity_text(student.get("soyad", "")),
                student.get("ogrenci_no", ""),
                sinif_display,
                rol_display,
                phone_display,
                email,
                "",  # durum metni yerine ikon göstereceğiz
            ]

            for col, value in enumerate(row_values):
                item = QTableWidgetItem(value or "")
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if col in (2, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            # Durum sütunu: ortalı ikon için QLabel kullan
            self._set_status_widget(row, is_active)

            # Satır renklendirme: pasifler gri, aktifler açık yeşil
            bg = QColor(220, 255, 220) if is_active else QColor(235, 235, 235)
            for col in range(self.table.columnCount()):
                it = self.table.item(row, col)
                if it:
                    it.setBackground(bg)

            student["sinif_id"] = sinif_id
            student["rol_id"] = rol_id
            student["telefon"] = _normalize_phone(phone_raw) or phone_raw or None
            self.table.item(row, 0).setData(Qt.UserRole, student)
            self._students.append(student)

        self.table.setSortingEnabled(True)
        self.apply_filter(self.search_box.text())
        # Durum sütunundaki widget ikonlarını yerleştir
        for r in range(self.table.rowCount()):
            data = self.table.item(r, 0).data(Qt.UserRole) or {}
            self._set_status_widget(r, bool(data.get("aktif", True)))

    # ------------------------------------------------------------------ #
    # Yardımcı fonksiyonlar
    def _resolve_class(self, student):
        sinif_data = student.get("sinif")
        sinif_id = student.get("sinif_id") or None
        display = ""

        if isinstance(sinif_data, dict):
            display = sinif_data.get("ad", "")
            sinif_id = sinif_id or sinif_data.get("id")
        elif isinstance(sinif_data, str):
            display = sinif_data
        elif isinstance(sinif_data, int):
            sinif_id = sinif_data

        if sinif_id and not display:
            display = next((c.get("ad", "") for c in self._classes if c.get("id") == sinif_id), display)

        return display, sinif_id

    def _resolve_role(self, student):
        rol_data = student.get("rol")
        rol_id = student.get("rol_id") or None
        display = ""

        if isinstance(rol_data, dict):
            display = rol_data.get("ad", "")
            rol_id = rol_id or rol_data.get("id")
        elif isinstance(rol_data, str):
            display = rol_data
        elif isinstance(rol_data, int):
            rol_id = rol_data

        if rol_id and not display:
            display = next((r.get("ad", "") for r in self._roles if r.get("id") == rol_id), display)

        return display, rol_id

    def apply_filter(self, text: str):
        query = (text or "").strip().lower()
        for row in range(self.table.rowCount()):
            row_data = self.table.item(row, 0).data(Qt.UserRole) or {}
            if self.filter_active_only.isChecked() and not row_data.get("aktif", True):
                self.table.setRowHidden(row, True)
                continue
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def reset_form(self):
        self.current_id = None
        self.input_first_name.clear()
        self.input_last_name.clear()
        self.input_number.clear()
        self.input_phone.clear()
        self.input_email.clear()
        self.check_active.blockSignals(True)
        self.check_active.setChecked(True)
        self._set_active_checkbox_visual(True)
        self.check_active.blockSignals(False)
        self._active_last_state = True
        if self.combo_class.count() > 0:
            self.combo_class.setCurrentIndex(0)
        if self.combo_role.count() > 0:
            self.combo_role.setCurrentIndex(0)
        self.table.clearSelection()

    def on_row_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        data = items[0].data(Qt.UserRole)
        if not data:
            return

        self.current_id = data.get("id")
        self.input_first_name.setText(data.get("ad", ""))
        self.input_last_name.setText(data.get("soyad", ""))
        self.input_number.setText(data.get("ogrenci_no", ""))
        self.input_phone.setText(_format_phone_display(data.get("telefon")))
        self.input_email.setText(data.get("eposta", "") or "")
        is_active = bool(data.get("aktif", True))
        self.check_active.blockSignals(True)
        self.check_active.setChecked(is_active)
        self._set_active_checkbox_visual(is_active)
        self.check_active.blockSignals(False)
        self._active_last_state = is_active

        sinif_id = data.get("sinif_id")
        if sinif_id is None:
            sinif_info = data.get("sinif")
            if isinstance(sinif_info, dict):
                sinif_id = sinif_info.get("id")
            elif isinstance(sinif_info, int):
                sinif_id = sinif_info
        self._set_combo_index(self.combo_class, sinif_id)

        rol_id = data.get("rol_id")
        if rol_id is None:
            rol_info = data.get("rol")
            if isinstance(rol_info, dict):
                rol_id = rol_info.get("id")
            elif isinstance(rol_info, int):
                rol_id = rol_info
        self._set_combo_index(self.combo_role, rol_id)

    def on_table_selection_changed(self, selected, deselected):
        try:
            sel_indexes = self.table.selectedIndexes()
            sel_row = sel_indexes[0].row() if sel_indexes else -1
            for r in range(self.table.rowCount()):
                for c in range(self.table.columnCount()):
                    it = self.table.item(r, c)
                    if not it:
                        continue
                    f = QFont(it.font())
                    f.setBold(r == sel_row)
                    f.setPointSize(it.font().pointSize())
                    it.setFont(f)
        except Exception:
            pass

    def _set_combo_index(self, combo: QComboBox, value):
        if value is None:
            combo.setCurrentIndex(0)
            return
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                combo.setCurrentIndex(idx)
                return
        combo.setCurrentIndex(0)

    def _collect_payload(self):
        first = normalize_entity_text(self.input_first_name.text())
        last = normalize_entity_text(self.input_last_name.text())
        student_no = self.input_number.text().strip()
        phone = self.input_phone.text().strip()
        if "_" in phone:
            phone = ""
        email = self.input_email.text().strip()
        sinif_id = self.combo_class.currentData()
        rol_id = self.combo_role.currentData()
        active = self.check_active.isChecked()

        if not first:
            QMessageBox.warning(self, "Uyarı", "Ad alanı boş olamaz.")
            return None
        if not last:
            QMessageBox.warning(self, "Uyarı", "Soyad alanı boş olamaz.")
            return None
        if not student_no:
            QMessageBox.warning(self, "Uyarı", "Öğrenci numarası boş olamaz.")
            return None
        if sinif_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sınıf seçin.")
            return None

        if self._is_duplicate_number(student_no):
            QMessageBox.warning(self, "Uyarı", "Bu öğrenci numarası zaten kayıtlı.")
            return None

        normalized_phone = None
        if phone:
            if not _is_valid_phone(phone):
                QMessageBox.warning(self, "Uyarı", "Telefon numarası (5XX) XXX XX XX formatında olmalıdır.")
                return None
            normalized_phone = _normalize_phone(phone)
            if normalized_phone is None:
                QMessageBox.warning(self, "Uyarı", "Telefon numarası geçerli değil.")
                return None
            phone_display = _format_phone_display(normalized_phone)
            self.input_phone.setText(phone_display)

        if email and not _is_valid_email(email):
            QMessageBox.warning(self, "Uyarı", "E-posta adresi geçerli bir formatta değil.")
            return None

        payload = {
            "ad": first,
            "soyad": last,
            "ogrenci_no": student_no,
            "sinif": sinif_id,
            "rol": rol_id,
            "telefon": normalized_phone,
            "eposta": email or None,
            "aktif": active,
        }

        selected = self._get_selected_student()
        if selected and selected.get("pasif_tarihi"):
            payload["pasif_tarihi"] = selected["pasif_tarihi"]
        return payload

    def _is_duplicate_number(self, number: str) -> bool:
        number = number.strip()
        if not number:
            return False
        for stu in self._students:
            if not stu:
                continue
            if stu.get("ogrenci_no") == number:
                if self.current_id is None or stu.get("id") != self.current_id:
                    return True
        return False

    def _get_selected_student(self):
        items = self.table.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.UserRole)

    # ------------------------------------------------------------------ #
    # İşlemler
    def save_student(self):
        data = self._collect_payload()
        if data is None:
            return

        if self.current_id:
            resp = student_api.update_student(self.current_id, data)
            success = resp.status_code in (200, 202)
            action_text = "güncelleme"
        else:
            resp = student_api.create_student(data)
            success = resp.status_code in (200, 201)
            action_text = "ekleme"

        if success:
            QMessageBox.information(self, "Başarılı", f"Öğrenci {action_text} işlemi tamamlandı.")
            self.load_students()
            self.reset_form()
        else:
            detail = student_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Öğrenci {action_text} işlemi başarısız.\n\nDetay: {detail}")

    def delete_student(self):
        student = self._get_selected_student()
        if not self.current_id or not student:
            QMessageBox.warning(self, "Uyarı", "Silmek için bir öğrenci seçin.")
            return

        if not student.get("aktif", True):
            QMessageBox.information(
                self,
                "Bilgi",
                "Pasif durumdaki öğrenciler silinemez.",
            )
            return

        student_id = self.current_id
        if student_api.student_has_loans(student_id):
            # Türkçe etiketli onay penceresi
            if not self._ask_yes_no(
                "Açık Ödünç Kayıtları",
                "Bu öğrenciye ait açık ödünç kayıtları var. Önce bu kayıtların durumunu güncellemek ister misiniz?",
            ):
                return

            dialog = LoanStatusDialog(
                student_id=student_id,
                require_resolution=True,
                parent=self,
                title="Öğrenci Ödünç Kayıtlarını Yönet",
                allowed_statuses={"kayip", "hasarli"},
            )
            if dialog.exec_() != QDialog.Accepted:
                return

            self.load_students()

            if student_api.student_has_loans(student_id):
                QMessageBox.warning(
                    self,
                    "Eksik İşlem",
                    "Öğrencinin hâlâ açık ödünç kayıtları var. Lütfen durumlarını güncelleyiniz.",
                )
                self.reset_form()
                return

            resp = student_api.patch_student(student_id, {"aktif": False})
            if resp.status_code in (200, 202):
                QMessageBox.information(
                    self,
                    "Bilgi",
                    "Öğrencinin ödünç kayıtları kapatıldı ve öğrenci pasif duruma alındı.",
                )
                self.load_students()
                self.reset_form()
            else:
                detail = student_api.extract_error(resp)
                QMessageBox.warning(
                    self,
                    "Hata",
                    f"Öğrenci pasif duruma alınamadı.\n\nDetay: {detail}",
                )
            return

        if not self._ask_yes_no(
            "Silme Onayı",
            "Öğrencinin herhangi bir ödünç kaydı bulunmuyor.\n\nBu öğrenciyi kalıcı olarak silmek istediğinize emin misiniz?",
        ):
            return

        resp = student_api.delete_student(self.current_id)
        if resp.status_code in (200, 204):
            QMessageBox.information(self, "Başarılı", "Öğrenci kaydı silindi.")
            self.load_students()
            self.reset_form()
        else:
            detail = student_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Öğrenci silme işlemi başarısız.\n\nDetay: {detail}")

    # ------------------------------------------------------------------ #
    # UI helpers
    def toggle_form_section(self, checked):
        collapsed = checked
        self.form_container.setVisible(not collapsed)
        self.button_row_widget.setVisible(not collapsed)
        if collapsed:
            self.toggle_form_button.setArrowType(Qt.RightArrow)
            self.toggle_form_button.setText("Formu Göster")
        else:
            self.toggle_form_button.setArrowType(Qt.DownArrow)
            self.toggle_form_button.setText("Formu Gizle")

    # Not: Üst üste açılma koruması aktifken sade kapatma yeterli

    def on_active_toggled(self, checked: bool):
        """Aktif/Pasif geçişlerinde iki aşamalı doğrulama uygular."""
        prev = getattr(self, "_active_last_state", True)
        # Pasiften aktife
        if checked and not prev:
            if not self._ask_yes_no("Onay", "Bu öğrenciyi aktifleştirmek istediğinize emin misiniz?"):
                self._revert_active(False)
                return
            ok = self._confirm_text("AKTİF yazın:", expect="AKTİF")
            if not ok:
                QMessageBox.information(self, "Bilgi", "İşlem iptal edildi.")
                self._revert_active(False)
                return
        # Aktiften pasife
        elif not checked and prev:
            if not self._ask_yes_no("Onay", "Bu öğrenciyi pasifleştirmek istediğinize emin misiniz?"):
                self._revert_active(True)
                return
            ok = self._confirm_text("PASIF yazın:", expect="PASIF")
            if not ok:
                QMessageBox.information(self, "Bilgi", "İşlem iptal edildi.")
                self._revert_active(True)
                return

        # UI güncelle: etiket, son durum, tablo satırı ve simge
        self._set_active_checkbox_visual(checked)
        self._active_last_state = checked
        self._update_current_row_visuals(checked)

    def _revert_active(self, state: bool):
        self.check_active.blockSignals(True)
        self.check_active.setChecked(state)
        self.check_active.setText("Aktif Öğrenci ✅" if state else "Aktif Öğrenci ❌")
        self.check_active.blockSignals(False)

    def _set_status_widget(self, row: int, is_active: bool):
        """Durum sütununa ortalı ikon atar (cell widget kullanmadan)."""
        try:
            col = self.table.columnCount() - 1
            # Varsa önce cellWidget'ı kaldır (artefakt engelle)
            if self.table.cellWidget(row, col):
                self.table.removeCellWidget(row, col)
            # Arka plan vb. için item bul/oluştur
            item = self.table.item(row, col)
            if item is None:
                item = QTableWidgetItem("")
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, col, item)
            # Sadece ikon kullan; hizalama delege ile merkezlenir
            icon = self._make_status_icon(is_active, size=16)
            item.setData(Qt.DecorationRole, icon)
            item.setText("")
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.TextAlignmentRole, Qt.AlignCenter)
        except Exception:
            pass

    def _ask_yes_no(self, title: str, text: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        yes_btn = box.addButton("Evet", QMessageBox.YesRole)
        no_btn = box.addButton("Hayır", QMessageBox.NoRole)
        box.setDefaultButton(no_btn)
        box.exec_()
        return box.clickedButton() == yes_btn

    def _confirm_text(self, label: str, expect: str) -> bool:
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Doğrulama")
        dlg.setLabelText(label)
        # Buton metinlerini Türkçeleştir
        bb = dlg.findChild(QDialogButtonBox)
        if bb:
            okb = bb.button(QDialogButtonBox.Ok)
            cb = bb.button(QDialogButtonBox.Cancel)
            if okb:
                okb.setText("Tamam")
            if cb:
                cb.setText("İptal")
        if dlg.exec_() != QDialog.Accepted:
            return False
        val = dlg.textValue() or ""
        return val.strip().upper() == expect.upper()

    def _update_current_row_visuals(self, is_active: bool):
        # Seçili satırın durum simgesini ve arka planını güncelle
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        durum_col = self.table.columnCount() - 1
        icon_text = "✅" if is_active else "❌"
        if self.table.item(row, durum_col):
            self.table.item(row, durum_col).setText(icon_text)
        bg = QColor(220, 255, 220) if is_active else QColor(235, 235, 235)
        for col in range(self.table.columnCount()):
            it = self.table.item(row, col)
            if it:
                it.setBackground(bg)
        # Filter kutusu açıksa pasife geçen satırı gizle
        if self.filter_active_only.isChecked():
            self.table.setRowHidden(row, not is_active)
        # Satırın UserRole verisini de güncelle
        data = self.table.item(row, 0).data(Qt.UserRole) or {}
        data["aktif"] = is_active
        self.table.item(row, 0).setData(Qt.UserRole, data)
        # Durum ikonu güncelle
        status_col = self.table.columnCount() - 1
        it_status = self.table.item(row, status_col)
        if it_status:
            icon = self._make_status_icon(is_active, size=16)
            it_status.setData(Qt.DecorationRole, icon)
            it_status.setText("")
            it_status.setTextAlignment(Qt.AlignCenter)
            it_status.setData(Qt.TextAlignmentRole, Qt.AlignCenter)


    def _set_active_checkbox_visual(self, is_active: bool):
        # Checkbox ikonunu yeşil tik / kırmızı çarpı olacak şekilde boyar
        size = 18
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        # Arkaplan daire
        color = QColor(46, 204, 113) if is_active else QColor(231, 76, 60)
        p.setBrush(QBrush(color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, size-1, size-1)
        # İşaret
        pen = QPen(Qt.white)
        pen.setWidth(3)
        p.setPen(pen)
        if is_active:
            # basit bir tik işareti
            p.drawLine(int(size*0.25), int(size*0.55), int(size*0.45), int(size*0.75))
            p.drawLine(int(size*0.45), int(size*0.75), int(size*0.78), int(size*0.28))
        else:
            # çarpı işareti
            p.drawLine(int(size*0.28), int(size*0.28), int(size*0.72), int(size*0.72))
            p.drawLine(int(size*0.72), int(size*0.28), int(size*0.28), int(size*0.72))
        p.end()
        self.check_active.setIcon(QIcon(pm))
        self.check_active.setIconSize(pm.size())

    def _make_status_icon(self, is_active: bool, size: int = 16) -> QIcon:
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor(46, 204, 113) if is_active else QColor(231, 76, 60)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size - 1, size - 1)
        pen = QPen(Qt.white)
        pen.setWidth(2)
        painter.setPen(pen)
        if is_active:
            painter.drawLine(int(size*0.25), int(size*0.55), int(size*0.45), int(size*0.75))
            painter.drawLine(int(size*0.45), int(size*0.75), int(size*0.78), int(size*0.28))
        else:
            painter.drawLine(int(size*0.28), int(size*0.28), int(size*0.72), int(size*0.72))
            painter.drawLine(int(size*0.72), int(size*0.28), int(size*0.28), int(size*0.72))
        painter.end()
        return QIcon(pm)


PHONE_PATTERN = re.compile(r"^\(5\d{2}\)\s\d{3}\s\d{2}\s\d{2}$")
EMAIL_PATTERN = re.compile(
    r"^(?=.{3,254}$)([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})$"
)


def _is_valid_phone(value: str) -> bool:
    return bool(PHONE_PATTERN.fullmatch(value.strip()))


def _is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(value))


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("05"):
        return digits
    if len(digits) == 10 and digits.startswith("5"):
        return "0" + digits
    return None


def _format_phone_display(value: str | None) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("05"):
        digits = digits[1:]
    if len(digits) != 10 or not digits.startswith("5"):
        return value or ""
    return f"({digits[0]}{digits[1]}{digits[2]}) {digits[3]}{digits[4]}{digits[5]} {digits[6]}{digits[7]} {digits[8]}{digits[9]}"


class _CenteredIconDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, icon_size: QSize | None = None):
        super().__init__(parent)
        self._icon_size = icon_size or QSize(16, 16)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        # Mevcut ikon verisini al ve varsayılan çizimde metin/ikon belirtme
        icon = index.data(Qt.DecorationRole)
        opt.text = ""
        try:
            opt.icon = QIcon()
        except Exception:
            pass
        style = opt.widget.style() if opt.widget else QApplication.style()
        # Arka plan/seçim vurgusunu çiz
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)
        # İkonu hücre ortasına çiz
        if icon:
            if isinstance(icon, QIcon):
                pm = icon.pixmap(self._icon_size)
            else:
                # Destek için: QPixmap verilmişse kabul et
                try:
                    pm = icon.pixmap(self._icon_size)
                except Exception:
                    pm = None
            if pm:
                r = opt.rect
                x = r.x() + (r.width() - pm.width()) // 2
                y = r.y() + (r.height() - pm.height()) // 2
                painter.drawPixmap(x, y, pm)

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        w = max(base.width(), self._icon_size.width() + 8)
        h = max(base.height(), self._icon_size.height() + 6)
        return QSize(w, h)
