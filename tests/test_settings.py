import json
import tempfile
import unittest
from pathlib import Path

from lulu_pet.settings import DEFAULT_SETTINGS, SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_missing_settings_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore(Path(tmp) / "missing.json")

            settings = store.load()

            self.assertEqual(settings.window_size, tuple(DEFAULT_SETTINGS["window_size"]))
            self.assertTrue(settings.always_on_top)
            self.assertFalse(settings.autostart)

    def test_invalid_settings_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{bad json", encoding="utf-8")
            store = SettingsStore(path)

            settings = store.load()

            self.assertEqual(settings.speech_interval_seconds, DEFAULT_SETTINGS["speech_interval_seconds"])

    def test_partial_settings_merge_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"always_on_top": False, "window_size": [260, 220]}), encoding="utf-8")
            store = SettingsStore(path)

            settings = store.load()

            self.assertFalse(settings.always_on_top)
            self.assertEqual(settings.window_size, (260, 220))
            self.assertTrue(settings.edge_snap)
            self.assertEqual(settings.motion_speed_percent, DEFAULT_SETTINGS["motion_speed_percent"])

    def test_motion_speed_percent_is_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"motion_speed_percent": 140}), encoding="utf-8")
            store = SettingsStore(path)

            settings = store.load()

            self.assertEqual(settings.motion_speed_percent, 140)

    def test_contract_name_defaults_to_shouting_for_old_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"always_on_top": False}), encoding="utf-8")
            store = SettingsStore(path)

            settings = store.load()

            self.assertEqual(settings.contract_name, "shouting")

    def test_invalid_contract_name_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"contract_name": "   "}), encoding="utf-8")
            store = SettingsStore(path)

            settings = store.load()

            self.assertEqual(settings.contract_name, "shouting")

    def test_save_writes_contract_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            store = SettingsStore(path)
            settings = store.load()
            settings = type(settings)(
                window_size=settings.window_size,
                always_on_top=settings.always_on_top,
                speech_interval_seconds=settings.speech_interval_seconds,
                edge_snap=settings.edge_snap,
                autostart=settings.autostart,
                motion_speed_percent=settings.motion_speed_percent,
                contract_name="露露",
            )

            store.save(settings)

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["contract_name"], "露露")


if __name__ == "__main__":
    unittest.main()
