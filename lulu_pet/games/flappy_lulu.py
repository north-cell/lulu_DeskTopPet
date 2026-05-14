from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from ..paths import resource_path


FRAME_INTERVAL_MS = 16

PIXEL_FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    " ": ["000", "000", "000", "000", "000", "000", "000"],
}


@dataclass
class PipePair:
    x: float
    gap_center: float
    scored: bool = False


class FlappyLuluWindow(QWidget):
    finished = Signal()

    def __init__(
        self,
        *,
        play_area: QRect | None = None,
        record_path: Path | None = None,
        seed: int | None = None,
    ):
        super().__init__()
        self.record_path = record_path or resource_path("config", "flappy_lulu_records.json")
        self._play_area = QRect(play_area) if play_area else None
        self._rng = random.Random(seed)
        self.bird_x = 180.0
        self.bird_y = 240.0
        self.bird_velocity = 0.0
        self.bird_size = 54
        self.gravity = 0.48
        self.flap_velocity = -7.8
        self.pipe_speed = 3.1
        self.pipe_width = 72
        self.pipe_gap = 198
        self.pipe_spacing = 330
        self.ground_height = 64
        self.pipe_color = "#5CBF43"
        self.pipes: list[PipePair] = []
        self.score = 0
        self.high_score = self._load_high_score()
        self.start_screen_visible = True
        self.awaiting_first_input = False
        self.results_visible = False
        self._closed_signal_emitted = False

        self.setWindowTitle("Flappy Lulu")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        if self._play_area:
            self.setGeometry(self._play_area)

        self._game_timer = QTimer(self)
        self._game_timer.timeout.connect(self.advance_frame)

        self._again_button = QPushButton("重新开始", self)
        self._again_button.clicked.connect(self.restart_game)
        self._close_button = QPushButton("关闭", self)
        self._close_button.clicked.connect(self.close)
        self._style_result_button(self._again_button, primary=True)
        self._style_result_button(self._close_button, primary=False)
        self._set_result_buttons_visible(False)

    @property
    def ground_y(self) -> int:
        return self._current_play_area().bottom() - self.ground_height

    def restart_game(self) -> None:
        area = self._current_play_area()
        self.bird_x = min(180, max(120, area.width() // 4))
        self.bird_y = area.height() // 2
        self.bird_velocity = 0
        self.score = 0
        self.start_screen_visible = True
        self.awaiting_first_input = False
        self.results_visible = False
        self._closed_signal_emitted = False
        self._game_timer.stop()
        self._set_result_buttons_visible(False)
        self.pipes = []
        first_x = area.width() + 120
        self._append_pipe(first_x)
        self._append_pipe(first_x + self.pipe_spacing)
        self._position_result_buttons()
        self.setFocus()
        self.update()

    def start_game(self) -> None:
        if self.results_visible:
            return
        self.start_screen_visible = False
        self.awaiting_first_input = False
        self.bird_velocity = 0
        self._game_timer.start(FRAME_INTERVAL_MS)
        self.setFocus()
        self.update()

    def prepare_to_start(self) -> None:
        if self.results_visible:
            return
        self.start_screen_visible = False
        self.awaiting_first_input = True
        self.bird_velocity = 0
        self._game_timer.stop()
        self.setFocus()
        self.update()

    def flap(self) -> None:
        if self.results_visible:
            return
        if self.awaiting_first_input:
            self.start_game()
        if self.start_screen_visible:
            return
        self.bird_velocity = self.flap_velocity

    def advance_frame(self) -> None:
        if self.start_screen_visible or self.awaiting_first_input or self.results_visible:
            return
        self.bird_velocity += self.gravity
        self.bird_y += self.bird_velocity
        for pipe in self.pipes:
            pipe.x -= self.pipe_speed
        self._remove_and_replace_pipes()
        self._score_passed_pipes()
        if self._has_collision():
            self.finish_game()
            return
        self.update()

    def finish_game(self) -> None:
        if self.results_visible:
            return
        self._save_high_score_if_needed()
        self.start_screen_visible = False
        self.awaiting_first_input = False
        self.results_visible = True
        self._game_timer.stop()
        self._set_result_buttons_visible(True)
        self._position_result_buttons()
        self.update()

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        if not self.results_visible and not self._game_timer.isActive() and not self.pipes:
            self.restart_game()

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._position_result_buttons()

    def closeEvent(self, event):  # noqa: N802 - Qt override
        self._game_timer.stop()
        if not self._closed_signal_emitted:
            self._closed_signal_emitted = True
            self.finished.emit()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):  # noqa: N802 - Qt override
        if event.key() == Qt.Key_Escape:
            if self.start_screen_visible or self.awaiting_first_input:
                self.close()
            else:
                self.finish_game()
            event.accept()
            return
        if event.key() == Qt.Key_Space:
            self.flap()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            if self.start_screen_visible:
                pos = event.position().toPoint()
                if self._start_button_rect().contains(pos):
                    self.prepare_to_start()
                elif self._quit_button_rect().contains(pos):
                    self.close()
                event.accept()
                return
            self.flap()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(104, 178, 204, 120))
        self._paint_pixel_background(painter)
        self._paint_pipes(painter)
        self._paint_ground(painter)
        if not self.start_screen_visible:
            self._paint_pixel_lulu(painter)
        if not self.start_screen_visible:
            self._paint_hud(painter)
        if self.awaiting_first_input:
            painter.setRenderHint(QPainter.Antialiasing)
            self._paint_ready_prompt(painter)
        if self.start_screen_visible:
            painter.setRenderHint(QPainter.Antialiasing)
            self._paint_start_screen(painter)
        if self.results_visible:
            painter.setRenderHint(QPainter.Antialiasing)
            self._paint_results(painter)

    def _append_pipe(self, x: float) -> None:
        area = self._current_play_area()
        min_center = 118 + self.pipe_gap / 2
        max_center = max(min_center, self.ground_y - self.pipe_gap / 2 - 46)
        self.pipes.append(PipePair(x, self._rng.uniform(min_center, max_center), scored=False))

    def _remove_and_replace_pipes(self) -> None:
        self.pipes = [pipe for pipe in self.pipes if pipe.x > -self.pipe_width]
        area = self._current_play_area()
        while len(self.pipes) < 2:
            last_x = max((pipe.x for pipe in self.pipes), default=area.width())
            self._append_pipe(last_x + self.pipe_spacing)

    def _score_passed_pipes(self) -> None:
        for pipe in self.pipes:
            if not pipe.scored and pipe.x + self.pipe_width < self.bird_x:
                pipe.scored = True
                self.score += 1

    def _has_collision(self) -> bool:
        bird = self._bird_rect()
        if bird.top() <= 0 or bird.bottom() >= self.ground_y:
            return True
        return any(self._pipe_rects(pipe)[0].intersects(bird) or self._pipe_rects(pipe)[1].intersects(bird) for pipe in self.pipes)

    def _bird_rect(self) -> QRectF:
        return QRectF(self.bird_x, self.bird_y, self.bird_size, self.bird_size)

    def _pipe_rects(self, pipe: PipePair) -> tuple[QRectF, QRectF]:
        top_bottom = pipe.gap_center - self.pipe_gap / 2
        bottom_top = pipe.gap_center + self.pipe_gap / 2
        top = QRectF(pipe.x, 0, self.pipe_width, top_bottom)
        bottom = QRectF(pipe.x, bottom_top, self.pipe_width, self.ground_y - bottom_top)
        return top, bottom

    def _paint_pixel_background(self, painter: QPainter) -> None:
        area = self._current_play_area()
        painter.fillRect(self.rect(), QColor("#6FC7D8"))
        painter.fillRect(QRect(0, int(area.height() * 0.58), area.width(), int(area.height() * 0.18)), QColor("#91D7E1"))
        painter.setPen(Qt.NoPen)
        for x in range(32, area.width(), 240):
            y = 62 + (x // 240 % 3) * 28
            painter.fillRect(QRect(x, y, 54, 18), QColor("#FFF1C9"))
            painter.fillRect(QRect(x + 24, y - 16, 44, 18), QColor("#FFF6DC"))
            painter.fillRect(QRect(x + 62, y + 2, 50, 16), QColor("#FFF1C9"))
        for x in range(0, area.width(), 88):
            base = self.ground_y - 38
            painter.fillRect(QRect(x, base + (x // 88 % 2) * 8, 50, 38), QColor("#B8E07F"))
            painter.fillRect(QRect(x + 50, base + 12, 38, 26), QColor("#9BD66C"))

    def _paint_pipes(self, painter: QPainter) -> None:
        painter.setPen(QColor("#2F6F2D"))
        for pipe in self.pipes:
            top, bottom = self._pipe_rects(pipe)
            for rect in (top, bottom):
                painter.fillRect(rect.toRect(), QColor(self.pipe_color))
                painter.fillRect(QRect(int(rect.left()) + 8, int(rect.top()), 14, int(rect.height())), QColor("#9BE36A"))
                painter.fillRect(QRect(int(rect.right()) - 16, int(rect.top()), 12, int(rect.height())), QColor("#3F9C38"))
                lip = QRect(int(rect.left()) - 6, int(rect.bottom()) - 18 if rect.top() == 0 else int(rect.top()), self.pipe_width + 12, 18)
                painter.fillRect(lip, QColor("#6DD651"))
                painter.fillRect(QRect(lip.left() + 8, lip.top() + 3, 18, lip.height() - 6), QColor("#A7EA76"))
                painter.drawRect(rect.toRect())
                painter.drawRect(lip)

    def _paint_ground(self, painter: QPainter) -> None:
        area = self._current_play_area()
        painter.fillRect(QRect(0, self.ground_y, area.width(), self.ground_height), QColor("#DDBB79"))
        painter.fillRect(QRect(0, self.ground_y, area.width(), 12), QColor("#73BF4D"))
        painter.fillRect(QRect(0, self.ground_y + 12, area.width(), 8), QColor("#4EA63E"))
        painter.setPen(QColor("#B7834B"))
        for x in range(0, area.width(), 34):
            painter.drawLine(x, self.ground_y + 22, x + 18, self.ground_y + 38)

    def _paint_pixel_lulu(self, painter: QPainter) -> None:
        scale = max(2, self.bird_size // 18)
        origin = QPointF(self.bird_x, self.bird_y)
        pixels = [
            ("#A84E05", 7, -1, 4, 1),
            ("#A84E05", 6, 0, 6, 3),
            ("#F47C10", 7, 0, 4, 3),
            ("#FF9A1A", 6, 1, 6, 1),
            ("#6E7D1E", 9, -3, 1, 2),
            ("#6E7D1E", 10, -2, 1, 1),
            ("#A84E05", 2, 4, 3, 4),
            ("#A84E05", 13, 4, 3, 4),
            ("#FFD64C", 3, 5, 2, 3),
            ("#FFD64C", 13, 5, 2, 3),
            ("#FFB23A", 2, 6, 3, 2),
            ("#FFB23A", 13, 6, 3, 2),
            ("#A84E05", 3, 2, 12, 1),
            ("#A84E05", 2, 3, 14, 2),
            ("#A84E05", 1, 5, 16, 8),
            ("#A84E05", 3, 13, 12, 3),
            ("#FFD64C", 3, 3, 12, 4),
            ("#FFE26A", 2, 5, 14, 5),
            ("#FFD64C", 2, 9, 14, 3),
            ("#FFB23A", 3, 11, 12, 3),
            ("#FF991C", 4, 12, 10, 2),
            ("#E87410", 5, 14, 8, 1),
            ("#7A3D12", 5, 6, 2, 1),
            ("#7A3D12", 11, 6, 2, 1),
            ("#123A66", 5, 7, 2, 3),
            ("#123A66", 11, 7, 2, 3),
            ("#1F63A5", 5, 7, 1, 2),
            ("#1F63A5", 11, 7, 1, 2),
            ("#9EDCFF", 6, 7, 1, 1),
            ("#9EDCFF", 12, 7, 1, 1),
            ("#FFB14B", 3, 10, 2, 1),
            ("#FFB14B", 13, 10, 2, 1),
            ("#C75B0A", 7, 11, 1, 1),
            ("#C75B0A", 10, 11, 1, 1),
            ("#7A3D12", 11, 13, 2, 1),
            ("#7A3D12", 10, 14, 2, 1),
            ("#FFD64C", 4, 15, 3, 2),
            ("#FFD64C", 11, 15, 3, 2),
            ("#E87410", 5, 17, 2, 1),
            ("#E87410", 11, 17, 2, 1),
        ]
        for color, x, y, w, h in pixels:
            painter.fillRect(
                QRect(
                    int(origin.x() + x * scale),
                    int(origin.y() + y * scale),
                    w * scale,
                    h * scale,
                ),
                QColor(color),
            )

    def _paint_hud(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("#FFF8E8"))
        painter.setBrush(QColor(36, 58, 62, 88))
        painter.drawRoundedRect(QRect(14, 12, 355, 34), 8, 8)
        painter.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        painter.drawText(24, 36, f"Flappy Lulu    分数 {self.score}    最高纪录 {self.high_score}")
        painter.setRenderHint(QPainter.Antialiasing, False)

    def _paint_start_screen(self, painter: QPainter) -> None:
        overlay = QColor(255, 244, 218, 54)
        painter.fillRect(self.rect(), overlay)
        panel = self._start_panel_rect()
        painter.setPen(QPen(QColor("#7D4E2E"), 2))
        painter.setBrush(QColor(255, 248, 224, 218))
        painter.drawRoundedRect(panel, 14, 14)
        title_scale = 6
        title = "FLAPPY LULU"
        title_x = panel.center().x() - self._pixel_text_width(title, title_scale, 1) // 2
        self._draw_pixel_text(painter, title, title_x, panel.top() + 38, title_scale, QColor("#35572A"), QColor("#F2A33A"))
        self._paint_start_button(painter, self._start_button_rect(), "START", QColor("#F2A33A"), QColor("#7D4E2E"))
        self._paint_start_button(painter, self._quit_button_rect(), "QUIT", QColor("#76C957"), QColor("#35572A"))

    def _paint_results(self, painter: QPainter) -> None:
        panel = self._result_panel_rect()
        painter.setPen(QColor("#8F6346"))
        painter.setBrush(QColor("#FFF4DA"))
        painter.drawRoundedRect(panel, 10, 10)
        painter.setPen(QColor("#3B271C"))
        painter.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        painter.drawText(panel.adjusted(0, 26, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "Flappy Lulu 结算")
        painter.setFont(QFont("Microsoft YaHei UI", 14))
        painter.drawText(panel.adjusted(88, 92, -88, -90), Qt.AlignLeft | Qt.AlignTop, f"分数：{self.score}\n最高纪录：{self.high_score}")

    def _paint_ready_prompt(self, painter: QPainter) -> None:
        area = self._current_play_area()
        prompt = QRect(0, 0, 360, 76)
        prompt.moveCenter(area.center())
        prompt.moveTop(self.ground_y - 150)
        painter.setPen(QPen(QColor("#7D4E2E"), 2))
        painter.setBrush(QColor(255, 248, 224, 220))
        painter.drawRoundedRect(prompt, 10, 10)
        painter.setPen(QColor("#3B271C"))
        painter.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        painter.drawText(prompt.adjusted(18, 12, -18, 0), Qt.AlignHCenter | Qt.AlignTop, "准备好了吗？")
        painter.setFont(QFont("Microsoft YaHei UI", 11))
        painter.drawText(prompt.adjusted(18, 42, -18, 0), Qt.AlignHCenter | Qt.AlignTop, "单击鼠标或按空格开始")

    def _current_play_area(self) -> QRect:
        if self._play_area:
            return QRect(0, 0, self._play_area.width(), self._play_area.height())
        return self.rect() if not self.rect().isEmpty() else QRect(0, 0, 1280, 720)

    def _result_panel_rect(self) -> QRect:
        panel = QRect(0, 0, 390, 250)
        panel.moveCenter(self.rect().center())
        return panel

    def _start_panel_rect(self) -> QRect:
        panel = QRect(0, 0, 440, 300)
        panel.moveCenter(self.rect().center())
        return panel

    def _set_result_buttons_visible(self, visible: bool) -> None:
        self._again_button.setVisible(visible)
        self._close_button.setVisible(visible)

    def _position_result_buttons(self) -> None:
        panel = self._result_panel_rect()
        self._again_button.setGeometry(panel.left() + 72, panel.bottom() - 62, 112, 34)
        self._close_button.setGeometry(panel.right() - 184, panel.bottom() - 62, 112, 34)

    def _start_button_rect(self) -> QRect:
        panel = self._start_panel_rect()
        return QRect(panel.left() + 82, panel.bottom() - 78, 126, 44)

    def _quit_button_rect(self) -> QRect:
        panel = self._start_panel_rect()
        return QRect(panel.right() - 208, panel.bottom() - 78, 126, 44)

    def _paint_start_button(self, painter: QPainter, rect: QRect, label: str, color: QColor, border: QColor) -> None:
        painter.setPen(QPen(border, 3))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 9, 9)
        painter.setPen(Qt.NoPen)
        scale = 3
        text_width = self._pixel_text_width(label, scale, 1)
        x = rect.center().x() - text_width // 2
        y = rect.center().y() - 11
        self._draw_pixel_text(painter, label, x + 2, y + 2, scale, QColor(87, 56, 36, 140))
        self._draw_pixel_text(painter, label, x, y, scale, QColor("#FFF7D7"))

    def _draw_pixel_text(
        self,
        painter: QPainter,
        text: str,
        x: int,
        y: int,
        scale: int,
        color: QColor,
        shadow: QColor | None = None,
    ) -> None:
        if shadow:
            self._draw_pixel_text(painter, text, x + scale, y + scale, scale, shadow)
        painter.setPen(Qt.NoPen)
        cursor = x
        for char in text.upper():
            pattern = PIXEL_FONT.get(char)
            if pattern is None:
                cursor += 4 * scale
                continue
            for row, line in enumerate(pattern):
                for col, pixel in enumerate(line):
                    if pixel == "1":
                        painter.fillRect(QRect(cursor + col * scale, y + row * scale, scale, scale), color)
            cursor += (len(pattern[0]) + 1) * scale

    def _pixel_text_width(self, text: str, scale: int, letter_spacing: int) -> int:
        width = 0
        for char in text.upper():
            pattern = PIXEL_FONT.get(char)
            width += ((len(pattern[0]) if pattern else 3) + letter_spacing) * scale
        return max(0, width - letter_spacing * scale)

    def _style_result_button(self, button: QPushButton, *, primary: bool) -> None:
        if primary:
            button.setStyleSheet(
                "QPushButton { background: #C78652; color: #FFF8E8; border: 1px solid #8F6346; "
                "border-radius: 8px; padding: 6px 16px; font-size: 13px; }"
                "QPushButton:hover { background: #A96B3F; }"
            )
        else:
            button.setStyleSheet(
                "QPushButton { background: #FFF8E8; color: #3B271C; border: 1px solid #8F6346; "
                "border-radius: 8px; padding: 6px 16px; font-size: 13px; }"
                "QPushButton:hover { background: #F5D39B; }"
            )

    def _load_high_score(self) -> int:
        try:
            if not self.record_path.exists():
                return 0
            data: Any = json.loads(self.record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
        if not isinstance(data, dict):
            return 0
        try:
            return max(0, int(data.get("high_score", 0)))
        except (TypeError, ValueError):
            return 0

    def _save_high_score_if_needed(self) -> None:
        if self.score <= self.high_score:
            return
        self.high_score = self.score
        self.record_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"high_score": self.high_score}
        self.record_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
