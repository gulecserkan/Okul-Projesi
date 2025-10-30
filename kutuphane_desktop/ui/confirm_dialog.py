from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt


class ConfirmDialog(QDialog):
    def __init__(self, message, detail=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Onay")
        self.setModal(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)

        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        if detail:
            detail_label = QLabel(f"<small>{detail}</small>")
            detail_label.setWordWrap(True)
            detail_label.setAlignment(Qt.AlignLeft)
            layout.addWidget(detail_label)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_yes = QPushButton("Evet")
        self.btn_yes.setObjectName("DialogNegativeButton")
        self.btn_no = QPushButton("Vazgeç")
        self.btn_no.setObjectName("DialogNeutralButton")
        row.addWidget(self.btn_yes)
        row.addWidget(self.btn_no)
        layout.addLayout(row)

        self.setLayout(layout)
        self.btn_yes.clicked.connect(self.accept)
        self.btn_no.clicked.connect(self.reject)
