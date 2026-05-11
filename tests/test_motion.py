import unittest

from lulu_pet.motion import DesktopBounds, MotionEngine, MotionMode, selectable_motion_modes


class MotionEngineTests(unittest.TestCase):
    def test_walk_moves_horizontally(self):
        engine = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=450)
        engine.start(MotionMode.WALK_RIGHT, duration_ticks=10)

        first = engine.tick()
        second = engine.tick()

        self.assertEqual(first.mode, MotionMode.WALK_RIGHT)
        self.assertGreater(second.x, first.x)
        self.assertEqual(second.y, 450)

    def test_run_is_faster_than_walk(self):
        walk = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=450)
        run = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=450)
        walk.start(MotionMode.WALK_RIGHT, duration_ticks=5)
        run.start(MotionMode.RUN_RIGHT, duration_ticks=5)

        walk.tick()
        run.tick()

        self.assertGreater(run.x - 300, walk.x - 300)

    def test_roll_left_stays_inside_bounds(self):
        engine = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=10, y=450)
        engine.start(MotionMode.ROLL_LEFT, duration_ticks=10)

        for _ in range(6):
            frame = engine.tick()

        self.assertGreaterEqual(frame.x, 0)
        self.assertEqual(frame.mode, MotionMode.ROLL_RIGHT)

    def test_drag_release_falls_to_floor(self):
        engine = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=100)
        engine.start_drag()
        engine.drag_to(320, 120)
        engine.release_drag()

        for _ in range(80):
            frame = engine.tick()

        self.assertEqual(frame.mode, MotionMode.IDLE)
        self.assertEqual(frame.y, 450)

    def test_release_without_drag_keeps_current_mode(self):
        engine = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=450)
        engine.start(MotionMode.WALK_LEFT, duration_ticks=10)

        before = engine.mode

        self.assertEqual(before, MotionMode.WALK_LEFT)

    def test_selectable_motion_modes_do_not_include_roll(self):
        modes = selectable_motion_modes()

        self.assertNotIn(MotionMode.ROLL_LEFT, modes)
        self.assertNotIn(MotionMode.ROLL_RIGHT, modes)

    def test_speed_scale_changes_walk_distance(self):
        normal = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=450, speed_scale=1.0)
        fast = MotionEngine(DesktopBounds(0, 0, 800, 600), size=(180, 150), x=300, y=450, speed_scale=2.0)
        normal.start(MotionMode.WALK_RIGHT, duration_ticks=5)
        fast.start(MotionMode.WALK_RIGHT, duration_ticks=5)

        normal.tick()
        fast.tick()

        self.assertEqual(normal.x, 303)
        self.assertEqual(fast.x, 306)


if __name__ == "__main__":
    unittest.main()
