from __future__ import annotations

import time

from .assets import AssetManager
from .models import PetAction


class PetController:
    def __init__(self, assets: AssetManager, speech_interval_seconds: int = 45):
        self.assets = assets
        self.speech_interval_seconds = speech_interval_seconds
        self.current_action = self.assets.get_action(self.assets.default_action)
        self.action_until = 0.0
        self._last_speech_at = -float("inf")

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
        return self.assets.random_line(self.current_action.name)
