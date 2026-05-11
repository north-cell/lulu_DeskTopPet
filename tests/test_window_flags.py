import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController
from lulu_pet.models import PetSettings
from lulu_pet.pet_window import PetWindow


class WindowFlagsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pet_window_requests_no_drop_shadow(self):
        settings = PetSettings((220, 180), True, 45, True, False, 100)
        window = PetWindow(PetController(AssetManager(None)), settings)
        try:
            self.assertTrue(window._window_flags() & Qt.NoDropShadowWindowHint)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
