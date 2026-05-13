from __future__ import annotations

import json
import random
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import QPushButton, QWidget

from ..paths import resource_path


MOVE_INTERVAL_MS = 140
CELL_SIZE = 28
HUD_HEIGHT = 58


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self) -> QPoint:
        dx, dy = self.value
        return QPoint(dx, dy)

    def is_opposite(self, other: Direction) -> bool:
        return self.value[0] + other.value[0] == 0 and self.value[1] + other.value[1] == 0


class GreedyLuluWindow(QWidget):
    finished = Signal()

    def __init__(
        self,
        head_asset: Path | None = None,
        *,
        play_area: QRect | None = None,
        record_path: Path | None = None,
        move_interval_ms: int = MOVE_INTERVAL_MS,
    ):
        super().__init__()
        self.head_asset = head_asset or resource_path("assets", "lulu_transparent_gifs", "xhs_lulu_02.gif")
        self.record_path = record_path or resource_path("config", "greedy_lulu_records.json")
        self.move_interval_ms = move_interval_ms
        self._play_area = QRect(play_area) if play_area else None
        self.snake: list[QPoint] = []
        self.direction = Direction.RIGHT
        self.food = QPoint()
        self.score = 0
        self.high_score = self._load_high_score()
        self.results_visible = False
        self._closed_signal_emitted = False
        self._head_movie: QMovie | None = None
        self._head_pixmap = QPixmap()

        self.setWindowTitle("贪吃噜")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        if self._play_area:
            self.setGeometry(self._play_area)

        self._move_timer = QTimer(self)
        self._move_timer.timeout.connect(self.advance_snake)

        self._again_button = QPushButton("重新开始", self)
        self._again_button.clicked.connect(self.restart_game)
        self._close_button = QPushButton("关闭", self)
        self._close_button.clicked.connect(self.close)
        self._style_result_button(self._again_button, primary=True)
        self._style_result_button(self._close_button, primary=False)
        self._set_result_buttons_visible(False)
        self._load_head_asset()

    @property
    def columns(self) -> int:
        return max(12, self._board_rect().width() // CELL_SIZE)

    @property
    def rows(self) -> int:
        return max(8, self._board_rect().height() // CELL_SIZE)

    def restart_game(self) -> None:
        self.score = 0
        self.direction = Direction.RIGHT
        center_x = self.columns // 2
        center_y = min(self.rows - 2, self.rows // 2 + 1)
        self.snake = [QPoint(center_x, center_y), QPoint(center_x - 1, center_y), QPoint(center_x - 2, center_y)]
        self.food = self._random_empty_cell()
        self.results_visible = False
        self._closed_signal_emitted = False
        self._set_result_buttons_visible(False)
        self._move_timer.start(self.move_interval_ms)
        self.setFocus()
        self.update()

    def finish_game(self) -> None:
        if self.results_visible:
            return
        self._save_high_score_if_needed()
        self.results_visible = True
        self._move_timer.stop()
        self._set_result_buttons_visible(True)
        self._position_result_buttons()
        self.update()

    def advance_snake(self) -> None:
        if self.results_visible or not self.snake:
            return
        next_head = self.snake[0] + self.direction.delta
        if self._is_wall_collision(next_head) or next_head in self.snake:
            self.finish_game()
            return
        ate_food = next_head == self.food
        self.snake.insert(0, next_head)
        if ate_food:
            self.score += 1
            self.food = self._random_empty_cell()
        else:
            self.snake.pop()
        self.update()

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        if not self.results_visible and not self._move_timer.isActive():
            self.restart_game()

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._position_result_buttons()

    def closeEvent(self, event):  # noqa: N802 - Qt override
        self._move_timer.stop()
        if self._head_movie:
            self._head_movie.stop()
        if not self._closed_signal_emitted:
            self._closed_signal_emitted = True
            self.finished.emit()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):  # noqa: N802 - Qt override
        if event.key() == Qt.Key_Escape:
            self.finish_game()
            event.accept()
            return
        new_direction = self._direction_for_key(event.key())
        if new_direction and not new_direction.is_opposite(self.direction):
            self.direction = new_direction
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(20, 16, 12, 92))
        self._paint_hud(painter)
        self._paint_board(painter)
        if self.results_visible:
            self._paint_results(painter)

    def _direction_for_key(self, key: int) -> Direction | None:
        return {
            Qt.Key_Up: Direction.UP,
            Qt.Key_W: Direction.UP,
            Qt.Key_Down: Direction.DOWN,
            Qt.Key_S: Direction.DOWN,
            Qt.Key_Left: Direction.LEFT,
            Qt.Key_A: Direction.LEFT,
            Qt.Key_Right: Direction.RIGHT,
            Qt.Key_D: Direction.RIGHT,
        }.get(key)

    def _is_wall_collision(self, cell: QPoint) -> bool:
        return cell.x() < 0 or cell.y() < 0 or cell.x() >= self.columns or cell.y() >= self.rows

    def _random_empty_cell(self) -> QPoint:
        occupied = {(cell.x(), cell.y()) for cell in self.snake}
        empty = [
            QPoint(x, y)
            for y in range(self.rows)
            for x in range(self.columns)
            if (x, y) not in occupied
        ]
        if not empty:
            self.finish_game()
            return QPoint()
        return random.choice(empty)

    def _load_head_asset(self) -> None:
        movie = QMovie(str(self.head_asset))
        if movie.isValid():
            movie.setCacheMode(QMovie.CacheAll)
            movie.frameChanged.connect(lambda _: self._set_head_frame(movie))
            self._head_movie = movie
            movie.start()
            self._set_head_frame(movie)
            return
        pixmap = QPixmap(str(self.head_asset))
        if not pixmap.isNull():
            self._head_pixmap = pixmap

    def _set_head_frame(self, movie: QMovie) -> None:
        self._head_pixmap = movie.currentPixmap()
        self.update()

    def _paint_hud(self, painter: QPainter) -> None:
        painter.setPen(QColor("#FFF8E8"))
        painter.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        painter.drawText(24, 36, f"贪吃噜    小桔子 {self.score}    最高纪录 {self.high_score}")

    def _paint_board(self, painter: QPainter) -> None:
        board = self._board_rect()
        painter.setPen(QColor(143, 99, 70, 170))
        painter.setBrush(QColor(255, 244, 218, 26))
        painter.drawRoundedRect(board, 10, 10)
        if not self.results_visible:
            self._paint_orange(painter, self._cell_rect(self.food), scale=0.92)
        for index, cell in enumerate(reversed(self.snake[1:])):
            self._paint_orange(painter, self._cell_rect(cell), scale=0.86 + min(index, 5) * 0.01)
        if self.snake:
            self._paint_head(painter, self._cell_rect(self.snake[0]))

    def _paint_head(self, painter: QPainter, rect: QRect) -> None:
        target = rect.adjusted(-5, -8, 5, 3)
        if not self._head_pixmap.isNull():
            painter.drawPixmap(target, self._head_pixmap)
            return
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#8A5D40"))
        painter.drawEllipse(target)

    def _paint_orange(self, painter: QPainter, rect: QRect, *, scale: float = 1.0) -> None:
        size = int(min(rect.width(), rect.height()) * scale)
        body = QRect(0, 0, size, size)
        body.moveCenter(rect.center())
        painter.setPen(QColor(190, 91, 26))
        painter.setBrush(QColor(248, 148, 45))
        painter.drawEllipse(body)
        leaf = QRect(body.center().x(), body.top() - max(2, size // 7), max(8, size // 3), max(5, size // 5))
        painter.setPen(QColor(76, 132, 58))
        painter.setBrush(QColor(91, 168, 75))
        painter.drawEllipse(leaf)
        painter.setPen(QColor(111, 77, 40))
        painter.drawLine(body.center().x(), body.top() + 2, leaf.left() + 2, leaf.bottom())

    def _paint_results(self, painter: QPainter) -> None:
        panel = self._result_panel_rect()
        painter.setPen(QColor("#8F6346"))
        painter.setBrush(QColor("#FFF4DA"))
        painter.drawRoundedRect(panel, 10, 10)
        painter.setPen(QColor("#3B271C"))
        painter.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        painter.drawText(panel.adjusted(0, 26, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "贪吃噜结算")
        painter.setFont(QFont("Microsoft YaHei UI", 14))
        details = f"本局小桔子：{self.score}\n最高纪录：{self.high_score}"
        painter.drawText(panel.adjusted(82, 92, -82, -90), Qt.AlignLeft | Qt.AlignTop, details)

    def _board_rect(self) -> QRect:
        area = self._current_play_area()
        return QRect(area.left() + 24, area.top() + HUD_HEIGHT, area.width() - 48, area.height() - HUD_HEIGHT - 24)

    def _current_play_area(self) -> QRect:
        if self._play_area:
            return QRect(0, 0, self._play_area.width(), self._play_area.height())
        return self.rect() if not self.rect().isEmpty() else QRect(0, 0, 1280, 720)

    def _cell_rect(self, cell: QPoint) -> QRect:
        board = self._board_rect()
        x = board.left() + cell.x() * CELL_SIZE
        y = board.top() + cell.y() * CELL_SIZE
        return QRect(x, y, CELL_SIZE, CELL_SIZE)

    def _set_result_buttons_visible(self, visible: bool) -> None:
        self._again_button.setVisible(visible)
        self._close_button.setVisible(visible)

    def _position_result_buttons(self) -> None:
        panel = self._result_panel_rect()
        self._again_button.setGeometry(panel.left() + 66, panel.bottom() - 62, 112, 34)
        self._close_button.setGeometry(panel.right() - 178, panel.bottom() - 62, 112, 34)

    def _result_panel_rect(self) -> QRect:
        panel = QRect(0, 0, 380, 250)
        panel.moveCenter(self.rect().center())
        return panel

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
