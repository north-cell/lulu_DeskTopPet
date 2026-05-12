from __future__ import annotations

import sys
from pathlib import Path

from .paths import project_root


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_RUN_VALUE_NAME = "LuluDesktopPet"


def build_startup_command(executable: Path | str, frozen: bool, entry_script: Path | str | None = None) -> str:
    if frozen:
        return _quote_path(Path(executable))
    python_executable = _source_python_executable(Path(executable))
    script = Path(entry_script) if entry_script else project_root() / "run_lulu_pet.py"
    return f"{_quote_path(python_executable)} {_quote_path(script)}"


class AutostartManager:
    def __init__(
        self,
        command: str | None = None,
        winreg_module=None,
        platform: str | None = None,
        value_name: str = APP_RUN_VALUE_NAME,
    ):
        self.command = command or build_startup_command(
            Path(sys.executable),
            bool(getattr(sys, "frozen", False)),
            project_root() / "run_lulu_pet.py",
        )
        self.platform = platform or sys.platform
        self.value_name = value_name
        self._winreg = winreg_module if winreg_module is not None else _load_winreg(self.platform)

    @property
    def is_available(self) -> bool:
        return self.platform.startswith("win") and self._winreg is not None

    def is_enabled(self) -> bool:
        if not self.is_available:
            return False
        try:
            key = self._winreg.OpenKey(
                self._winreg.HKEY_CURRENT_USER,
                RUN_KEY_PATH,
                0,
                self._winreg.KEY_READ,
            )
            value, _ = self._winreg.QueryValueEx(key, self.value_name)
            return bool(value)
        except OSError:
            return False
        finally:
            self._close_key_if_present(locals().get("key"))

    def enable(self) -> None:
        if not self.is_available:
            return
        key = self._winreg.OpenKey(
            self._winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            self._winreg.KEY_SET_VALUE,
        )
        try:
            self._winreg.SetValueEx(key, self.value_name, 0, self._winreg.REG_SZ, self.command)
        finally:
            self._close_key_if_present(key)

    def disable(self) -> None:
        if not self.is_available:
            return
        key = self._winreg.OpenKey(
            self._winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            self._winreg.KEY_SET_VALUE,
        )
        try:
            self._winreg.DeleteValue(key, self.value_name)
        except FileNotFoundError:
            return
        finally:
            self._close_key_if_present(key)

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.enable()
        else:
            self.disable()

    def _close_key_if_present(self, key) -> None:
        if key is not None and self._winreg is not None:
            self._winreg.CloseKey(key)


def _quote_path(path: Path) -> str:
    return f'"{str(path).replace("/", "\\")}"'


def _source_python_executable(executable: Path) -> Path:
    if executable.name.lower() == "python.exe":
        return executable.with_name("pythonw.exe")
    return executable


def _load_winreg(platform: str):
    if not platform.startswith("win"):
        return None
    try:
        import winreg
    except ImportError:
        return None
    return winreg
