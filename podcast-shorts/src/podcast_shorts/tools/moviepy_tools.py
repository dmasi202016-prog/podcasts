"""MoviePy composition — scene clip assembly and final video rendering."""

from __future__ import annotations

from pathlib import Path

import pysrt
import structlog
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import MultiplyVolume

logger = structlog.get_logger()

# Korean bold font (extracted ExtraBold from AppleSDGothicNeo.ttc)
from podcast_shorts.config import get_assets_dir

_ASSETS_DIR = get_assets_dir()
_KOREAN_FONT_BOLD = str(_ASSETS_DIR / "fonts" / "AppleSDGothicNeo-ExtraBold.ttf")


def compose_scene_clip(
    audio_path: str,
    image_path: str,
    captions: list[pysrt.SubRipItem],
    scene_start: float,
    video_path: str | None = None,
    width: int = 1080,
    height: int = 1920,
) -> VideoClip:
    """Build a single scene clip with captions and audio.

    Two modes:
    - *video_path* provided: Luma video as full background (no image overlay).
    - *video_path* is None: DALL-E image as static full-screen background.

    *captions* should already be filtered to this scene's time window.
    *scene_start* is the absolute start time of this scene in the full timeline
    (used to offset caption timestamps).

    Returns a ``CompositeVideoClip`` whose duration matches the narration audio.
    """
    # --- Audio (determines scene duration) ---
    audio = AudioFileClip(audio_path)
    scene_duration = audio.duration

    # --- Background layer ---
    if video_path:
        bg = VideoFileClip(video_path)
        if bg.duration < scene_duration:
            loops_needed = int(scene_duration / bg.duration) + 1
            bg = concatenate_videoclips([bg] * loops_needed)
        bg = bg.subclipped(0, scene_duration).resized((width, height))
    else:
        bg = (
            ImageClip(image_path)
            .resized((width, height))
            .with_duration(scene_duration)
        )

    # --- Caption TextClips (bold, bottom-center aligned) ---
    caption_clips = []
    caption_margin_bottom = 120  # pixels from bottom edge

    for sub in captions:
        # Convert caption times to scene-local offsets
        sub_start = sub.start.ordinal / 1000.0 - scene_start
        sub_end = sub.end.ordinal / 1000.0 - scene_start
        # Clamp to scene boundaries
        sub_start = max(0.0, sub_start)
        sub_end = min(scene_duration, sub_end)
        if sub_end <= sub_start:
            continue

        txt = (
            TextClip(
                text=sub.text,
                font=_KOREAN_FONT_BOLD,
                font_size=54,
                color="white",
                stroke_color="black",
                stroke_width=4,
                method="caption",
                size=(width - 80, None),
                text_align="center",
            )
            .with_position(("center", height - caption_margin_bottom))
            .with_start(sub_start)
            .with_duration(sub_end - sub_start)
        )
        caption_clips.append(txt)

    # --- Extend last caption to scene end (prevent subtitle disappearing early) ---
    if caption_clips:
        last = caption_clips[-1]
        last_end = last.start + last.duration
        if scene_duration - last_end < 1.0:  # within 1 second of scene end
            caption_clips[-1] = last.with_duration(scene_duration - last.start)

    # --- Composite ---
    clip = CompositeVideoClip(
        [bg, *caption_clips],
        size=(width, height),
    ).with_audio(audio).with_duration(scene_duration)

    logger.info(
        "compose_scene_clip.done",
        audio_path=audio_path,
        duration=scene_duration,
        num_captions=len(caption_clips),
        has_video=bool(video_path),
    )
    return clip


def render_final_video(
    scene_clips: list[VideoClip],
    output_path: str,
    bgm_path: str | None = None,
    fps: int = 30,
    audio_codec: str = "aac",
) -> str:
    """Concatenate scene clips, optionally mix BGM, and render to *output_path*.

    Returns *output_path* on success.
    """
    final = concatenate_videoclips(scene_clips, method="compose")

    # --- BGM mixing (if provided) ---
    if bgm_path:
        bgm = AudioFileClip(bgm_path)
        if bgm.duration < final.duration:
            loops_needed = int(final.duration / bgm.duration) + 1
            from moviepy import concatenate_audioclips

            bgm = concatenate_audioclips([bgm] * loops_needed)
        bgm = bgm.subclipped(0, final.duration).with_effects(
            [MultiplyVolume(0.15)]
        )
        narration = final.audio
        mixed = CompositeAudioClip([narration, bgm])
        final = final.with_audio(mixed)

    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec=audio_codec,
        preset="medium",
        logger=None,
    )

    logger.info(
        "render_final_video.done",
        output_path=output_path,
        duration=final.duration,
    )

    # Clean up
    final.close()
    for clip in scene_clips:
        clip.close()

    return output_path
