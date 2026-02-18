"""X/Twitter trending API tool."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
async def twitter_trending(woeid: int = 23424868) -> str:
    """Get trending topics from X/Twitter. Default WOEID is South Korea."""
    # TODO: Implement with tweepy
    return f"[STUB] Twitter trending for WOEID={woeid}"
