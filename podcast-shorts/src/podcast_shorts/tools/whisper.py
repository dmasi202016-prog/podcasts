"""Whisper transcription — calls OpenAI Whisper API and produces an SRT file."""

from __future__ import annotations

import asyncio

import pysrt
import structlog
from openai import OpenAI

logger = structlog.get_logger()


async def whisper_transcribe(audio_path: str, output_srt_path: str) -> str:
    """Transcribe *audio_path* via Whisper-1 and write an SRT caption file.

    Uses ``response_format="verbose_json"`` with segment-level timestamps so
    each subtitle entry maps to a Whisper segment.

    Returns *output_srt_path* on success.
    """
    loop = asyncio.get_running_loop()

    client = OpenAI()  # picks up OPENAI_API_KEY from env

    def _call_whisper() -> dict:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        return response

    logger.info("whisper.transcribe.start", audio_path=audio_path)
    result = await loop.run_in_executor(None, _call_whisper)

    # Build SRT from segments
    srt_file = pysrt.SubRipFile()

    segments = result.segments or []
    for idx, seg in enumerate(segments, start=1):
        start_time = pysrt.SubRipTime.from_ordinal(int(seg.start * 1000))
        end_time = pysrt.SubRipTime.from_ordinal(int(seg.end * 1000))
        item = pysrt.SubRipItem(
            index=idx,
            start=start_time,
            end=end_time,
            text=seg.text.strip(),
        )
        srt_file.append(item)

    srt_file.save(output_srt_path, encoding="utf-8")
    logger.info(
        "whisper.transcribe.done",
        output_srt_path=output_srt_path,
        num_segments=len(segments),
    )
    return output_srt_path
