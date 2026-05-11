import unittest

from lulu_pet.interaction import DragIntentTracker


class DragIntentTrackerTests(unittest.TestCase):
    def test_press_release_without_motion_is_click(self):
        tracker = DragIntentTracker(threshold=6)
        tracker.press(100, 100)

        self.assertFalse(tracker.move(103, 104))
        self.assertEqual(tracker.release(), "click")

    def test_motion_past_threshold_starts_drag(self):
        tracker = DragIntentTracker(threshold=6)
        tracker.press(100, 100)

        self.assertTrue(tracker.move(120, 100))
        self.assertEqual(tracker.release(), "drag")


if __name__ == "__main__":
    unittest.main()
