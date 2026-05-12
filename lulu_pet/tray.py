from __future__ import annotations

from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .menu_style import apply_lulu_menu_style
from .pet_window import PetWindow


class TrayController:
    def __init__(self, pet_window: PetWindow):
        self.pet_window = pet_window
        self.tray = QSystemTrayIcon(_tray_icon(), pet_window)
        self.tray.setToolTip("水豚噜噜")
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_activated)

    def show(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def _build_menu(self) -> QMenu:
        menu = apply_lulu_menu_style(QMenu())
        menu.addAction("显示/隐藏", self.pet_window.toggle_visible)
        pause_action = QAction("暂停移动", menu)
        pause_action.setCheckable(True)
        pause_action.setChecked(self.pet_window.motion_paused)
        pause_action.triggered.connect(self.pet_window.set_motion_paused)
        menu.aboutToShow.connect(lambda: pause_action.setChecked(self.pet_window.motion_paused))
        menu.addAction(pause_action)
        top_action = QAction("保持置顶", menu)
        top_action.setCheckable(True)
        top_action.setChecked(self.pet_window.settings.always_on_top)
        top_action.triggered.connect(self.pet_window.set_always_on_top)
        menu.addAction(top_action)
        menu.addSeparator()
        menu.addAction("休息一下", self.pet_window.trigger_rest)
        self.pet_window.add_character_change_menu(menu)
        menu.addSeparator()
        menu.addAction("退出", QApplication.instance().quit)
        return menu

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.pet_window.toggle_visible()


def _tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(151, 111, 82))
    painter.setPen(QColor(93, 66, 49))
    painter.drawRoundedRect(8, 18, 48, 34, 18, 18)
    painter.setBrush(QColor(35, 25, 20))
    painter.drawEllipse(24, 31, 4, 4)
    painter.drawEllipse(38, 31, 4, 4)
    painter.end()
    return QIcon(pixmap)
