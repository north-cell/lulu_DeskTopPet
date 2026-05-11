from __future__ import annotations


class DragIntentTracker:
    def __init__(self, threshold: int = 8):
        self.threshold = threshold
        self._press: tuple[int, int] | None = None
        self._dragging = False

    @property
    def dragging(self) -> bool:
        return self._dragging

    def press(self, x: int, y: int) -> None:
        self._press = (x, y)
        self._dragging = False

    def move(self, x: int, y: int) -> bool:
        if self._press is None:
            return False
        dx = x - self._press[0]
        dy = y - self._press[1]
        if (dx * dx + dy * dy) ** 0.5 >= self.threshold:
            self._dragging = True
        return self._dragging

    def release(self) -> str:
        result = "drag" if self._dragging else "click"
        self._press = None
        self._dragging = False
        return result
