from dataclasses import dataclass

from PyQt5.QtCore import (
    Qt,
    QPoint,
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    QSize,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QSizePolicy,
    QScrollArea,
)
from PyQt5.QtGui import QIcon, QPixmap


@dataclass
class SideMenuEntry:
    title: str
    description: str = ""
    icon: QIcon = None
    callback: callable = None


class SideMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SideMenu")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(280)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Scrollable içerik
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("SideMenuScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Scroll alanı ve viewport arkaplanını şeffaf yap
        self._scroll.setStyleSheet(
            "QScrollArea#SideMenuScroll{background:transparent;border:none;}"
            "QScrollArea#SideMenuScroll > QWidget{background:transparent;}"
            "QScrollArea#SideMenuScroll > QWidget > QWidget{background:transparent;}"
        )
        self._container = QWidget(self)
        self._container.setAttribute(Qt.WA_StyledBackground, True)
        self._container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(16, 24, 16, 16)
        self._container_layout.setSpacing(12)
        self._scroll.setWidget(self._container)
        self._layout.addWidget(self._scroll)

        self._entries = []
        self._visible = False
        self._animate = True

        self._animation = QPropertyAnimation(self, b"pos", self)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.finished.connect(self._on_animation_finished)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_menu)

        self.hide()

    def set_items(self, entries):
        self._entries = entries or []
        # İçeriği temizle (scroll container)
        for i in reversed(range(self._container_layout.count())):
            item = self._container_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        for entry in self._entries:
            widget = MenuItemWidget(entry, self)
            widget.clicked.connect(lambda cb=entry.callback: self._item_triggered(cb))
            self._container_layout.addWidget(widget)

        self._container_layout.addStretch()

    def _item_triggered(self, callback):
        self.hide_menu()
        if callback:
            # Animasyon bitmesini beklemeden işlevi sıradaki döngüde çalıştır
            QTimer.singleShot(0, callback)

    def toggle_menu(self):
        if self._visible:
            self.hide_menu()
        else:
            self.show_menu()

    def show_menu(self):
        if self._visible:
            return
        self._visible = True
        self.update_geometry()
        self.show()
        self.raise_()
        if not self._animate:
            self.move(0, 0)
            return
        start = QPoint(-self.width(), 0)
        end = QPoint(0, 0)
        self._animation.stop()
        self.move(start)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def hide_menu(self):
        if not self._visible:
            return
        self._visible = False
        if not self._animate:
            self.hide()
            self.move(-self.width(), 0)
            return
        self._animation.stop()
        start = self.pos()
        end = QPoint(-self.width(), 0)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def force_hide(self):
        """Animasyon beklemeden menüyü anında gizler."""
        self._animation.stop()
        self._visible = False
        self.hide()
        self.move(-self.width(), 0)

    def disable_animation(self):
        """Tüm aç-kapa animasyonlarını kapat."""
        self._animate = False

    def update_geometry(self):
        parent = self.parent()
        if not parent:
            return
        height = parent.height()
        self.setFixedHeight(height)
        if self._visible:
            self.move(0, 0)
        else:
            self.move(-self.width(), 0)

    def is_visible(self):
        return self._visible

    def leaveEvent(self, event):
        if self._visible:
            self._hide_timer.start(300)
        super().leaveEvent(event)

    def enterEvent(self, event):
        self._hide_timer.stop()
        super().enterEvent(event)

    def _on_animation_finished(self):
        if not self._visible:
            self.hide()
            self.move(-self.width(), 0)


class MenuItemWidget(QFrame):
    clicked = pyqtSignal()
    def __init__(self, entry: SideMenuEntry, parent=None):
        super().__init__(parent)
        self.setObjectName("SideMenuItem")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Hover algılamayı güçlendir
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("hover", False)
        
        self._entry = entry

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        # Daha kompakt sabit yükseklik
        self.setFixedHeight(92)

        if entry.icon:
            icon_label = QLabel(self)
            pixmap = entry.icon.pixmap(QSize(30, 30))
            icon_label.setPixmap(pixmap)
            icon_label.setObjectName("SideMenuItemIcon")
            icon_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        # Başlık ile açıklama arası çok az olsun
        text_layout.setSpacing(0)

        title_label = QLabel(entry.title, self)
        title_label.setObjectName("SideMenuItemTitle")
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_label.setMinimumHeight(24)
        title_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        self._title_label = title_label

        if entry.description:
            desc_label = QLabel(entry.description, self)
            desc_label.setObjectName("SideMenuItemDesc")
            desc_label.setWordWrap(True)
            desc_label.setMinimumHeight(26)
            desc_label.setContentsMargins(0, 0, 0, 0)
            desc_label.setAlignment(Qt.AlignTop)
            desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            text_layout.addWidget(desc_label)
            self._desc_label = desc_label
        else:
            self._desc_label = None

        layout.addLayout(text_layout)
        layout.setAlignment(text_layout, Qt.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Sadece clicked sinyali yay – SideMenu set_items içinde callback tetikleniyor
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setProperty("hover", True)
        # Sadece kapsayıcıya arkaplan uygula; iç etiketlerin arkaplanı şeffaf kalsın
        self.setStyleSheet("background-color: #1f2b3a;")
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        # Yalnızca kapsayıcı stilini temizle; çocukları değiştirmeyelim
        self.setStyleSheet("")
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)
