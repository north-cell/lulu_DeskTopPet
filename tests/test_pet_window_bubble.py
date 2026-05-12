import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.motion import MotionMode
from lulu_pet.pet_window import PetWindow


def default_settings() -> PetSettings:
    return PetSettings(
        window_size=(220, 180),
        always_on_top=True,
        speech_interval_seconds=45,
        edge_snap=True,
        autostart=False,
        motion_speed_percent=100,
    )


class PetWindowBubbleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_hidden_pet_does_not_show_speech_bubble(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.show()
            window.hide()

            window._say_random_line(force=True)

            self.assertFalse(window._bubble.isVisible())
        finally:
            window.close()

    def test_visible_bubble_keeps_relative_position_when_pet_moves(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.show()
            window._bubble.show_message("噜噜会跟着走。", window)
            initial_offset = window._bubble.pos() - window.pos()

            window.motion.start(MotionMode.WALK_RIGHT, duration_ticks=20)
            window._on_tick()

            self.assertEqual(window._bubble.pos() - window.pos(), initial_offset)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
