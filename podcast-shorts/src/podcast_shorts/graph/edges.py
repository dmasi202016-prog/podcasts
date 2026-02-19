"""Conditional edge routing functions for the pipeline graph."""

from __future__ import annotations

from typing import Literal

from podcast_shorts.config import settings
from podcast_shorts.graph.state import PipelineState

END = "__end__"


def _should_retry(state: PipelineState, node_name: str) -> bool:
    """Check if a node should retry based on quality and retry count."""
    quality = state.get("quality")
    if quality is None or quality["passed"]:
        return False
    retry_counts = state.get("retry_counts", {})
    return retry_counts.get(node_name, 0) < settings.max_retries


def route_after_trend(state: PipelineState) -> Literal["trend_researcher", "topic_selection_gate", "__end__"]:
    """Route after trend_researcher: retry, proceed to topic selection, or fail."""
    quality = state.get("quality")
    if quality is None or quality["passed"]:
        return "topic_selection_gate"
    if _should_retry(state, "trend_researcher"):
        return "trend_researcher"
    return END


def route_after_script(
    state: PipelineState,
) -> Literal["scriptwriter", "human_review_gate", "__end__"]:
    """Route after scriptwriter: retry, proceed to human review, or fail."""
    quality = state.get("quality")
    if quality is None or quality["passed"]:
        return "human_review_gate"
    if _should_retry(state, "scriptwriter"):
        return "scriptwriter"
    return END


def route_after_review(
    state: PipelineState,
) -> Literal["scriptwriter", "audio_choice_gate"]:
    """Route after human review: approved → audio_choice_gate, rejected → scriptwriter with feedback."""
    if state.get("human_approved"):
        return "audio_choice_gate"
    return "scriptwriter"


def route_after_media(
    state: PipelineState,
) -> Literal["media_producer", "hook_prompt_gate", "__end__"]:
    """Route after media_producer: retry, proceed to hook prompt gate, or fail."""
    quality = state.get("quality")
    if quality is None or quality["passed"]:
        return "hook_prompt_gate"
    if _should_retry(state, "media_producer"):
        return "media_producer"
    return END


def route_after_editor(state: PipelineState) -> Literal["auto_editor", "upload_results"]:
    """Route after auto_editor: retry or proceed to upload."""
    quality = state.get("quality")
    if quality is None or quality["passed"]:
        return "upload_results"
    if _should_retry(state, "auto_editor"):
        return "auto_editor"
    return "upload_results"
