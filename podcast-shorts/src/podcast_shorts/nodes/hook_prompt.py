"""Hook Prompt Gate — pauses pipeline for hook video prompt review before expensive Luma generation."""

from __future__ import annotations

import structlog
from langgraph.types import interrupt

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()


async def hook_prompt_gate(state: PipelineState) -> dict:
    """Interrupt the pipeline and present the LLM-generated hook video prompt for user review.

    The user can approve the prompt as-is or edit it before Luma video generation.
    On resume, the Command(resume=...) payload provides:
      {"prompt": "approved or edited prompt text"}
    """
    logger.info("hook_prompt_gate.waiting", run_id=state.get("run_id"))

    hook_video_prompt = state.get("hook_video_prompt", "")

    review_result = interrupt(
        {
            "type": "hook_prompt",
            "prompt": hook_video_prompt,
            "message": "Hook 영상 프롬프트를 검토해주세요. 수정하거나 그대로 승인할 수 있습니다.",
        }
    )

    final_prompt = review_result.get("prompt", hook_video_prompt)

    logger.info(
        "hook_prompt_gate.result",
        prompt_changed=final_prompt != hook_video_prompt,
    )

    return {
        "hook_video_prompt": final_prompt,
        "hook_prompt_approved": True,
    }
