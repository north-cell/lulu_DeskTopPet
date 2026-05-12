from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FocusRecord:
    date: str
    start_time: str
    end_time: str
    duration_seconds: int
    duration_text: str

    @property
    def menu_text(self) -> str:
        return f"{self.date} {self.start_time}-{self.end_time} {self.duration_text}"


class FocusRecordStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> list[FocusRecord]:
        try:
            if not self.path.exists():
                return []
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [record for item in data if (record := _record_from_json(item))]

    def add(self, record: FocusRecord) -> None:
        records = self.load()
        records.append(record)
        self.save(records)

    def remove(self, record: FocusRecord) -> None:
        records = self.load()
        try:
            records.remove(record)
        except ValueError:
            return
        self.save(records)

    def save(self, records: list[FocusRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "date": item.date,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "duration_seconds": item.duration_seconds,
                "duration_text": item.duration_text,
            }
            for item in records
        ]
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _record_from_json(value: Any) -> FocusRecord | None:
    if not isinstance(value, dict):
        return None
    try:
        duration_seconds = int(value["duration_seconds"])
        return FocusRecord(
            date=str(value["date"]),
            start_time=str(value["start_time"]),
            end_time=str(value["end_time"]),
            duration_seconds=max(0, duration_seconds),
            duration_text=str(value["duration_text"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
