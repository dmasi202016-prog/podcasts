"""MoviePy composition — scene clip assembly and final video rendering."""

from __future__ import annotations

from pathlib import Path

import pysrt
import structlog
from moviepy import (
    AudioFileClip,
    ColorClip,
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
    trend_summary: str | None = None,
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
    if trend_summary:
        # Body scene: image occupies lower 4:5 area; top band shows trend summary.
        image_height = int(width * 5 / 4)
        banner_height = height - image_height  # pixels reserved at top for banner

        # Dark gray full-frame background
        full_bg = ColorClip(size=(width, height), color=(35, 35, 35)).with_duration(scene_duration)

        # Image/video scaled to 4:5 area, positioned below the banner
        if video_path:
            raw = VideoFileClip(video_path)
            if raw.duration < scene_duration:
                loops_needed = int(scene_duration / raw.duration) + 1
                raw = concatenate_videoclips([raw] * loops_needed)
            raw = raw.subclipped(0, scene_duration).resized((width, image_height)).with_position((0, banner_height))
        else:
            raw = (
                ImageClip(image_path)
                .resized((width, image_height))
                .with_duration(scene_duration)
                .with_position((0, banner_height))
            )

        # Trend summary text — dark yellow on dark gray banner
        banner_font_size = max(22, banner_height // 7)
        trend_clip = (
            TextClip(
                text=trend_summary,
                font=_KOREAN_FONT_BOLD,
                font_size=banner_font_size,
                color=(210, 180, 40),   # dark-ish yellow
                method="caption",
                size=(width - 60, banner_height - 20),
                text_align="center",
            )
            .with_position(("center", 10))
            .with_duration(scene_duration)
        )

        base_layers: list = [full_bg, raw, trend_clip]
    else:
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
        base_layers = [bg]

    # --- Caption TextClips (bold, bottom-center aligned) ---
    caption_clips = []
    caption_margin_bottom = 220  # pixels from bottom edge — moved up to prevent clipping

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
                font_size=44,
                color="white",
                stroke_color="black",
                stroke_width=3,
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
        [*base_layers, *caption_clips],
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
    fps: int = 24,
    audio_codec: str = "aac",
) -> str:
    """Concatenate scene clips, optionally mix BGM, and render to *output_path*.

    Returns *output_path* on success.
    """
    final = concatenate_videoclips(scene_clips, method="chain")

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
        preset="ultrafast",
        threads=2,
        logger=None,
    )

    logger.info(
        "render_final_video.done",
        output_path=output_path,
        duration=final.duration,
    )

    # Clean up MoviePy objects before ffmpeg post-processing
    final.close()
    for clip in scene_clips:
        clip.close()

    # --- CRT TV static overlay (post-process via ffmpeg) ---
    import os as _os
    import subprocess as _sp

    _crt_tmp = output_path.replace(".mp4", "_precrt.mp4")
    _os.rename(output_path, _crt_tmp)
    try:
        _result = _sp.run(
            [
                "ffmpeg", "-y",
                "-i", _crt_tmp,
                "-vf", "noise=alls=8:allf=t+u",  # analog static noise
                "-c:a", "copy",
                "-preset", "ultrafast",
                output_path,
            ],
            capture_output=True,
            timeout=300,
        )
        if _result.returncode == 0:
            _os.remove(_crt_tmp)
            logger.info("render_final_video.crt_applied")
        else:
            _os.rename(_crt_tmp, output_path)  # restore on failure
            logger.warning("render_final_video.crt_failed", stderr=_result.stderr.decode()[-300:])
    except Exception:
        logger.exception("render_final_video.crt_error")
        if _os.path.isfile(_crt_tmp):
            _os.rename(_crt_tmp, output_path)

    return output_path
