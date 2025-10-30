from __future__ import annotations

import re
import random
from datetime import datetime
from typing import Dict, List

from PyQt5.QtCore import Qt, QStringListModel, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QSizePolicy, QMessageBox, QToolButton, QFormLayout, QDialogButtonBox,
    QListWidget, QListWidgetItem, QCompleter, QCheckBox
)

from api import books as book_api
from printing.template_renderer import get_default_template_path, print_label_batch
from ui.entity_manager_dialog import AuthorManagerDialog, CategoryManagerDialog, normalize_entity_text


BOOK_TABLE_HEADERS = ["Başlık", "Yazar", "Kategori", "ISBN", "Nüsha"]


ISBN_PATTERN = re.compile(r"^(97[89]\d{10}|\d{9}[\dXx])$")


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
        self.resize(360, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        info = QLabel("Yazdırılacak nüshaları seçin:")
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        self.btn_all = QPushButton("Hepsi")
        self.btn_none = QPushButton("Hiçbiri")
        self.btn_toggle = QPushButton("Seçimi Tersle")
        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)
        btn_row.addWidget(self.btn_toggle)
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

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.btn_print = QPushButton("Yazdır")
        self.btn_print.setEnabled(self._has_checked())
        buttons.addButton(self.btn_print, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        self.btn_print.clicked.connect(self.accept)
        layout.addWidget(buttons)

        self.btn_all.clicked.connect(lambda: self._set_all(Qt.Checked))
        self.btn_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        self.btn_toggle.clicked.connect(self._invert_selection)
        self.list.itemChanged.connect(lambda _: self._update_print_state())

    def _set_all(self, state):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)
        self.list.blockSignals(False)
        self._update_print_state()

    def _invert_selection(self):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            item = self.list.item(i)
            new_state = Qt.Checked if item.checkState() == Qt.Unchecked else Qt.Unchecked
            item.setCheckState(new_state)
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
        form_v.addWidget(self._form_row_single("Başlık", title_container))

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
        self.author_suggestion_list.itemClicked.connect(lambda item: self._apply_author_suggestion(item.text(), item.data(Qt.UserRole)))
        btn_add_author = QToolButton()
        btn_add_author.setText("+")
        btn_add_author.setToolTip("Yeni yazar ekle")
        btn_add_author.clicked.connect(self.add_author_quick)

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
        row2h.addWidget(self._form_row_labeled("Yazar", self.input_author, btn_add_author))
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

        # Butonlar
        self.button_row_widget = QWidget()
        btn_row = QHBoxLayout(self.button_row_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        self.btn_new = QPushButton("Yeni")
        self.btn_new.setObjectName("DialogNeutralButton")
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setObjectName("DialogPositiveButton")
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setObjectName("DialogNegativeButton")
        self.btn_print = QPushButton("Barkod Bas")
        self.btn_print.setEnabled(True)
        self.btn_close = QPushButton("Kapat")

        for b in (self.btn_new, self.btn_save, self.btn_delete, self.btn_print, self.btn_close):
            b.setAutoDefault(False)
            b.setDefault(False)

        self.btn_save.setAutoDefault(True)
        self.btn_save.setDefault(True)

        self.btn_new.clicked.connect(self.reset_form)
        self.btn_save.clicked.connect(self.save_book)
        self.btn_delete.clicked.connect(self.delete_book)
        self.btn_print.clicked.connect(self.print_labels)
        self.btn_close.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_print)
        main.addWidget(self.button_row_widget)

        self.setTabOrder(self.input_title, self.input_author)
        self.setTabOrder(self.input_author, self.input_category)
        self.setTabOrder(self.input_category, self.input_isbn)
        self.setTabOrder(self.input_isbn, self.btn_save)

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

            values = [title, author, category, isbn, str(copies)]
            for col, val in enumerate(values):
                it = QTableWidgetItem(val or "")
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if col in (3, 4):
                    it.setTextAlignment(Qt.AlignCenter)
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
    def reset_form(self):
        self.current_id = None
        self.input_title.clear()
        self.input_isbn.clear()
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
        self.table.clearSelection()
        self._hide_title_suggestions()
        self.input_title.setFocus()

    def on_row_selected(self):
        items = self.table.selectedItems()
        if not items:
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
            return None
        if not self.current_id and self._has_duplicate_title(title):
            self._handle_duplicate_title(title)
            return None
        if isbn and not ISBN_PATTERN.fullmatch(isbn):
            QMessageBox.warning(self, "Uyarı", "ISBN 10 ya da 13 hane olmalıdır (rakam/X).")
            return None
        if (self.input_category.text() or "").strip() and self._selected_category_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden geçerli bir kategori seçin.")
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
        book_title = book.get("baslik", title)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Kitap zaten mevcut")
        box.setText(
            f"'{book_title}' başlıklı bir kitap zaten kayıtlı.\n"
            "Yeni bir kayıt oluşturmak yerine mevcut kitaba nüsha eklemelisiniz."
        )
        btn_add = box.addButton("Nüsha Ekle", QMessageBox.AcceptRole)
        btn_cancel = box.addButton("Vazgeç", QMessageBox.RejectRole)
        box.setDefaultButton(btn_add)
        box.exec_()
        if box.clickedButton() == btn_add:
            self._open_copies_dialog_for_book(book, select_in_table=True)
        else:
            QMessageBox.information(
                self,
                "Bilgi",
                "Aynı başlıkla ikinci bir kitap eklenemez. Lütfen mevcut kayıt için nüsha ekleyin."
            )
        self._pending_duplicate_matches = []

    def save_book(self):
        data = self._collect_payload()
        if data is None:
            return
        creating = not bool(self.current_id)
        if creating:
            resp = book_api.create_book(data)
            ok = resp.status_code in (200, 201)
        else:
            resp = book_api.update_book(self.current_id, data)
            ok = resp.status_code in (200, 202)
        if ok:
            # yeni kayıttaysa varsayılan 1 nüshayI KITxxxxx şablonuyla oluştur
            if creating:
                try:
                    created = resp.json() or {}
                    bid = created.get("id")
                    if bid:
                        try:
                            barkod = book_api.get_next_barcode(prefix="KIT", width=6)
                        except Exception:
                            barkod = ""
                        _resp = book_api.create_copy(bid, barkod)
                        if _resp.status_code not in (200, 201):
                            # Boş göndererek sunucu otomatik üretimini deneyelim
                            _resp2 = book_api.create_copy(bid, "")
                            if _resp2.status_code not in (200, 201):
                                QMessageBox.warning(self, "Uyarı", "Varsayılan nüsha otomatik oluşturulamadı.")
                except Exception:
                    pass
            QMessageBox.information(self, "Başarılı", "Kitap kaydedildi.")
            self.load_books()
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
        dlg.exec_()
        if dlg.new_copies:
            template_path = get_default_template_path()
            if not template_path:
                QMessageBox.warning(
                    self,
                    "Etiket",
                    "Varsayılan etiket şablonu bulunamadı. Lütfen Etiket Editörü'nde şablon seçin."
                )
            else:
                reply = QMessageBox.question(
                    self,
                    "Etiket Yazdır",
                    "Yeni eklenen nüshalar için barkod yazdırmak ister misiniz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes:
                    contexts = []
                    for cp in dlg.new_copies:
                        ctx = dict(context)
                        ctx["barcode"] = str(cp.get("barkod", "") or "")
                        ctx["shelf_code"] = str(cp.get("raf_kodu", "") or "")
                        contexts.append(ctx)
                    if contexts:
                        try:
                            print_label_batch(template_path, contexts)
                            QMessageBox.information(self, "Etiket", f"{len(contexts)} etiket yazıcıya gönderildi.")
                        except Exception as exc:
                            QMessageBox.warning(self, "Etiket", f"Etiketler yazdırılamadı:\n{exc}")

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
                return


class CopiesManagerDialog(QDialog):
    def __init__(self, book_id, context, parent=None):
        super().__init__(parent)
        self.book_id = book_id
        self.parent_context = context or {}
        self.new_copies: List[Dict] = []
        self._existing_ids = set()
        self._last_shelf = ""
        self._shelf_model = QStringListModel()
        self.setWindowTitle("Nüsha Yönetimi")
        self.resize(520, 380)

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
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        # Kapat
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

        self.load_copies()
        self._prepare_next_barcode()

    def load_copies(self):
        data = book_api.list_copies_for_book(self.book_id) or []
        self.table.setRowCount(len(data))
        shelves = []
        self._existing_ids = set()
        for i, cp in enumerate(data):
            barkod = str(cp.get("barkod", ""))
            raf = str(cp.get("raf_kodu", "") or "")
            self.table.setItem(i, 0, QTableWidgetItem(barkod))
            self.table.setItem(i, 1, QTableWidgetItem(raf))
            if cp.get("id") is not None:
                self._existing_ids.add(cp.get("id"))
            if raf:
                shelves.append(raf)
            btn = QPushButton("Sil")
            btn.setObjectName("DialogNegativeButton")
            btn.clicked.connect(lambda _, cid=cp.get("id"): self.delete_copy(cid))
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.addStretch(1)
            h.addWidget(btn)
            self.table.setCellWidget(i, 2, w)
        if shelves:
            self._last_shelf = shelves[-1]
        elif not shelves and not self.new_copies:
            self._last_shelf = ""
        self._shelf_model.setStringList(sorted(set(shelves)))
        return data

    def add_copy(self):
        barkod = (self.input_barcode.text() or "").strip()
        shelf = self.input_shelf.text().strip() or None
        # Barkod boşsa sunucu otomatik üretecek
        prev_ids = set(self._existing_ids)
        resp = book_api.create_copy(self.book_id, barkod, shelf)
        if resp.status_code in (200, 201):
            self.input_shelf.clear()
            created = None
            try:
                created = resp.json() or {}
            except Exception:
                created = None
            data = self.load_copies()
            self._prepare_next_barcode()
            if not created or created.get("id") in prev_ids:
                created = None
                for cp in data:
                    cid = cp.get("id")
                    if cid is not None and cid not in prev_ids:
                        created = cp
                        break
            if not created and barkod:
                for cp in data:
                    if str(cp.get("barkod", "")) == barkod:
                        created = cp
                        break
            if created:
                if shelf and not created.get("raf_kodu"):
                    created["raf_kodu"] = shelf
                created.setdefault("barkod", barkod or "")
                self.new_copies.append(created)
        else:
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Nüsha eklenemedi.\n\nDetay: {detail}")

    def delete_copy(self, copy_id):
        if not copy_id:
            return
        if QMessageBox.question(self, "Onay", "Bu nüshayı silmek istiyor musunuz?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        resp = book_api.delete_copy(copy_id)
        if resp.status_code in (200, 204):
            self.load_copies()
        else:
            detail = book_api.extract_error(resp)
            QMessageBox.warning(self, "Hata", f"Nüsha silinemedi.\n\nDetay: {detail}")

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
