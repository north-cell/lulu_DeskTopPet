import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.games.lulu_2048 import Direction, Lulu2048Window
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


def nonzero_count(board: list[list[int]]) -> int:
    return sum(1 for row in board for value in row if value)


def press_key(window: Lulu2048Window, key: Qt.Key) -> None:
    event = QKeyEvent(QKeyEvent.KeyPress, key, Qt.NoModifier)
    window.keyPressEvent(event)


class Lulu2048GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_restart_game_spawns_two_starting_tiles(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.restart_game()

            self.assertEqual(window.score, 0)
            self.assertEqual(window.max_tile, max(max(row) for row in window.board))
            self.assertEqual(nonzero_count(window.board), 2)
            self.assertTrue(all(value in (0, 2, 4) for row in window.board for value in row))
            self.assertFalse(window.results_visible)
        finally:
            window.close()

    def test_move_left_merges_three_same_tiles_once_per_tile(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 2, 2, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]

            moved = window.move_tiles(Direction.LEFT, spawn_tile=False)

            self.assertTrue(moved)
            self.assertEqual(window.board[0], [4, 2, 0, 0])
            self.assertEqual(window.score, 4)
        finally:
            window.close()

    def test_move_left_merges_two_pairs_and_scores_sum(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 2, 4, 4],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]

            moved = window.move_tiles(Direction.LEFT, spawn_tile=False)

            self.assertTrue(moved)
            self.assertEqual(window.board[0], [4, 8, 0, 0])
            self.assertEqual(window.score, 12)
        finally:
            window.close()

    def test_move_right_and_up_compress_tiles(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 0, 0, 2],
                [0, 4, 0, 0],
                [0, 4, 0, 0],
                [0, 0, 0, 0],
            ]

            window.move_tiles(Direction.RIGHT, spawn_tile=False)
            self.assertEqual(window.board[0], [0, 0, 0, 4])
            self.assertEqual(window.board[1], [0, 0, 0, 4])
            self.assertEqual(window.board[2], [0, 0, 0, 4])

            window.move_tiles(Direction.UP, spawn_tile=False)
            self.assertEqual([row[3] for row in window.board], [8, 4, 0, 0])
        finally:
            window.close()

    def test_unchanged_move_does_not_spawn_tile(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 4, 8, 16],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]

            moved = window.move_tiles(Direction.LEFT)

            self.assertFalse(moved)
            self.assertEqual(nonzero_count(window.board), 4)
        finally:
            window.close()

    def test_valid_move_spawns_one_new_tile(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]

            moved = window.move_tiles(Direction.RIGHT)

            self.assertTrue(moved)
            self.assertEqual(nonzero_count(window.board), 2)
        finally:
            window.close()

    def test_reaching_2048_marks_won_and_keeps_game_running(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [1024, 1024, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]

            window.move_tiles(Direction.LEFT, spawn_tile=False)

            self.assertTrue(window.won)
            self.assertEqual(window.max_tile, 2048)
            self.assertFalse(window.results_visible)
        finally:
            window.close()

    def test_full_board_without_moves_finishes_game(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 4, 2, 4],
                [4, 2, 4, 2],
                [2, 4, 2, 4],
                [4, 2, 4, 2],
            ]

            moved = window.move_tiles(Direction.LEFT)

            self.assertFalse(moved)
            self.assertTrue(window.results_visible)
        finally:
            window.close()

    def test_finish_game_saves_new_high_score_and_keeps_existing_higher_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "lulu_2048_records.json"
            window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), record_path=record_path, seed=1)
            try:
                window.score = 128
                window.finish_game()

                self.assertEqual(window.high_score, 128)
                self.assertIn("128", record_path.read_text(encoding="utf-8"))

                lower = Lulu2048Window(play_area=QRect(0, 0, 640, 520), record_path=record_path, seed=1)
                lower.score = 16
                lower.finish_game()
                self.assertEqual(lower.high_score, 128)
            finally:
                window.close()
                if "lower" in locals():
                    lower.close()

    def test_invalid_record_json_loads_as_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "lulu_2048_records.json"
            record_path.write_text("{bad json", encoding="utf-8")
            window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), record_path=record_path, seed=1)
            try:
                self.assertEqual(window.high_score, 0)
            finally:
                window.close()

    def test_keyboard_controls_move_tiles_and_escape_finishes(self):
        window = Lulu2048Window(play_area=QRect(0, 0, 640, 520), seed=1)
        try:
            window.board = [
                [2, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ]

            press_key(window, Qt.Key_D)

            self.assertEqual(window.board[0][3], 2)

            press_key(window, Qt.Key_Escape)
            self.assertTrue(window.results_visible)
        finally:
            window.close()

    def test_pet_window_restores_visibility_and_motion_after_lulu_2048(self):
        pet = PetWindow(PetController(AssetManager(None)), default_settings())
        pet._bubble = FakeBubble()
        pet._sticker = FakeSticker()
        try:
            pet.show()
            pet.set_motion_paused(False)

            pet.start_lulu_2048_game()

            self.assertFalse(pet.isVisible())
            self.assertTrue(pet.motion_paused)
            self.assertTrue(pet._bubble.hidden)
            self.assertTrue(pet._sticker.hidden)
            self.assertIsNotNone(pet._active_game_window)
            self.assertFalse(pet._active_game_window.isFullScreen())

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
