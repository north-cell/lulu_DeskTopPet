import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.pet_window import PetWindow


class RestModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_rest_uses_qq_lulu_04_and_stays_bottom_right(self):
        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=False,
            motion_speed_percent=100,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        try:
            window.move(10, 10)
            window.motion.x = 10
            window.motion.y = 10

            window.trigger_rest()
            expected = (
                window.motion.bounds.right - window.width(),
                window.motion.bounds.bottom - window.height(),
            )
            start = (window.motion.x, window.motion.y)
            for _ in range(4):
                window._on_tick()

            self.assertEqual(start, expected)
            self.assertEqual((window.motion.x, window.motion.y), expected)
            self.assertEqual(window._character_key, "rest")
            self.assertEqual(window._rest_character_asset.name, "qq_lulu_04.gif")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
