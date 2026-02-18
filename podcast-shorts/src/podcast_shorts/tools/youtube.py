"""YouTube trending API tool."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
async def youtube_trending(region: str = "KR", category: str = "0") -> str:
    """Get currently trending videos from YouTube for a region."""
    # TODO: Implement with google-api-python-client
    return f"[STUB] YouTube trending for region={region}, category={category}"
