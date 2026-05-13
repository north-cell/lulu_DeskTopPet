import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.games.whack_lulu import WhackLuluWindow
from lulu_pet.models import PetSettings
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


class FakeBubble:
    def __init__(self):
        self.hidden = False

    def hide(self):
        self.hidden = True


class FakeSticker:
    def __init__(self):
        self.hidden = False

    def hide(self):
        self.hidden = True


class WhackLuluGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_hit_updates_score_combo_and_moves_target(self):
        window = WhackLuluWindow(play_area=QRect(0, 0, 500, 400))
        try:
            window.restart_game()
            first_target = QRect(window.target_rect)

            window.hit_target()

            self.assertEqual(window.hits, 1)
            self.assertEqual(window.misses, 0)
            self.assertEqual(window.combo, 1)
            self.assertEqual(window.best_combo, 1)
            self.assertNotEqual(window.target_rect, first_target)
            self.assertFalse(window.results_visible)
        finally:
            window.close()

    def test_default_target_visible_time_keeps_game_challenging(self):
        window = WhackLuluWindow(play_area=QRect(0, 0, 500, 400))
        try:
            self.assertEqual(window.target_visible_ms, 700)
        finally:
            window.close()

    def test_target_timeout_counts_miss_and_clears_combo(self):
        window = WhackLuluWindow(play_area=QRect(0, 0, 500, 400))
        try:
            window.restart_game()
            window.hit_target()

            window.miss_target()

            self.assertEqual(window.hits, 1)
            self.assertEqual(window.misses, 1)
            self.assertEqual(window.combo, 0)
            self.assertEqual(window.best_combo, 1)
            self.assertFalse(window.results_visible)
        finally:
            window.close()

    def test_finish_game_shows_results_and_stops_spawning(self):
        window = WhackLuluWindow(play_area=QRect(0, 0, 500, 400))
        try:
            window.restart_game()
            target_before_finish = QRect(window.target_rect)

            window.finish_game()
            window.hit_target()
            window.miss_target()

            self.assertTrue(window.results_visible)
            self.assertEqual(window.hits, 0)
            self.assertEqual(window.misses, 0)
            self.assertEqual(window.target_rect, target_before_finish)
        finally:
            window.close()

    def test_finish_game_saves_new_high_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "whack_lulu_records.json"
            window = WhackLuluWindow(play_area=QRect(0, 0, 500, 400), record_path=record_path)
            try:
                window.restart_game()
                window.hit_target()
                window.hit_target()

                window.finish_game()

                self.assertEqual(window.high_score, 2)
                self.assertIn("2", record_path.read_text(encoding="utf-8"))
            finally:
                window.close()

    def test_finish_game_keeps_existing_high_score_when_current_score_is_lower(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "whack_lulu_records.json"
            record_path.write_text('{"high_score": 5}', encoding="utf-8")
            window = WhackLuluWindow(play_area=QRect(0, 0, 500, 400), record_path=record_path)
            try:
                window.restart_game()
                window.hit_target()
                window.finish_game()

                self.assertEqual(window.high_score, 5)
                self.assertIn("5", record_path.read_text(encoding="utf-8"))
            finally:
                window.close()

    def test_results_panel_has_room_for_high_score_line(self):
        window = WhackLuluWindow(play_area=QRect(0, 0, 560, 370))
        try:
            window.resize(560, 370)
            window.restart_game()
            window.finish_game()

            metrics = QFontMetrics(window._result_details_font())
            required_text_height = metrics.lineSpacing() * 5

            self.assertGreaterEqual(window._result_details_rect().height(), required_text_height)
            self.assertGreaterEqual(window._again_button.y(), window._result_details_rect().bottom() + 16)
        finally:
            window.close()

    def test_pet_window_restores_visibility_and_motion_after_game(self):
        pet = PetWindow(PetController(AssetManager(None)), default_settings())
        pet._bubble = FakeBubble()
        pet._sticker = FakeSticker()
        try:
            pet.show()
            pet.set_motion_paused(False)

            pet.start_whack_lulu_game()

            self.assertFalse(pet.isVisible())
            self.assertTrue(pet.motion_paused)
            self.assertTrue(pet._bubble.hidden)
            self.assertTrue(pet._sticker.hidden)
            self.assertIsNotNone(pet._active_game_window)

            pet._active_game_window.finish_game()
            pet._active_game_window.close()
            QApplication.processEvents()

            self.assertTrue(pet.isVisible())
            self.assertFalse(pet.motion_paused)
            self.assertIsNone(pet._active_game_window)
        finally:
            if pet._active_game_window:
                pet._active_game_window.close()
            pet.close()

    def test_pet_window_preserves_initial_hidden_and_paused_state_after_game(self):
        pet = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            pet.hide()
            pet.set_motion_paused(True)

            pet.start_whack_lulu_game()
            pet._active_game_window.finish_game()
            pet._active_game_window.close()
            QApplication.processEvents()

            self.assertFalse(pet.isVisible())
            self.assertTrue(pet.motion_paused)
        finally:
            if pet._active_game_window:
                pet._active_game_window.close()
            pet.close()


if __name__ == "__main__":
    unittest.main()
