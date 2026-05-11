from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum


class MotionMode(StrEnum):
    IDLE = "idle"
    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    RUN_LEFT = "run_left"
    RUN_RIGHT = "run_right"
    ROLL_LEFT = "roll_left"
    ROLL_RIGHT = "roll_right"
    SLEEP = "sleep"
    DRAGGED = "dragged"
    FALLING = "falling"


def selectable_motion_modes() -> tuple[MotionMode, ...]:
    return (
        MotionMode.IDLE,
        MotionMode.IDLE,
        MotionMode.SLEEP,
        MotionMode.WALK_LEFT,
        MotionMode.WALK_RIGHT,
        MotionMode.RUN_LEFT,
        MotionMode.RUN_RIGHT,
    )


@dataclass(frozen=True)
class DesktopBounds:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height


@dataclass(frozen=True)
class MotionFrame:
    mode: MotionMode
    x: int
    y: int
    frame_index: int
    facing: int
    rotation_degrees: int = 0


class MotionEngine:
    def __init__(
        self,
        bounds: DesktopBounds,
        size: tuple[int, int],
        x: int | None = None,
        y: int | None = None,
        speed_scale: float = 1.0,
    ):
        self.bounds = bounds
        self.width, self.height = size
        self.speed_scale = max(0.4, min(2.2, speed_scale))
        self.x = self._clamp_x(bounds.right - self.width - 80 if x is None else x)
        self.floor_y = bounds.bottom - self.height
        self.y = self._clamp_y(self.floor_y if y is None else y)
        self.mode = MotionMode.IDLE
        self.facing = -1
        self.frame_index = 0
        self.ticks_left = 80
        self.velocity_y = 0.0

    def start(self, mode: MotionMode, duration_ticks: int | None = None) -> None:
        self.mode = mode
        self.ticks_left = duration_ticks if duration_ticks is not None else self._default_duration(mode)
        if mode in (MotionMode.WALK_LEFT, MotionMode.RUN_LEFT, MotionMode.ROLL_LEFT):
            self.facing = -1
        elif mode in (MotionMode.WALK_RIGHT, MotionMode.RUN_RIGHT, MotionMode.ROLL_RIGHT):
            self.facing = 1
        if mode == MotionMode.FALLING:
            self.velocity_y = max(self.velocity_y, 2.0)

    def start_drag(self) -> None:
        self.mode = MotionMode.DRAGGED
        self.ticks_left = 0
        self.velocity_y = 0.0

    def drag_to(self, x: int, y: int) -> MotionFrame:
        self.x = self._clamp_x(x)
        self.y = self._clamp_y(y)
        return self._frame()

    def release_drag(self) -> None:
        if self.y < self.floor_y:
            self.start(MotionMode.FALLING, duration_ticks=9999)
        else:
            self.start(MotionMode.IDLE)

    def tick(self) -> MotionFrame:
        self.frame_index += 1

        if self.mode == MotionMode.DRAGGED:
            return self._frame()
        if self.mode == MotionMode.FALLING:
            self._fall()
            return self._frame()

        self._move_horizontal(self._speed_for(self.mode))
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self._choose_next_mode()
        return self._frame()

    def _move_horizontal(self, speed: int) -> None:
        if speed == 0:
            return
        self.x += speed * self.facing
        if self.x <= self.bounds.left:
            self.x = self.bounds.left
            self.start(self._opposite_mode(), self.ticks_left)
        elif self.x + self.width >= self.bounds.right:
            self.x = self.bounds.right - self.width
            self.start(self._opposite_mode(), self.ticks_left)

    def _fall(self) -> None:
        self.velocity_y = min(self.velocity_y + 1.4, 28)
        self.y = self._clamp_y(round(self.y + self.velocity_y))
        if self.y >= self.floor_y:
            self.y = self.floor_y
            self.velocity_y = 0.0
            self.start(MotionMode.IDLE)

    def _choose_next_mode(self) -> None:
        self.start(random.choice(selectable_motion_modes()))

    def _opposite_mode(self) -> MotionMode:
        opposites = {
            MotionMode.WALK_LEFT: MotionMode.WALK_RIGHT,
            MotionMode.WALK_RIGHT: MotionMode.WALK_LEFT,
            MotionMode.RUN_LEFT: MotionMode.RUN_RIGHT,
            MotionMode.RUN_RIGHT: MotionMode.RUN_LEFT,
            MotionMode.ROLL_LEFT: MotionMode.ROLL_RIGHT,
            MotionMode.ROLL_RIGHT: MotionMode.ROLL_LEFT,
        }
        return opposites.get(self.mode, MotionMode.IDLE)

    def _frame(self) -> MotionFrame:
        rotation = 0
        if self.mode in (MotionMode.ROLL_LEFT, MotionMode.ROLL_RIGHT):
            rotation = (self.frame_index * 28 * self.facing) % 360
        return MotionFrame(self.mode, int(self.x), int(self.y), self.frame_index, self.facing, rotation)

    def _speed_for(self, mode: MotionMode) -> int:
        if mode in (MotionMode.WALK_LEFT, MotionMode.WALK_RIGHT):
            return max(1, round(3 * self.speed_scale))
        if mode in (MotionMode.RUN_LEFT, MotionMode.RUN_RIGHT):
            return max(1, round(8 * self.speed_scale))
        if mode in (MotionMode.ROLL_LEFT, MotionMode.ROLL_RIGHT):
            return max(1, round(6 * self.speed_scale))
        return 0

    def _default_duration(self, mode: MotionMode) -> int:
        if mode == MotionMode.IDLE:
            return random.randint(70, 140)
        if mode == MotionMode.SLEEP:
            return random.randint(120, 220)
        if mode in (MotionMode.RUN_LEFT, MotionMode.RUN_RIGHT):
            return random.randint(28, 60)
        if mode in (MotionMode.ROLL_LEFT, MotionMode.ROLL_RIGHT):
            return random.randint(45, 90)
        return random.randint(55, 120)

    def _clamp_x(self, value: int) -> int:
        return max(self.bounds.left, min(value, self.bounds.right - self.width))

    def _clamp_y(self, value: int) -> int:
        return max(self.bounds.top, min(value, self.floor_y))
