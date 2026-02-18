"""ElevenLabs voice cloning and TTS — async helper function."""

from __future__ import annotations

from pathlib import Path

import structlog
from elevenlabs import AsyncElevenLabs, VoiceSettings

from podcast_shorts.config import settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Emotion → VoiceSettings mapping
# ---------------------------------------------------------------------------

_EMOTION_SETTINGS: dict[str, VoiceSettings] = {
    "neutral": VoiceSettings(
        stability=0.50, similarity_boost=0.75, style=0.00, speed=1.20,
    ),
    "excited": VoiceSettings(
        stability=0.30, similarity_boost=0.80, style=0.60, speed=1.20,
    ),
    "curious": VoiceSettings(
        stability=0.45, similarity_boost=0.75, style=0.30, speed=1.20,
    ),
    "informative": VoiceSettings(
        stability=0.65, similarity_boost=0.80, style=0.10, speed=1.19,
    ),
    "thoughtful": VoiceSettings(
        stability=0.60, similarity_boost=0.70, style=0.20, speed=1.13,
    ),
    "enthusiastic": VoiceSettings(
        stability=0.30, similarity_boost=0.80, style=0.55, speed=1.20,
    ),
    "friendly": VoiceSettings(
        stability=0.45, similarity_boost=0.80, style=0.40, speed=1.20,
    ),
}


async def elevenlabs_tts(
    text: str,
    voice_id: str,
    emotion: str = "neutral",
    output_path: str = "/tmp/output.mp3",
) -> str:
    """Generate speech audio from text using ElevenLabs with emotion-aware tone.

    Args:
        text: The text to convert to speech.
        voice_id: ElevenLabs voice ID (cloned or preset).
        emotion: Emotion key for VoiceSettings lookup.
        output_path: File path to write the MP3 output.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If the API returns empty audio data.
    """
    voice_settings = _EMOTION_SETTINGS.get(emotion, _EMOTION_SETTINGS["neutral"])

    logger.info(
        "elevenlabs_tts.start",
        voice_id=voice_id,
        emotion=emotion,
        text_len=len(text),
    )

    client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)

    audio_iter = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=voice_settings,
    )

    chunks: list[bytes] = []
    async for chunk in audio_iter:
        chunks.append(chunk)

    audio_data = b"".join(chunks)
    if not audio_data:
        raise RuntimeError(
            f"ElevenLabs returned empty audio for voice_id={voice_id}"
        )

    Path(output_path).write_bytes(audio_data)

    logger.info(
        "elevenlabs_tts.done",
        output_path=output_path,
        bytes_written=len(audio_data),
    )
    return output_path
