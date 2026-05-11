from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget


class BubbleWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Microsoft YaHei UI", 10))
        self.label.setStyleSheet("color: #3b2a21; padding: 10px 14px;")

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, anchor: QWidget, duration_ms: int = 2600) -> None:
        if not text:
            return
        self.label.setText(text)
        self.label.adjustSize()
        width = min(max(self.label.width() + 8, 130), 260)
        height = self.label.height() + 8
        self.resize(width, height)
        self.label.setGeometry(4, 4, width - 8, height - 8)

        anchor_pos = anchor.mapToGlobal(anchor.rect().topLeft())
        x = anchor_pos.x() + max(0, (anchor.width() - width) // 2)
        y = anchor_pos.y() - height - 8
        if y < 0:
            y = anchor_pos.y() + 8
        self.move(x, y)
        self.show()
        self._timer.start(duration_ms)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
        painter.fillPath(path, QColor(255, 250, 241, 238))
        painter.setPen(QPen(QColor(142, 111, 88, 180), 1))
        painter.drawPath(path)
