"""Audio Choice Gate — pauses pipeline for TTS vs manual recording selection."""

from __future__ import annotations

import structlog
from langgraph.types import interrupt

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()


async def audio_choice_gate(state: PipelineState) -> dict:
    """Interrupt the pipeline and wait for audio source selection.

    The user can choose:
    - TTS mode: pipeline generates voice audio via ElevenLabs
    - Manual mode: user provides pre-recorded audio files

    On resume, the Command(resume=...) payload provides:
      {"audio_source": "tts"}
    or
      {"audio_source": "manual", "audio_files": {"scene_id": "/path/to/file.mp3", ...}}
    """
    logger.info("audio_choice_gate.waiting", run_id=state.get("run_id"))

    script_data = state.get("script_data") or {}
    scenes = script_data.get("scenes", [])
    script_file_path = state.get("script_file_path")

    # Build scene list for user reference
    scene_list = [
        {
            "scene_id": s["scene_id"],
            "speaker": s.get("speaker", "host"),
            "text": s["text"],
        }
        for s in scenes
    ]

    choice_result = interrupt(
        {
            "type": "audio_choice",
            "message": "오디오 소스를 선택해주세요: TTS(자동 음성 생성) 또는 수동 녹음",
            "script_file_path": script_file_path,
            "scenes": scene_list,
        }
    )

    audio_source = choice_result.get("audio_source", "tts")
    audio_files = choice_result.get("audio_files")

    logger.info(
        "audio_choice_gate.result",
        audio_source=audio_source,
        has_audio_files=audio_files is not None,
    )

    return {
        "audio_source": audio_source,
        "audio_choice_approved": True,
        "audio_files": audio_files,
    }
