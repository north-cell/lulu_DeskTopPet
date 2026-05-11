import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.pet_window import PetWindow


class PetWindowStickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_trigger_sticker_plays_inside_pet_window_not_popup(self):
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
            window.trigger_sticker()

            self.assertTrue(window._sticker_active)
            self.assertFalse(window._sticker.isVisible())
        finally:
            window.close()

    def test_trigger_sticker_uses_original_transparent_gif_library(self):
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
            window.trigger_sticker()

            self.assertIsNotNone(window._last_sticker_path)
            self.assertIn("lulu_transparent_gifs", str(window._last_sticker_path))
            self.assertEqual(window._sticker_movie.frameCount() > 1, True)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
