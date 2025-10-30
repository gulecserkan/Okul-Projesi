from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtCore import Qt


class RichLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setTextFormat(Qt.RichText)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def setText(self, text):
        super().setText(text)
        self.adjustSize()
