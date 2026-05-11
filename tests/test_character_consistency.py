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

    def test_all_motion_modes_keep_same_character_asset(self):
        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=False,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        try:
            keys = {
                window._character_key_for_mode(mode)
                for mode in (
                    MotionMode.IDLE,
                    MotionMode.WALK_LEFT,
                    MotionMode.WALK_RIGHT,
                    MotionMode.RUN_LEFT,
                    MotionMode.RUN_RIGHT,
                    MotionMode.ROLL_LEFT,
                    MotionMode.ROLL_RIGHT,
                    MotionMode.SLEEP,
                    MotionMode.DRAGGED,
                    MotionMode.FALLING,
                )
            }
        finally:
            window.close()

        self.assertEqual(keys, {"body"})


if __name__ == "__main__":
    unittest.main()
