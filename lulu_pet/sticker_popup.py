from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import QLabel, QWidget


class StickerPopup(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self._movie: QMovie | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_sticker(self, path: Path | None, anchor: QWidget, duration_ms: int = 2600) -> None:
        if not path or not path.exists():
            return
        if self._movie:
            self._movie.stop()
        self._movie = None
        size = 148
        self.resize(size, size)
        self.label.setGeometry(0, 0, size, size)

        if path.suffix.lower() == ".gif":
            movie = QMovie(str(path))
            movie.setScaledSize(self.label.size())
            self.label.setMovie(movie)
            self._movie = movie
            movie.start()
        else:
            pixmap = QPixmap(str(path))
            self.label.setPixmap(pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        anchor_pos = anchor.mapToGlobal(anchor.rect().topLeft())
        self.move(anchor_pos.x() + anchor.width() + 12, max(0, anchor_pos.y() - size // 2))
        self.show()
        self._timer.start(duration_ms)
