"""FastAPI dependency injection — graph instance and checkpointer."""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver

from podcast_shorts.graph.builder import build_graph


@lru_cache(maxsize=1)
def get_checkpointer() -> InMemorySaver:
    """Return a singleton in-memory checkpointer."""
    return InMemorySaver()


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Return the compiled pipeline graph with checkpointer."""
    checkpointer = get_checkpointer()
    return build_graph(checkpointer=checkpointer)
