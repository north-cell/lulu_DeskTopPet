import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.games.greedy_lulu import Direction, GreedyLuluWindow
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


def press_key(window: GreedyLuluWindow, key: Qt.Key) -> None:
    event = QKeyEvent(QKeyEvent.KeyPress, key, Qt.NoModifier)
    window.keyPressEvent(event)


class GreedyLuluGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_restart_game_sets_initial_snake_direction_and_score(self):
        window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480))
        try:
            window.restart_game()

            self.assertEqual(window.score, 0)
            self.assertEqual(window.direction, Direction.RIGHT)
            self.assertEqual(len(window.snake), 3)
            self.assertEqual(window.snake[0], QPoint(10, 8))
            self.assertEqual(window.snake[1], QPoint(9, 8))
            self.assertEqual(window.snake[2], QPoint(8, 8))
            self.assertFalse(window.results_visible)
        finally:
            window.close()

    def test_keyboard_changes_direction_and_ignores_direct_reverse(self):
        window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480))
        try:
            window.restart_game()

            press_key(window, Qt.Key_Left)
            self.assertEqual(window.direction, Direction.RIGHT)

            press_key(window, Qt.Key_W)
            self.assertEqual(window.direction, Direction.UP)

            press_key(window, Qt.Key_S)
            self.assertEqual(window.direction, Direction.UP)

            press_key(window, Qt.Key_A)
            self.assertEqual(window.direction, Direction.LEFT)
        finally:
            window.close()

    def test_tick_moves_snake_one_cell_without_food(self):
        window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480))
        try:
            window.restart_game()
            window.food = QPoint(18, 8)

            window.advance_snake()

            self.assertEqual(window.snake, [QPoint(11, 8), QPoint(10, 8), QPoint(9, 8)])
            self.assertEqual(window.score, 0)
            self.assertFalse(window.results_visible)
        finally:
            window.close()

    def test_eating_food_increases_score_and_length(self):
        window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480))
        try:
            window.restart_game()
            original_food = QPoint(11, 8)
            window.food = original_food

            window.advance_snake()

            self.assertEqual(window.score, 1)
            self.assertEqual(len(window.snake), 4)
            self.assertEqual(window.snake[0], original_food)
            self.assertNotEqual(window.food, original_food)
            self.assertNotIn(window.food, window.snake)
        finally:
            window.close()

    def test_wall_collision_finishes_game(self):
        window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480))
        try:
            window.restart_game()
            window.snake = [QPoint(window.columns - 1, 4), QPoint(window.columns - 2, 4), QPoint(window.columns - 3, 4)]
            window.direction = Direction.RIGHT

            window.advance_snake()

            self.assertTrue(window.results_visible)
            self.assertFalse(window._move_timer.isActive())
        finally:
            window.close()

    def test_self_collision_finishes_game(self):
        window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480))
        try:
            window.restart_game()
            window.snake = [QPoint(5, 5), QPoint(5, 6), QPoint(4, 6), QPoint(4, 5), QPoint(5, 5)]
            window.direction = Direction.DOWN

            window.advance_snake()

            self.assertTrue(window.results_visible)
        finally:
            window.close()

    def test_finish_game_saves_new_high_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "greedy_lulu_records.json"
            window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480), record_path=record_path)
            try:
                window.restart_game()
                window.score = 7

                window.finish_game()

                self.assertEqual(window.high_score, 7)
                self.assertIn("7", record_path.read_text(encoding="utf-8"))
            finally:
                window.close()

    def test_finish_game_keeps_existing_high_score_when_current_score_is_lower(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "greedy_lulu_records.json"
            record_path.write_text('{"high_score": 12}', encoding="utf-8")
            window = GreedyLuluWindow(play_area=QRect(0, 0, 640, 480), record_path=record_path)
            try:
                window.restart_game()
                window.score = 3

                window.finish_game()

                self.assertEqual(window.high_score, 12)
                self.assertIn("12", record_path.read_text(encoding="utf-8"))
            finally:
                window.close()

    def test_pet_window_restores_visibility_and_motion_after_greedy_lulu(self):
        pet = PetWindow(PetController(AssetManager(None)), default_settings())
        pet._bubble = FakeBubble()
        pet._sticker = FakeSticker()
        try:
            pet.show()
            pet.set_motion_paused(False)

            pet.start_greedy_lulu_game()

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


if __name__ == "__main__":
    unittest.main()
