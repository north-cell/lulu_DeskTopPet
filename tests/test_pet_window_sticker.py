import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.motion import MotionMode
from lulu_pet.pet_window import PetWindow
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent


class FakeMouseEvent:
    def __init__(self, button):
        self._button = button
        self.accepted = False

    def button(self):
        return self._button

    def accept(self):
        self.accepted = True


def double_click_event() -> QMouseEvent:
    point = QPointF(20, 20)
    return QMouseEvent(
        QEvent.MouseButtonDblClick,
        point,
        point,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )


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

    def test_trigger_sticker_uses_next_asset_in_folder_order(self):
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
            expected = window._sticker_assets[:3]

            window.trigger_sticker()
            first = window._last_sticker_path
            window.trigger_sticker()
            second = window._last_sticker_path
            window.trigger_sticker()
            third = window._last_sticker_path

            self.assertEqual([first, second, third], expected)
        finally:
            window.close()

    def test_sticker_playback_freezes_pet_position_until_finished(self):
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
            window.motion.start(MotionMode.WALK_RIGHT, duration_ticks=20)
            start = (window.motion.x, window.motion.y)

            window.trigger_sticker()
            for _ in range(4):
                window._on_tick()
            during_sticker = (window.motion.x, window.motion.y)
            window._clear_sticker()
            window._on_tick()
            after_sticker = (window.motion.x, window.motion.y)

            self.assertEqual(during_sticker, start)
            self.assertNotEqual(after_sticker, start)
        finally:
            window.close()

    def test_single_click_does_not_trigger_sticker(self):
        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=False,
            motion_speed_percent=100,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        event = FakeMouseEvent(Qt.LeftButton)
        try:
            window.mouseReleaseEvent(event)

            self.assertTrue(event.accepted)
            self.assertFalse(window._sticker_active)
        finally:
            window.close()

    def test_double_click_triggers_sticker(self):
        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=False,
            motion_speed_percent=100,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        event = double_click_event()
        try:
            window.mouseDoubleClickEvent(event)

            self.assertTrue(event.isAccepted())
            self.assertTrue(window._sticker_active)
        finally:
            window.close()

    def test_trigger_sticker_plays_more_slowly_than_default_movie_speed(self):
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

            self.assertIsNotNone(window._sticker_movie)
            self.assertLess(window._sticker_movie.speed(), 100)
        finally:
            window.close()

    def test_sticker_pool_excludes_low_quality_scene_gifs(self):
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
            sticker_names = {path.name for path in window._sticker_assets}

            self.assertNotIn("lulu_transparent_15.gif", sticker_names)
            self.assertNotIn("lulu_transparent_16.gif", sticker_names)
            self.assertNotIn("lulu_transparent_17.gif", sticker_names)
            self.assertNotIn("lulu_transparent_19.gif", sticker_names)
            self.assertNotIn("lulu_transparent_20.gif", sticker_names)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
