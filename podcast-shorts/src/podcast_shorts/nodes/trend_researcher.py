"""Trend Researcher node — discovers and analyzes trending topics."""

from __future__ import annotations

import asyncio

import structlog
from langchain_openai import ChatOpenAI

from podcast_shorts.config import settings
from podcast_shorts.graph.state import PipelineState, QualityAssessment, TrendData
from podcast_shorts.models.trend import (
    QualityEvaluation,
    TrendAnalysisResult,
)
from podcast_shorts.tools.search import (
    fetch_google_trends_kr,
    search_tavily_trends,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """\
당신은 한국 트렌드 분석 전문가입니다. 주어진 원시 트렌드 데이터를 분석하여 각 키워드가 왜 트렌딩인지 설명하고, \
팟캐스트 쇼츠(1-3분 분량)에 가장 적합한 주제를 추천해야 합니다.

**중요: 모든 분석 결과(keyword, why_trending, summary, category, recommended_topic, reasoning 등)를 반드시 한국어로 작성하세요.**

분석 기준:
- 대중의 관심도와 화제성
- 팟캐스트 쇼츠로 다룰 때의 흥미도
- 충분한 맥락과 이야기 소재가 있는지
- 1-3분 분량으로 압축 가능한 주제인지

카테고리 분류: 기술, 엔터테인먼트, 사회, 경제, 스포츠, 정치, 문화, 과학, 건강, 교육"""

ANALYSIS_USER_PROMPT = """\
아래는 오늘의 한국 트렌드 원시 데이터입니다. 각 키워드를 분석하고 팟캐스트 쇼츠에 가장 적합한 주제를 추천해 주세요.

## Tavily 뉴스 검색 결과
{tavily_data}

## Google Trends 인기 검색어
{google_trends_data}"""

QUALITY_SYSTEM_PROMPT = """\
당신은 팟캐스트 쇼츠 파이프라인의 품질 평가자입니다. 트렌드 분석 결과를 평가하여 \
다음 단계(스크립트 작성)로 넘어가기에 충분한 품질인지 판단해야 합니다.

**중요: feedback을 반드시 한국어로 작성하세요.**

평가 기준:
- 추천 주제가 실제로 트렌딩이며 대중의 관심을 끌 수 있는가
- 분석에 충분한 맥락과 배경 정보가 포함되어 있는가
- 스크립트 작성자가 1-3분 분량의 대본을 쓸 수 있을 만큼의 소재가 있는가"""

QUALITY_USER_PROMPT = """\
다음 트렌드 분석 결과의 품질을 평가해 주세요.

추천 주제: {recommended_topic}
카테고리: {recommended_category}
추천 이유: {reasoning}

키워드별 분석:
{analyses_text}"""


# ---------------------------------------------------------------------------
# Node implementation
# ---------------------------------------------------------------------------


async def trend_researcher(state: PipelineState) -> dict:
    """Pull trending topics from multiple sources, analyze why they're trending,
    and select the best topic matching user interest categories.
    """
    logger.info("trend_researcher.start", run_id=state.get("run_id"))

    retry_counts = state.get("retry_counts", {})
    attempt = retry_counts.get("trend_researcher", 0) + 1

    try:
        # ── Step 1: Parallel source collection ──────────────────────────
        tavily_results, google_results = await asyncio.gather(
            search_tavily_trends(),
            fetch_google_trends_kr(),
        )

        logger.info(
            "trend_researcher.sources_collected",
            tavily_count=len(tavily_results),
            google_count=len(google_results),
        )

        if not tavily_results and not google_results:
            raise RuntimeError("Both trend sources returned empty results")

        # ── Step 2: Format raw data for LLM ─────────────────────────────
        tavily_text = "\n".join(
            f"- [{r.title}]({r.url}): {r.content[:200]}" for r in tavily_results
        ) or "(결과 없음)"

        google_text = "\n".join(
            f"- {r.keyword}" for r in google_results
        ) or "(결과 없음)"

        # ── Step 3: GPT-4o structured analysis ──────────────────────────
        llm = ChatOpenAI(
            model=settings.reasoning_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
        )

        analysis_llm = llm.with_structured_output(TrendAnalysisResult)
        analysis: TrendAnalysisResult = await analysis_llm.ainvoke(
            [
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ANALYSIS_USER_PROMPT.format(
                        tavily_data=tavily_text,
                        google_trends_data=google_text,
                    ),
                },
            ]
        )

        logger.info(
            "trend_researcher.analysis_done",
            keyword_count=len(analysis.analyses),
            recommended=analysis.recommended_topic,
        )

        # ── Step 4: Filter by user interest categories ──────────────────
        user_prefs = state.get("user_preferences", {})
        preferred_categories = user_prefs.get("categories", [])

        if preferred_categories:
            filtered = [
                a
                for a in analysis.analyses
                if a.category in preferred_categories
            ]
            if filtered:
                # Re-pick recommendation from filtered set
                best = max(filtered, key=lambda a: a.relevance_score)
                analysis.recommended_topic = best.keyword
                analysis.recommended_category = best.category
                analysis.analyses = filtered
                logger.info(
                    "trend_researcher.filtered",
                    categories=preferred_categories,
                    remaining=len(filtered),
                )
            else:
                logger.info(
                    "trend_researcher.filter_fallback",
                    reason="No results matched user categories, using all results",
                )

        # ── Step 5: Convert to TrendData TypedDict ──────────────────────
        trend_data: TrendData = {
            "keywords": [a.keyword for a in analysis.analyses],
            "topic_summaries": [
                {
                    "keyword": a.keyword,
                    "summary": f"{a.why_trending} {a.summary}",
                    "source": a.source,
                    "trending_score": a.relevance_score,
                }
                for a in analysis.analyses
            ],
            "selected_topic": analysis.recommended_topic,
            "category": analysis.recommended_category,
        }

        # ── Step 6: Self quality evaluation ─────────────────────────────
        analyses_text = "\n".join(
            f"- {a.keyword} ({a.category}, 적합도: {a.relevance_score}): {a.why_trending}"
            for a in analysis.analyses
        )

        quality_llm = llm.with_structured_output(QualityEvaluation)
        quality_eval: QualityEvaluation = await quality_llm.ainvoke(
            [
                {"role": "system", "content": QUALITY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": QUALITY_USER_PROMPT.format(
                        recommended_topic=analysis.recommended_topic,
                        recommended_category=analysis.recommended_category,
                        reasoning=analysis.reasoning,
                        analyses_text=analyses_text,
                    ),
                },
            ]
        )

        passed = quality_eval.score >= settings.quality_threshold

        quality: QualityAssessment = {
            "node_name": "trend_researcher",
            "passed": passed,
            "score": quality_eval.score,
            "feedback": quality_eval.feedback,
            "attempt": attempt,
        }

        logger.info(
            "trend_researcher.done",
            topic=trend_data["selected_topic"],
            quality_score=quality_eval.score,
            passed=passed,
            attempt=attempt,
        )

    except Exception:
        logger.exception("trend_researcher.error", attempt=attempt)
        trend_data = {
            "keywords": [],
            "topic_summaries": [],
            "selected_topic": "",
            "category": "",
        }
        quality = {
            "node_name": "trend_researcher",
            "passed": False,
            "score": 0.0,
            "feedback": "Trend research failed due to an error. Will retry.",
            "attempt": attempt,
        }

    retry_counts = {**retry_counts, "trend_researcher": attempt}

    return {
        "trend_data": trend_data,
        "quality": quality,
        "retry_counts": retry_counts,
    }
