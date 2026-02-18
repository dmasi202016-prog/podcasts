"""Style history tracker — records past video styles for consistency."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StyleRecord:
    run_id: str
    tone: str
    bgm_style: str
    visual_style: str


class StyleHistoryStore:
    """In-memory store for video style history. Replace with database-backed implementation."""

    def __init__(self):
        self._store: dict[str, list[StyleRecord]] = {}

    async def get_history(self, user_id: str, limit: int = 10) -> list[StyleRecord]:
        return self._store.get(user_id, [])[:limit]

    async def add_record(self, user_id: str, record: StyleRecord) -> None:
        if user_id not in self._store:
            self._store[user_id] = []
        self._store[user_id].append(record)
