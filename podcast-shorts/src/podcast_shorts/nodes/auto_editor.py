"""Auto Editor node — composites audio, video, images, captions into final short."""

from __future__ import annotations

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
from podcast_shorts.tools.whisper import whisper_transcribe

# Channel intro assets
_ASSETS_DIR = get_assets_dir()
_CHANNEL_AD_IMAGE = str(_ASSETS_DIR / "channel_ad.png")
_CHANNEL_INTRO_TEXT = "바로지금! 지금 알아야할 소식과 함께합니다."

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _distribute_captions(
    srt_path: str,
    audio_segments: list[AudioSegment],
) -> list[list[pysrt.SubRipItem]]:
    """Split SRT captions into per-scene buckets based on audio segment timing.

    Returns a list (one entry per scene) of ``SubRipItem`` lists.
    """
    subs = pysrt.open(srt_path, encoding="utf-8")

    # Compute each scene's absolute time window
    scene_windows: list[tuple[float, float]] = []
    cursor = 0.0
    for seg in audio_segments:
        end = cursor + seg["duration"]
        scene_windows.append((cursor, end))
        cursor = end

    buckets: list[list[pysrt.SubRipItem]] = [[] for _ in audio_segments]

    for sub in subs:
        sub_mid = (sub.start.ordinal + sub.end.ordinal) / 2000.0
        for i, (win_start, win_end) in enumerate(scene_windows):
            if win_start <= sub_mid < win_end:
                buckets[i].append(sub)
                break

    # Extend the last caption in each scene to reach the scene boundary
    for i, (win_start, win_end) in enumerate(scene_windows):
        if buckets[i]:
            last_sub = buckets[i][-1]
            last_sub_end = last_sub.end.ordinal / 1000.0
            if win_end - last_sub_end < 1.0:  # within 1 second of scene end
                last_sub.end = pysrt.SubRipTime.from_ordinal(int(win_end * 1000))

    return buckets


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

        # ── Step 1: Whisper transcription → SRT ──────────────────────
        await whisper_transcribe(full_audio, srt_path)

        # ── Step 2: Distribute captions to scenes ────────────────────
        scene_captions = _distribute_captions(srt_path, audio_segments)

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

            # Pass srt_cursor so captions align with Whisper SRT timestamps
            clip = compose_scene_clip(
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
                _intro_audio = _AFC(intro_audio_path)
                intro_duration = _intro_audio.duration
                _intro_audio.close()

                intro_clip = compose_scene_clip(
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
        bgm_path = state.get("user_preferences", {}).get("bgm_path")
        render_final_video(
            scene_clips=clips,
            output_path=final_video_path,
            bgm_path=bgm_path,
            fps=settings.video_fps,
        )

        # ── Step 5: Thumbnail (copy first scene image) ───────────────
        if images:
            shutil.copy2(images[0]["image_path"], thumbnail_path)

        # ── Step 6: Metadata ─────────────────────────────────────────
        metadata = _generate_metadata(script_data, trend_data)

        # Measure actual duration from rendered file
        from moviepy import VideoFileClip as _VFC

        rendered = _VFC(final_video_path)
        duration_sec = rendered.duration
        rendered.close()

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
