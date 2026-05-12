from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import PetSettings


DEFAULT_SETTINGS: dict[str, Any] = {
    "window_size": [184, 151],
    "always_on_top": True,
    "speech_interval_seconds": 45,
    "edge_snap": True,
    "autostart": False,
    "motion_speed_percent": 100,
}


class SettingsStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> PetSettings:
        data = dict(DEFAULT_SETTINGS)
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data.update(loaded)
        except (OSError, json.JSONDecodeError):
            data = dict(DEFAULT_SETTINGS)

        return PetSettings(
            window_size=_window_size(data.get("window_size")),
            always_on_top=bool(data.get("always_on_top", DEFAULT_SETTINGS["always_on_top"])),
            speech_interval_seconds=_positive_int(
                data.get("speech_interval_seconds"),
                DEFAULT_SETTINGS["speech_interval_seconds"],
            ),
            edge_snap=bool(data.get("edge_snap", DEFAULT_SETTINGS["edge_snap"])),
            autostart=bool(data.get("autostart", DEFAULT_SETTINGS["autostart"])),
            motion_speed_percent=_bounded_int(
                data.get("motion_speed_percent"),
                DEFAULT_SETTINGS["motion_speed_percent"],
                40,
                220,
            ),
        )

    def save(self, settings: PetSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "window_size": list(settings.window_size),
            "always_on_top": settings.always_on_top,
            "speech_interval_seconds": settings.speech_interval_seconds,
            "edge_snap": settings.edge_snap,
            "autostart": settings.autostart,
            "motion_speed_percent": settings.motion_speed_percent,
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _window_size(value: Any) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        width = _positive_int(value[0], DEFAULT_SETTINGS["window_size"][0])
        height = _positive_int(value[1], DEFAULT_SETTINGS["window_size"][1])
        return width, height
    return tuple(DEFAULT_SETTINGS["window_size"])


def _positive_int(value: Any, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return int(fallback)
    return number if number > 0 else int(fallback)


def _bounded_int(value: Any, fallback: int, minimum: int, maximum: int) -> int:
    number = _positive_int(value, fallback)
    return max(minimum, min(maximum, number))
