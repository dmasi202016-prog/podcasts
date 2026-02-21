"""DALL-E 3 image generation — async helper function."""

from __future__ import annotations

from pathlib import Path

import httpx
import structlog
from openai import AsyncOpenAI

from podcast_shorts.config import settings

logger = structlog.get_logger()


async def dalle_generate(
    prompt: str,
    output_path: str = "/tmp/output.png",
    scene_type: str = "default",
) -> str:
    """Generate an image using DALL-E 3 and download it to a local file.

    Args:
        prompt: Text prompt for image generation.
        output_path: File path to save the PNG image.
        scene_type: "body" → 1024x1024 (fits 4:5 banner area),
                    others → 1024x1792 (9:16 portrait).

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If no image URL is returned or download fails.
    """
    # DALL-E 3 supported sizes: 1024x1024 | 1024x1792 | 1792x1024
    size = "1024x1024" if scene_type == "body" else "1024x1792"

    logger.info(
        "dalle_generate.start",
        prompt_len=len(prompt),
        size=size,
        scene_type=scene_type,
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Standard prefixes: no text, cat for people, portrait orientation
    full_prompt = (
        "No text, no letters, no words, no typography visible in the image. "
        "If any human or person must appear, replace with a cute cartoon cat character. "
        f"Portrait orientation, vertical format, do not generate landscape. {prompt}"
    )

    response = await client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size=size,
        quality="hd",
        style="vivid",
        n=1,
        response_format="url",
    )

    image_url = response.data[0].url
    if not image_url:
        raise RuntimeError("DALL-E 3 returned no image URL")

    async with httpx.AsyncClient(timeout=60) as http:
        dl_resp = await http.get(image_url)
        dl_resp.raise_for_status()

    Path(output_path).write_bytes(dl_resp.content)

    logger.info(
        "dalle_generate.done",
        output_path=output_path,
        bytes_written=len(dl_resp.content),
    )
    return output_path
