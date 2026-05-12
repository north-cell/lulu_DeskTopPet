from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PetSettings:
    window_size: tuple[int, int]
    always_on_top: bool
    speech_interval_seconds: int
    edge_snap: bool
    autostart: bool
    motion_speed_percent: int = 100
    contract_name: str = "shouting"


@dataclass(frozen=True)
class PetAction:
    name: str
    file_path: Path | None
    file_paths: tuple[Path, ...]
    duration_ms: int
    weight: int
    lines: tuple[str, ...]
