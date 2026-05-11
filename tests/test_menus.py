import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
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
            self.assertIn("保持置顶", texts)
            self.assertIn("退出", texts)
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
            self.assertIn("保持置顶", texts)
            self.assertIn("退出", texts)
        finally:
            tray.hide()
            window.close()


if __name__ == "__main__":
    unittest.main()
