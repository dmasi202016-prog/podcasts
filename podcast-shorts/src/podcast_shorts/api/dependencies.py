"""FastAPI dependency injection — graph instance and checkpointer."""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from podcast_shorts.config import settings
from podcast_shorts.graph.builder import build_graph


@lru_cache(maxsize=1)
def get_checkpointer() -> BaseCheckpointSaver:
    """Return a singleton checkpointer.

    Uses AsyncPostgresSaver when checkpoint_backend="postgres" and database_url is set,
    otherwise falls back to InMemorySaver.
    """
    if settings.checkpoint_backend == "postgres" and settings.database_url.startswith(
        "postgres"
    ):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # Append prepare_threshold=0 for Supabase PgBouncer compatibility
        conn_string = settings.database_url
        separator = "&" if "?" in conn_string else "?"
        if "prepare_threshold" not in conn_string:
            conn_string = f"{conn_string}{separator}prepare_threshold=0"

        return AsyncPostgresSaver.from_conn_string(conn_string)
    return InMemorySaver()


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Return the compiled pipeline graph with checkpointer."""
    checkpointer = get_checkpointer()
    return build_graph(checkpointer=checkpointer)
