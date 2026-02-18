"""Tavily search and Google Trends — async helper functions."""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx
import structlog
from tavily import AsyncTavilyClient

from podcast_shorts.config import settings

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class TavilySearchResult:
    title: str
    url: str
    content: str
    score: float = 0.0


@dataclass
class GoogleTrendsResult:
    keyword: str
    source: str = "google_trends"


# ---------------------------------------------------------------------------
# Tavily
# ---------------------------------------------------------------------------


async def search_tavily_trends() -> list[TavilySearchResult]:
    """Search Tavily for trending Korean news across two queries in parallel.

    Returns an empty list on failure (graceful degradation).
    """
    if not settings.tavily_api_key:
        logger.warning("tavily.skip", reason="TAVILY_API_KEY not configured")
        return []

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    queries = ["한국 오늘 화제 트렌드", "오늘 인기 뉴스 이슈"]

    async def _search(query: str) -> list[dict]:
        try:
            resp = await client.search(
                query=query,
                topic="news",
                max_results=5,
                include_answer=False,
                search_depth="basic",
            )
            return resp.get("results", [])
        except Exception:
            logger.exception("tavily.query_failed", query=query)
            return []

    try:
        raw_results = await asyncio.gather(*[_search(q) for q in queries])

        # Flatten and deduplicate by URL
        seen_urls: set[str] = set()
        results: list[TavilySearchResult] = []
        for batch in raw_results:
            for item in batch:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(
                    TavilySearchResult(
                        title=item.get("title", ""),
                        url=url,
                        content=item.get("content", ""),
                        score=item.get("score", 0.0),
                    )
                )

        logger.info("tavily.done", result_count=len(results))
        return results
    except Exception:
        logger.exception("tavily.failed")
        return []


# ---------------------------------------------------------------------------
# Google Trends
# ---------------------------------------------------------------------------


_GOOGLE_TRENDS_RSS_URL = (
    "https://trends.google.co.kr/trending/rss?geo=KR"
)


async def fetch_google_trends_kr() -> list[GoogleTrendsResult]:
    """Fetch currently trending searches in South Korea.

    Primary: Google Trends RSS feed (async httpx).
    Fallback: pytrends library (sync, run in executor).
    Returns an empty list if both fail (graceful degradation).
    """
    # --- Primary: RSS feed ---
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_GOOGLE_TRENDS_RSS_URL)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        keywords: list[str] = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                keywords.append(title_el.text.strip())

        if keywords:
            results = [GoogleTrendsResult(keyword=kw) for kw in keywords]
            logger.info("google_trends.rss_done", keyword_count=len(results))
            return results
    except Exception:
        logger.warning("google_trends.rss_failed", reason="Falling back to pytrends")

    # --- Fallback: pytrends ---
    loop = asyncio.get_running_loop()

    def _fetch() -> list[str]:
        from pytrends.request import TrendReq  # lazy import — heavy module

        pytrends = TrendReq(hl="ko", tz=540)  # KST = UTC+9
        df = pytrends.trending_searches(pn="south_korea")
        return df[0].tolist()

    try:
        kw_list = await loop.run_in_executor(None, _fetch)
        results = [GoogleTrendsResult(keyword=kw) for kw in kw_list]
        logger.info("google_trends.pytrends_done", keyword_count=len(results))
        return results
    except Exception:
        logger.exception("google_trends.failed")
        return []
