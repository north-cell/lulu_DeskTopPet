from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .models import PetAction


BUILTIN_ACTIONS: dict[str, dict[str, Any]] = {
    "idle": {
        "file": None,
        "duration_ms": 4200,
        "weight": 8,
        "lines": [
            "噜噜在发呆。",
            "今天也适合慢慢来。",
            "水豚正在充电。",
            "shouting今天也要被温柔对待。",
            "噜噜最喜欢shouting啦。",
            "shouting认真起来亮晶晶的。",
        ],
    },
    "walk": {
        "file": None,
        "duration_ms": 3200,
        "weight": 4,
        "lines": ["噜噜挪了两步。", "去桌面边边看看。", "噜噜巡视一下，看看shouting有没有累。"],
    },
    "sleep": {
        "file": None,
        "duration_ms": 5500,
        "weight": 3,
        "lines": ["困困。", "噜噜眯一会儿。", "shouting也要记得休息。"],
    },
    "happy": {
        "file": None,
        "duration_ms": 2600,
        "weight": 5,
        "lines": ["被发现啦。", "嘿嘿。", "看见shouting，噜噜就开心。"],
    },
    "dragged": {
        "file": None,
        "duration_ms": 1000,
        "weight": 0,
        "lines": ["慢点慢点。", "噜噜要回去陪shouting。"],
    },
    "clicked": {
        "file": None,
        "duration_ms": 1800,
        "weight": 0,
        "lines": [
            "摸摸头。",
            "噜噜喜欢这个。",
            "shouting辛苦啦，噜噜给你贴贴。",
            "shouting超可爱，噜噜认证。",
            "噜噜想一直陪着shouting。",
        ],
    },
}


class AssetManager:
    def __init__(self, manifest_path: Path | None):
        self.manifest_path = Path(manifest_path) if manifest_path else None
        self.base_dir = self.manifest_path.parent if self.manifest_path else Path.cwd()
        self.default_action = "idle"
        self._actions = self._load_actions()

    @property
    def action_names(self) -> tuple[str, ...]:
        return tuple(self._actions)

    def get_action(self, name: str) -> PetAction:
        action = self._actions.get(name) or self._actions[self.default_action]
        if len(action.file_paths) <= 1:
            return action
        return PetAction(
            name=action.name,
            file_path=random.choice(action.file_paths),
            file_paths=action.file_paths,
            duration_ms=action.duration_ms,
            weight=action.weight,
            lines=action.lines,
        )

    def random_action_name(self) -> str:
        actions = [action for action in self._actions.values() if action.weight > 0]
        if not actions:
            return self.default_action
        return random.choices([action.name for action in actions], weights=[action.weight for action in actions], k=1)[0]

    def random_line(self, action_name: str) -> str:
        action = self.get_action(action_name)
        return random.choice(action.lines) if action.lines else ""

    def random_file_path(self) -> Path | None:
        paths = [path for action in self._actions.values() for path in action.file_paths]
        return random.choice(paths) if paths else None

    def _load_actions(self) -> dict[str, PetAction]:
        manifest = self._read_manifest()
        self.default_action = str(manifest.get("default_action") or "idle")
        actions_data = manifest.get("actions")
        if not isinstance(actions_data, dict) or not actions_data:
            actions_data = BUILTIN_ACTIONS
            self.default_action = "idle"

        actions: dict[str, PetAction] = {}
        for name, raw in actions_data.items():
            if not isinstance(raw, dict):
                continue
            action = self._action_from_raw(str(name), raw)
            actions[action.name] = action

        if self.default_action not in actions:
            self.default_action = "idle" if "idle" in actions else next(iter(actions), "idle")
        if not actions:
            actions = {name: self._action_from_raw(name, raw) for name, raw in BUILTIN_ACTIONS.items()}
            self.default_action = "idle"
        return actions

    def _read_manifest(self) -> dict[str, Any]:
        if not self.manifest_path:
            return {"default_action": "idle", "actions": BUILTIN_ACTIONS}
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"default_action": "idle", "actions": BUILTIN_ACTIONS}

    def _action_from_raw(self, name: str, raw: dict[str, Any]) -> PetAction:
        file_paths = self._file_paths(raw)
        file_path = file_paths[0] if file_paths else None
        lines = raw.get("lines")
        return PetAction(
            name=name,
            file_path=file_path,
            file_paths=file_paths,
            duration_ms=_positive_int(raw.get("duration_ms"), 3000),
            weight=max(0, _positive_int(raw.get("weight"), 1)),
            lines=tuple(str(line) for line in lines) if isinstance(lines, list) else (),
        )

    def _file_paths(self, raw: dict[str, Any]) -> tuple[Path, ...]:
        files = raw.get("files")
        if isinstance(files, list):
            paths = [self.base_dir / file for file in files if isinstance(file, str) and file]
            if paths:
                return tuple(paths)

        file_value = raw.get("file")
        if isinstance(file_value, str) and file_value:
            return (self.base_dir / file_value,)
        return ()


def _positive_int(value: Any, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return int(fallback)
    return number if number > 0 else int(fallback)
