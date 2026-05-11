from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from .motion import MotionFrame, MotionMode


class LuluRenderer:
    def paint(self, painter: QPainter, rect: QRectF, frame: MotionFrame) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(rect.center())
        if frame.facing > 0:
            painter.scale(-1, 1)
        if frame.rotation_degrees:
            painter.rotate(frame.rotation_degrees)
        painter.translate(-rect.width() / 2, -rect.height() / 2)
        self._paint_shadow(painter, rect)
        self._paint_body(painter, rect, frame)
        painter.restore()

    def _paint_shadow(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(74, 54, 42, 48))
        painter.drawEllipse(QRectF(rect.width() * 0.18, rect.height() * 0.79, rect.width() * 0.64, rect.height() * 0.11))

    def _paint_body(self, painter: QPainter, rect: QRectF, frame: MotionFrame) -> None:
        w = rect.width()
        h = rect.height()
        bounce = self._bounce(frame)
        body = QRectF(w * 0.12, h * (0.25 + bounce), w * 0.76, h * 0.46)
        head = QRectF(w * 0.42, h * (0.13 + bounce), w * 0.38, h * 0.36)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(166, 126, 93))
        painter.drawRoundedRect(body, w * 0.19, h * 0.18)
        painter.setBrush(QColor(177, 137, 102))
        painter.drawRoundedRect(head, w * 0.15, h * 0.15)

        painter.setBrush(QColor(120, 86, 63))
        painter.drawEllipse(QRectF(w * 0.46, h * (0.10 + bounce), w * 0.08, h * 0.09))
        painter.drawEllipse(QRectF(w * 0.67, h * (0.10 + bounce), w * 0.08, h * 0.09))

        self._paint_face(painter, w, h, frame, bounce)
        self._paint_legs(painter, w, h, frame, bounce)

        painter.setPen(QPen(QColor(111, 78, 58), max(2, int(w * 0.018))))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(QRectF(w * 0.14, h * (0.29 + bounce), w * 0.13, h * 0.15), 30 * 16, 110 * 16)

    def _paint_face(self, painter: QPainter, w: float, h: float, frame: MotionFrame, bounce: float) -> None:
        painter.setBrush(QColor(35, 25, 20))
        painter.setPen(Qt.NoPen)
        if frame.mode == MotionMode.SLEEP:
            pen = QPen(QColor(35, 25, 20), max(2, int(w * 0.018)), Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(w * 0.52, h * (0.29 + bounce), w * 0.07, h * 0.04), 20 * 16, 140 * 16)
            painter.drawArc(QRectF(w * 0.65, h * (0.29 + bounce), w * 0.07, h * 0.04), 20 * 16, 140 * 16)
        else:
            painter.drawEllipse(QRectF(w * 0.54, h * (0.31 + bounce), w * 0.035, h * 0.045))
            painter.drawEllipse(QRectF(w * 0.68, h * (0.31 + bounce), w * 0.035, h * 0.045))

        painter.setPen(QPen(QColor(51, 36, 27), max(2, int(w * 0.017)), Qt.SolidLine, Qt.RoundCap))
        mouth_y = h * (0.42 + bounce)
        if frame.mode in (MotionMode.RUN_LEFT, MotionMode.RUN_RIGHT, MotionMode.ROLL_LEFT, MotionMode.ROLL_RIGHT):
            painter.drawEllipse(QRectF(w * 0.61, mouth_y - h * 0.01, w * 0.045, h * 0.035))
        else:
            painter.drawArc(QRectF(w * 0.58, mouth_y - h * 0.02, w * 0.11, h * 0.07), 200 * 16, 140 * 16)

    def _paint_legs(self, painter: QPainter, w: float, h: float, frame: MotionFrame, bounce: float) -> None:
        phase = frame.frame_index % 12
        swing = math.sin(phase / 12 * math.tau)
        if frame.mode in (MotionMode.IDLE, MotionMode.SLEEP):
            swing = 0
        if frame.mode in (MotionMode.RUN_LEFT, MotionMode.RUN_RIGHT):
            swing *= 1.8
        if frame.mode in (MotionMode.ROLL_LEFT, MotionMode.ROLL_RIGHT):
            swing = 0

        painter.setPen(QPen(QColor(107, 75, 55), max(7, int(w * 0.06)), Qt.SolidLine, Qt.RoundCap))
        base_y = h * (0.68 + bounce)
        painter.drawLine(QPointF(w * 0.31, base_y), QPointF(w * (0.30 + swing * 0.035), h * 0.80))
        painter.drawLine(QPointF(w * 0.47, base_y), QPointF(w * (0.48 - swing * 0.035), h * 0.80))
        painter.drawLine(QPointF(w * 0.65, base_y), QPointF(w * (0.66 + swing * 0.035), h * 0.80))
        painter.drawLine(QPointF(w * 0.79, base_y), QPointF(w * (0.78 - swing * 0.035), h * 0.80))

    def _bounce(self, frame: MotionFrame) -> float:
        if frame.mode in (MotionMode.WALK_LEFT, MotionMode.WALK_RIGHT):
            return math.sin(frame.frame_index / 6 * math.tau) * 0.012
        if frame.mode in (MotionMode.RUN_LEFT, MotionMode.RUN_RIGHT):
            return math.sin(frame.frame_index / 4 * math.tau) * 0.022
        if frame.mode == MotionMode.DRAGGED:
            return -0.05
        return 0.0
