"""Human Review Gate — pauses pipeline for script approval before expensive media generation."""

from __future__ import annotations

import structlog
from langgraph.types import interrupt

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()


async def human_review_gate(state: PipelineState) -> dict:
    """Interrupt the pipeline and wait for human approval of the script.

    The user can approve or reject (with feedback) via the API.
    On resume, the Command(resume=...) payload provides approval status.
    """
    logger.info("human_review_gate.waiting", run_id=state.get("run_id"))

    script_data = state.get("script_data")
    script_file_path = state.get("script_file_path")

    # Interrupt execution and present the script for review.
    # The resume value is expected to be:
    #   {"approved": True} or {"approved": False, "feedback": "..."}
    review_result = interrupt(
        {
            "type": "script_review",
            "script_data": script_data,
            "script_file_path": script_file_path,
            "message": "대본을 검토해주세요. 승인하거나 수정 피드백을 제공해주세요.",
        }
    )

    approved = review_result.get("approved", False)
    feedback = review_result.get("feedback")

    logger.info("human_review_gate.result", approved=approved, has_feedback=bool(feedback))

    return {
        "human_approved": approved,
        "human_feedback": feedback,
    }
