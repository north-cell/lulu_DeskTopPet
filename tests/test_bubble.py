import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from lulu_pet.bubble import BubbleWidget


class BubbleWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_bubble_does_not_use_widget_shadow_effect(self):
        bubble = BubbleWidget()
        try:
            self.assertIsNone(bubble.graphicsEffect())
        finally:
            bubble.close()

    def test_bubble_uses_frameless_window_without_native_tooltip_shadow(self):
        bubble = BubbleWidget()
        try:
            flags = bubble.windowFlags()
            window_type = flags & Qt.WindowType_Mask

            self.assertEqual(window_type, Qt.Tool)
            self.assertTrue(flags & Qt.FramelessWindowHint)
            self.assertTrue(flags & Qt.NoDropShadowWindowHint)
        finally:
            bubble.close()

    def test_bubble_applies_shape_mask_after_message(self):
        anchor = BubbleWidget()
        bubble = BubbleWidget()
        try:
            anchor.resize(120, 120)
            anchor.show()
            bubble.show_message("shouting辛苦啦，先让噜噜等一下。", anchor)

            self.assertFalse(bubble.mask().isEmpty())
        finally:
            bubble.close()
            anchor.close()


if __name__ == "__main__":
    unittest.main()
