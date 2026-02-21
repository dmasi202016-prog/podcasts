"""Ideogram AI image generation — async helper function."""

from __future__ import annotations

from pathlib import Path

import httpx
import structlog

from podcast_shorts.config import settings

logger = structlog.get_logger()

_IDEOGRAM_API_URL = "https://api.ideogram.ai/generate"

# scene_type → Ideogram aspect ratio enum
_ASPECT_MAP: dict[str, str] = {
    "body": "ASPECT_3_4",   # 3:4 portrait — fits center zone between top/bottom banners
    "hook": "ASPECT_9_16",
    "cta": "ASPECT_9_16",
    "default": "ASPECT_9_16",
}


async def ideogram_generate(
    prompt: str,
    output_path: str = "/tmp/output.png",
    scene_type: str = "default",
) -> str:
    """Generate an image using Ideogram V2 API.

    Args:
        prompt: Text prompt for image generation.
        output_path: File path to save the image.
        scene_type: "body" → ASPECT_4_5 (4:5), others → ASPECT_9_16 (9:16).

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If no image URL is returned.
    """
    aspect_ratio = _ASPECT_MAP.get(scene_type, "ASPECT_9_16")

    # Standard prefixes applied to every image
    prefix = (
        "ABSOLUTE RULE: zero text, zero letters, zero words, zero numbers, zero symbols, "
        "zero signs, zero labels, zero captions, zero watermarks, zero typography of any kind — "
        "not even a single character anywhere in the image. Pure visual only. "
        "Art style: colorful anime illustration, vibrant cel-shading, smooth clean lines. "
        "All human characters must be drawn in anime/animation style — no photorealistic people. "
        "Portrait orientation. "
    )
    # Ideogram API hard limit is 1500 characters
    max_prompt_len = 1500 - len(prefix)
    truncated_prompt = prompt[:max_prompt_len] if len(prompt) > max_prompt_len else prompt
    full_prompt = prefix + truncated_prompt

    logger.info(
        "ideogram_generate.start",
        prompt_len=len(full_prompt),
        prompt_preview=full_prompt[:200],
        aspect_ratio=aspect_ratio,
        scene_type=scene_type,
    )

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            _IDEOGRAM_API_URL,
            headers={
                "Api-Key": settings.ideao_api_key,
                "Content-Type": "application/json",
            },
            json={
                "image_request": {
                    "prompt": full_prompt,
                    "aspect_ratio": aspect_ratio,
                    "model": "V_2_TURBO",
                    "magic_prompt_option": "OFF",
                }
            },
        )
        if not resp.is_success:
            logger.error(
                "ideogram_generate.api_error",
                status_code=resp.status_code,
                response_body=resp.text[:500],
            )
            resp.raise_for_status()
        data = resp.json()

    image_url = data["data"][0]["url"]
    if not image_url:
        raise RuntimeError("Ideogram returned no image URL")

    async with httpx.AsyncClient(timeout=60) as http:
        dl_resp = await http.get(image_url)
        dl_resp.raise_for_status()

    Path(output_path).write_bytes(dl_resp.content)

    logger.info(
        "ideogram_generate.done",
        output_path=output_path,
        bytes_written=len(dl_resp.content),
    )
    return output_path
