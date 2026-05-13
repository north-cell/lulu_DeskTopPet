from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import QPushButton, QWidget

from ..paths import resource_path


GAME_DURATION_MS = 30_000
TARGET_VISIBLE_MS = 700
TARGET_SIZE = 128


class WhackLuluWindow(QWidget):
    finished = Signal()

    def __init__(
        self,
        target_asset: Path | None = None,
        *,
        play_area: QRect | None = None,
        record_path: Path | None = None,
        duration_ms: int = GAME_DURATION_MS,
        target_visible_ms: int = TARGET_VISIBLE_MS,
    ):
        super().__init__()
        self.target_asset = target_asset or resource_path("assets", "lulu_transparent_gifs", "qq_lulu_15.gif")
        self.record_path = record_path or resource_path("config", "whack_lulu_records.json")
        self.duration_ms = duration_ms
        self.target_visible_ms = target_visible_ms
        self._play_area = QRect(play_area) if play_area else None
        self.hits = 0
        self.misses = 0
        self.combo = 0
        self.best_combo = 0
        self.high_score = self._load_high_score()
        self.target_rect = QRect()
        self.results_visible = False
        self._started_at = 0.0
        self._closed_signal_emitted = False
        self._target_movie: QMovie | None = None
        self._target_pixmap = QPixmap()

        self.setWindowTitle("打噜鼠")
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        if self._play_area:
            self.setGeometry(self._play_area)

        self._target_timer = QTimer(self)
        self._target_timer.setSingleShot(True)
        self._target_timer.timeout.connect(self.miss_target)

        self._game_timer = QTimer(self)
        self._game_timer.setSingleShot(True)
        self._game_timer.timeout.connect(self.finish_game)

        self._hud_timer = QTimer(self)
        self._hud_timer.timeout.connect(self.update)

        self._again_button = QPushButton("再玩一次", self)
        self._again_button.clicked.connect(self.restart_game)
        self._close_button = QPushButton("关闭", self)
        self._close_button.clicked.connect(self.close)
        self._style_result_button(self._again_button, primary=True)
        self._style_result_button(self._close_button, primary=False)
        self._set_result_buttons_visible(False)
        self._load_target_asset()

    @property
    def accuracy_percent(self) -> int:
        attempts = self.hits + self.misses
        return round((self.hits / attempts) * 100) if attempts else 0

    def restart_game(self) -> None:
        self.hits = 0
        self.misses = 0
        self.combo = 0
        self.best_combo = 0
        self.results_visible = False
        self._closed_signal_emitted = False
        self._set_result_buttons_visible(False)
        self._started_at = time.monotonic()
        self._game_timer.start(self.duration_ms)
        self._hud_timer.start(100)
        self._spawn_target()
        self.update()

    def hit_target(self) -> None:
        if self.results_visible:
            return
        self.hits += 1
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        self._spawn_target()
        self.update()

    def miss_target(self) -> None:
        if self.results_visible:
            return
        self.misses += 1
        self.combo = 0
        self._spawn_target()
        self.update()

    def finish_game(self) -> None:
        if self.results_visible:
            return
        self._save_high_score_if_needed()
        self.results_visible = True
        self._target_timer.stop()
        self._game_timer.stop()
        self._hud_timer.stop()
        self._set_result_buttons_visible(True)
        self._position_result_buttons()
        self.update()

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        if not self.results_visible and not self._game_timer.isActive():
            self.restart_game()

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._position_result_buttons()

    def closeEvent(self, event):  # noqa: N802 - Qt override
        self._target_timer.stop()
        self._game_timer.stop()
        self._hud_timer.stop()
        if self._target_movie:
            self._target_movie.stop()
        if not self._closed_signal_emitted:
            self._closed_signal_emitted = True
            self.finished.emit()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):  # noqa: N802 - Qt override
        if event.key() == Qt.Key_Escape:
            self.finish_game()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and not self.results_visible:
            if self.target_rect.contains(event.position().toPoint()):
                self.hit_target()
                event.accept()
                return
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(20, 16, 12, 86))
        self._paint_hud(painter)
        if self.results_visible:
            self._paint_results(painter)
        else:
            self._paint_target(painter)

    def _load_target_asset(self) -> None:
        movie = QMovie(str(self.target_asset))
        if movie.isValid():
            movie.setCacheMode(QMovie.CacheAll)
            movie.frameChanged.connect(lambda _: self._set_target_frame(movie))
            self._target_movie = movie
            movie.start()
            self._set_target_frame(movie)
            return
        pixmap = QPixmap(str(self.target_asset))
        if not pixmap.isNull():
            self._target_pixmap = pixmap

    def _set_target_frame(self, movie: QMovie) -> None:
        self._target_pixmap = movie.currentPixmap()
        self.update(self.target_rect)

    def _spawn_target(self) -> None:
        area = self._current_play_area()
        size = min(TARGET_SIZE, max(64, area.width() // 4), max(64, area.height() // 4))
        max_x = max(area.left(), area.right() - size)
        max_y = max(area.top() + 54, area.bottom() - size)
        old_rect = QRect(self.target_rect)
        for _ in range(8):
            x = random.randint(area.left(), max_x)
            y = random.randint(area.top() + 54, max_y)
            candidate = QRect(x, y, size, size)
            if candidate != old_rect:
                self.target_rect = candidate
                break
        else:
            self.target_rect = QRect(area.left(), area.top() + 54, size, size)
        self._target_timer.start(self.target_visible_ms)

    def _current_play_area(self) -> QRect:
        if self._play_area:
            return QRect(0, 0, self._play_area.width(), self._play_area.height())
        return self.rect() if not self.rect().isEmpty() else QRect(0, 0, 1280, 720)

    def _remaining_seconds(self) -> int:
        if not self._started_at:
            return self.duration_ms // 1000
        elapsed_ms = int((time.monotonic() - self._started_at) * 1000)
        return max(0, (self.duration_ms - elapsed_ms + 999) // 1000)

    def _paint_hud(self, painter: QPainter) -> None:
        painter.setPen(QColor("#FFF8E8"))
        painter.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        text = f"剩余 {self._remaining_seconds()}s    命中 {self.hits}    漏掉 {self.misses}    连击 {self.combo}"
        painter.drawText(24, 36, text)

    def _paint_target(self, painter: QPainter) -> None:
        if not self.target_rect.isValid():
            return
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 244, 218, 76))
        painter.drawEllipse(self.target_rect.adjusted(-8, -8, 8, 8))
        if not self._target_pixmap.isNull():
            painter.drawPixmap(self.target_rect, self._target_pixmap)
            return
        painter.setBrush(QColor("#C78652"))
        painter.drawEllipse(self.target_rect)

    def _paint_results(self, painter: QPainter) -> None:
        panel = self._result_panel_rect()
        painter.setPen(QColor("#8F6346"))
        painter.setBrush(QColor("#FFF4DA"))
        painter.drawRoundedRect(panel, 10, 10)

        painter.setPen(QColor("#3B271C"))
        painter.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        painter.drawText(panel.adjusted(0, 26, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "打噜鼠结算")
        painter.setFont(self._result_details_font())
        details = (
            f"命中：{self.hits}\n"
            f"漏掉：{self.misses}\n"
            f"准确率：{self.accuracy_percent}%\n"
            f"最高连击：{self.best_combo}\n"
            f"最高纪录：{self.high_score}"
        )
        painter.drawText(self._result_details_rect(), Qt.AlignLeft | Qt.AlignTop, details)

    def _set_result_buttons_visible(self, visible: bool) -> None:
        self._again_button.setVisible(visible)
        self._close_button.setVisible(visible)

    def _position_result_buttons(self) -> None:
        panel = self._result_panel_rect()
        self._again_button.setGeometry(panel.left() + 72, panel.bottom() - 62, 104, 34)
        self._close_button.setGeometry(panel.right() - 176, panel.bottom() - 62, 104, 34)

    def _result_panel_rect(self) -> QRect:
        panel = QRect(0, 0, 380, 300)
        panel.moveCenter(self.rect().center())
        return panel

    def _result_details_rect(self) -> QRect:
        return self._result_panel_rect().adjusted(72, 78, -72, -96)

    def _result_details_font(self) -> QFont:
        return QFont("Microsoft YaHei UI", 13)

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
        if self.hits <= self.high_score:
            return
        self.high_score = self.hits
        self.record_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"high_score": self.high_score}
        self.record_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
