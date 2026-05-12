import unittest
from pathlib import Path

from lulu_pet.autostart import AutostartManager, build_startup_command


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}
        self.opened = []
        self.deleted = []

    def OpenKey(self, root, path, reserved=0, access=0):  # noqa: N802 - mirrors winreg
        self.opened.append((root, path, reserved, access))
        return self

    def SetValueEx(self, key, name, reserved, value_type, value):  # noqa: N802 - mirrors winreg
        self.values[name] = (value_type, value)

    def QueryValueEx(self, key, name):  # noqa: N802 - mirrors winreg
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name][1], self.values[name][0]

    def DeleteValue(self, key, name):  # noqa: N802 - mirrors winreg
        self.deleted.append(name)
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]

    def CloseKey(self, key):  # noqa: N802 - mirrors winreg
        pass


class AutostartTests(unittest.TestCase):
    def test_build_startup_command_uses_executable_for_packaged_app(self):
        command = build_startup_command(
            executable=Path("C:/Apps/LuluDesktopPet/LuluDesktopPet.exe"),
            frozen=True,
            entry_script=Path("E:/repo/run_lulu_pet.py"),
        )

        self.assertEqual(command, '"C:\\Apps\\LuluDesktopPet\\LuluDesktopPet.exe"')

    def test_build_startup_command_uses_python_and_entry_script_for_source_run(self):
        command = build_startup_command(
            executable=Path("C:/Python312/pythonw.exe"),
            frozen=False,
            entry_script=Path("E:/repo/run_lulu_pet.py"),
        )

        self.assertEqual(command, '"C:\\Python312\\pythonw.exe" "E:\\repo\\run_lulu_pet.py"')

    def test_build_startup_command_prefers_pythonw_for_source_run_to_avoid_console(self):
        command = build_startup_command(
            executable=Path("C:/Python312/python.exe"),
            frozen=False,
            entry_script=Path("E:/repo/run_lulu_pet.py"),
        )

        self.assertEqual(command, '"C:\\Python312\\pythonw.exe" "E:\\repo\\run_lulu_pet.py"')

    def test_enable_disable_and_is_enabled_use_current_user_run_key(self):
        winreg = FakeWinreg()
        manager = AutostartManager(
            command='"C:\\Apps\\LuluDesktopPet\\LuluDesktopPet.exe"',
            winreg_module=winreg,
            platform="win32",
        )

        self.assertFalse(manager.is_enabled())

        manager.enable()

        self.assertTrue(manager.is_enabled())
        self.assertEqual(
            winreg.values["LuluDesktopPet"],
            (winreg.REG_SZ, '"C:\\Apps\\LuluDesktopPet\\LuluDesktopPet.exe"'),
        )

        manager.disable()

        self.assertFalse(manager.is_enabled())
        self.assertEqual(winreg.deleted, ["LuluDesktopPet"])

    def test_is_enabled_accepts_existing_legacy_command_for_same_run_value(self):
        winreg = FakeWinreg()
        winreg.values["LuluDesktopPet"] = (
            winreg.REG_SZ,
            '"C:\\Python312\\python.exe" "E:\\repo\\run_lulu_pet.py"',
        )
        manager = AutostartManager(
            command='"C:\\Python312\\pythonw.exe" "E:\\repo\\run_lulu_pet.py"',
            winreg_module=winreg,
            platform="win32",
        )

        self.assertTrue(manager.is_enabled())

    def test_non_windows_manager_is_safely_unavailable(self):
        manager = AutostartManager(command='"app"', winreg_module=None, platform="linux")

        self.assertFalse(manager.is_available)
        self.assertFalse(manager.is_enabled())
        manager.set_enabled(True)
        manager.set_enabled(False)


if __name__ == "__main__":
    unittest.main()
