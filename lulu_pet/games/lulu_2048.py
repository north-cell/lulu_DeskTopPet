from __future__ import annotations

import json
import random
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter
from PySide6.QtWidgets import QPushButton, QWidget

from ..paths import resource_path


BOARD_SIZE = 4


class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Lulu2048Window(QWidget):
    finished = Signal()

    def __init__(
        self,
        *,
        play_area: QRect | None = None,
        record_path: Path | None = None,
        seed: int | None = None,
    ):
        super().__init__()
        self.record_path = record_path or resource_path("config", "lulu_2048_records.json")
        self._play_area = QRect(play_area) if play_area else None
        self._rng = random.Random(seed)
        self.board = self._empty_board()
        self.score = 0
        self.high_score = self._load_high_score()
        self.won = False
        self.results_visible = False
        self._closed_signal_emitted = False

        self.setWindowTitle("2048噜")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        if self._play_area:
            self.setGeometry(self._play_area)

        self._again_button = QPushButton("重新开始", self)
        self._again_button.clicked.connect(self.restart_game)
        self._close_button = QPushButton("关闭", self)
        self._close_button.clicked.connect(self.close)
        self._style_result_button(self._again_button, primary=True)
        self._style_result_button(self._close_button, primary=False)
        self._set_result_buttons_visible(False)

    @property
    def max_tile(self) -> int:
        return max(max(row) for row in self.board)

    def restart_game(self) -> None:
        self.board = self._empty_board()
        self.score = 0
        self.won = False
        self.results_visible = False
        self._closed_signal_emitted = False
        self._set_result_buttons_visible(False)
        self._spawn_tile()
        self._spawn_tile()
        self.setFocus()
        self.update()

    def move_tiles(self, direction: Direction, *, spawn_tile: bool = True) -> bool:
        if self.results_visible:
            return False
        original = [row[:] for row in self.board]
        score_gain = 0
        if direction in (Direction.LEFT, Direction.RIGHT):
            new_rows = []
            for row in self.board:
                merged, gain = self._merge_line(row, reverse=direction == Direction.RIGHT)
                new_rows.append(merged)
                score_gain += gain
            self.board = new_rows
        else:
            columns = [[self.board[row][col] for row in range(BOARD_SIZE)] for col in range(BOARD_SIZE)]
            new_columns = []
            for column in columns:
                merged, gain = self._merge_line(column, reverse=direction == Direction.DOWN)
                new_columns.append(merged)
                score_gain += gain
            self.board = [
                [new_columns[col][row] for col in range(BOARD_SIZE)]
                for row in range(BOARD_SIZE)
            ]

        moved = self.board != original
        if not moved:
            if not self._can_move():
                self.finish_game()
            return False

        self.score += score_gain
        if self.max_tile >= 2048:
            self.won = True
        if spawn_tile:
            self._spawn_tile()
        if not self._can_move():
            self.finish_game()
        self.update()
        return True

    def finish_game(self) -> None:
        if self.results_visible:
            return
        self._save_high_score_if_needed()
        self.results_visible = True
        self._set_result_buttons_visible(True)
        self._position_result_buttons()
        self.update()

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        if not self.results_visible and self.board == self._empty_board():
            self.restart_game()

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._position_result_buttons()

    def closeEvent(self, event):  # noqa: N802 - Qt override
        if not self._closed_signal_emitted:
            self._closed_signal_emitted = True
            self.finished.emit()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):  # noqa: N802 - Qt override
        if event.key() == Qt.Key_Escape:
            self.finish_game()
            event.accept()
            return
        direction = self._direction_for_key(event.key())
        if direction:
            self.move_tiles(direction)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(20, 16, 12, 92))
        self._paint_hud(painter)
        self._paint_board(painter)
        if self.results_visible:
            self._paint_results(painter)

    def _merge_line(self, line: list[int], *, reverse: bool = False) -> tuple[list[int], int]:
        values = [value for value in (reversed(line) if reverse else line) if value]
        merged: list[int] = []
        score_gain = 0
        index = 0
        while index < len(values):
            value = values[index]
            if index + 1 < len(values) and values[index + 1] == value:
                value *= 2
                score_gain += value
                index += 2
            else:
                index += 1
            merged.append(value)
        merged.extend([0] * (BOARD_SIZE - len(merged)))
        if reverse:
            merged.reverse()
        return merged, score_gain

    def _spawn_tile(self) -> bool:
        empty_cells = [
            (row, col)
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if self.board[row][col] == 0
        ]
        if not empty_cells:
            return False
        row, col = self._rng.choice(empty_cells)
        self.board[row][col] = 4 if self._rng.random() < 0.1 else 2
        return True

    def _can_move(self) -> bool:
        if any(value == 0 for row in self.board for value in row):
            return True
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                value = self.board[row][col]
                if col + 1 < BOARD_SIZE and self.board[row][col + 1] == value:
                    return True
                if row + 1 < BOARD_SIZE and self.board[row + 1][col] == value:
                    return True
        return False

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

    def _paint_hud(self, painter: QPainter) -> None:
        painter.setPen(QColor("#FFF8E8"))
        painter.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        painter.drawText(24, 36, f"2048噜    分数 {self.score}    最高纪录 {self.high_score}    最大方块 {self.max_tile}")
        if self.won and not self.results_visible:
            painter.setFont(QFont("Microsoft YaHei UI", 11))
            painter.drawText(24, 58, "已经合成 2048，可以继续挑战更高分。")

    def _paint_board(self, painter: QPainter) -> None:
        board = self._board_rect()
        painter.setPen(QColor("#8F6346"))
        painter.setBrush(QColor("#C9A176"))
        painter.drawRoundedRect(board, 12, 12)
        gap = 10
        cell_size = (board.width() - gap * (BOARD_SIZE + 1)) // BOARD_SIZE
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = board.left() + gap + col * (cell_size + gap)
                y = board.top() + gap + row * (cell_size + gap)
                self._paint_tile(painter, QRect(x, y, cell_size, cell_size), self.board[row][col])

    def _paint_tile(self, painter: QPainter, rect: QRect, value: int) -> None:
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._tile_color(value))
        painter.drawRoundedRect(rect, 8, 8)
        if value == 0:
            return
        if value >= 2048:
            painter.setPen(QColor("#5BA84B"))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 7, 7)
        painter.setPen(QColor("#3B271C") if value < 128 else QColor("#FFF8E8"))
        font = QFont("Microsoft YaHei UI", 22 if value < 1000 else 18, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, str(value))

    def _paint_results(self, painter: QPainter) -> None:
        panel = self._result_panel_rect()
        painter.setPen(QColor("#8F6346"))
        painter.setBrush(QColor("#FFF4DA"))
        painter.drawRoundedRect(panel, 10, 10)
        painter.setPen(QColor("#3B271C"))
        painter.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        painter.drawText(panel.adjusted(0, 26, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "2048噜结算")
        painter.setFont(QFont("Microsoft YaHei UI", 14))
        details = f"分数：{self.score}\n最大方块：{self.max_tile}\n最高纪录：{self.high_score}"
        painter.drawText(panel.adjusted(82, 88, -82, -90), Qt.AlignLeft | Qt.AlignTop, details)

    def _board_rect(self) -> QRect:
        area = self._current_play_area()
        size = min(area.width() - 96, area.height() - 130, 520)
        rect = QRect(0, 0, size, size)
        rect.moveCenter(area.center())
        rect.moveTop(max(72, rect.top()))
        return rect

    def _current_play_area(self) -> QRect:
        if self._play_area:
            return QRect(0, 0, self._play_area.width(), self._play_area.height())
        return self.rect() if not self.rect().isEmpty() else QRect(0, 0, 1280, 720)

    def _result_panel_rect(self) -> QRect:
        panel = QRect(0, 0, 380, 270)
        panel.moveCenter(self.rect().center())
        return panel

    def _set_result_buttons_visible(self, visible: bool) -> None:
        self._again_button.setVisible(visible)
        self._close_button.setVisible(visible)

    def _position_result_buttons(self) -> None:
        panel = self._result_panel_rect()
        self._again_button.setGeometry(panel.left() + 66, panel.bottom() - 62, 112, 34)
        self._close_button.setGeometry(panel.right() - 178, panel.bottom() - 62, 112, 34)

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

    def _tile_color(self, value: int) -> QColor:
        colors = {
            0: "#E8CFA8",
            2: "#FFF4DA",
            4: "#F5D39B",
            8: "#E8A05B",
            16: "#D88B47",
            32: "#C9783E",
            64: "#B85D35",
            128: "#A96B3F",
            256: "#9B5E38",
            512: "#8C5232",
            1024: "#7B4D32",
            2048: "#5BA84B",
        }
        return QColor(colors.get(value, "#4D3B2D"))

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

    def _empty_board(self) -> list[list[int]]:
        return [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
