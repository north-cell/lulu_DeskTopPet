from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRegion
from PySide6.QtWidgets import QLabel, QWidget

from .native_window import remove_windows_frame_artifacts


class BubbleWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
            | Qt.BypassWindowManagerHint
        )
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))
        self.label.setStyleSheet("color: #3a2a22; padding: 12px 16px 13px 16px; line-height: 150%;")

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._anchor: QWidget | None = None
        self._anchor_offset = QPoint()

    def show_message(self, text: str, anchor: QWidget, duration_ms: int = 2600) -> None:
        if not text:
            return
        if not anchor.isVisible():
            self.hide()
            return
        self.label.setText(text)
        self.label.adjustSize()
        width = min(max(self.label.width() + 16, 160), 300)
        height = self.label.height() + 24
        self.resize(width, height)
        self._apply_shape_mask()
        self.label.setGeometry(8, 5, width - 16, height - 18)

        anchor_pos = anchor.mapToGlobal(anchor.rect().topLeft())
        x = anchor_pos.x() + max(0, (anchor.width() - width) // 2)
        y = anchor_pos.y() - height - 8
        if y < 0:
            y = anchor_pos.y() + 8
        self.move(x, y)
        self._anchor = anchor
        self._anchor_offset = self.pos() - anchor_pos
        self.show()
        self._remove_native_frame_artifacts()
        self._timer.start(duration_ms)

    def follow_anchor(self, anchor: QWidget | None = None) -> None:
        anchor = anchor or self._anchor
        if not self.isVisible() or anchor is None:
            return
        if not anchor.isVisible():
            self.hide()
            return
        anchor_pos = anchor.mapToGlobal(anchor.rect().topLeft())
        self.move(anchor_pos + self._anchor_offset)

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        self._remove_native_frame_artifacts()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        body = self._body_rect()
        path = self._bubble_path(body)

        gradient = QLinearGradient(QPointF(body.left(), body.top()), QPointF(body.left(), body.bottom()))
        gradient.setColorAt(0, QColor(255, 253, 247, 248))
        gradient.setColorAt(1, QColor(255, 239, 219, 244))
        painter.fillPath(path, gradient)

        painter.setPen(QPen(QColor(151, 104, 78, 165), 1))
        painter.drawPath(path)

        highlight = QPainterPath()
        highlight.addRoundedRect(body.adjusted(4, 4, -4, -body.height() // 2), 13, 13)
        painter.setPen(Qt.NoPen)
        painter.fillPath(highlight, QColor(255, 255, 255, 44))

    def _remove_native_frame_artifacts(self) -> None:
        remove_windows_frame_artifacts(int(self.winId()))

    def _apply_shape_mask(self) -> None:
        path = self._bubble_path(self._body_rect())
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _body_rect(self) -> QRect:
        return self.rect().adjusted(1, 1, -1, -9)

    def _bubble_path(self, body: QRect) -> QPainterPath:
        body_path = QPainterPath()
        body_path.addRoundedRect(body, 17, 17)

        tail_x = body.center().x()
        tail_y = body.bottom()
        tail_path = QPainterPath()
        tail_path.moveTo(tail_x - 13, tail_y - 2)
        tail_path.cubicTo(tail_x - 8, tail_y + 8, tail_x + 7, tail_y + 8, tail_x + 12, tail_y - 2)
        tail_path.lineTo(tail_x - 13, tail_y - 2)
        tail_path.closeSubpath()

        return body_path.united(tail_path)
