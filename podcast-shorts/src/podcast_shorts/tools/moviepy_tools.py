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
    _BOTTOM_TAGLINE = "바로지금, 지금알아야할소식"

    if trend_summary:
        # Body scene layout (top-to-bottom):
        #   ┌─────────────────────────┐
        #   │  top banner (trend text)│  dark gray + dark yellow text
        #   ├─────────────────────────┤
        #   │     image  (center)     │
        #   ├─────────────────────────┤
        #   │  bottom banner (tagline)│  dark gray + white text
        #   └─────────────────────────┘
        top_h = max(120, height // 8)    # top banner height
        bot_h = max(90, height // 10)    # bottom banner height
        image_height = height - top_h - bot_h

        # Dark gray full-frame base
        full_bg = ColorClip(size=(width, height), color=(35, 35, 35)).with_duration(scene_duration)

        # Image/video fit into center zone (preserve aspect ratio, no crop, dark gray fills gaps)
        if video_path:
            raw = VideoFileClip(video_path)
            if raw.duration < scene_duration:
                loops_needed = int(scene_duration / raw.duration) + 1
                raw = concatenate_videoclips([raw] * loops_needed)
            raw = raw.subclipped(0, scene_duration)
            vw, vh = raw.size
            scale = min(width / vw, image_height / vh)
            nw, nh = int(vw * scale), int(vh * scale)
            x_off = (width - nw) // 2
            y_off = top_h + (image_height - nh) // 2
            raw = raw.resized((nw, nh)).with_position((x_off, y_off))
        else:
            _img = ImageClip(image_path)
            iw, ih = _img.size
            scale = min(width / iw, image_height / ih)
            nw, nh = int(iw * scale), int(ih * scale)
            x_off = (width - nw) // 2
            y_off = top_h + (image_height - nh) // 2
            raw = (
                _img.resized((nw, nh))
                .with_duration(scene_duration)
                .with_position((x_off, y_off))
            )

        # Top banner — trend summary in dark yellow
        # Dynamic font size: shrink so full text fits within 2 lines.
        # Korean full-width chars ≈ font_size px each; 2 lines = 2*(avail_w/font_size) chars.
        _avail_banner_w = width - 80
        _text_chars = max(len(trend_summary), 1)
        _max_for_2_lines = int(2 * _avail_banner_w / _text_chars)
        top_font_size = max(16, min(_max_for_2_lines, top_h // 3))
        trend_clip = (
            TextClip(
                text=trend_summary,
                font=_KOREAN_FONT_BOLD,
                font_size=top_font_size,
                color=(210, 180, 40),  # dark yellow
                method="caption",
                size=(_avail_banner_w, top_h - 12),
                text_align="center",
            )
            .with_position(((width - _avail_banner_w) // 2, 6))
            .with_duration(scene_duration)
        )

        # Bottom banner — fixed tagline in white
        bot_font_size = max(18, bot_h // 5)
        tagline_clip = (
            TextClip(
                text=_BOTTOM_TAGLINE,
                font=_KOREAN_FONT_BOLD,
                font_size=bot_font_size,
                color=(255, 255, 255),  # white
                method="caption",
                size=(_avail_banner_w, bot_h - 12),
                text_align="center",
            )
            .with_position(((width - _avail_banner_w) // 2, height - bot_h + 6))
            .with_duration(scene_duration)
        )

        base_layers: list = [full_bg, raw, trend_clip, tagline_clip]
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
    # For body scenes (with bottom banner), push captions above the bottom banner
    _bot_h = max(90, height // 10) if trend_summary else 0
    caption_margin_bottom = max(220, _bot_h + 60)  # always above bottom banner

    for sub in captions:
        # Convert caption times to scene-local offsets
        sub_start = sub.start.ordinal / 1000.0 - scene_start
        sub_end = sub.end.ordinal / 1000.0 - scene_start
        # Clamp to scene boundaries
        sub_start = max(0.0, sub_start)
        sub_end = min(scene_duration, sub_end)
        if sub_end <= sub_start:
            continue

        # Dynamic caption font size: shrink for long subtitles so nothing is cut off.
        # Korean chars ≈ font_size px wide; cap at 2 lines within caption box.
        _cap_avail_w = width - 160  # generous side padding to prevent edge cut-off
        _cap_chars = max(len(sub.text), 1)
        _cap_max_font = int(2 * _cap_avail_w / _cap_chars)
        _cap_font_size = max(22, min(_cap_max_font, 44))

        txt = (
            TextClip(
                text=sub.text,
                font=_KOREAN_FONT_BOLD,
                font_size=_cap_font_size,
                color="white",
                stroke_color="black",
                stroke_width=max(2, _cap_font_size // 15),
                method="caption",
                size=(_cap_avail_w, None),
                text_align="center",
            )
            .with_position(((width - _cap_avail_w) // 2, height - caption_margin_bottom))
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
