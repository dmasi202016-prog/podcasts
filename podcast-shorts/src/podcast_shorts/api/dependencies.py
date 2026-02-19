"""FastAPI dependency injection — graph instance and checkpointer."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from podcast_shorts.config import settings
from podcast_shorts.graph.builder import build_graph

# Module-level singletons — set during app lifespan
_checkpointer: BaseCheckpointSaver | None = None
_compiled_graph = None


def set_checkpointer(saver: BaseCheckpointSaver) -> None:
    """Store the checkpointer singleton (called from lifespan)."""
    global _checkpointer, _compiled_graph
    _checkpointer = saver
    # Invalidate cached graph so it rebuilds with the new checkpointer
    _compiled_graph = None


def get_checkpointer() -> BaseCheckpointSaver:
    """Return the active checkpointer."""
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized — app lifespan not started?")
    return _checkpointer


def get_compiled_graph():
    """Return the compiled pipeline graph with checkpointer."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph(checkpointer=get_checkpointer())
    return _compiled_graph


def is_postgres_backend() -> bool:
    """Check if we should use PostgresSaver."""
    return (
        settings.checkpoint_backend == "postgres"
        and bool(settings.database_url)
        and settings.database_url.startswith("postgres")
    )
