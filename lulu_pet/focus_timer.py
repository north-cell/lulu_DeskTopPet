from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from .native_window import remove_windows_frame_artifacts


class FocusTimerWidget(QWidget):
    finished_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
            | Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._elapsed_seconds = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.resize(132, 96)

    def show_for(self, anchor: QWidget, elapsed_seconds: int = 0) -> None:
        self.set_elapsed(elapsed_seconds)
        anchor_pos = anchor.mapToGlobal(anchor.rect().topLeft())
        x = anchor_pos.x() + max(0, (anchor.width() - self.width()) // 2)
        y = anchor_pos.y() - self.height() - 8
        if y < 0:
            y = anchor_pos.y() + 8
        self.move(x, y)
        self.show()
        self._remove_native_frame_artifacts()
        self._timer.start(1000)

    def set_elapsed(self, seconds: int) -> None:
        self._elapsed_seconds = max(0, int(seconds))
        self.update()

    def hide(self) -> None:
        self._timer.stop()
        super().hide()

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self.finished_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        self._remove_native_frame_artifacts()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        shadow = QRectF(25, 72, self.width() - 50, 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(114, 75, 38, 34))
        painter.drawEllipse(shadow)

        body = QRectF(15, 24, self.width() - 30, 56)
        body_path = QPainterPath()
        body_path.moveTo(body.left() + 12, body.center().y() - 2)
        body_path.cubicTo(body.left() + 12, body.top() + 10, body.center().x() - 22, body.top(), body.center().x() + 4, body.top() + 2)
        body_path.cubicTo(body.right() - 6, body.top() + 5, body.right() - 4, body.bottom() - 9, body.center().x() + 20, body.bottom() - 2)
        body_path.cubicTo(body.center().x() - 6, body.bottom() + 4, body.left() + 4, body.bottom() - 7, body.left() + 12, body.center().y() - 2)
        body_path.closeSubpath()

        gradient = QRadialGradient(QPointF(body.left() + 35, body.top() + 16), body.width() * 0.78)
        gradient.setColorAt(0, QColor(255, 198, 91, 255))
        gradient.setColorAt(0.48, QColor(255, 156, 61, 255))
        gradient.setColorAt(1, QColor(239, 116, 42, 255))
        painter.fillPath(body_path, gradient)

        painter.setPen(QPen(QColor(198, 94, 36, 115), 1.5))
        painter.drawPath(body_path)

        highlight = QPainterPath()
        highlight.moveTo(body.left() + 30, body.top() + 12)
        highlight.cubicTo(body.left() + 52, body.top() + 3, body.right() - 26, body.top() + 12, body.right() - 18, body.top() + 30)
        painter.setPen(QPen(QColor(255, 218, 133, 120), 7, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(highlight)

        groove = QPainterPath()
        groove.moveTo(body.center().x() + 10, body.top() + 6)
        groove.cubicTo(body.center().x() + 24, body.top() + 20, body.center().x() + 31, body.bottom() - 12, body.center().x() + 8, body.bottom() - 3)
        painter.setPen(QPen(QColor(213, 95, 37, 95), 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(groove)

        painter.setPen(QPen(QColor(91, 84, 63), 7, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(self.width() * 0.51, 25, self.width() * 0.55, 13)
        painter.setBrush(QColor(101, 143, 83, 235))
        painter.setPen(Qt.NoPen)
        leaf = QPainterPath()
        leaf.moveTo(self.width() * 0.54, 16)
        leaf.cubicTo(self.width() * 0.62, 7, self.width() * 0.71, 10, self.width() * 0.67, 20)
        leaf.cubicTo(self.width() * 0.62, 26, self.width() * 0.57, 22, self.width() * 0.54, 16)
        painter.fillPath(leaf, painter.brush())

        painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        painter.setPen(QColor(92, 45, 23))
        painter.drawText(body.adjusted(0, 8, 0, 0), Qt.AlignCenter, self._format_elapsed())

    def _tick(self) -> None:
        self.set_elapsed(self._elapsed_seconds + 1)

    def _format_elapsed(self) -> str:
        seconds = self._elapsed_seconds
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _remove_native_frame_artifacts(self) -> None:
        remove_windows_frame_artifacts(int(self.winId()))
