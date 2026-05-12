from __future__ import annotations

import time

from .assets import AssetManager
from .models import PetAction


class PetController:
    def __init__(self, assets: AssetManager, speech_interval_seconds: int = 45, contract_name: str = "shouting"):
        self.assets = assets
        self.speech_interval_seconds = speech_interval_seconds
        self.contract_name = self._normalize_contract_name(contract_name)
        self.current_action = self.assets.get_action(self.assets.default_action)
        self.action_until = 0.0
        self._last_speech_at = -float("inf")

    def set_contract_name(self, contract_name: str) -> None:
        self.contract_name = self._normalize_contract_name(contract_name)

    def set_action(self, name: str, now: float | None = None) -> PetAction:
        timestamp = time.monotonic() if now is None else now
        self.current_action = self.assets.get_action(name)
        self.action_until = timestamp + (self.current_action.duration_ms / 1000)
        return self.current_action

    def handle_click(self, now: float | None = None) -> PetAction:
        return self.set_action("clicked", now)

    def start_drag(self, now: float | None = None) -> PetAction:
        return self.set_action("dragged", now)

    def end_drag(self, now: float | None = None) -> PetAction:
        return self.set_action(self.assets.default_action, now)

    def tick(self, now: float | None = None) -> PetAction:
        timestamp = time.monotonic() if now is None else now
        if self.action_until and timestamp < self.action_until:
            return self.current_action
        return self.set_action(self.assets.random_action_name(), timestamp)

    def next_line(self, now: float | None = None) -> str:
        timestamp = time.monotonic() if now is None else now
        if timestamp - self._last_speech_at < self.speech_interval_seconds:
            return ""
        self._last_speech_at = timestamp
        return self.format_line(self.assets.random_line(self.current_action.name))

    def random_line(self, action_name: str) -> str:
        return self.format_line(self.assets.random_line(action_name))

    def format_line(self, line: str) -> str:
        return line.replace("shouting", self.contract_name)

    def _normalize_contract_name(self, contract_name: str) -> str:
        name = contract_name.strip() if isinstance(contract_name, str) else ""
        return name[:12] if name else "shouting"
