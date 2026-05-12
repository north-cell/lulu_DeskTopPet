from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


LULU_CONTRACT_DIALOG_STYLE = """
QDialog#contractDialog {
    background-color: #FFF4DA;
    border: 1px solid #8F6346;
    border-radius: 10px;
}

QLabel#titleLabel {
    color: #3B271C;
    font-size: 17px;
    font-weight: 700;
}

QLabel#hintLabel {
    color: #6F4A33;
    font-size: 12px;
}

QLineEdit#contractNameEdit {
    background-color: #FFF9EC;
    color: #3B271C;
    border: 1px solid #D8B487;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: #C78652;
    selection-color: #FFF8E8;
    font-size: 14px;
}

QLineEdit#contractNameEdit:focus {
    border: 2px solid #C78652;
    padding: 6px 9px;
}

QPushButton {
    min-width: 78px;
    min-height: 28px;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 13px;
}

QPushButton#primaryButton {
    background-color: #7B4D32;
    color: #FFF8E8;
    border: 1px solid #5D3825;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background-color: #8F5A3A;
}

QPushButton#secondaryButton,
QPushButton#closeButton {
    background-color: #FFEBC7;
    color: #5C3A27;
    border: 1px solid #D8B487;
}

QPushButton#secondaryButton:hover,
QPushButton#closeButton:hover {
    background-color: #F7D9A8;
}

QPushButton#closeButton {
    min-width: 24px;
    min-height: 24px;
    max-width: 24px;
    max-height: 24px;
    border-radius: 12px;
    padding: 0;
}
"""


class ContractDialog(QDialog):
    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("contractDialog")
        self.setWindowTitle("签订契约")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedWidth(336)
        self.setStyleSheet(LULU_CONTRACT_DIALOG_STYLE)

        title = QLabel("签订契约", self)
        title.setObjectName("titleLabel")

        close_button = QPushButton("×", self)
        close_button.setObjectName("closeButton")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.reject)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close_button)

        hint = QLabel("噜噜以后怎么称呼你？", self)
        hint.setObjectName("hintLabel")

        self.name_edit = QLineEdit(self)
        self.name_edit.setObjectName("contractNameEdit")
        self.name_edit.setMaxLength(12)
        self.name_edit.setText((current_name or "shouting").strip()[:12])
        self.name_edit.selectAll()

        primary_button = QPushButton("签订", self)
        primary_button.setObjectName("primaryButton")
        primary_button.setCursor(Qt.PointingHandCursor)
        primary_button.clicked.connect(self.accept)

        secondary_button = QPushButton("先不了", self)
        secondary_button.setObjectName("secondaryButton")
        secondary_button.setCursor(Qt.PointingHandCursor)
        secondary_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(secondary_button)
        buttons.addWidget(primary_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(hint)
        layout.addWidget(self.name_edit)
        layout.addSpacing(2)
        layout.addLayout(buttons)

    @classmethod
    def get_contract_name(cls, current_name: str, parent=None) -> tuple[str, bool]:
        dialog = cls(current_name, parent)
        accepted = dialog.exec() == QDialog.Accepted
        return dialog.name_edit.text(), accepted
