"""Topic Selection Gate — pauses pipeline for user to select a trending topic."""

from __future__ import annotations

import structlog
from langgraph.types import interrupt

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()


async def topic_selection_gate(state: PipelineState) -> dict:
    """Interrupt the pipeline and present trending topics for user selection.

    The trend_researcher has already populated trend_data with topic_summaries.
    The user picks one topic to proceed with for scriptwriting.

    On resume, the Command(resume=...) payload provides:
      {"selected_topic": "키워드"}
    """
    logger.info("topic_selection_gate.waiting", run_id=state.get("run_id"))

    trend_data = state.get("trend_data") or {}
    topic_summaries = trend_data.get("topic_summaries", [])

    selection_result = interrupt(
        {
            "type": "topic_selection",
            "topics": topic_summaries,
            "message": "트렌드 결과를 확인하고 하나의 주제를 선택해주세요.",
        }
    )

    selected_topic = selection_result.get("selected_topic", "")

    logger.info("topic_selection_gate.result", selected_topic=selected_topic)

    # Update trend_data with selected topic
    updated_trend_data = {**trend_data, "selected_topic": selected_topic}

    return {
        "trend_data": updated_trend_data,
        "topic_selected": selected_topic,
        "topic_selection_approved": True,
    }
