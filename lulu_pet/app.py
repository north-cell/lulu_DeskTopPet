from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .assets import AssetManager
from .controller import PetController
from .paths import resource_path
from .pet_window import PetWindow
from .settings import SettingsStore
from .tray import TrayController


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("水豚噜噜")
    app.setQuitOnLastWindowClosed(False)

    settings_store = SettingsStore(resource_path("config", "settings.json"))
    settings = settings_store.load()
    assets = AssetManager(resource_path("assets", "manifest.json"))
    controller = PetController(assets, settings.speech_interval_seconds)
    pet = PetWindow(controller, settings, settings_store)
    tray = TrayController(pet)

    tray.show()
    pet.show()
    exit_code = app.exec()
    tray.hide()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
