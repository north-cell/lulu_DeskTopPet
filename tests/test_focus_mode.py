import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.motion import MotionMode
from lulu_pet.focus_records import FocusRecordStore
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


class FakeDragEvent:
    def __init__(self, button=Qt.LeftButton, buttons=Qt.LeftButton, x=20, y=20):
        self._button = button
        self._buttons = buttons
        self._point = QPointF(x, y)
        self.accepted = False

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def globalPosition(self):
        return self._point

    def accept(self):
        self.accepted = True


class FakeBubble:
    def __init__(self):
        self.messages = []

    def show_message(self, text, anchor, duration_ms=2600):
        self.messages.append((text, duration_ms))

    def hide(self):
        pass


class FocusModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_enter_focus_mode_moves_to_bottom_right_and_stops_motion(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.move(10, 10)
            window.motion.x = 10
            window.motion.y = 10

            window.trigger_focus_mode()

            expected = (
                window.motion.bounds.right - window.width(),
                window.motion.bounds.bottom - window.height(),
            )
            self.assertTrue(window.focus_mode_active)
            self.assertEqual((window.motion.x, window.motion.y), expected)
            self.assertEqual(window.pos().x(), expected[0])
            self.assertEqual(window.pos().y(), expected[1])

            before = (window.motion.x, window.motion.y)
            window.motion.start(MotionMode.WALK_LEFT, duration_ticks=20)
            window._on_tick()

            self.assertEqual((window.motion.x, window.motion.y), before)
            self.assertEqual(window._focus_character_asset.name, "1.gif")
        finally:
            window.close()

    def test_focus_mode_selects_expected_stage_gifs(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.trigger_focus_mode()

            cases = [
                (0, "1.gif"),
                (5 * 60, "2.gif"),
                (10 * 60, "3.gif"),
                (15 * 60, "4.gif"),
                (20 * 60, "5.gif"),
                (45 * 60, "5.gif"),
            ]
            for elapsed, expected_name in cases:
                with self.subTest(elapsed=elapsed):
                    window._focus_started_at = time.monotonic() - elapsed
                    window._on_tick()
                    self.assertEqual(window._focus_character_asset.name, expected_name)
        finally:
            window.close()

    def test_focus_mode_ignores_drag_and_double_click_sticker(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.trigger_focus_mode()
            start_pos = window.pos()

            window.mousePressEvent(FakeDragEvent(x=20, y=20))
            window.mouseMoveEvent(FakeDragEvent(x=80, y=80))
            window.mouseReleaseEvent(FakeDragEvent(x=80, y=80))
            window.mouseDoubleClickEvent(FakeDragEvent(x=80, y=80))

            self.assertFalse(window._dragging)
            self.assertEqual(window.pos(), start_pos)
            self.assertFalse(window._sticker_active)
        finally:
            window.close()

    def test_focus_timer_sits_above_pet_without_covering_body(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.trigger_focus_mode()

            self.assertLessEqual(window._focus_timer.geometry().bottom(), window.geometry().top() - 6)
        finally:
            window.close()

    def test_end_focus_mode_plays_finish_gif_inside_pet_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            window = PetWindow(PetController(AssetManager(None)), default_settings(), focus_record_store=store)
            try:
                window.trigger_focus_mode()

                window.end_focus_mode()

                self.assertFalse(window.focus_mode_active)
                self.assertEqual(window._last_sticker_path.name, "6.gif")
                self.assertTrue(window._sticker_active)
                self.assertFalse(window._focus_timer.isVisible())
            finally:
                window.close()

    def test_end_focus_mode_shows_thank_you_bubble_with_focus_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            window = PetWindow(PetController(AssetManager(None)), default_settings(), focus_record_store=store)
            bubble = FakeBubble()
            window._bubble = bubble
            try:
                window.trigger_focus_mode()
                window._focus_started_at = time.monotonic() - (12 * 60 + 34)

                window.end_focus_mode()

                self.assertEqual(window._last_sticker_path.name, "6.gif")
                self.assertEqual(len(bubble.messages), 1)
                self.assertIn("谢谢你陪本噜噜大王学习", bubble.messages[0][0])
                self.assertIn("12分34秒", bubble.messages[0][0])
            finally:
                window.close()

    def test_end_focus_mode_saves_learning_record_with_dates_and_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            window = PetWindow(PetController(AssetManager(None)), default_settings(), focus_record_store=store)
            try:
                window.trigger_focus_mode()
                window._focus_started_wall_time = datetime(2026, 5, 12, 9, 15, 30)
                window._focus_started_at = time.monotonic() - (25 * 60 + 5)

                window.end_focus_mode()

                records = store.load()
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0].date, "2026-05-12")
                self.assertEqual(records[0].start_time, "09:15:30")
                self.assertRegex(records[0].end_time, r"^\d{2}:\d{2}:\d{2}$")
                self.assertEqual(records[0].duration_seconds, 25 * 60 + 5)
                self.assertEqual(records[0].duration_text, "25分05秒")
            finally:
                window.close()

    def test_end_focus_mode_does_not_save_learning_record_under_one_minute(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            window = PetWindow(PetController(AssetManager(None)), default_settings(), focus_record_store=store)
            try:
                window.trigger_focus_mode()
                window._focus_started_at = time.monotonic() - 59

                window.end_focus_mode()

                self.assertEqual(store.load(), [])
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
