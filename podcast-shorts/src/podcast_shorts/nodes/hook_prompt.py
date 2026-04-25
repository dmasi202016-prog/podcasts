"""Hook Prompt — auto-approves the LLM-generated hook prompt without user interaction."""

from __future__ import annotations

import structlog

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()


async def hook_prompt_gate(state: PipelineState) -> dict:
    """Auto-approve the hook video/image prompt. The pipeline no longer pauses here —
    the LLM-generated prompt is used as-is."""
    hook_video_prompt = state.get("hook_video_prompt", "")
    logger.info(
        "hook_prompt.auto_approved",
        run_id=state.get("run_id"),
        has_prompt=bool(hook_video_prompt),
    )
    return {
        "hook_video_prompt": hook_video_prompt,
        "hook_prompt_approved": True,
    }
