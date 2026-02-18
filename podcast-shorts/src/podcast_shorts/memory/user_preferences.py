"""User preferences store — persists interest categories and persona settings."""

from __future__ import annotations


class UserPreferencesStore:
    """In-memory store for user preferences. Replace with database-backed implementation."""

    def __init__(self):
        self._store: dict[str, dict] = {}

    async def get(self, user_id: str) -> dict:
        return self._store.get(user_id, {})

    async def update(self, user_id: str, preferences: dict) -> None:
        existing = self._store.get(user_id, {})
        existing.update(preferences)
        self._store[user_id] = existing
