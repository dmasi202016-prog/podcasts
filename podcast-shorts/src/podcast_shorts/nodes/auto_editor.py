"""Auto Editor node — composites audio, video, images, captions into final short."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import pysrt
import structlog

from podcast_shorts.config import get_assets_dir, settings
from podcast_shorts.graph.state import (
    AudioSegment,
    EditorOutput,
    PipelineState,
    QualityAssessment,
    VideoMetadata,
)
from podcast_shorts.tools.elevenlabs import elevenlabs_tts
from podcast_shorts.tools.luma import luma_video_generate
from podcast_shorts.tools.moviepy_tools import compose_scene_clip, render_final_video

# Channel intro assets
_ASSETS_DIR = get_assets_dir()
_CHANNEL_AD_IMAGE = str(_ASSETS_DIR / "channel_ad.png")
_CHANNEL_INTRO_TEXT = "바로지금! 지금 알아야할 소식과 함께합니다."

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_text(text: str, max_chars: int = 22) -> list[str]:
    """Split text into caption chunks of at most max_chars characters.

    Tries to break at natural Korean/punctuation boundaries.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        # Try to split at punctuation or space near the limit
        split_at = max_chars
        for punct in [" ", ",", ".", "?", "!", "。", "，", "？", "！", "~"]:
            pos = text.rfind(punct, max_chars // 2, max_chars + 1)
            if pos > 0:
                split_at = pos + 1
                break
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()

    return [c for c in chunks if c]


def _generate_captions_from_script(
    scenes: list,
    audio_segments: list[AudioSegment],
    srt_path: str,
    max_chars: int = 22,
) -> list[list[pysrt.SubRipItem]]:
    """Generate SRT captions directly from script text + audio segment timing.

    Each scene's text is split into short chunks and distributed evenly
    across its audio duration. Returns per-scene caption buckets.
    Writes the full SRT file to *srt_path*.
    """
    scene_text_map = {s["scene_id"]: s.get("text", "") for s in scenes}

    all_subs: list[pysrt.SubRipItem] = []
    scene_buckets: list[list[pysrt.SubRipItem]] = []
    sub_index = 1
    cursor = 0.0  # absolute timeline position in seconds

    for seg in audio_segments:
        scene_id = seg["scene_id"]
        duration = seg["duration"]
        text = scene_text_map.get(scene_id, "")
        chunks = _split_text(text, max_chars)

        scene_subs: list[pysrt.SubRipItem] = []
        if chunks:
            chunk_dur = duration / len(chunks)
            for j, chunk in enumerate(chunks):
                start_ms = int((cursor + j * chunk_dur) * 1000)
                end_ms = int((cursor + (j + 1) * chunk_dur) * 1000)
                sub = pysrt.SubRipItem(
                    index=sub_index,
                    start=pysrt.SubRipTime.from_ordinal(start_ms),
                    end=pysrt.SubRipTime.from_ordinal(end_ms),
                    text=chunk,
                )
                scene_subs.append(sub)
                all_subs.append(sub)
                sub_index += 1

        scene_buckets.append(scene_subs)
        cursor += duration

    srt_file = pysrt.SubRipFile(items=all_subs)
    srt_file.save(srt_path, encoding="utf-8")

    logger.info(
        "captions_from_script.done",
        srt_path=srt_path,
        total_subs=len(all_subs),
        scenes=len(audio_segments),
    )
    return scene_buckets


def _generate_metadata(
    script_data: dict,
    trend_data: dict,
) -> VideoMetadata:
    """Build a ``VideoMetadata`` dict from pipeline state data."""
    topic = trend_data.get("selected_topic", "")
    return {
        "title": script_data.get("title", f"{topic} 팟캐스트 쇼츠"),
        "description": f"{topic}에 대한 팟캐스트 쇼츠입니다.",
        "tags": trend_data.get("keywords", []),
        "category": trend_data.get("category", ""),
    }


def _assess_quality(
    final_video: str,
    srt_path: str,
    thumbnail: str,
    duration: float,
) -> QualityAssessment:
    """File-existence / size / duration checks → quality score."""
    total_checks = 4
    passed_checks = 0

    # 1. Final video exists and has content
    if os.path.isfile(final_video) and os.path.getsize(final_video) > 0:
        passed_checks += 1

    # 2. SRT exists
    if os.path.isfile(srt_path) and os.path.getsize(srt_path) > 0:
        passed_checks += 1

    # 3. Thumbnail exists
    if os.path.isfile(thumbnail) and os.path.getsize(thumbnail) > 0:
        passed_checks += 1

    # 4. Duration within acceptable range (30–200 seconds)
    if 30.0 <= duration <= 200.0:
        passed_checks += 1

    score = passed_checks / total_checks
    passed = score >= settings.quality_threshold

    feedback_parts = []
    if passed:
        feedback_parts.append(
            f"Video rendered successfully: {passed_checks}/{total_checks} checks passed."
        )
    else:
        feedback_parts.append(
            f"Video rendering incomplete: {passed_checks}/{total_checks} checks passed."
        )
        if not (os.path.isfile(final_video) and os.path.getsize(final_video) > 0):
            feedback_parts.append("Final video file missing or empty.")
        if not (30.0 <= duration <= 200.0):
            feedback_parts.append(f"Duration {duration:.1f}s outside 30–200s range.")

    return {
        "node_name": "auto_editor",
        "passed": passed,
        "score": round(score, 3),
        "feedback": " ".join(feedback_parts),
        "attempt": 0,  # caller sets this
    }


# ---------------------------------------------------------------------------
# Node implementation
# ---------------------------------------------------------------------------


async def auto_editor(state: PipelineState) -> dict:
    """Compose the final video: Whisper captioning → MoviePy timeline assembly
    (images/video + audio + captions + BGM) → render (1080×1920, 9:16)
    → metadata generation.
    """
    logger.info("auto_editor.start", run_id=state.get("run_id"))

    retry_counts = state.get("retry_counts", {})
    attempt = retry_counts.get("auto_editor", 0) + 1
    script_data = state.get("script_data") or {}
    trend_data = state.get("trend_data") or {}
    media_assets = state.get("media_assets") or {}
    run_id = state.get("run_id", "unknown")

    try:
        audio_segments: list[AudioSegment] = media_assets.get("audio_segments", [])
        full_audio = media_assets.get("audio_path", "")
        images = media_assets.get("images", [])
        video_clips = media_assets.get("video_clips", [])

        if not audio_segments or not full_audio:
            raise RuntimeError("No audio assets available from media_producer")

        # ── Output directories ───────────────────────────────────────
        output_dir = Path(settings.output_base_dir) / run_id / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        final_video_path = str(output_dir / f"{run_id}_final.mp4")
        srt_path = str(output_dir / f"{run_id}_captions.srt")
        thumbnail_path = str(output_dir / f"{run_id}_thumbnail.png")

        # ── Step 1: Generate SRT captions from script text + audio timing ──
        # Run in thread to keep the event loop responsive (file I/O + pysrt).
        scenes = (state.get("script_data") or {}).get("scenes", [])
        scene_captions = await asyncio.to_thread(
            _generate_captions_from_script, scenes, audio_segments, srt_path
        )

        # ── Step 3: Generate channel intro TTS ─────────────────────
        intro_audio_path = str(output_dir / "channel_intro.mp3")
        audio_source = state.get("audio_source", "tts")
        voice_ids = (media_assets.get("voice_ids") or {})
        host_voice_id = voice_ids.get("host", "")
        if audio_source == "tts" and host_voice_id:
            await elevenlabs_tts(
                text=_CHANNEL_INTRO_TEXT,
                voice_id=host_voice_id,
                emotion="friendly",
                output_path=intro_audio_path,
            )
        logger.info("auto_editor.channel_intro_tts_done", audio_source=audio_source)

        # ── Step 3.5: Generate hook video from approved prompt ─────────
        hook_video_prompt = state.get("hook_video_prompt")
        hook_mode = state.get("hook_mode", "video")
        hook_video_path: str | None = None
        if hook_video_prompt and hook_mode == "video":
            run_output_dir = Path(settings.output_base_dir) / run_id
            hook_vid_dir = run_output_dir / "video"
            hook_vid_dir.mkdir(parents=True, exist_ok=True)
            hook_video_path = str(hook_vid_dir / "hook.mp4")
            # Determine duration from hook audio segment
            hook_seg = next((s for s in audio_segments if s["scene_id"] == "hook"), None)
            hook_duration = hook_seg["duration"] if hook_seg else 5.0
            luma_duration = "9s" if hook_duration > 7.0 else "5s"
            try:
                await luma_video_generate(
                    prompt=hook_video_prompt,
                    output_path=hook_video_path,
                    duration=luma_duration,
                )
                logger.info("auto_editor.hook_video_generated", path=hook_video_path)
            except Exception:
                logger.exception("auto_editor.hook_video_failed")
                hook_video_path = None

        # ── Step 4: Build per-scene VideoClips ───────────────────────
        resolution = state.get("video_resolution", "720x1280")
        try:
            width, height = (int(x) for x in resolution.split("x"))
        except (ValueError, AttributeError):
            width, height = 720, 1280

        # One-line trend summary shown in the dark banner above body-scene images
        # Prefer LLM-generated curiosity-inducing banner text from scriptwriter
        trend_summary_text = (
            (state.get("script_data") or {}).get("trend_banner_text")
            or (lambda t: (t[:55] + "…") if len(t) > 55 else t)(
                trend_data.get("selected_topic") or state.get("topic_selected", "")
            )
        )

        clips = []
        # srt_cursor: position in Whisper SRT timeline (full_audio, no intro)
        # video_cursor: position in final video timeline (includes intro)
        srt_cursor = 0.0

        for i, seg in enumerate(audio_segments):
            scene_id = seg["scene_id"]
            audio_path = seg["audio_path"]

            # Find matching image (required for all scenes)
            img_path = next(
                (im["image_path"] for im in images if im["scene_id"] == scene_id),
                images[0]["image_path"] if images else "",
            )
            # Find matching video (hook uses Luma-generated video; others are empty)
            vid_path = None
            if scene_id == "hook" and hook_video_path:
                vid_path = hook_video_path
            else:
                vid_path = next(
                    (vc["video_path"] for vc in video_clips if vc["scene_id"] == scene_id and vc["video_path"]),
                    None,
                )

            if not img_path:
                logger.warning("auto_editor.missing_image", scene_id=scene_id)
                continue

            # Body scenes get the dark trend-summary banner at top (4:5 image area)
            is_body = scene_id.startswith("body_")

            # Pass srt_cursor so captions align with Whisper SRT timestamps.
            # to_thread keeps the event loop free for /status polling.
            clip = await asyncio.to_thread(
                compose_scene_clip,
                audio_path=audio_path,
                image_path=img_path,
                captions=scene_captions[i] if i < len(scene_captions) else [],
                scene_start=srt_cursor,
                video_path=vid_path,
                width=width,
                height=height,
                trend_summary=trend_summary_text if is_body else None,
            )
            clips.append(clip)
            srt_cursor += seg["duration"]

            # Insert channel intro clip right after the hook scene
            # (intro is NOT in full_audio/SRT, so only video_cursor advances)
            if scene_id == "hook" and os.path.isfile(intro_audio_path):
                from moviepy import AudioFileClip as _AFC

                def _measure_intro_duration(path: str) -> float:
                    _a = _AFC(path)
                    d = _a.duration
                    _a.close()
                    return d

                intro_duration = await asyncio.to_thread(
                    _measure_intro_duration, intro_audio_path
                )

                intro_clip = await asyncio.to_thread(
                    compose_scene_clip,
                    audio_path=intro_audio_path,
                    image_path=_CHANNEL_AD_IMAGE,
                    captions=[],
                    scene_start=0.0,  # no SRT captions for intro
                    video_path=None,
                    width=width,
                    height=height,
                )
                clips.append(intro_clip)
                logger.info("auto_editor.channel_intro_inserted", intro_duration=intro_duration)

        if not clips:
            raise RuntimeError("No scene clips could be assembled")

        # ── Step 4: Final render ─────────────────────────────────────
        # Heavy: write_videofile + ffmpeg subprocess (timeout=300s). Must run
        # off the event loop or /status polling will hang for the entire render.
        bgm_path = state.get("user_preferences", {}).get("bgm_path")
        await asyncio.to_thread(
            render_final_video,
            scene_clips=clips,
            output_path=final_video_path,
            bgm_path=bgm_path,
            fps=settings.video_fps,
        )

        # ── Step 5: Thumbnail (copy first scene image) ───────────────
        if images:
            await asyncio.to_thread(shutil.copy2, images[0]["image_path"], thumbnail_path)

        # ── Step 6: Metadata ─────────────────────────────────────────
        metadata = _generate_metadata(script_data, trend_data)

        # Measure actual duration from rendered file
        from moviepy import VideoFileClip as _VFC

        def _measure_video_duration(path: str) -> float:
            r = _VFC(path)
            d = r.duration
            r.close()
            return d

        duration_sec = await asyncio.to_thread(_measure_video_duration, final_video_path)

        # ── Step 7: Quality assessment ───────────────────────────────
        quality = _assess_quality(final_video_path, srt_path, thumbnail_path, duration_sec)
        quality["attempt"] = attempt

        editor_output: EditorOutput = {
            "final_video_path": final_video_path,
            "caption_srt_path": srt_path,
            "thumbnail_path": thumbnail_path,
            "metadata": metadata,
            "duration_sec": duration_sec,
        }

        logger.info(
            "auto_editor.done",
            video_path=final_video_path,
            duration=duration_sec,
            quality_score=quality["score"],
            attempt=attempt,
        )

    except Exception:
        logger.exception("auto_editor.error", attempt=attempt)
        editor_output = {
            "final_video_path": "",
            "caption_srt_path": "",
            "thumbnail_path": "",
            "metadata": {"title": "", "description": "", "tags": [], "category": ""},
            "duration_sec": 0.0,
        }
        quality = {
            "node_name": "auto_editor",
            "passed": False,
            "score": 0.0,
            "feedback": "Auto-editing failed due to an error. Will retry.",
            "attempt": attempt,
        }

    retry_counts = {**retry_counts, "auto_editor": attempt}

    return {
        "editor_output": editor_output,
        "quality": quality,
        "retry_counts": retry_counts,
    }
