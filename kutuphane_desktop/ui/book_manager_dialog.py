from __future__ import annotations

import re
import random
from datetime import datetime
from typing import Dict, List, Set

from PyQt5.QtCore import Qt, QStringListModel, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QColor
from PyQt5.QtPrintSupport import QPrinterInfo
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QSizePolicy, QMessageBox, QToolButton, QFormLayout, QDialogButtonBox,
    QListWidget, QListWidgetItem, QCompleter, QCheckBox, QSpinBox,
    QStackedWidget, QAbstractItemView
)

from api import books as book_api
from core.config import load_settings
from printing.printer_guard import ensure_printer_ready, enforce_media_type
from printing.template_renderer import get_default_template_path, print_label_batch
from ui.entity_manager_dialog import AuthorManagerDialog, CategoryManagerDialog, normalize_entity_text


BOOK_TABLE_HEADERS = ["Başlık", "Yazar", "Kategori", "ISBN", "Nüsha"]


ISBN_PATTERN = re.compile(r"^(97[89]\d{10}|\d{9}[\dXx])$")


class NumericTableWidgetItem(QTableWidgetItem):
    """Sayısal sıralama için QTableWidgetItem."""

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                return float(self.text()) < float(other.text())
            except Exception:
                pass
        return super().__lt__(other)


class TitleLineEdit(QLineEdit):
    focusLost = pyqtSignal()
    suggestionsNavigate = pyqtSignal(int)
    suggestionChosen = pyqtSignal()
    escapePressed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._suggestions_active = False

    def setSuggestionsActive(self, active: bool):
        self._suggestions_active = bool(active)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focusLost.emit()

    def keyPressEvent(self, event):
        key = event.key()
        if self._suggestions_active and key in (Qt.Key_Up, Qt.Key_Down):
            delta = -1 if key == Qt.Key_Up else 1
            self.suggestionsNavigate.emit(delta)
            event.accept()
            return
        if self._suggestions_active and key in (Qt.Key_Return, Qt.Key_Enter):
            self.suggestionChosen.emit()
            event.accept()
            return
        if self._suggestions_active and key == Qt.Key_Escape:
            self.escapePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class LabelPrintDialog(QDialog):
    def __init__(self, copies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Etiket Yazdır")
        self.resize(300, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        info = QLabel("Yazdırılacak nüshaları seçin:")
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        self.btn_all = QPushButton("Hepsi")
        self.btn_none = QPushButton("Hiçbiri")
        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)
        layout.addLayout(btn_row)

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.NoSelection)
        for cp in copies:
            text = str(cp.get("barkod") or "—")
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, cp)
            self.list.addItem(item)
        layout.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        self.btn_close = QPushButton("Kapat")
        self.btn_close.setObjectName("DialogCloseButton")
        self.btn_close.clicked.connect(self.reject)

        self.btn_print = QPushButton("Yazdır")
        self.btn_print.setObjectName("DialogWarnLargeButton")
        self.btn_print.setEnabled(self._has_checked())
        self.btn_print.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_print.clicked.connect(self.accept)

        buttons.addWidget(self.btn_close)
        buttons.addWidget(self.btn_print, 1)
        layout.addLayout(buttons)

        self.btn_all.clicked.connect(lambda: self._set_all(Qt.Checked))
        self.btn_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        self.list.itemChanged.connect(lambda _: self._update_print_state())

    def _set_all(self, state):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)
        self.list.blockSignals(False)
        self._update_print_state()

    def _has_checked(self):
        for i in range(self.list.count()):
            if self.list.item(i).checkState() == Qt.Checked:
                return True
        return False

    def _update_print_state(self):
        self.btn_print.setEnabled(self._has_checked())

    def selected_copies(self):
        result = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.data(Qt.UserRole) or {})
        return result

class BookManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kitap Yönetimi")
        self.resize(920, 620)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.current_id = None
        self._authors = []
        self._categories = []
        self._all_titles = []
        self._suppress_similarity_check = False
        self._selected_author_id = None
        self._selected_category_id = None
        self._title_index = {}
        self._book_index = {}
        self._pending_duplicate_matches: List[Dict] = []
        self._mode = "view"
        self._pending_copy_plan: List[str] = []
        self._pending_label_contexts: List[Dict] = []

        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(10)

        # Formu göster/gizle
        self.toggle_form_button = QToolButton()
        self.toggle_form_button.setText("Formu Gizle")
        self.toggle_form_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_form_button.setArrowType(Qt.DownArrow)
        self.toggle_form_button.setCheckable(True)
        self.toggle_form_button.setChecked(False)
        self.toggle_form_button.clicked.connect(self.toggle_form_section)

        # Form alanı
        self.form_container = QWidget()
        form_v = QVBoxLayout(self.form_container)
        form_v.setContentsMargins(0, 0, 0, 0)
        form_v.setSpacing(8)

        # Satır 1: Başlık
        self.input_title = TitleLineEdit()
        self.input_title.setPlaceholderText("Kitap başlığı")
        self.input_title.textChanged.connect(self._update_title_suggestions)
        self.input_title.focusLost.connect(self._on_title_focus_lost)
        self.input_title.suggestionsNavigate.connect(self._navigate_title_suggestions)
        self.input_title.suggestionChosen.connect(self._accept_current_suggestion)
        self.input_title.escapePressed.connect(self._hide_title_suggestions)

        self.chk_titlecase = QCheckBox("Baş harflerini otomatik büyüt")
        self.chk_titlecase.setChecked(True)

        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        title_layout.addWidget(self.input_title, 1)
        title_layout.addWidget(self.chk_titlecase)
        form_v.addWidget(self._form_row_single("Kitap Adı", title_container))

        self.title_suggestion_list = QListWidget()
        self.title_suggestion_list.setObjectName("TitleSuggestionList")
        self.title_suggestion_list.setSelectionMode(QListWidget.SingleSelection)
        self.title_suggestion_list.setVisible(False)
        self.title_suggestion_list.setMaximumHeight(140)
        self.title_suggestion_list.itemClicked.connect(self._on_title_suggestion_clicked)
        form_v.addWidget(self.title_suggestion_list)

        # Satır 2: Yazar + hızlı ekle | Kategori + hızlı ekle
        self.input_author = TitleLineEdit()
        self.input_author.setPlaceholderText("Yazar adı")
        self.input_author.textChanged.connect(self._on_author_text_changed)
        self.input_author.focusLost.connect(self._on_author_focus_lost)
        self.input_author.suggestionsNavigate.connect(lambda delta: self._navigate_suggestions(self.author_suggestion_list, delta))
        self.input_author.suggestionChosen.connect(lambda: self._accept_suggestion(self.author_suggestion_list, self._apply_author_suggestion))
        self.input_author.escapePressed.connect(self._hide_author_suggestions)
        self.author_suggestion_list = QListWidget()
        self.author_suggestion_list.setObjectName("AuthorSuggestionList")
        self.author_suggestion_list.setSelectionMode(QListWidget.SingleSelection)
        self.author_suggestion_list.setVisible(False)
        self.author_suggestion_list.setMaximumHeight(140)
        self.author_suggestion_list.itemClicked.connect(
            lambda item: self._apply_author_suggestion(item.text(), item.data(Qt.UserRole))
        )
        self.btn_add_author = QToolButton()
        self.btn_add_author.setText("+")
        self.btn_add_author.setToolTip("Yeni yazar ekle")
        self.btn_add_author.clicked.connect(self.add_author_quick)

        self.input_category = TitleLineEdit()
        self.input_category.setPlaceholderText("Kategori")
        self.input_category.textChanged.connect(self._on_category_text_changed)
        self.input_category.focusLost.connect(self._on_category_focus_lost)
        self.input_category.suggestionsNavigate.connect(lambda delta: self._navigate_suggestions(self.category_suggestion_list, delta))
        self.input_category.suggestionChosen.connect(lambda: self._accept_suggestion(self.category_suggestion_list, self._apply_category_suggestion))
        self.input_category.escapePressed.connect(self._hide_category_suggestions)
        self.category_suggestion_list = QListWidget()
        self.category_suggestion_list.setObjectName("CategorySuggestionList")
        self.category_suggestion_list.setSelectionMode(QListWidget.SingleSelection)
        self.category_suggestion_list.setVisible(False)
        self.category_suggestion_list.setMaximumHeight(140)
        self.category_suggestion_list.itemClicked.connect(lambda item: self._apply_category_suggestion(item.text(), item.data(Qt.UserRole)))
        self.btn_category_info = QToolButton()
        self.btn_category_info.setText("?")
        self.btn_category_info.setToolTip("Mevcut kategorileri görüntüle")
        self.btn_category_info.setCursor(Qt.PointingHandCursor)
        self.btn_category_info.clicked.connect(self._show_category_info)

        row2 = QWidget()
        row2h = QHBoxLayout(row2)
        row2h.setContentsMargins(0, 0, 0, 0)
        row2h.setSpacing(8)
        row2h.addWidget(self._form_row_labeled("Yazar", self.input_author, self.btn_add_author))
        row2h.addWidget(self._form_row_labeled("Kategori", self.input_category, self.btn_category_info))
        row2h.setStretch(0, 1)
        row2h.setStretch(1, 1)
        form_v.addWidget(row2)
        form_v.addWidget(self.author_suggestion_list)
        form_v.addWidget(self.category_suggestion_list)

        # Satır 3: ISBN | Kopya sayısı + yönet
        self.input_isbn = QLineEdit()
        self.input_isbn.setPlaceholderText("ISBN (10/13)")

        self.label_copy_count = QLabel("0")
        self.btn_manage_copies = QPushButton("Nüshaları Yönet")
        self.btn_manage_copies.setEnabled(False)
        self.btn_manage_copies.clicked.connect(self.open_copies_dialog)

        row3 = QWidget()
        row3h = QHBoxLayout(row3)
        row3h.setContentsMargins(0, 0, 0, 0)
        row3h.setSpacing(8)
        row3h.addWidget(self._form_row_single("ISBN", self.input_isbn))

        copies_widget = QWidget()
        cw = QHBoxLayout(copies_widget)
        cw.setContentsMargins(0, 0, 0, 0)
        cw.setSpacing(6)
        cw.addWidget(QLabel("Nüsha:"))
        cw.addWidget(self.label_copy_count)
        cw.addStretch(1)
        cw.addWidget(self.btn_manage_copies)
        row3h.addWidget(copies_widget)
        row3h.setStretch(0, 1)
        row3h.setStretch(1, 1)
        form_v.addWidget(row3)

        main.addWidget(self.form_container)

        self._form_edit_widgets = [
            self.input_title,
            self.chk_titlecase,
            self.title_suggestion_list,
            self.input_author,
            self.author_suggestion_list,
            self.input_category,
            self.category_suggestion_list,
            self.input_isbn,
            self.btn_add_author,
            self.btn_category_info,
        ]

        # Butonlar
        self.button_row_widget = QWidget()
        btn_row = QHBoxLayout(self.button_row_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        self.btn_new = QPushButton("Yeni")
        self.btn_new.setObjectName("ActionNewButton")
        self.btn_edit = QPushButton("Düzenle")
        self.btn_edit.setObjectName("ActionEditButton")
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setObjectName("DialogPositiveButton")
        self.btn_cancel_edit = QPushButton("İptal")
        self.btn_cancel_edit.setObjectName("DialogNegativeButton")
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setObjectName("DialogNegativeButton")
        self.btn_print = QPushButton("Barkod Bas")
        self.btn_print.setEnabled(False)
        self.btn_close = QPushButton("Pencereyi Kapat")
        self.chk_serial_entry = QCheckBox("Seri kitap kaydı")
        self.chk_serial_entry.setToolTip("Kaydettikten sonra otomatik yeni kayıt başlat")
        self.chk_serial_entry.setVisible(False)
        self.chk_auto_label = QCheckBox("Etiketi otomatik yazdır")
        self.chk_auto_label.setToolTip("Kaydettikten sonra barkod etiketini otomatik yazdır")
        self.chk_auto_label.setVisible(False)
        self.chk_auto_label.toggled.connect(self._handle_auto_label_toggle)

        for b in (
            self.btn_new,
            self.btn_edit,
            self.btn_save,
            self.btn_cancel_edit,
            self.btn_delete,
            self.btn_print,
            self.btn_close,
        ):
            b.setAutoDefault(False)
            b.setDefault(False)

        self.btn_save.installEventFilter(self)

        self.btn_new.clicked.connect(self.start_new_entry)
        self.btn_edit.clicked.connect(self.start_edit_mode)
        self.btn_save.clicked.connect(self.save_book)
        self.btn_cancel_edit.clicked.connect(self.cancel_editing)
        self.btn_delete.clicked.connect(self.delete_book)
        self.btn_print.clicked.connect(self.print_labels)
        self.btn_close.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.chk_serial_entry)
        btn_row.addWidget(self.chk_auto_label)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel_edit)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_print)
        main.addWidget(self.button_row_widget)

        self.setTabOrder(self.input_title, self.input_author)
        self.setTabOrder(self.input_author, self.input_category)
        self.setTabOrder(self.input_category, self.input_isbn)
        self.setTabOrder(self.input_isbn, self.btn_save)
        self._setup_enter_shortcuts()

        # Arama ve tablo
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Kitap ara (başlık, yazar, kategori, ISBN)...")
        self.search_box.textChanged.connect(self.apply_filter)

        control = QWidget()
        ch = QHBoxLayout(control)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(8)
        ch.addWidget(self.toggle_form_button)
        ch.addWidget(self.search_box, 1)
        ch.addWidget(self.btn_close)
        main.addWidget(control)

        self.table = QTableWidget(0, len(BOOK_TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(BOOK_TABLE_HEADERS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_row_selected)

        main.addWidget(self.table, 1)

        # Veri yükle
        self.load_reference_data()
        self.load_books()
        self.reset_form()

    # --------------------------- UI helpers --------------------------- #
    def _form_row_single(self, label_text: str, widget):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(QLabel(label_text))
        h.addWidget(widget, 1)
        return w

    def _form_row_labeled(self, label_text: str, main_widget, trailing_widget=None):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(QLabel(label_text))
        h.addWidget(main_widget, 1)
        if trailing_widget is not None:
            h.addWidget(trailing_widget)
        return w

    def toggle_form_section(self, checked):
        collapsed = checked
        self.form_container.setVisible(not collapsed)
        # Form ile birlikte işlem butonlarını da gizle/göster
        if hasattr(self, 'button_row_widget') and self.button_row_widget:
            self.button_row_widget.setVisible(not collapsed)
        if collapsed:
            self.toggle_form_button.setArrowType(Qt.RightArrow)
            self.toggle_form_button.setText("Formu Göster")
        else:
            self.toggle_form_button.setArrowType(Qt.DownArrow)
            self.toggle_form_button.setText("Formu Gizle")

    # --------------------------- Data load --------------------------- #
    def load_reference_data(self):
        prev_author_id = self._selected_author_id
        prev_category_id = self._selected_category_id
        current_author_text = self.input_author.text()
        current_category_text = self.input_category.text()

        self._authors = book_api.list_authors() or []
        self._categories = book_api.list_categories() or []

        if prev_author_id:
            author = self._find_author_by_id(prev_author_id)
            if author:
                self._apply_author_suggestion(author.get("ad_soyad", ""), author)
            else:
                self._selected_author_id = None
                self._apply_author_suggestion(current_author_text, None)
        else:
            self._apply_author_suggestion(current_author_text, None)

        if prev_category_id:
            category = self._find_category_by_id(prev_category_id)
            if category:
                self._apply_category_suggestion(category.get("ad", ""), category)
            else:
                self._selected_category_id = None
                self._apply_category_suggestion(current_category_text, None)
        else:
            self._apply_category_suggestion(current_category_text, None)

    def load_books(self):
        self.table.setSortingEnabled(False)
        data = book_api.list_books() or []
        self._title_index = {}
        self._book_index = {}
        self._all_titles = []
        self.table.setRowCount(len(data))
        for row, bk in enumerate(data):
            title = bk.get("baslik", "")
            norm_title = self._normalize_for_compare(title)
            if norm_title:
                self._title_index.setdefault(norm_title, []).append(bk)
                self._all_titles.append(title)
            author = self._resolve_author(bk.get("yazar"))
            category = self._resolve_category(bk.get("kategori"))
            isbn = bk.get("isbn", "")
            copies = bk.get("nusha_sayisi")
            if copies is None:
                # Eski backend versiyonları için geriye dönük destek
                copies = len(book_api.list_copies_for_book(bk.get("id"))) if bk.get("id") else 0
                bk["nusha_sayisi"] = copies

            book_id = bk.get("id")
            if book_id is not None:
                self._book_index[book_id] = bk

            values = [title, author, category, isbn, copies]
            for col, val in enumerate(values):
                if col == 4:
                    it = NumericTableWidgetItem(str(val if val is not None else 0))
                    it.setData(Qt.UserRole, val if val is not None else 0)
                    it.setTextAlignment(Qt.AlignCenter)
                else:
                    it = QTableWidgetItem(val or "")
                    it.setTextAlignment(Qt.AlignCenter if col == 3 else Qt.AlignLeft)
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, col, it)
            # raw veriyi sakla
            self.table.item(row, 0).setData(Qt.UserRole, bk)

        self.table.setSortingEnabled(True)
        self.apply_filter(self.search_box.text())
        self._hide_title_suggestions()
        self._hide_author_suggestions()
        self._hide_category_suggestions()

    def _resolve_author(self, author):
        if isinstance(author, dict):
            return author.get("ad_soyad", "")
        return str(author or "")

    def _resolve_category(self, category):
        if isinstance(category, dict):
            return category.get("ad", "")
        return str(category or "")

    def apply_filter(self, text: str):
        q = (text or "").strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                it = self.table.item(row, col)
                if it and q in it.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def _update_title_suggestions(self, text: str):
        cleaned = (text or "").strip()
        if not cleaned:
            self._hide_title_suggestions()
            return

        norm_input = self._normalize_for_compare(cleaned)
        if not norm_input:
            self._hide_title_suggestions()
            return

        matches = []
        for title in self._all_titles:
            norm_title = self._normalize_for_compare(title)
            if not norm_title or norm_title == norm_input:
                continue

            similarity = self._similarity(norm_input, norm_title)
            if norm_input in norm_title or similarity >= 0.45:
                matches.append((similarity, title))

        if not matches:
            self._hide_title_suggestions()
            return

        matches.sort(key=lambda item: (-item[0], item[1]))
        self.title_suggestion_list.clear()
        for similarity, title in matches[:5]:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, title)
            item.setToolTip(f"Benzerlik: {similarity * 100:.0f}%")
            self.title_suggestion_list.addItem(item)

        self.title_suggestion_list.setCurrentRow(0)
        self.title_suggestion_list.setVisible(True)
        self.input_title.setSuggestionsActive(True)

    def _hide_title_suggestions(self):
        if self.title_suggestion_list.isVisible():
            self.title_suggestion_list.setVisible(False)
        self.title_suggestion_list.clear()
        self.input_title.setSuggestionsActive(False)

    def _on_title_suggestion_clicked(self, item: QListWidgetItem):
        title = item.data(Qt.UserRole) or item.text()
        if not title:
            return
        self._apply_suggestion(title)

    def _on_title_focus_lost(self):
        self._hide_title_suggestions()
        if self._suppress_similarity_check:
            self._suppress_similarity_check = False
            return
        if self._maybe_switch_to_existing_title():
            return
        self._check_title_similarity()

    def _check_title_similarity(self):
        text = (self.input_title.text() or "").strip()
        if not text:
            return

        norm_input = self._normalize_for_compare(text)
        if not norm_input:
            return

        if any(self._normalize_for_compare(title) == norm_input for title in self._all_titles):
            return

        candidates = []
        for title in self._all_titles:
            norm_title = self._normalize_for_compare(title)
            if not norm_title:
                continue
            similarity = self._similarity(norm_input, norm_title)
            if similarity >= 0.7:
                candidates.append((similarity, title))

        if not candidates:
            return

        candidates.sort(key=lambda item: (-item[0], item[1]))
        top_matches = candidates[:3]

        box = QMessageBox(self)
        box.setWindowTitle("Benzer kitap kaydı bulundu")
        suggestions_text = "\n".join(
            f"• {title} ({similarity * 100:.0f}%)" for similarity, title in top_matches
        )
        box.setText(
            "Girdiğiniz başlık mevcut kayıtlarla benzer görünüyor:\n\n"
            f"{suggestions_text}\n\nBu önerilerden birini seçmek ister misiniz?"
        )

        buttons = {}
        for similarity, title in top_matches:
            btn = box.addButton(title, QMessageBox.ActionRole)
            buttons[btn] = title
        skip_btn = box.addButton("Yine de devam", QMessageBox.RejectRole)

        box.exec_()
        clicked = box.clickedButton()
        if clicked in buttons:
            chosen = buttons[clicked]
            self._apply_suggestion(chosen)
        # Kullanıcı "Yine de devam" dediğinde yalnızca uyarıyı kapatıyoruz

    @staticmethod
    def _normalize_for_compare(text: str) -> str:
        if not text:
            return ""
        return " ".join(text.split()).casefold()

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)

        if len(a) < len(b):
            a, b = b, a

        previous = list(range(len(b) + 1))
        for i, char_a in enumerate(a, start=1):
            current = [i]
            for j, char_b in enumerate(b, start=1):
                insert_cost = current[j - 1] + 1
                delete_cost = previous[j] + 1
                replace_cost = previous[j - 1] + (char_a != char_b)
                current.append(min(insert_cost, delete_cost, replace_cost))
            previous = current
        return previous[-1]

    @classmethod
    def _similarity(cls, a: str, b: str) -> float:
        dist = cls._levenshtein(a, b)
        max_len = max(len(a), len(b), 1)
        return 1.0 - (dist / max_len)

    def _navigate_title_suggestions(self, delta: int):
        if not self.title_suggestion_list.isVisible() or self.title_suggestion_list.count() == 0:
            return
        current = self.title_suggestion_list.currentRow()
        current = (current + delta) % self.title_suggestion_list.count()
        self.title_suggestion_list.setCurrentRow(current)

    def _accept_current_suggestion(self):
        if not (self.title_suggestion_list.isVisible() and self.title_suggestion_list.count() > 0):
            self.input_title.returnPressed.emit()
            return
        item = self.title_suggestion_list.currentItem()
        if item:
            self._apply_suggestion(item.data(Qt.UserRole) or item.text())

    def _apply_suggestion(self, title: str):
        if not title:
            return
        self._suppress_similarity_check = True
        self.input_title.setText(title)
        self.input_title.setFocus()
        self._hide_title_suggestions()
        QTimer.singleShot(0, lambda: setattr(self, "_suppress_similarity_check", False))

    def _on_author_text_changed(self, text: str):
        self._selected_author_id = None
        self._update_author_suggestions(text)

    def _on_category_text_changed(self, text: str):
        self._selected_category_id = None
        self._update_category_suggestions(text)

    def _on_author_focus_lost(self):
        self._hide_author_suggestions()
        text = (self.input_author.text() or "").strip()
        if not text:
            self._selected_author_id = None
            return
        match = self._find_author_by_name(text)
        if match:
            self._apply_author_suggestion(match.get("ad_soyad", ""), match)
            return
        normalized = normalize_entity_text(text)
        reply = QMessageBox.question(
            self,
            "Yeni yazar",
            f"'{normalized}' isminde bir yazar bulunamadı. Eklemek ister misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            resp = book_api.create_author(normalized)
            if resp.status_code in (200, 201):
                try:
                    data = resp.json() or {}
                except ValueError:
                    data = {}
                self.load_reference_data()
                author = self._find_author_by_id(data.get("id"))
                self._apply_author_suggestion(author.get("ad_soyad", "") if author else normalized, author)
                return
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Yazar eklenemedi", detail)
        self._apply_author_suggestion("", None)

    def _on_category_focus_lost(self):
        self._hide_category_suggestions()
        text = (self.input_category.text() or "").strip()
        if not text:
            self._selected_category_id = None
            return
        match = self._find_category_by_name(text)
        if match:
            self._apply_category_suggestion(match.get("ad", ""), match)
            return
        QMessageBox.warning(
            self,
            "Kategori bulunamadı",
            "Yalnızca mevcut kategoriler seçilebilir. Lütfen listeden bir değer seçin.",
        )
        self._apply_category_suggestion("", None)

    def _update_author_suggestions(self, text: str):
        cleaned = (text or "").strip()
        matches = []
        if cleaned:
            norm_input = self._normalize_for_compare(cleaned)
            for author in self._authors:
                name = author.get("ad_soyad", "")
                norm_name = self._normalize_for_compare(name)
                if not norm_name or norm_name == norm_input:
                    continue
                similarity = self._similarity(norm_input, norm_name)
                if norm_input in norm_name or similarity >= 0.45:
                    matches.append((similarity, name, author))
        if not matches:
            self._hide_author_suggestions()
            return
        matches.sort(key=lambda item: (-item[0], item[1]))
        self.author_suggestion_list.clear()
        for similarity, name, author in matches[:5]:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, author)
            item.setToolTip(f"Benzerlik: {similarity * 100:.0f}%")
            self.author_suggestion_list.addItem(item)
        self.author_suggestion_list.setCurrentRow(0)
        self.author_suggestion_list.setVisible(True)
        self.input_author.setSuggestionsActive(True)

    def _update_category_suggestions(self, text: str):
        cleaned = (text or "").strip()
        matches = []
        if cleaned:
            norm_input = self._normalize_for_compare(cleaned)
            for category in self._categories:
                name = category.get("ad", "")
                norm_name = self._normalize_for_compare(name)
                if not norm_name:
                    continue
                similarity = self._similarity(norm_input, norm_name)
                if norm_input in norm_name or similarity >= 0.45:
                    matches.append((similarity, name, category))
        if not matches:
            self._hide_category_suggestions()
            return
        matches.sort(key=lambda item: (-item[0], item[1]))
        self.category_suggestion_list.clear()
        for similarity, name, category in matches[:5]:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, category)
            item.setToolTip(f"Benzerlik: {similarity * 100:.0f}%")
            self.category_suggestion_list.addItem(item)
        self.category_suggestion_list.setCurrentRow(0)
        self.category_suggestion_list.setVisible(True)
        self.input_category.setSuggestionsActive(True)

    def _hide_author_suggestions(self):
        if self.author_suggestion_list.isVisible():
            self.author_suggestion_list.setVisible(False)
        self.author_suggestion_list.clear()
        self.input_author.setSuggestionsActive(False)

    def _hide_category_suggestions(self):
        if self.category_suggestion_list.isVisible():
            self.category_suggestion_list.setVisible(False)
        self.category_suggestion_list.clear()
        self.input_category.setSuggestionsActive(False)

    def _navigate_suggestions(self, widget: QListWidget, delta: int):
        if not widget.isVisible() or widget.count() == 0:
            return
        current = widget.currentRow()
        current = (current + delta) % widget.count()
        widget.setCurrentRow(current)

    def _accept_suggestion(self, widget: QListWidget, apply_callback):
        if widget.isVisible() and widget.count() > 0:
            item = widget.currentItem()
            if item:
                apply_callback(item.text(), item.data(Qt.UserRole))

    def _apply_author_suggestion(self, text: str, author=None):
        self.input_author.blockSignals(True)
        self.input_author.setText(text or "")
        self.input_author.blockSignals(False)
        if isinstance(author, dict):
            self._selected_author_id = author.get("id")
        else:
            match = self._find_author_by_name(text)
            self._selected_author_id = match.get("id") if match else None
        self._hide_author_suggestions()

    def _apply_category_suggestion(self, text: str, category=None):
        self.input_category.blockSignals(True)
        self.input_category.setText(text or "")
        self.input_category.blockSignals(False)
        if isinstance(category, dict):
            self._selected_category_id = category.get("id")
        else:
            match = self._find_category_by_name(text)
            self._selected_category_id = match.get("id") if match else None
        self._hide_category_suggestions()

    def _find_author_by_name(self, text: str):
        norm = (text or "").casefold()
        for author in self._authors:
            name = (author.get("ad_soyad") or "").casefold()
            if name == norm:
                return author
        return None

    def _find_author_by_id(self, author_id):
        for author in self._authors:
            if author.get("id") == author_id:
                return author
        return None

    def _find_category_by_name(self, text: str):
        norm = (text or "").casefold()
        for category in self._categories:
            name = (category.get("ad") or "").casefold()
            if name == norm:
                return category
        return None

    def _find_category_by_id(self, category_id):
        for category in self._categories:
            if category.get("id") == category_id:
                return category
        return None

    def _show_category_info(self):
        names = sorted(
            {
                (category.get("ad") or "").strip()
                for category in self._categories
                if category.get("ad")
            }
        )
        if not names:
            QMessageBox.information(self, "Kategoriler", "Tanımlı kategori bulunmuyor.")
            return
        lines = "\n".join(f"• {name}" for name in names)
        QMessageBox.information(self, "Kategoriler", lines)

    # --------------------------- Form ops --------------------------- #
    def _set_mode(self, mode: str):
        if mode not in ("view", "create", "edit"):
            mode = "view"
        if self._mode != mode:
            self._mode = mode
        self._update_action_states()

    def _update_action_states(self):
        editing = self._mode in ("create", "edit")
        has_book = bool(self.current_id)

        for widget in self._form_edit_widgets:
            widget.setEnabled(editing)

        self.btn_save.setEnabled(editing)
        self.btn_cancel_edit.setEnabled(editing)

        self.btn_new.setEnabled(not editing)
        self.btn_edit.setEnabled(not editing and has_book)
        self.btn_delete.setEnabled(not editing and has_book)
        self.btn_manage_copies.setEnabled((self._mode == "edit") and has_book)
        self.btn_print.setEnabled(not editing and has_book)

        self.table.setEnabled(not editing)
        self.search_box.setEnabled(not editing)
        self.toggle_form_button.setEnabled(not editing)
        self.btn_close.setEnabled(not editing)

        serial_visible = self._mode == "create"
        self.chk_serial_entry.setVisible(serial_visible)
        self.chk_serial_entry.setEnabled(serial_visible)
        self.chk_auto_label.setVisible(serial_visible)
        self.chk_auto_label.setEnabled(serial_visible)

    def _focus_widget(self, widget):
        if not widget:
            return
        if widget.isEnabled():
            widget.setFocus(Qt.TabFocusReason)
        else:
            widget.setFocus(Qt.OtherFocusReason)

    def _setup_enter_shortcuts(self):
        def bind_enter(source, target):
            if not source or not hasattr(source, "returnPressed"):
                return
            source.returnPressed.connect(lambda target=target: self._focus_widget(target))

        bind_enter(self.input_title, self.input_author)
        bind_enter(self.input_author, self.input_category)
        bind_enter(self.input_category, self.input_isbn)
        if hasattr(self.input_isbn, "returnPressed"):
            try:
                self.input_isbn.returnPressed.disconnect(self._handle_isbn_enter)
            except Exception:
                pass
            self.input_isbn.returnPressed.connect(self._handle_isbn_enter)

    # --------------------------- Auto label helpers --------------------------- #
    def _set_auto_label_checked(self, value: bool):
        self.chk_auto_label.blockSignals(True)
        self.chk_auto_label.setChecked(bool(value))
        self.chk_auto_label.blockSignals(False)

    def _auto_label_enabled(self) -> bool:
        return self.chk_auto_label.isVisible() and self.chk_auto_label.isChecked()

    def _handle_auto_label_toggle(self, checked: bool):
        if not checked:
            return
        if not self._ensure_label_print_ready(show_warning=True):
            self._set_auto_label_checked(False)

    def _set_default_auto_label(self):
        ready = bool(self._ensure_label_print_ready(show_warning=False))
        self._set_auto_label_checked(ready)

    def _ensure_label_print_ready(self, show_warning: bool = True):
        template_path = get_default_template_path()
        if not template_path:
            if show_warning:
                QMessageBox.warning(
                    self,
                    "Etiket",
                    "Varsayılan etiket şablonu bulunamadı. Lütfen Etiket Editörü'nde şablon seçin."
                )
            return None

        settings = load_settings() or {}
        label_prefs = settings.get("label_editor", {}) or {}
        printing_prefs = settings.get("printing", {}) or {}
        printer_name = (printing_prefs.get("label_printer") or label_prefs.get("default_printer")) or ""

        if not printer_name:
            if show_warning:
                QMessageBox.warning(
                    self,
                    "Etiket",
                    "Varsayılan etiket yazıcısı seçilmemiş. Yazıcı Ayarları sekmesinden bir yazıcı belirleyin."
                )
            return None

        try:
            available = {p.printerName() for p in QPrinterInfo.availablePrinters()}
        except Exception:
            available = set()

        if available and printer_name not in available:
            if show_warning:
                QMessageBox.warning(self, "Etiket", f"'{printer_name}' adlı yazıcı sistemde bulunamadı.")
            return None

        try:
            ensure_printer_ready(printer_name)
            enforce_media_type("label", printer_name, printing_prefs)
        except Exception as exc:
            if show_warning:
                QMessageBox.warning(self, "Etiket", str(exc))
            return None

        return template_path

    def _prompt_initial_copy_plan(self) -> bool:
        context = self._build_print_context()
        wizard = InitialCopyWizard(None, context, parent=self, plan_only=True)
        result = wizard.exec_()
        if result == QDialog.Accepted:
            raw_plan = wizard.planned_shelves() or []
            plan = [str(item or "").strip() for item in raw_plan]
            if plan:
                self._pending_copy_plan = plan
                self.label_copy_count.setText(str(len(plan)))
                return True
            QMessageBox.warning(self, "Nüsha", "En az bir nüsha planlamanız gerekiyor.")
        self._clear_copy_plan()
        self.label_copy_count.setText("0")
        return False

    def _handle_isbn_enter(self):
        if self._mode == "create":
            planned = self._prompt_initial_copy_plan()
            if planned:
                self._focus_widget(self.btn_save)
            else:
                self._focus_widget(self.input_isbn)
            return
        if self.btn_manage_copies.isEnabled():
            self.btn_manage_copies.click()
            return
        self._focus_widget(self.btn_save)

    def _clear_form_fields(self):
        self.input_title.clear()
        self.input_isbn.clear()
        self._clear_copy_plan()
        self._pending_label_contexts = []
        self._selected_author_id = None
        self._selected_category_id = None
        self.input_author.blockSignals(True)
        self.input_author.setText("")
        self.input_author.blockSignals(False)
        self._hide_author_suggestions()
        self.input_category.blockSignals(True)
        self.input_category.setText("")
        self.input_category.blockSignals(False)
        self._hide_category_suggestions()
        self.label_copy_count.setText("0")
        self._hide_title_suggestions()
        self._set_auto_label_checked(False)

    def _clear_copy_plan(self):
        self._pending_copy_plan = []

    def reset_form(self):
        self.current_id = None
        self.table.clearSelection()
        self._clear_form_fields()
        self._set_mode("view")
        self.chk_serial_entry.setChecked(False)
        self._set_auto_label_checked(False)

    def start_new_entry(self):
        self.current_id = None
        self.table.clearSelection()
        self._clear_form_fields()
        self._set_mode("create")
        self._set_default_auto_label()
        self.input_title.setFocus(Qt.TabFocusReason)

    def start_edit_mode(self):
        if not self.current_id:
            QMessageBox.information(self, "Bilgi", "Önce bir kitap seçin.")
            return
        self._set_mode("edit")
        self.input_title.setFocus(Qt.TabFocusReason)

    def cancel_editing(self):
        if self._mode not in ("create", "edit"):
            return
        if self._mode == "create":
            self.reset_form()
            return
        self._set_mode("view")
        if self.table.selectedItems():
            self.on_row_selected()
        else:
            self.reset_form()

    def on_row_selected(self):
        items = self.table.selectedItems()
        if not items:
            self.current_id = None
            self._update_action_states()
            return
        if self._mode in ("create", "edit"):
            return
        data = items[0].data(Qt.UserRole) or {}
        self.current_id = data.get("id")
        title_text = data.get("baslik", "")
        self.input_title.blockSignals(True)
        self.input_title.setText(title_text)
        self.input_title.blockSignals(False)
        self._hide_title_suggestions()
        self.input_isbn.setText(data.get("isbn", "") or "")

        # author/category
        self._set_author_from_record(data.get("yazar"))
        self._set_category_from_record(data.get("kategori"))

        # copies
        copies = data.get("nusha_sayisi")
        if copies is None and self.current_id:
            copies = len(book_api.list_copies_for_book(self.current_id))
        self.label_copy_count.setText(str(copies or 0))
        self._update_action_states()

    def _set_author_from_record(self, value):
        if isinstance(value, dict):
            self._apply_author_suggestion(value.get("ad_soyad", ""), value)
        elif value:
            match = self._find_author_by_name(value)
            if match:
                self._apply_author_suggestion(match.get("ad_soyad", ""), match)
            else:
                self._apply_author_suggestion(str(value), None)
                self._selected_author_id = None
        else:
            self._apply_author_suggestion("", None)

    def _set_category_from_record(self, value):
        if isinstance(value, dict):
            self._apply_category_suggestion(value.get("ad", ""), value)
        elif value:
            match = self._find_category_by_name(value)
            if match:
                self._apply_category_suggestion(match.get("ad", ""), match)
            else:
                self._apply_category_suggestion(str(value), None)
                self._selected_category_id = None
        else:
            self._apply_category_suggestion("", None)

    def _collect_payload(self):
        raw_title = (self.input_title.text() or "").strip()
        title = normalize_entity_text(raw_title) if self.chk_titlecase.isChecked() else raw_title
        isbn = self.input_isbn.text().replace("-", "").strip()
        author_id = self._selected_author_id
        category_id = self._selected_category_id

        if not title:
            QMessageBox.warning(self, "Uyarı", "Başlık boş olamaz.")
            self._focus_widget(self.input_title)
            return None
        if not self.current_id and self._has_duplicate_title(title):
            self._handle_duplicate_title(title)
            return None
        if isbn and not ISBN_PATTERN.fullmatch(isbn):
            QMessageBox.warning(self, "Uyarı", "ISBN 10 ya da 13 hane olmalıdır (rakam/X).")
            self._focus_widget(self.input_isbn)
            return None
        if (self.input_category.text() or "").strip() and self._selected_category_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden geçerli bir kategori seçin.")
            self._focus_widget(self.input_category)
            return None

        payload = {
            "baslik": title,
            "isbn": isbn or None,
            "yazar_id": author_id,
            "kategori_id": category_id,
        }
        return payload

    def _has_duplicate_title(self, title: str) -> bool:
        norm = self._normalize_for_compare(title)
        if not norm:
            return False
        matches = [bk for bk in self._title_index.get(norm, []) if bk.get("id") != self.current_id]
        self._pending_duplicate_matches = matches
        return bool(matches)

    def _handle_duplicate_title(self, title: str):
        matches = getattr(self, "_pending_duplicate_matches", None)
        if matches is None:
            norm = self._normalize_for_compare(title)
            matches = [bk for bk in self._title_index.get(norm, []) if bk.get("id") != self.current_id]
        if not matches:
            QMessageBox.warning(
                self,
                "Kitap zaten mevcut",
                "Bu başlıkla kayıtlı bir kitap bulundu ancak detaylarına erişilemedi."
            )
            return

        book = matches[0]
        self._prompt_existing_book_switch(book, title)
        self._pending_duplicate_matches = []
        return True

    def _maybe_switch_to_existing_title(self, explicit_title: str | None = None) -> bool:
        if self._mode != "create":
            return False
        text = (explicit_title or self.input_title.text() or "").strip()
        if not text:
            return False
        norm = self._normalize_for_compare(text)
        if not norm:
            return False
        matches = [bk for bk in self._title_index.get(norm, []) if bk.get("id")]
        if not matches:
            return False
        self._prompt_existing_book_switch(matches[0], text)
        return True

    def _prompt_existing_book_switch(self, book: Dict, typed_title: str) -> bool:
        if not book:
            return False
        book_title = book.get("baslik") or typed_title
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Kitap zaten kayıtlı")
        msg.setText(
            f"'{book_title}' başlıklı bir kitap zaten kayıtlı.\n"
            "Yeni kayıt oluşturmak yerine bu kitap düzenleme modunda açılacak ve nüsha ekleme penceresi gösterilecek."
        )
        btn_open = msg.addButton("Nüsha ekle", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("İptal", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_open)
        msg.exec_()
        if msg.clickedButton() == btn_open:
            self._switch_to_existing_book(book)
        else:
            self.input_title.clear()
            self._focus_widget(self.input_title)
        return True

    def _switch_to_existing_book(self, book: Dict):
        book_id = book.get("id") if isinstance(book, dict) else None
        if not book_id:
            QMessageBox.warning(self, "Uyarı", "Mevcut kitap kaydı bulunamadı.")
            return
        self.chk_serial_entry.setChecked(False)
        self._set_mode("view")
        found = self._select_book_in_table(book_id)
        if not found:
            self.load_books()
            found = self._select_book_in_table(book_id)
        if not found:
            QMessageBox.warning(self, "Uyarı", "Kitap listede bulunamadı.")
            return
        self.on_row_selected()
        self.start_edit_mode()
        QTimer.singleShot(0, lambda: self._open_copies_dialog_for_book(book, select_in_table=True))

    def save_book(self):
        if self._mode not in ("create", "edit"):
            QMessageBox.information(self, "Bilgi", "Kaydetmek için önce Yeni veya Düzenle ile düzenleme moduna geçin.")
            return
        data = self._collect_payload()
        if data is None:
            return
        creating = not bool(self.current_id)
        if creating and not self._pending_copy_plan:
            if not self._prompt_initial_copy_plan():
                QMessageBox.information(self, "Nüsha", "Kaydetmeden önce nüsha planı oluşturmanız gerekiyor.")
                self._focus_widget(self.input_isbn)
                return
        serial_loop = creating and self.chk_serial_entry.isChecked()
        auto_label = creating and self._auto_label_enabled()
        if creating:
            resp = book_api.create_book(data)
            ok = resp.status_code in (200, 201)
        else:
            resp = book_api.update_book(self.current_id, data)
            ok = resp.status_code in (200, 202)
        if ok:
            if creating:
                created = {}
                try:
                    created = resp.json() or {}
                except Exception:
                    created = {}
                book_id = created.get("id")
                if not book_id:
                    QMessageBox.warning(self, "Uyarı", "Kitap oluşturuldu ancak kimlik alınamadı. Lütfen listeyi yenileyin.")
                    self.load_books()
                    self.reset_form()
                    return
                context = self._build_print_context(created)
                copies, errors = self._create_initial_copies_for_plan(book_id)
                if errors:
                    detail = "\n".join(f"- {err}" for err in errors if err)
                    QMessageBox.warning(self, "Nüsha", f"Bazı nüshalar eklenemedi:\n{detail}")
                if not copies:
                    book_api.delete_book(book_id)
                    QMessageBox.information(self, "İptal", "Nüsha eklenmediği için kitap kaydı iptal edildi.")
                    self._clear_copy_plan()
                    return
                QMessageBox.information(self, "Nüsha", f"{len(copies)} nüsha oluşturuldu.")
                self._offer_initial_copy_print(context, copies, force_auto=auto_label)
            QMessageBox.information(self, "Başarılı", "Kitap kaydedildi.")
            self.load_books()
            if not creating and self._pending_label_contexts:
                self._flush_label_print_queue()
            self._clear_copy_plan()
            if serial_loop:
                self.start_new_entry()
                self.chk_serial_entry.setChecked(True)
            else:
                self.reset_form()
        else:
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Kitap kaydedilemedi.\n\nDetay: {detail}")

    def _generate_barcode(self, book_id: int) -> str:
        # Zaman damgası + kısa rastgele ek
        ts = datetime.now().strftime("%y%m%d%H%M%S")
        rnd = f"{random.randint(0, 999):03d}"
        return f"BK-{book_id}-{ts}{rnd}"

    def delete_book(self):
        if not self.current_id:
            QMessageBox.warning(self, "Uyarı", "Silmek için bir kitap seçin.")
            return
        if not self._ask_yes_no("Silme Onayı", "Bu kitabı kalıcı olarak silmek istediğinize emin misiniz?"):
            return
        resp = book_api.delete_book(self.current_id)
        if resp.status_code in (200, 204):
            QMessageBox.information(self, "Başarılı", "Kitap silindi.")
            self.load_books()
            self.reset_form()
        else:
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Kitap silinemedi.\n\nDetay: {detail}")

    # ------------------------ Printing ------------------------------- #
    def print_labels(self):
        items = self.table.selectedItems()
        if not items:
            QMessageBox.information(self, "Bilgi", "Önce bir kitap seçin.")
            return
        data = items[0].data(Qt.UserRole) or {}
        book_id = data.get("id")
        if not book_id:
            QMessageBox.warning(self, "Hata", "Seçili kitap verisi eksik.")
            return
        title = data.get("baslik", "")
        author = ""
        ya = data.get("yazar")
        if isinstance(ya, dict):
            author = ya.get("ad_soyad", "")
        category = ""
        ka = data.get("kategori")
        if isinstance(ka, dict):
            category = ka.get("ad", "")

        copies = book_api.list_copies_for_book(book_id) or []
        if not copies:
            QMessageBox.information(self, "Bilgi", "Bu kitap için nüsha bulunamadı.")
            return
        dlg = LabelPrintDialog(copies, self)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setResult(QDialog.Rejected)  # her açılışta temiz başlangıç
        if dlg.exec_() != QDialog.Accepted:
            return
        selected = dlg.selected_copies()
        if not selected:
            return

        template_path = get_default_template_path()
        if not template_path:
            QMessageBox.warning(self, "Etiket", "Varsayılan etiket şablonu bulunamadı. Lütfen Etiket Editörü'nde şablon seçin.")
            return

        contexts = []
        isbn = str(data.get("isbn", "") or "")
        for cp in selected:
            barkod_text = str(cp.get("barkod", "") or "")
            shelf = str(cp.get("raf_kodu", "") or "")
            ctx = {
                "title": title,
                "author": author,
                "category": category,
                "barcode": barkod_text,
                "isbn": isbn,
                "shelf_code": shelf,
            }
            contexts.append(ctx)

        if not contexts:
            return

        try:
            print_label_batch(template_path, contexts)
        except Exception as exc:
            QMessageBox.warning(self, "Etiket", f"Etiketler yazdırılamadı:\n{exc}")
            return

        QMessageBox.information(self, "Etiket", f"{len(contexts)} etiket yazıcıya gönderildi.")

    def _ask_yes_no(self, title, text) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        yes = box.addButton("Evet", QMessageBox.YesRole)
        no = box.addButton("Vazgeç", QMessageBox.NoRole)
        box.setDefaultButton(no)
        box.exec_()
        return box.clickedButton() == yes

    def _build_print_context(self, data=None):
        data = data or {}
        title = str(data.get("baslik", "") or self.input_title.text().strip())
        author = self._resolve_author(data.get("yazar"))
        if not author:
            if self._selected_author_id:
                author_obj = self._find_author_by_id(self._selected_author_id)
                author = author_obj.get("ad_soyad", "") if author_obj else ""
            if not author:
                author = self.input_author.text().strip()
        category = self._resolve_category(data.get("kategori"))
        if not category:
            if self._selected_category_id:
                cat_obj = self._find_category_by_id(self._selected_category_id)
                category = cat_obj.get("ad", "") if cat_obj else ""
            if not category:
                category = self.input_category.text().strip()
        isbn = str(data.get("isbn", "") or self.input_isbn.text().strip())
        return {
            "title": title or "",
            "author": author or "",
            "category": category or "",
            "isbn": isbn or "",
            "barcode": "",
            "shelf_code": "",
        }

    def _create_initial_copies_for_plan(self, book_id: int):
        plan = list(self._pending_copy_plan or [])
        created = []
        errors = []
        for shelf in plan:
            resp = book_api.create_copy(book_id, "", shelf or None)
            if resp.status_code in (200, 201):
                try:
                    data = resp.json() or {}
                except Exception:
                    data = {}
                if shelf and not data.get("raf_kodu"):
                    data["raf_kodu"] = shelf
                created.append(data)
            else:
                errors.append(book_api.extract_error(resp))
        return created, errors

    def _compose_label_contexts(self, base_context, copies):
        contexts = []
        if not copies:
            return contexts
        title = base_context.get("title", "")
        author = base_context.get("author", "")
        category = base_context.get("category", "")
        isbn = base_context.get("isbn", "")
        for cp in copies:
            contexts.append(
                {
                    "title": title,
                    "author": author,
                    "category": category,
                    "isbn": isbn,
                    "barcode": str(cp.get("barkod", "") or ""),
                    "shelf_code": str(cp.get("raf_kodu", "") or ""),
                }
            )
        return contexts

    def _offer_initial_copy_print(self, context, copies, force_auto: bool = False):
        if not copies:
            return
        auto = force_auto or self._auto_label_enabled()
        template_path = self._ensure_label_print_ready(show_warning=not auto)
        if not template_path:
            return
        contexts = self._compose_label_contexts(context, copies)
        if not contexts:
            return
        if not auto:
            reply = QMessageBox.question(
                self,
                "Etiket Yazdır",
                "Yeni eklenen nüshalar için barkod yazdırmak ister misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return
        try:
            print_label_batch(template_path, contexts)
            QMessageBox.information(self, "Etiket", f"{len(contexts)} etiket yazıcıya gönderildi.")
        except Exception as exc:
            QMessageBox.warning(self, "Etiket", f"Etiketler yazdırılamadı:\n{exc}")

    def _queue_label_prints(self, contexts):
        if not contexts:
            return
        self._pending_label_contexts.extend(contexts)

    def _flush_label_print_queue(self):
        if not self._pending_label_contexts:
            return
        template_path = get_default_template_path()
        if not template_path:
            QMessageBox.warning(
                self,
                "Etiket",
                "Varsayılan etiket şablonu bulunamadı. Lütfen Etiket Editörü'nde şablon seçin."
            )
            self._pending_label_contexts = []
            return
        reply = QMessageBox.question(
            self,
            "Etiket Yazdır",
            "Nüsha yönetimi sırasında eklenen yeni barkodları yazdırmak ister misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            self._pending_label_contexts = []
            return
        try:
            print_label_batch(template_path, self._pending_label_contexts)
            QMessageBox.information(self, "Etiket", f"{len(self._pending_label_contexts)} etiket yazıcıya gönderildi.")
        except Exception as exc:
            QMessageBox.warning(self, "Etiket", f"Etiketler yazdırılamadı:\n{exc}")
        finally:
            self._pending_label_contexts = []


    # ------------------------ Copies management ----------------------- #
    def open_copies_dialog(self):
        if not self.current_id:
            QMessageBox.information(self, "Bilgi", "Önce bir kitap seçin veya kaydedin.")
            return
        book = self._book_index.get(self.current_id)
        if not book:
            QMessageBox.warning(self, "Uyarı", "Seçilen kitabın bilgileri bulunamadı. Listeyi yenilemeyi deneyin.")
            return
        self._open_copies_dialog_for_book(book, select_in_table=False)

    def add_author_quick(self):
        dlg = AuthorManagerDialog(self)
        dlg.exec_()
        self.load_reference_data()

    def add_category_quick(self):
        dlg = CategoryManagerDialog(self)
        dlg.exec_()
        self.load_reference_data()

    def _open_copies_dialog_for_book(self, book, select_in_table=False):
        book_id = book.get("id")
        if not book_id:
            QMessageBox.warning(self, "Uyarı", "Kitap kimliği bulunamadı. İşlem iptal edildi.")
            return

        context = self._build_print_context(book)
        dlg = CopiesManagerDialog(book_id, context, self)
        result = dlg.exec_()
        if result == QDialog.Accepted and dlg.new_copies:
            contexts = self._compose_label_contexts(context, dlg.new_copies)
            self._queue_label_prints(contexts)

        if self.current_id == book_id:
            count = len(book_api.list_copies_for_book(book_id))
            self.label_copy_count.setText(str(count))

        self.load_books()
        self._select_book_in_table(book_id)
        if select_in_table or self.current_id == book_id:
            self.current_id = book_id

    def _select_book_in_table(self, book_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            data = item.data(Qt.UserRole) if item else None
            if data and data.get("id") == book_id:
                self.table.setCurrentCell(row, 0)
                self.table.selectRow(row)
                return True
        return False

    def eventFilter(self, source, event):
        if source is self.btn_save and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.btn_save.isEnabled():
                    self.btn_save.click()
                return True
        return super().eventFilter(source, event)


class CopiesManagerDialog(QDialog):
    def __init__(self, book_id, context, parent=None):
        super().__init__(parent)
        self.book_id = book_id
        self.parent_context = context or {}
        self.new_copies: List[Dict] = []
        self._last_shelf = ""
        self._shelf_model = QStringListModel()
        self._shelf_values: Set[str] = set()
        self._row_ids: List[int] = []
        self._row_meta: Dict[int, Dict] = {}
        self._original_data: Dict[int, Dict] = {}
        self._session_new_ids: Set[int] = set()
        self._session_deleted_ids: Set[int] = set()
        self.setWindowTitle("Nüsha Yönetimi")
        self.resize(480, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Üst: ekle butonu
        top = QHBoxLayout()
        self.input_shelf = QLineEdit()
        self.input_shelf.setPlaceholderText("Raf kodu (opsiyonel)")
        self._shelf_completer = QCompleter(self._shelf_model, self)
        self._shelf_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._shelf_completer.setFilterMode(Qt.MatchContains)
        self.input_shelf.setCompleter(self._shelf_completer)
        self.input_barcode = QLineEdit()
        self.input_barcode.setPlaceholderText("Barkod (otomatik)")
        self.input_barcode.setMaxLength(50)
        self.input_barcode.setReadOnly(True)
        self.input_barcode.setFocusPolicy(Qt.NoFocus)
        btn_add = QPushButton("Nüsha Ekle")
        btn_add.clicked.connect(self.add_copy)
        top.addWidget(self.input_barcode, 1)
        top.addWidget(self.input_shelf, 1)
        top.addWidget(btn_add)
        layout.addLayout(top)

        # Tablo
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Barkod", "Raf", "İşlem"])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        # Alt butonlar
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

        self.load_copies()
        self._prepare_next_barcode()

    def load_copies(self):
        data = book_api.list_copies_for_book(self.book_id) or []
        self.table.setRowCount(len(data))
        self._row_ids = [None] * len(data)
        self._row_meta = {}
        self._original_data = {}
        self._session_new_ids.clear()
        self._session_deleted_ids.clear()
        shelves = []
        for i, cp in enumerate(data):
            self._populate_row(i, cp, state="existing")
            raf = str(cp.get("raf_kodu", "") or "")
            if raf:
                shelves.append(raf)
        if shelves:
            self._last_shelf = shelves[-1]
        elif not shelves and not self.new_copies:
            self._last_shelf = ""
        self._shelf_values = set(shelves)
        self._shelf_model.setStringList(sorted(self._shelf_values))
        return data

    def _populate_row(self, row: int, copy_data: Dict, state: str = "existing"):
        barkod = str(copy_data.get("barkod", "") or "")
        raf = str(copy_data.get("raf_kodu", "") or "")
        barkod_item = QTableWidgetItem(barkod)
        barkod_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        barkod_item.setData(Qt.UserRole, copy_data.get("id"))
        raf_item = QTableWidgetItem(raf)
        raf_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table.setItem(row, 0, barkod_item)
        self.table.setItem(row, 1, raf_item)
        self._register_row_meta(row, copy_data, state)
        self._render_action_cell(row, copy_data.get("id"), state)
        self._apply_row_style(row, state)

    def _register_row_meta(self, row: int, copy_data: Dict, state: str):
        copy_id = copy_data.get("id")
        while len(self._row_ids) <= row:
            self._row_ids.append(None)
        self._row_ids[row] = copy_id
        if copy_id is not None:
            meta = self._row_meta.get(copy_id, {})
            meta["data"] = copy_data
            meta["state"] = state
            self._row_meta[copy_id] = meta
            if copy_id not in self._original_data:
                self._original_data[copy_id] = dict(copy_data)

    def _state_for_copy(self, copy_id) -> str:
        meta = self._row_meta.get(copy_id)
        if not meta:
            return "existing"
        return meta.get("state", "existing")

    def _apply_row_style(self, row: int, state: str):
        color_map = {
            "existing": QColor("#86efac"),  # canlı yeşil
            "new": QColor("#fef08a"),       # açık sarı
            "deleted": QColor("#d1d5db"),   # gri
        }
        color = color_map.get(state, QColor("white"))
        for col in range(2):
            item = self.table.item(row, col)
            if item:
                item.setBackground(color)

    def _render_action_cell(self, row: int, copy_id, state: str):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        if state == "deleted":
            btn = QPushButton("Geri Al")
            btn.setObjectName("DialogPositiveButton")
            btn.clicked.connect(lambda _, cid=copy_id: self.undo_delete_copy(cid))
            btn.setStyleSheet("background-color: #bfdbfe; color: #1e3a8a;")
        else:
            btn = QPushButton("Sil")
            btn.setObjectName("DialogNegativeButton")
            btn.clicked.connect(lambda _, cid=copy_id: self.delete_copy(cid))
            btn.setStyleSheet("background-color: #fda4af; color: #7f1d1d;")
        btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout.addWidget(btn)
        self.table.setCellWidget(row, 2, widget)

    def _append_copy(self, copy_data: Dict, state: str = "existing"):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._populate_row(row, copy_data, state)
        shelf = str(copy_data.get("raf_kodu", "") or "")
        if shelf:
            if shelf not in self._shelf_values:
                self._shelf_values.add(shelf)
                self._shelf_model.setStringList(sorted(self._shelf_values))
            self._last_shelf = shelf

    def _find_row_by_copy_id(self, copy_id) -> int:
        for idx, cid in enumerate(self._row_ids):
            if cid == copy_id:
                return idx
        return -1

    def _remove_row(self, copy_id):
        row = self._find_row_by_copy_id(copy_id)
        if row == -1:
            return
        self.table.removeRow(row)
        if 0 <= row < len(self._row_ids):
            self._row_ids.pop(row)
        self._row_meta.pop(copy_id, None)

    def _mark_row_deleted(self, copy_id):
        row = self._find_row_by_copy_id(copy_id)
        if row == -1:
            return
        meta = self._row_meta.get(copy_id, {})
        data = meta.get("data") or {}
        meta["state"] = "deleted"
        self._row_meta[copy_id] = meta
        self._populate_row(row, data, state="deleted")

    def _update_new_copy_records(self, copy_id):
        if not self.new_copies:
            return
        self.new_copies = [cp for cp in self.new_copies if cp.get("id") != copy_id]
        if copy_id in self._session_new_ids:
            self._session_new_ids.discard(copy_id)

    def add_copy(self):
        barkod = (self.input_barcode.text() or "").strip()
        shelf = self.input_shelf.text().strip() or None
        # Barkod boşsa sunucu otomatik üretecek
        resp = book_api.create_copy(self.book_id, barkod, shelf)
        if resp.status_code in (200, 201):
            self.input_shelf.clear()
            created = None
            try:
                created = resp.json() or {}
            except Exception:
                created = None
            self._prepare_next_barcode()
            if not created:
                snapshot = book_api.list_copies_for_book(self.book_id) or []
                for cp in snapshot:
                    cid = cp.get("id")
                    if cid and cid not in self._row_meta:
                        created = cp
                        break
            if created:
                if shelf and not created.get("raf_kodu"):
                    created["raf_kodu"] = shelf
                created.setdefault("barkod", barkod or "")
                self.new_copies.append(created)
                cid = created.get("id")
                if cid:
                    self._session_new_ids.add(cid)
                self._append_copy(created, state="new")
                if shelf:
                    self._last_shelf = shelf
                    if shelf not in self._shelf_values:
                        self._shelf_values.add(shelf)
                        self._shelf_model.setStringList(sorted(self._shelf_values))
            else:
                QMessageBox.warning(self, "Hata", "Sunucudan nüsha bilgisi alınamadı.")
        else:
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Nüsha eklenemedi.\n\nDetay: {detail}")

    def delete_copy(self, copy_id):
        if not copy_id:
            return
        state = self._state_for_copy(copy_id)
        if QMessageBox.question(self, "Onay", "Bu nüshayı silmek istiyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        resp = book_api.delete_copy(copy_id)
        if resp.status_code in (200, 204):
            if state == "new":
                self._remove_row(copy_id)
                self._update_new_copy_records(copy_id)
            else:
                self._session_deleted_ids.add(copy_id)
                self._mark_row_deleted(copy_id)
        else:
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Nüsha silinemedi.\n\nDetay: {detail}")

    def undo_delete_copy(self, copy_id):
        if not copy_id:
            return
        meta = self._row_meta.get(copy_id)
        if not meta:
            return
        data = meta.get("data") or {}
        barkod = data.get("barkod", "")
        shelf = data.get("raf_kodu") or None
        resp = book_api.create_copy(self.book_id, barkod, shelf)
        if resp.status_code not in (200, 201):
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Nüsha geri alınamadı.\n\nDetay: {detail}")
            return
        try:
            created = resp.json() or {}
        except Exception:
            created = {}
        if shelf and not created.get("raf_kodu"):
            created["raf_kodu"] = shelf
        self._session_deleted_ids.discard(copy_id)
        row = self._find_row_by_copy_id(copy_id)
        self._row_meta.pop(copy_id, None)
        if row != -1:
            self.table.removeRow(row)
            if 0 <= row < len(self._row_ids):
                self._row_ids.pop(row)
            self.table.insertRow(row)
            self._row_ids.insert(row, None)
            self._populate_row(row, created, state="existing")
        else:
            self._append_copy(created, state="existing")

    def _rollback_changes(self) -> bool:
        errors = []
        for cid in list(self._session_new_ids):
            resp = book_api.delete_copy(cid)
            if resp.status_code not in (200, 204):
                detail = book_api.extract_error(resp)
                errors.append(f"Yeni nüsha silinemedi (ID {cid}): {detail}")
            else:
                self._session_new_ids.discard(cid)
                self._update_new_copy_records(cid)
        for cid in list(self._session_deleted_ids):
            data = self._original_data.get(cid) or ((self._row_meta.get(cid) or {}).get("data") or {})
            barkod = data.get("barkod", "")
            shelf = data.get("raf_kodu") or None
            resp = book_api.create_copy(self.book_id, barkod, shelf)
            if resp.status_code not in (200, 201):
                detail = book_api.extract_error(resp)
                errors.append(f"Nüsha geri alınamadı (ID {cid}): {detail}")
            else:
                self._session_deleted_ids.discard(cid)
        if errors:
            QMessageBox.warning(
                self,
                "Nüsha",
                "Aşağıdaki değişiklikler geri alınamadı:\n\n" + "\n".join(errors)
            )
            return False
        self.new_copies = []
        return True

    def accept(self):
        self._session_new_ids.clear()
        self._session_deleted_ids.clear()
        super().accept()

    def reject(self):
        if self._session_new_ids or self._session_deleted_ids:
            if not self._rollback_changes():
                return
        else:
            self.new_copies = []
        super().reject()
    # --- Helpers ---
    def _prepare_next_barcode(self):
        try:
            code = book_api.get_next_barcode(prefix="KIT", width=6)
            self.input_barcode.setText(code)
        except Exception:
            self.input_barcode.setText("")
        if getattr(self, "_last_shelf", ""):
            self.input_shelf.setText(self._last_shelf)
        else:
            self.input_shelf.clear()


class InitialCopyWizard(QDialog):
    def __init__(self, book_id, context, parent=None, plan_only=False):
        super().__init__(parent)
        self.book_id = book_id
        self.context = context or {}
        self.created_copies: List[Dict] = []
        self.plan_only = bool(plan_only)
        self._planned_shelves: List[str] = []
        self.setWindowTitle("Nüsha Oluştur" if not self.plan_only else "Nüsha Planı")
        # Daha kompakt; minimum değer de tanımla
        self.resize(400, 360)
        self.setMinimumSize(360, 320)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        config_page = QWidget()
        config_layout = QVBoxLayout(config_page)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(8)

        info_text = (
            "Bu kitap için oluşturulacak nüshaları planlayın ve raf kodlarını girin.\n"
            "En az bir nüsha tanımlamanız zorunludur."
            if self.plan_only
            else
            "Bu kitap için oluşturulacak nüsha sayısını ve raf kodlarını girin.\n"
            "En az bir nüsha oluşturmanız zorunludur."
        )
        info = QLabel(info_text)
        info.setWordWrap(True)
        config_layout.addWidget(info)

        spin_row = QHBoxLayout()
        spin_row.addWidget(QLabel("Nüsha sayısı:"))
        self.spin_count = QSpinBox()
        self.spin_count.setMinimum(1)
        self.spin_count.setMaximum(100)
        self.spin_count.setValue(1)
        self.spin_count.valueChanged.connect(self._sync_copy_rows)
        spin_row.addWidget(self.spin_count, 0)
        spin_row.addStretch(1)
        config_layout.addLayout(spin_row)

        self.copy_table = QTableWidget(1, 1)
        self.copy_table.setHorizontalHeaderLabels(["Raf Kodu (opsiyonel)"])
        header = self.copy_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self._last_shelf_value = ""
        self.copy_table.itemChanged.connect(self._remember_last_shelf)
        self._set_row_default(0)
        config_layout.addWidget(self.copy_table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_cancel = QPushButton("İptal")
        self.btn_create = QPushButton("Nüshaları Oluştur")
        self.btn_cancel.setObjectName("DialogNegativeButton")
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.setDefault(False)
        self.btn_create.setObjectName("DialogPositiveButton")
        self.btn_create.setAutoDefault(True)
        self.btn_create.setDefault(True)
        if self.plan_only:
            self.btn_create.setText("Planı Kaydet")
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_create)
        config_layout.addLayout(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_create.clicked.connect(self._create_copies)

        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(8)

        self.summary_label = QLabel("")
        summary_layout.addWidget(self.summary_label)

        self.summary_table = QTableWidget(0, 2)
        self.summary_table.setHorizontalHeaderLabels(["Barkod", "Raf"])
        header = self.summary_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        summary_layout.addWidget(self.summary_table, 1)

        summary_btn_row = QHBoxLayout()
        summary_btn_row.addStretch(1)
        self.btn_print = QPushButton("Etiket Yazdır")
        self.btn_finish = QPushButton("Bitti")
        self.btn_print.setAutoDefault(False)
        self.btn_print.setDefault(False)
        self.btn_finish.setObjectName("DialogPositiveButton")
        self.btn_finish.setAutoDefault(True)
        self.btn_finish.setDefault(False)
        summary_btn_row.addWidget(self.btn_print)
        summary_btn_row.addWidget(self.btn_finish)
        summary_layout.addLayout(summary_btn_row)

        self.btn_print.clicked.connect(self._print_labels)
        self.btn_finish.clicked.connect(self.accept)

        self.stack.addWidget(config_page)
        self.stack.addWidget(summary_page)
        self.stack.setCurrentIndex(0)
        if self.plan_only:
            self.btn_print.setVisible(False)
            QTimer.singleShot(0, self._focus_plan_entry)
        else:
            QTimer.singleShot(0, lambda: self.spin_count.setFocus(Qt.TabFocusReason))

    def _sync_copy_rows(self, count):
        current = self.copy_table.rowCount()
        if count > current:
            for _ in range(count - current):
                row = self.copy_table.rowCount()
                self.copy_table.insertRow(row)
                self._set_row_default(row)
        elif count < current:
            for _ in range(current - count):
                self.copy_table.removeRow(self.copy_table.rowCount() - 1)

    def _set_row_default(self, row):
        value = self._last_shelf_value or ""
        item = QTableWidgetItem(value)
        self.copy_table.setItem(row, 0, item)

    def _remember_last_shelf(self, item):
        if item and item.column() == 0:
            text = item.text().strip()
            if text:
                self._last_shelf_value = text

    def _focus_plan_entry(self):
        if not self.plan_only:
            return
        if self.copy_table.rowCount() == 0:
            self.copy_table.insertRow(0)
            self._set_row_default(0)
        self.copy_table.setCurrentCell(0, 0)
        item = self.copy_table.item(0, 0)
        if item is None:
            item = QTableWidgetItem("")
            self.copy_table.setItem(0, 0, item)
        self.copy_table.setFocus(Qt.TabFocusReason)
        QTimer.singleShot(0, lambda: self.copy_table.editItem(item))

    def _create_copies(self):
        count = self.spin_count.value()
        shelves = []
        for row in range(count):
            item = self.copy_table.item(row, 0)
            shelves.append((item.text().strip() if item else "") or None)

        if self.plan_only:
            self._planned_shelves = [shelf or "" for shelf in shelves]
            if not self._planned_shelves:
                QMessageBox.warning(self, "Nüsha", "En az bir nüsha planlamanız gerekiyor.")
                return
            self.created_copies = [{"barkod": "", "raf_kodu": shelf} for shelf in self._planned_shelves]
            self.accept()
            return

        self.btn_create.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        copies = []
        for shelf in shelves:
            resp = book_api.create_copy(self.book_id, "", shelf)
            if resp.status_code not in (200, 201):
                detail = book_api.extract_error(resp)
                QMessageBox.warning(self, "Hata", f"Nüsha oluşturulamadı.\n\nDetay: {detail}")
                self.btn_create.setEnabled(True)
                self.btn_cancel.setEnabled(True)
                return
            try:
                data = resp.json() or {}
            except Exception:
                data = {}
            data.setdefault("raf_kodu", shelf or "")
            copies.append(data)

        if not copies:
            QMessageBox.warning(self, "Hata", "Nüsha oluşturulamadı.")
            self.btn_create.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            return

        self.created_copies = copies
        self._populate_summary()
        self.stack.setCurrentIndex(1)
        self.btn_finish.setDefault(True)
        self.btn_create.setDefault(False)

    def _populate_summary(self):
        self.summary_table.setRowCount(len(self.created_copies))
        for row, cp in enumerate(self.created_copies):
            self.summary_table.setItem(row, 0, QTableWidgetItem(str(cp.get("barkod") or "")))
            self.summary_table.setItem(row, 1, QTableWidgetItem(str(cp.get("raf_kodu") or "")))
        self.summary_label.setText(f"{len(self.created_copies)} nüsha oluşturuldu.")

    def _print_labels(self):
        if not self.created_copies:
            return
        template_path = get_default_template_path()
        if not template_path:
            QMessageBox.warning(self, "Etiket", "Varsayılan etiket şablonu bulunamadı. Etiket Editörü'nden seçin.")
            return
        contexts = []
        title = self.context.get("title", "")
        author = self.context.get("author", "")
        category = self.context.get("category", "")
        isbn = self.context.get("isbn", "")
        for cp in self.created_copies:
            contexts.append(
                {
                    "title": title,
                    "author": author,
                    "category": category,
                    "isbn": isbn,
                    "barcode": cp.get("barkod", ""),
                    "shelf_code": cp.get("raf_kodu", ""),
                }
            )
        try:
            print_label_batch(template_path, contexts)
        except Exception as exc:
            QMessageBox.warning(self, "Etiket", f"Etiketler yazdırılamadı:\n{exc}")
            return
        QMessageBox.information(self, "Etiket", f"{len(contexts)} etiket yazıcıya gönderildi.")

    def keyPressEvent(self, event):
        if self.stack.currentIndex() == 0:
            key = event.key()
            if self.plan_only and key in (Qt.Key_Left, Qt.Key_Right):
                if key == Qt.Key_Left and self.btn_create.hasFocus():
                    self.btn_cancel.setFocus(Qt.TabFocusReason)
                    event.accept()
                    return
                if key == Qt.Key_Right and self.btn_cancel.hasFocus():
                    self.btn_create.setFocus(Qt.TabFocusReason)
                    event.accept()
                    return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if self.copy_table.state() == QAbstractItemView.EditingState:
                    super().keyPressEvent(event)
                    return
                if self.plan_only and not self.btn_create.hasFocus():
                    self.btn_create.setFocus(Qt.TabFocusReason)
                    event.accept()
                    return
                if self.btn_create.isEnabled():
                    self.btn_create.click()
                    event.accept()
                    return
            if key in (Qt.Key_Up, Qt.Key_Down):
                delta = 1 if key == Qt.Key_Up else -1
                new_value = max(
                    self.spin_count.minimum(),
                    min(self.spin_count.maximum(), self.spin_count.value() + delta)
                )
                if new_value != self.spin_count.value():
                    self.spin_count.setValue(new_value)
                event.accept()
                return
        super().keyPressEvent(event)

    def reject(self):
        if self.stack.currentIndex() == 0:
            super().reject()
        else:
            super().accept()

    def planned_shelves(self) -> List[str]:
        return list(self._planned_shelves)
