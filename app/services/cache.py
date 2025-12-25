from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Entry:
    value: str
    expires_at: float


class TTLCache:

    def __init__(self, ttl_seconds: int = 600, max_items: int = 512):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._data: dict[str, _Entry] = {}

    def get(self, key: str) -> str | None:
        now = time.time()
        ent = self._data.get(key)
        if not ent:
            return None
        if ent.expires_at < now:
            self._data.pop(key, None)
            return None
        return ent.value

    def set(self, key: str, value: str) -> None:
        now = time.time()
        if len(self._data) >= self.max_items and key not in self._data:
            self._data.pop(next(iter(self._data)), None)
        self._data[key] = _Entry(value=value, expires_at=now + self.ttl_seconds)

    def clear(self) -> None:
        self._data.clear()
