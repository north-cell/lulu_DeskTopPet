from __future__ import annotations

import time
import random
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QBitmap, QColor, QImage, QMovie, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .bubble import BubbleWidget
from .contract_dialog import ContractDialog
from .controller import PetController
from .focus_records import FocusRecord, FocusRecordStore
from .focus_records_dialog import FocusRecordsDialog
from .focus_timer import FocusTimerWidget
from .games.whack_lulu import WhackLuluWindow
from .interaction import DragIntentTracker
from .menu_style import apply_lulu_menu_style
from .models import PetSettings
from .motion import DesktopBounds, MotionEngine, MotionFrame, MotionMode
from .native_window import remove_windows_frame_artifacts
from .paths import resource_path
from .settings import SettingsStore
from .settings_dialog import SettingsDialog
from .sticker_popup import StickerPopup


LOW_QUALITY_STICKER_GIFS = {
    "lulu_transparent_15.gif",
    "lulu_transparent_16.gif",
    "lulu_transparent_17.gif",
    "lulu_transparent_19.gif",
    "lulu_transparent_20.gif",
}

STICKER_PLAYBACK_SPEED_PERCENT = 75
DEFAULT_CHARACTER_GIF = "lulu_transparent_09.gif"
SWIMMING_CHARACTER_GIF = "lulu_transparent_01.gif"
LIFTED_CHARACTER_GIF = "xhs_lulu_01.gif"
PAJAMA_CHARACTER_GIF = "xhs_lulu_02.gif"
FOCUS_STAGE_SECONDS = 5 * 60
FOCUS_STICKER_DURATION_MS = 2600


class PetWindow(QWidget):
    def __init__(
        self,
        controller: PetController,
        settings: PetSettings,
        settings_store: SettingsStore | None = None,
        focus_record_store: FocusRecordStore | None = None,
    ):
        super().__init__()
        self.controller = controller
        self.settings = settings
        self.settings_store = settings_store
        self.focus_record_store = focus_record_store or FocusRecordStore(resource_path("config", "focus_records.json"))
        self._drag_offset = QPoint()
        self._press_global = QPoint()
        self._dragging = False
        self._drag_intent = DragIntentTracker()
        self._bubble = BubbleWidget()
        self._sticker = StickerPopup()
        self._always_on_top = settings.always_on_top
        self._has_been_shown = False
        self._motion_frame: MotionFrame | None = None
        self._movie: QMovie | None = None
        self._pixmap = QPixmap()
        self._sticker_movie: QMovie | None = None
        self._sticker_pixmap = QPixmap()
        self._sticker_active = False
        self._last_sticker_path: Path | None = None
        self._sticker_play_once = False
        self._next_sticker_index = 0
        self._resting = False
        self._motion_paused = False
        self._focus_active = False
        self._focus_started_at = 0.0
        self._focus_started_wall_time: datetime | None = None
        self._focus_stage_index = -1
        self._focus_character_asset: Path | None = None
        self._sticker_timer = QTimer(self)
        self._sticker_timer.setSingleShot(True)
        self._sticker_timer.timeout.connect(self._clear_sticker)
        self._sticker_assets = self._load_sticker_assets()
        self._focus_timer = FocusTimerWidget()
        self._focus_timer.finished_requested.connect(self.end_focus_mode)
        self._focus_records_dialog: FocusRecordsDialog | None = None
        self._active_game_window: WhackLuluWindow | None = None
        self._pre_game_visible = False
        self._pre_game_motion_paused = False
        self._character_key = ""
        self._rest_character_asset = resource_path("assets", "lulu_transparent_gifs", "qq_lulu_04.gif")
        self._default_character_asset = resource_path("assets", "lulu_transparent_gifs", DEFAULT_CHARACTER_GIF)
        self._swimming_character_asset = resource_path("assets", "lulu_transparent_gifs", SWIMMING_CHARACTER_GIF)
        self._lifted_character_asset = resource_path("assets", "lulu_transparent_gifs", LIFTED_CHARACTER_GIF)
        self._pajama_character_asset = resource_path("assets", "lulu_transparent_gifs", PAJAMA_CHARACTER_GIF)
        self._character_assets = {
            "body": self._default_character_asset,
            "lifted": self._lifted_character_asset,
            "rest": self._rest_character_asset,
        }
        self._focus_assets = [
            resource_path("assets", "lulu_FocusMode", f"{index}.gif")
            for index in range(1, 6)
        ]
        self._focus_finish_asset = resource_path("assets", "lulu_FocusMode", "6.gif")

        self.setWindowTitle("水豚噜噜")
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowFlags(self._window_flags())
        self.resize(*settings.window_size)
        self.motion = MotionEngine(
            self._desktop_bounds(),
            settings.window_size,
            speed_scale=settings.motion_speed_percent / 100,
        )
        self.move(self.motion.x, self.motion.y)
        self._motion_frame = self.motion.tick()
        self._apply_character_for_mode(self._motion_frame.mode)

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(55)

        self._speech_timer = QTimer(self)
        self._speech_timer.timeout.connect(self._say_random_line)
        self._speech_timer.start(5000)

    def set_always_on_top(self, enabled: bool, *, save_settings: bool = True) -> None:
        self._always_on_top = enabled
        self.settings = replace(self.settings, always_on_top=enabled)
        if save_settings and self.settings_store:
            self.settings_store.save(self.settings)
        visible = self.isVisible()
        self.setWindowFlags(self._window_flags())
        if visible:
            self.show()
            self._remove_native_frame_artifacts()

    def toggle_visible(self) -> None:
        self.hide() if self.isVisible() else self.show()

    @property
    def motion_paused(self) -> bool:
        return self._motion_paused

    @property
    def focus_mode_active(self) -> bool:
        return self._focus_active

    def set_motion_paused(self, paused: bool) -> None:
        self._motion_paused = paused

    def trigger_random_action(self) -> None:
        mode = self.motion_random_mode()
        self.motion.start(mode)
        self._say_random_line(force=True)

    def trigger_rest(self) -> None:
        self._enter_rest_mode()
        self._bubble.show_message("噜噜提醒你休息一下。", self)

    def trigger_sticker(self) -> None:
        if self._focus_active:
            return
        source = self._next_sticker_asset() if self._sticker_assets else self.controller.assets.random_file_path()
        self._load_sticker(source or self._character_assets["body"])

    def trigger_focus_mode(self) -> None:
        if self._focus_active:
            return
        self._focus_active = True
        self._focus_started_at = time.monotonic()
        self._focus_started_wall_time = datetime.now()
        self._focus_stage_index = -1
        self._resting = False
        self._dragging = False
        self._drag_intent.release()
        self._bubble.hide()
        self._clear_sticker()
        self.motion.start(MotionMode.IDLE, duration_ticks=999999)
        self.motion.x = self.motion.bounds.right - self.width()
        self.motion.y = self.motion.bounds.bottom - self.height()
        self._motion_frame = MotionFrame(
            MotionMode.IDLE,
            int(self.motion.x),
            int(self.motion.y),
            self.motion.frame_index,
            self.motion.facing,
        )
        self.move(self._motion_frame.x, self._motion_frame.y)
        self._update_focus_stage()
        self._focus_timer.show_for(self, 0)
        self.update()

    def end_focus_mode(self) -> None:
        if not self._focus_active:
            return
        focused_seconds = self._focus_elapsed_seconds()
        self._save_focus_record(focused_seconds)
        self._focus_active = False
        self._focus_started_wall_time = None
        self._focus_timer.hide()
        self._focus_stage_index = -1
        self._focus_character_asset = None
        self._character_key = ""
        self._apply_character_for_mode(self.motion.mode)
        self._load_sticker(self._focus_finish_asset, duration_ms=FOCUS_STICKER_DURATION_MS, play_once=True)
        self._bubble.show_message(
            f"谢谢你陪本噜噜大王学习 {self._format_focus_duration(focused_seconds)}",
            self,
            duration_ms=FOCUS_STICKER_DURATION_MS,
        )

    def show_swimming_character(self) -> None:
        self._set_body_character(self._swimming_character_asset)

    def show_pajama_character(self) -> None:
        self._set_body_character(self._pajama_character_asset)

    def show_proud_character(self) -> None:
        self._set_body_character(self._default_character_asset)

    def sign_contract(self) -> None:
        text, accepted = ContractDialog.get_contract_name(self.settings.contract_name, self)
        if not accepted:
            return
        contract_name = text.strip()[:12]
        if not contract_name:
            return
        self.settings = replace(self.settings, contract_name=contract_name)
        self.controller.set_contract_name(contract_name)
        if self.settings_store:
            self.settings_store.save(self.settings)
        self._bubble.show_message("契约签订成功，噜噜以后会这样叫你。", self)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != dialog.Accepted:
            return
        self.settings = dialog.to_settings(self.settings)
        self.controller.speech_interval_seconds = self.settings.speech_interval_seconds
        self.motion.speed_scale = self.settings.motion_speed_percent / 100
        self.set_always_on_top(self.settings.always_on_top, save_settings=False)
        if self.settings_store:
            self.settings_store.save(self.settings)

    def motion_random_mode(self) -> MotionMode:
        return time_random_motion()

    def context_menu(self) -> QMenu:
        menu = apply_lulu_menu_style(QMenu(self))
        if self._focus_active:
            menu.addAction("结束专注模式", self.end_focus_mode)
            menu.addAction("学习记录", self.show_focus_records)
            menu.addSeparator()
            menu.addAction("退出", QApplication.instance().quit)
            return menu

        self.add_focus_mode_menu(menu)
        self.add_games_menu(menu)
        menu.addAction("休息一下", self.trigger_rest)
        menu.addAction("签订契约", self.sign_contract)
        self.add_character_change_menu(menu)
        menu.addSeparator()

        visible_action = QAction("隐藏" if self.isVisible() else "显示", menu)
        visible_action.triggered.connect(self.toggle_visible)
        menu.addAction(visible_action)

        pause_action = QAction("暂停移动", menu)
        pause_action.setCheckable(True)
        pause_action.setChecked(self._motion_paused)
        pause_action.triggered.connect(self.set_motion_paused)
        menu.addAction(pause_action)

        top_action = QAction("保持置顶", menu)
        top_action.setCheckable(True)
        top_action.setChecked(self._always_on_top)
        top_action.triggered.connect(self.set_always_on_top)
        menu.addAction(top_action)

        menu.addSeparator()
        menu.addAction("退出", QApplication.instance().quit)
        return menu

    def add_character_change_menu(self, menu: QMenu) -> QMenu:
        change_menu = apply_lulu_menu_style(QMenu("更换形象", menu))
        change_menu.addAction("游泳噜噜", self.show_swimming_character)
        change_menu.addAction("睡衣噜噜", self.show_pajama_character)
        change_menu.addAction("得瑟噜噜", self.show_proud_character)
        menu.addMenu(change_menu)
        return change_menu

    def add_focus_mode_menu(self, menu: QMenu, start_focus_callback=None) -> QMenu:
        focus_menu = apply_lulu_menu_style(QMenu("专注模式", menu))
        focus_menu.addAction("开始专注", start_focus_callback or self.trigger_focus_mode)
        focus_menu.addAction("学习记录", self.show_focus_records)
        menu.addMenu(focus_menu)
        return focus_menu

    def add_games_menu(self, menu: QMenu) -> QMenu:
        games_menu = apply_lulu_menu_style(QMenu("小游戏", menu))
        games_menu.addAction("打噜鼠", self.start_whack_lulu_game)
        menu.addMenu(games_menu)
        return games_menu

    def start_whack_lulu_game(self) -> None:
        if self._focus_active:
            return
        if self._active_game_window:
            self._active_game_window.raise_()
            self._active_game_window.activateWindow()
            return
        self._pre_game_visible = self.isVisible()
        self._pre_game_motion_paused = self._motion_paused
        self._bubble.hide()
        self._sticker.hide()
        self._clear_sticker()
        self.set_motion_paused(True)
        self.hide()
        game = WhackLuluWindow()
        game.finished.connect(self._restore_after_game)
        self._active_game_window = game
        game.showFullScreen()

    def show_focus_records(self) -> None:
        if self._focus_records_dialog:
            self._focus_records_dialog.close()
        self._focus_records_dialog = FocusRecordsDialog(
            self.focus_record_store.load(),
            self,
            record_store=self.focus_record_store,
        )
        self._focus_records_dialog.show()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._drag_offset = self._press_global - self.frameGeometry().topLeft()
            self._dragging = False
            self._drag_intent.press(self._press_global.x(), self._press_global.y())
            event.accept()
        elif event.button() == Qt.RightButton:
            self.context_menu().exec(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        if self._focus_active:
            event.accept()
            return
        if self._dragging and event.buttons() & Qt.LeftButton:
            self._move_drag(event.globalPosition().toPoint())
        elif event.buttons() & Qt.LeftButton:
            global_pos = event.globalPosition().toPoint()
            if self._drag_intent.move(global_pos.x(), global_pos.y()):
                self._leave_rest_mode()
                self._dragging = True
                self.controller.start_drag()
                self.motion.start_drag()
                self._move_drag(global_pos)
        event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override
        if self._focus_active and event.button() == Qt.LeftButton:
            self._drag_intent.release()
            self._dragging = False
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._dragging:
            self._drag_intent.release()
            self._dragging = False
            self.motion.release_drag()
            self.controller.end_drag()
            event.accept()
        elif event.button() == Qt.LeftButton:
            self._drag_intent.release()
            self.controller.handle_click()
            event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton:
            if self._focus_active:
                event.accept()
                return
            self.controller.handle_click()
            self.trigger_sticker()
            self._say_random_line(force=True)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if self._sticker_active and not self._sticker_pixmap.isNull():
            self._paint_pixmap(painter, self._sticker_pixmap, self._motion_frame)
        elif self._motion_frame and not self._pixmap.isNull():
            self._paint_character(painter, self._motion_frame)
        else:
            self._paint_placeholder(painter)

    def closeEvent(self, event):  # noqa: N802 - Qt override
        self._bubble.hide()
        self._sticker.hide()
        self._clear_sticker()
        self._focus_timer.hide()
        event.accept()

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        self._has_been_shown = True
        self._remove_native_frame_artifacts()

    def hideEvent(self, event):  # noqa: N802 - Qt override
        self._bubble.hide()
        super().hideEvent(event)

    def moveEvent(self, event):  # noqa: N802 - Qt override
        super().moveEvent(event)
        if hasattr(self._bubble, "follow_anchor"):
            self._bubble.follow_anchor(self)

    def _window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint | Qt.BypassWindowManagerHint
        if self._always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        return flags

    def _remove_native_frame_artifacts(self) -> None:
        remove_windows_frame_artifacts(int(self.winId()))

    def _on_tick(self) -> None:
        if self._focus_active:
            self._update_focus_stage()
            self._focus_timer.set_elapsed(self._focus_elapsed_seconds())
            self.update()
            return
        if self._sticker_active:
            if self._sticker_movie:
                self._sticker_movie.jumpToNextFrame()
            self.update()
            return
        if self._resting:
            self.update()
            return
        if self._motion_paused:
            self.update()
            return
        self._motion_frame = self.motion.tick()
        self.move(self._motion_frame.x, self._motion_frame.y)
        self._apply_character_for_mode(self._motion_frame.mode)
        self.update()

    def _move_drag(self, global_pos: QPoint) -> None:
        target = global_pos - self._drag_offset
        frame = self.motion.drag_to(target.x(), target.y())
        self._motion_frame = frame
        self.move(frame.x, frame.y)
        self._apply_character_for_mode(frame.mode)
        self.update()

    def _say_random_line(self, force: bool = False) -> None:
        if self._has_been_shown and not self.isVisible():
            self._bubble.hide()
            return
        if force:
            line = self.controller.random_line(self.controller.current_action.name)
        else:
            line = self.controller.next_line(time.monotonic())
        self._bubble.show_message(line, self)

    def _paint_placeholder(self, painter: QPainter) -> None:
        body = QRect(28, 48, self.width() - 56, self.height() - 72)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(151, 111, 82))
        painter.drawRoundedRect(body, 38, 38)

        painter.setBrush(QColor(119, 86, 65))
        painter.drawEllipse(body.left() + 22, body.top() - 16, 30, 28)
        painter.drawEllipse(body.right() - 52, body.top() - 16, 30, 28)

        painter.setBrush(QColor(35, 25, 20))
        painter.drawEllipse(body.left() + 45, body.top() + 30, 8, 8)
        painter.drawEllipse(body.right() - 53, body.top() + 30, 8, 8)
        painter.setPen(QPen(QColor(45, 32, 24), 3))
        painter.drawArc(body.center().x() - 12, body.top() + 50, 24, 12, 180 * 16, 180 * 16)

    def _paint_character(self, painter: QPainter, frame: MotionFrame) -> None:
        self._paint_pixmap(painter, self._pixmap, frame)

    def _paint_pixmap(self, painter: QPainter, pixmap: QPixmap, frame: MotionFrame | None) -> None:
        target = self._fit_rect(pixmap.size())
        painter.save()
        if frame and frame.mode in (MotionMode.ROLL_LEFT, MotionMode.ROLL_RIGHT):
            painter.translate(self.rect().center())
            painter.rotate(frame.rotation_degrees)
            painter.translate(-self.rect().center())
        if frame and frame.facing > 0:
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)
            target.moveLeft(self.width() - target.right())
        painter.drawPixmap(target, pixmap)
        painter.restore()

    def _fit_rect(self, source_size) -> QRect:
        source_w = max(1, source_size.width())
        source_h = max(1, source_size.height())
        scale = min(self.width() / source_w, self.height() / source_h)
        target_w = int(source_w * scale)
        target_h = int(source_h * scale)
        return QRect((self.width() - target_w) // 2, self.height() - target_h, target_w, target_h)

    def _apply_character_for_mode(self, mode: MotionMode) -> None:
        key = self._character_key_for_mode(mode)
        if key == self._character_key:
            return
        self._character_key = key
        self._load_character(self._character_assets[key])

    def _character_key_for_mode(self, mode: MotionMode) -> str:
        if mode in (MotionMode.DRAGGED, MotionMode.FALLING):
            return "lifted"
        return "body"

    def _load_character(self, path: Path) -> None:
        if self._movie:
            self._movie.stop()
        self._movie = None
        self._pixmap = QPixmap()
        movie = QMovie(str(path))
        if movie.isValid():
            movie.frameChanged.connect(lambda _: self._set_character_frame(movie))
            self._movie = movie
            movie.start()
            self._set_character_frame(movie)
            return
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            self._pixmap = pixmap

    def _set_body_character(self, path: Path) -> None:
        self._character_assets["body"] = path
        self._resting = False
        self._clear_sticker()
        self._character_key = ""
        self._apply_character_for_mode(self.motion.mode)
        self.update()

    def _set_character_frame(self, movie: QMovie) -> None:
        self._pixmap = movie.currentPixmap()
        if not self._sticker_active:
            self._apply_alpha_mask(self._pixmap)
        self.update()

    def _load_sticker(self, path: Path, duration_ms: int = 2600, play_once: bool = False) -> None:
        self._clear_sticker()
        self._last_sticker_path = path
        self._sticker_play_once = play_once
        movie = QMovie(str(path))
        if movie.isValid():
            movie.setCacheMode(QMovie.CacheAll)
            movie.setSpeed(STICKER_PLAYBACK_SPEED_PERCENT)
            movie.frameChanged.connect(lambda _: self._set_sticker_frame(movie))
            self._sticker_movie = movie
            self._sticker_active = True
            movie.start()
            self._set_sticker_frame(movie)
        else:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self._sticker_pixmap = pixmap
                self._sticker_active = True
        if self._sticker_active:
            self._sticker_timer.start(duration_ms)
            self.update()

    def _next_sticker_asset(self) -> Path:
        source = self._sticker_assets[self._next_sticker_index % len(self._sticker_assets)]
        self._next_sticker_index += 1
        return source

    def _load_sticker_assets(self) -> list[Path]:
        sticker_dir = resource_path("assets", "lulu_transparent_gifs")
        return [
            path
            for path in sorted(sticker_dir.glob("*.gif"))
            if path.name not in LOW_QUALITY_STICKER_GIFS
        ]

    def _enter_rest_mode(self) -> None:
        self._resting = True
        self._clear_sticker()
        self.motion.start(MotionMode.SLEEP, duration_ticks=999999)
        self.motion.x = self.motion.bounds.right - self.width()
        self.motion.y = self.motion.bounds.bottom - self.height()
        self._motion_frame = MotionFrame(
            MotionMode.SLEEP,
            int(self.motion.x),
            int(self.motion.y),
            self.motion.frame_index,
            self.motion.facing,
        )
        self.move(self._motion_frame.x, self._motion_frame.y)
        self._character_key = "rest"
        self._load_character(self._rest_character_asset)
        self.update()

    def _leave_rest_mode(self) -> None:
        if not self._resting:
            return
        self._resting = False
        self._character_key = ""
        self._apply_character_for_mode(self.motion.mode)

    def _set_sticker_frame(self, movie: QMovie) -> None:
        self._sticker_pixmap = movie.currentPixmap()
        self._apply_alpha_mask(self._sticker_pixmap)
        if self._sticker_play_once and movie.frameCount() > 0 and movie.currentFrameNumber() >= movie.frameCount() - 1:
            self._sticker_timer.start(max(1, movie.nextFrameDelay()))
        self.update()

    def _clear_sticker(self) -> None:
        if self._sticker_movie:
            self._sticker_movie.stop()
        self._sticker_movie = None
        self._sticker_pixmap = QPixmap()
        self._sticker_active = False
        self._sticker_play_once = False
        if not self._pixmap.isNull():
            self._apply_alpha_mask(self._pixmap)
        self.update()

    def _apply_alpha_mask(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.clearMask()
            return
        target = self._fit_rect(pixmap.size())
        mask_image = QImage(self.size(), QImage.Format_Mono)
        mask_image.fill(0)
        mask_painter = QPainter(mask_image)
        mask_painter.drawPixmap(target, pixmap.mask())
        mask_painter.end()
        self.setMask(QBitmap.fromImage(mask_image))

    def _focus_elapsed_seconds(self) -> int:
        if not self._focus_active:
            return 0
        return max(0, int(time.monotonic() - self._focus_started_at))

    def _update_focus_stage(self) -> None:
        stage_index = min(self._focus_elapsed_seconds() // FOCUS_STAGE_SECONDS, len(self._focus_assets) - 1)
        if stage_index == self._focus_stage_index:
            return
        self._focus_stage_index = stage_index
        self._focus_character_asset = self._focus_assets[stage_index]
        self._character_key = f"focus:{stage_index}"
        self._load_character(self._focus_character_asset)

    def _format_focus_duration(self, seconds: int) -> str:
        hours, remainder = divmod(max(0, int(seconds)), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}小时{minutes:02d}分{secs:02d}秒"
        return f"{minutes}分{secs:02d}秒"

    def _save_focus_record(self, focused_seconds: int) -> None:
        if focused_seconds < 60:
            return
        started_at = self._focus_started_wall_time or datetime.now()
        ended_at = datetime.now()
        self.focus_record_store.add(
            FocusRecord(
                date=started_at.strftime("%Y-%m-%d"),
                start_time=started_at.strftime("%H:%M:%S"),
                end_time=ended_at.strftime("%H:%M:%S"),
                duration_seconds=max(0, int(focused_seconds)),
                duration_text=self._format_focus_duration(focused_seconds),
            )
        )

    def _restore_after_game(self) -> None:
        self.set_motion_paused(self._pre_game_motion_paused)
        if self._pre_game_visible:
            self.show()
        else:
            self.hide()
        self._active_game_window = None

    def _desktop_bounds(self) -> DesktopBounds:
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen:
            return DesktopBounds(screen.left(), screen.top(), screen.width(), screen.height())
        return DesktopBounds(0, 0, 1280, 720)

    def _snap_to_screen_edge(self) -> None:
        screen = self.screen().availableGeometry() if self.screen() else None
        if not screen:
            return
        frame = self.frameGeometry()
        distances = {
            "left": abs(frame.left() - screen.left()),
            "right": abs(screen.right() - frame.right()),
            "top": abs(frame.top() - screen.top()),
            "bottom": abs(screen.bottom() - frame.bottom()),
        }
        edge = min(distances, key=distances.get)
        x, y = self.x(), self.y()
        if edge == "left":
            x = screen.left()
        elif edge == "right":
            x = screen.right() - self.width()
        elif edge == "top":
            y = screen.top()
        elif edge == "bottom":
            y = screen.bottom() - self.height()
        self.move(x, y)


def time_random_motion() -> MotionMode:
    from .motion import selectable_motion_modes

    return random.choice(selectable_motion_modes())
