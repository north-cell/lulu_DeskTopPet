import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.motion import MotionMode
from lulu_pet.pet_window import PetWindow
from lulu_pet.tray import TrayController


def default_settings() -> PetSettings:
    return PetSettings(
        window_size=(220, 180),
        always_on_top=True,
        speech_interval_seconds=45,
        edge_snap=True,
        autostart=False,
        motion_speed_percent=100,
    )


def action_texts(menu):
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def submenu_by_text(menu, text):
    return next(action.menu() for action in menu.actions() if action.text() == text)


class MenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pet_context_menu_hides_manual_random_and_settings_actions(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            texts = action_texts(window.context_menu())

            self.assertNotIn("随机运动", texts)
            self.assertNotIn("随机表情包", texts)
            self.assertNotIn("设置", texts)
            self.assertIn("休息一下", texts)
            self.assertIn("暂停移动", texts)
            self.assertIn("保持置顶", texts)
            self.assertIn("退出", texts)
        finally:
            window.close()

    def test_pet_context_menu_can_pause_motion(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            action = next(action for action in window.context_menu().actions() if action.text() == "暂停移动")

            self.assertTrue(action.isCheckable())
            self.assertFalse(action.isChecked())

            action.trigger()

            self.assertTrue(window.motion_paused)
            self.assertTrue(next(action for action in window.context_menu().actions() if action.text() == "暂停移动").isChecked())
        finally:
            window.close()

    def test_pet_context_menu_can_switch_character_images(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            menu = window.context_menu()
            change_menu = submenu_by_text(menu, "更换形象")
            texts = action_texts(change_menu)

            self.assertEqual(texts, ["游泳噜噜", "得瑟噜噜"])

            swim_action = next(action for action in change_menu.actions() if action.text() == "游泳噜噜")
            swim_action.trigger()

            self.assertEqual(window._character_assets["body"].name, "lulu_transparent_01.gif")

            proud_action = next(action for action in change_menu.actions() if action.text() == "得瑟噜噜")
            proud_action.trigger()

            self.assertEqual(window._character_assets["body"].name, "lulu_transparent_09.gif")
        finally:
            window.close()

    def test_paused_motion_does_not_move_on_tick(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.motion.start(MotionMode.WALK_RIGHT, duration_ticks=20)
            window.set_motion_paused(True)
            position = window.pos()

            window._on_tick()

            self.assertEqual(window.pos(), position)
        finally:
            window.close()

    def test_tray_menu_hides_manual_random_and_settings_actions(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        tray = TrayController(window)
        try:
            texts = action_texts(tray.tray.contextMenu())

            self.assertNotIn("随机运动", texts)
            self.assertNotIn("随机表情包", texts)
            self.assertNotIn("设置", texts)
            self.assertIn("显示/隐藏", texts)
            self.assertIn("休息一下", texts)
            self.assertIn("暂停移动", texts)
            self.assertIn("保持置顶", texts)
            self.assertIn("退出", texts)
        finally:
            tray.hide()
            window.close()

    def test_tray_menu_can_pause_motion(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        tray = TrayController(window)
        try:
            action = next(action for action in tray.tray.contextMenu().actions() if action.text() == "暂停移动")

            self.assertTrue(action.isCheckable())
            self.assertFalse(action.isChecked())

            action.trigger()

            self.assertTrue(window.motion_paused)
        finally:
            tray.hide()
            window.close()


if __name__ == "__main__":
    unittest.main()
