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
    size: str = "1024x1792",
) -> str:
    """Generate an image using DALL-E 3 and download it to a local file.

    Args:
        prompt: Text prompt for image generation.
        output_path: File path to save the PNG image.
        size: Image dimensions (default vertical 9:16 ratio).

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If no image URL is returned or download fails.
    """
    logger.info(
        "dalle_generate.start",
        prompt_len=len(prompt),
        size=size,
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
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
