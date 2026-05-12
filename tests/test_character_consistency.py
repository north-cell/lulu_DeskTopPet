import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.motion import DesktopBounds, MotionEngine, MotionMode
from lulu_pet.pet_window import PetWindow


class CharacterConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dragged_and_falling_modes_use_lifted_character_asset(self):
        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=False,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        try:
            body_modes = (
                MotionMode.IDLE,
                MotionMode.WALK_LEFT,
                MotionMode.WALK_RIGHT,
                MotionMode.RUN_LEFT,
                MotionMode.RUN_RIGHT,
                MotionMode.ROLL_LEFT,
                MotionMode.ROLL_RIGHT,
                MotionMode.SLEEP,
            )

            body_keys = {window._character_key_for_mode(mode) for mode in body_modes}
            lifted_keys = {
                window._character_key_for_mode(MotionMode.DRAGGED),
                window._character_key_for_mode(MotionMode.FALLING),
            }

            self.assertEqual(body_keys, {"body"})
            self.assertEqual(lifted_keys, {"lifted"})
            self.assertEqual(window._character_assets["lifted"].name, "xhs_lulu_01.gif")
        finally:
            window.close()

    def test_lifted_character_returns_to_body_after_falling_lands(self):
        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=False,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        try:
            window.motion = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(220, 180), x=300, y=100)
            window.motion.start_drag()
            window._motion_frame = window.motion.drag_to(320, 120)
            window._apply_character_for_mode(window._motion_frame.mode)

            self.assertEqual(window._character_key, "lifted")

            window.motion.release_drag()
            for _ in range(80):
                window._on_tick()

            self.assertEqual(window.motion.mode, MotionMode.IDLE)
            self.assertEqual(window._character_key, "body")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
