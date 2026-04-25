"""Audio Choice — auto-selects TTS (ElevenLabs) without user interaction."""

from __future__ import annotations

import structlog

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()


async def audio_choice_gate(state: PipelineState) -> dict:
    """Auto-select TTS audio source. The pipeline no longer pauses here —
    the user only approves the script; audio is always AI-generated."""
    logger.info("audio_choice.auto_tts", run_id=state.get("run_id"))
    return {
        "audio_source": "tts",
        "audio_choice_approved": True,
        "audio_files": None,
    }
