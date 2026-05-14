import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPointingDevice
from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.games.flappy_lulu import FlappyLuluWindow, PipePair
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


def press_key(window: FlappyLuluWindow, key: Qt.Key) -> None:
    event = QKeyEvent(QKeyEvent.KeyPress, key, Qt.NoModifier)
    window.keyPressEvent(event)


def left_click(window: FlappyLuluWindow, pos=None) -> None:
    click_pos = pos or window.rect().center()
    event = QMouseEvent(
        QMouseEvent.MouseButtonPress,
        click_pos,
        click_pos,
        click_pos,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
        QPointingDevice.primaryPointingDevice(),
    )
    window.mousePressEvent(event)


class FlappyLuluGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_restart_game_initializes_physics_score_and_pipes(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()

            self.assertEqual(window.score, 0)
            self.assertEqual(window.bird_x, 180)
            self.assertEqual(window.bird_y, 240)
            self.assertEqual(window.bird_velocity, 0)
            self.assertGreaterEqual(len(window.pipes), 2)
            self.assertFalse(window.results_visible)
            self.assertTrue(window.start_screen_visible)
            self.assertFalse(window._game_timer.isActive())
        finally:
            window.close()

    def test_start_game_hides_start_screen_and_starts_timer(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()

            window.start_game()

            self.assertFalse(window.start_screen_visible)
            self.assertFalse(window.results_visible)
            self.assertTrue(window._game_timer.isActive())
        finally:
            window.close()

    def test_start_button_waits_for_first_space_or_mouse_before_running(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()

            left_click(window, window._start_button_rect().center())

            self.assertFalse(window.start_screen_visible)
            self.assertTrue(window.awaiting_first_input)
            self.assertFalse(window.results_visible)
            self.assertFalse(window._game_timer.isActive())

            press_key(window, Qt.Key_Space)

            self.assertFalse(window.awaiting_first_input)
            self.assertTrue(window._game_timer.isActive())
            self.assertEqual(window.bird_velocity, window.flap_velocity)
        finally:
            window.close()

        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            left_click(window, window._start_button_rect().center())

            left_click(window)

            self.assertFalse(window.awaiting_first_input)
            self.assertTrue(window._game_timer.isActive())
            self.assertEqual(window.bird_velocity, window.flap_velocity)
        finally:
            window.close()

    def test_first_version_uses_easier_timing_and_pipe_spacing(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            self.assertGreaterEqual(window.pipe_gap, 190)
            self.assertGreaterEqual(window.pipe_spacing, 320)
            self.assertLessEqual(window.pipe_speed, 3.2)
            self.assertLessEqual(window.gravity, 0.55)
        finally:
            window.close()

    def test_pixel_lulu_uses_orange_palette_without_white_hood(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        image = QImage(80, 80, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        try:
            window.bird_x = 8
            window.bird_y = 12

            window._paint_pixel_lulu(painter)
        finally:
            painter.end()
            window.close()

        colors = []
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixelColor(x, y))
                if color.alpha() > 0:
                    colors.append(color)

        self.assertTrue(colors)
        self.assertFalse(
            any(color.red() >= 238 and color.green() >= 224 and color.blue() >= 200 for color in colors),
            "Flappy Lulu sprite should not contain white or cream hood pixels.",
        )

    def test_flap_sets_upward_velocity_for_space_and_mouse(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()
            window.bird_velocity = 5

            press_key(window, Qt.Key_Space)

            self.assertLess(window.bird_velocity, 0)

            window.bird_velocity = 5
            left_click(window)
            self.assertLess(window.bird_velocity, 0)
        finally:
            window.close()

    def test_advance_frame_applies_gravity_and_moves_pipes_left(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()
            first_y = window.bird_y
            first_pipe_x = window.pipes[0].x

            window.advance_frame()

            self.assertGreater(window.bird_y, first_y)
            self.assertLess(window.pipes[0].x, first_pipe_x)
        finally:
            window.close()

    def test_offscreen_pipe_is_removed_and_replaced(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()
            window.pipes = [PipePair(-100, 180, scored=False), PipePair(520, 180, scored=False)]

            window.advance_frame()

            self.assertEqual(len(window.pipes), 2)
            self.assertTrue(all(pipe.x > -window.pipe_width for pipe in window.pipes))
            self.assertGreater(window.pipes[-1].x, 520)
        finally:
            window.close()

    def test_passing_pipe_scores_only_once(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()
            window.pipes = [PipePair(window.bird_x - window.pipe_width - 1, 180, scored=False)]
            window.bird_y = 180

            window.advance_frame()
            window.advance_frame()

            self.assertEqual(window.score, 1)
            self.assertTrue(window.pipes[0].scored)
        finally:
            window.close()

    def test_pipe_collision_finishes_game(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()
            window.pipes = [PipePair(window.bird_x, 280, scored=False)]
            window.bird_y = 120

            window.advance_frame()

            self.assertTrue(window.results_visible)
            self.assertFalse(window._game_timer.isActive())
        finally:
            window.close()

    def test_ground_and_ceiling_collision_finish_game(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()
            window.pipes = []
            window.bird_y = window.ground_y + 1
            window.advance_frame()
            self.assertTrue(window.results_visible)

            window.restart_game()
            window.start_game()
            window.pipes = []
            window.bird_y = -window.bird_size
            window.advance_frame()
            self.assertTrue(window.results_visible)
        finally:
            window.close()

    def test_escape_finishes_game(self):
        window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), seed=1)
        try:
            window.restart_game()
            window.start_game()

            press_key(window, Qt.Key_Escape)

            self.assertTrue(window.results_visible)
        finally:
            window.close()

    def test_finish_game_saves_new_high_score_and_keeps_existing_higher_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "flappy_lulu_records.json"
            window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), record_path=record_path, seed=1)
            try:
                window.score = 9
                window.finish_game()

                self.assertEqual(window.high_score, 9)
                self.assertIn("9", record_path.read_text(encoding="utf-8"))

                lower = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), record_path=record_path, seed=1)
                lower.score = 3
                lower.finish_game()
                self.assertEqual(lower.high_score, 9)
            finally:
                window.close()
                if "lower" in locals():
                    lower.close()

    def test_invalid_record_json_loads_as_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "flappy_lulu_records.json"
            record_path.write_text("{bad json", encoding="utf-8")
            window = FlappyLuluWindow(play_area=QRect(0, 0, 800, 480), record_path=record_path, seed=1)
            try:
                self.assertEqual(window.high_score, 0)
            finally:
                window.close()

    def test_pet_window_restores_visibility_and_motion_after_flappy_lulu(self):
        pet = PetWindow(PetController(AssetManager(None)), default_settings())
        pet._bubble = FakeBubble()
        pet._sticker = FakeSticker()
        try:
            pet.show()
            pet.set_motion_paused(False)

            pet.start_flappy_lulu_game()

            self.assertFalse(pet.isVisible())
            self.assertTrue(pet.motion_paused)
            self.assertTrue(pet._bubble.hidden)
            self.assertTrue(pet._sticker.hidden)
            self.assertIsNotNone(pet._active_game_window)

            pet._active_game_window.start_game()
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
