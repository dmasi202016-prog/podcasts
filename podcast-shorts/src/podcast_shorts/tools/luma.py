"""Luma Dream Machine video generation — async helper function."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import structlog
from lumaai import AsyncLumaAI

from podcast_shorts.config import settings

logger = structlog.get_logger()

_POLL_INTERVAL_SEC = 5
_POLL_TIMEOUT_SEC = 300


async def luma_video_generate(
    prompt: str,
    output_path: str = "/tmp/output.mp4",
    duration: str = "5s",
) -> str:
    """Generate a short video clip using Luma Dream Machine.

    Args:
        prompt: Text prompt for video generation.
        output_path: File path to save the MP4 video.
        duration: Video duration string ("5s" or "9s").

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If generation fails or times out.
    """
    logger.info(
        "luma_video_generate.start",
        prompt_len=len(prompt),
        duration=duration,
    )

    client = AsyncLumaAI(auth_token=settings.luma_api_key)

    generation = await client.generations.create(
        prompt=prompt,
        model="ray-2",
        aspect_ratio="9:16",
        resolution="1080p",
        duration=duration,
    )

    generation_id = generation.id
    elapsed = 0

    while elapsed < _POLL_TIMEOUT_SEC:
        generation = await client.generations.get(id=generation_id)

        if generation.state == "completed":
            break
        if generation.state == "failed":
            raise RuntimeError(
                f"Luma generation failed: {generation.failure_reason}"
            )

        await asyncio.sleep(_POLL_INTERVAL_SEC)
        elapsed += _POLL_INTERVAL_SEC
    else:
        raise RuntimeError(
            f"Luma generation timed out after {_POLL_TIMEOUT_SEC}s "
            f"(id={generation_id})"
        )

    video_url = generation.assets.video
    if not video_url:
        raise RuntimeError(
            f"Luma generation completed but no video URL (id={generation_id})"
        )

    async with httpx.AsyncClient(timeout=60) as http:
        dl_resp = await http.get(video_url)
        dl_resp.raise_for_status()

    Path(output_path).write_bytes(dl_resp.content)

    logger.info(
        "luma_video_generate.done",
        output_path=output_path,
        bytes_written=len(dl_resp.content),
    )
    return output_path
