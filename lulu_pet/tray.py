from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .autostart import AutostartManager
from .menu_style import apply_lulu_menu_style
from .pet_window import PetWindow


class TrayController:
    def __init__(self, pet_window: PetWindow, autostart_manager: AutostartManager | None = None):
        self.pet_window = pet_window
        self.autostart_manager = autostart_manager or AutostartManager()
        if self.pet_window.settings.autostart and getattr(self.autostart_manager, "is_available", True):
            self.autostart_manager.enable()
        self.tray = QSystemTrayIcon(_tray_icon(), pet_window)
        self.tray.setToolTip("水豚噜噜")
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_activated)

    def show(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def refresh_menu(self) -> None:
        self.tray.setContextMenu(self._build_menu())

    def _build_menu(self) -> QMenu:
        menu = apply_lulu_menu_style(QMenu())
        self._populate_menu(menu)
        menu.aboutToShow.connect(lambda: self._populate_menu(menu))
        return menu

    def _populate_menu(self, menu: QMenu) -> None:
        menu.clear()
        menu.addAction("显示/隐藏", self.pet_window.toggle_visible)
        if self.pet_window.focus_mode_active:
            menu.addAction("结束专注模式", self._end_focus_mode)
            menu.addAction("学习记录", self.pet_window.show_focus_records)
            self._add_autostart_action(menu)
            menu.addSeparator()
            menu.addAction("退出", QApplication.instance().quit)
            return

        self.pet_window.add_focus_mode_menu(menu, self._trigger_focus_mode)
        pause_action = QAction("暂停移动", menu)
        pause_action.setCheckable(True)
        pause_action.setChecked(self.pet_window.motion_paused)
        pause_action.triggered.connect(self.pet_window.set_motion_paused)
        menu.addAction(pause_action)
        top_action = QAction("保持置顶", menu)
        top_action.setCheckable(True)
        top_action.setChecked(self.pet_window.settings.always_on_top)
        top_action.triggered.connect(self._set_always_on_top)
        menu.addAction(top_action)
        self._add_autostart_action(menu)
        menu.addSeparator()
        menu.addAction("休息一下", self.pet_window.trigger_rest)
        menu.addAction("签订契约", self.pet_window.sign_contract)
        self.pet_window.add_character_change_menu(menu)
        menu.addSeparator()
        menu.addAction("退出", QApplication.instance().quit)

    def _trigger_focus_mode(self) -> None:
        self.pet_window.trigger_focus_mode()
        self.refresh_menu()

    def _end_focus_mode(self) -> None:
        self.pet_window.end_focus_mode()
        self.refresh_menu()

    def _set_always_on_top(self, enabled: bool) -> None:
        self.pet_window.set_always_on_top(enabled)
        self.refresh_menu()

    def _autostart_checked(self) -> bool:
        if getattr(self.autostart_manager, "is_available", True):
            return self.autostart_manager.is_enabled()
        return self.pet_window.settings.autostart

    def _add_autostart_action(self, menu: QMenu) -> QAction:
        autostart_action = QAction("开机自启动", menu)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(self._autostart_checked())
        autostart_action.triggered.connect(self._set_autostart_enabled)
        menu.addAction(autostart_action)
        return autostart_action

    def _set_autostart_enabled(self, enabled: bool) -> None:
        self.autostart_manager.set_enabled(enabled)
        self.pet_window.settings = replace(self.pet_window.settings, autostart=enabled)
        if self.pet_window.settings_store:
            self.pet_window.settings_store.save(self.pet_window.settings)
        self.refresh_menu()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.pet_window.toggle_visible()


def _tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor(190, 91, 26))
    painter.setBrush(QColor(248, 148, 45))
    painter.drawEllipse(12, 18, 40, 38)

    painter.setPen(QColor(76, 132, 58))
    painter.setBrush(QColor(91, 168, 75))
    painter.drawEllipse(32, 8, 18, 10)

    painter.setPen(QColor(111, 77, 40))
    painter.drawLine(31, 18, 34, 10)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(92, 54, 31))
    painter.drawEllipse(25, 34, 3, 3)
    painter.drawEllipse(37, 34, 3, 3)
    painter.setBrush(QColor(219, 107, 35))
    painter.drawEllipse(18, 40, 6, 4)
    painter.drawEllipse(42, 40, 6, 4)
    painter.end()
    return QIcon(pixmap)
