"""Media Producer node — generates voice audio, images, and video clips."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import structlog
from moviepy import AudioFileClip, concatenate_audioclips

from podcast_shorts.config import get_assets_dir, settings
from podcast_shorts.graph.state import (
    AudioSegment,
    ImageAsset,
    MediaAssets,
    PipelineState,
    QualityAssessment,
    Scene,
    VideoClip,
)
from langchain_openai import ChatOpenAI

from podcast_shorts.tools.dalle import dalle_generate
from podcast_shorts.tools.ideogram import ideogram_generate
from podcast_shorts.tools.elevenlabs import elevenlabs_tts

# Static images for CTA scenes
_ASSETS_DIR = get_assets_dir()
_CHANNEL_AD_IMAGE = str(_ASSETS_DIR / "channel_ad.png")
_CHANNEL_CTA_IMAGE = str(_ASSETS_DIR / "channel_cta.png")

logger = structlog.get_logger()


def _get_speaker_pic(speaker: str, selected_speakers: dict | None) -> str | None:
    """Return the ai_pic path for a participant speaker, or None for host/missing.

    Maps participant_N → family member key via selected_speakers, then checks
    if assets/ai_pic/{key}.png exists.
    """
    if not speaker or speaker == "host" or not selected_speakers:
        return None
    if not speaker.startswith("participant_"):
        return None
    try:
        idx = int(speaker.split("_")[1]) - 1  # participant_1 → index 0
    except (IndexError, ValueError):
        return None
    participants = selected_speakers.get("participants", [])
    if idx < 0 or idx >= len(participants):
        return None
    family_key = participants[idx]
    pic_path = _ASSETS_DIR / "ai_pic" / f"{family_key}.png"
    return str(pic_path) if pic_path.is_file() else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ElevenLabs allows max 2 concurrent requests on most plans
_tts_semaphore = asyncio.Semaphore(2)


def _get_static_image(scene_id: str) -> str | None:
    """Return a pre-made image path for CTA scenes, or None (use AI generator).

    cta_2 → channel_cta.png (channel call-to-action card)
    cta / cta_1 → channel_ad.png (channel ad card)
    others → None (generate with DALL-E or Ideogram)
    """
    if scene_id == "cta_2":
        return _CHANNEL_CTA_IMAGE
    if scene_id.startswith("cta"):
        return _CHANNEL_AD_IMAGE
    return None


def _scene_type(scene_id: str) -> str:
    """Map scene_id to a generator scene type key."""
    if scene_id.startswith("body_"):
        return "body"
    if scene_id == "hook":
        return "hook"
    if scene_id.startswith("cta"):
        return "cta"
    return "default"


async def _generate_image(prompt: str, output_path: str, scene_type: str = "default", generator: str = "dalle") -> str:
    """Dispatch image generation to Ideogram or DALL-E.

    *generator*: "ideogram" | "dalle" (falls back to settings.image_generator if empty).
    """
    use = generator or settings.image_generator
    if use == "ideogram":
        return await ideogram_generate(prompt, output_path, scene_type=scene_type)
    return await dalle_generate(prompt, output_path, scene_type=scene_type)


async def _generate_scene_assets(
    scene: Scene,
    voice_ids: dict[str, str],
    output_dir: Path,
    generate_video: bool = False,
    selected_speakers: dict | None = None,
    generator: str = "dalle",
) -> tuple[AudioSegment, ImageAsset, VideoClip]:
    """Generate audio and image for a single scene.

    *voice_ids*: mapping of speaker → ElevenLabs voice ID.
    *generate_video*: reserved for future use.
    *selected_speakers*: used to resolve participant ai_pic images.

    Image priority per scene:
      1. static_image (cta → channel_ad/channel_cta)
      2. speaker ai_pic (participants with pre-made photos)
      3. AI generator (DALL-E or Ideogram based on settings.image_generator)

    Returns a tuple of (AudioSegment, ImageAsset, VideoClip) TypedDicts.
    """
    import shutil

    scene_id = scene["scene_id"]
    audio_path = str(output_dir / "audio" / f"{scene_id}.mp3")
    image_path = str(output_dir / "images" / f"{scene_id}.png")

    # Select voice_id for this scene's speaker
    speaker = scene.get("speaker", "host")
    voice_id = voice_ids.get(speaker, voice_ids.get("host", ""))

    async def _tts_with_limit():
        async with _tts_semaphore:
            return await elevenlabs_tts(
                text=scene["text"],
                voice_id=voice_id,
                emotion=scene.get("emotion", "neutral"),
                output_path=audio_path,
            )

    static_img = _get_static_image(scene_id)
    speaker_pic = _get_speaker_pic(speaker, selected_speakers)

    if static_img:
        # CTA scenes: use pre-made static image (channel_ad or channel_cta)
        shutil.copy2(static_img, image_path)
        tasks: list = [_tts_with_limit()]
        results = await asyncio.gather(*tasks)
        audio_result = results[0]
        image_result = image_path
    elif speaker_pic:
        # Participant scene: use ai_pic instead of generating
        shutil.copy2(speaker_pic, image_path)
        tasks = [_tts_with_limit()]
        results = await asyncio.gather(*tasks)
        audio_result = results[0]
        image_result = image_path
        logger.info("scene_assets.using_ai_pic", scene_id=scene_id, speaker=speaker, pic=speaker_pic)
    else:
        # Host / non-participant: generate with DALL-E or Ideogram
        stype = _scene_type(scene_id)
        tasks = [
            _tts_with_limit(),
            _generate_image(
                prompt=scene["image_prompt"],
                output_path=image_path,
                scene_type=stype,
                generator=generator,
            ),
        ]
        results = await asyncio.gather(*tasks)
        audio_result = results[0]
        image_result = results[1]

    # Measure actual audio duration
    clip = AudioFileClip(audio_result)
    actual_duration = clip.duration
    clip.close()

    audio_segment: AudioSegment = {
        "scene_id": scene_id,
        "audio_path": audio_result,
        "duration": actual_duration,
    }
    image_asset: ImageAsset = {
        "scene_id": scene_id,
        "image_path": image_result,
        "prompt": scene["image_prompt"],
    }
    video_clip: VideoClip = {
        "scene_id": scene_id,
        "video_path": "",
        "duration": scene["duration"],
    }

    logger.info(
        "scene_assets.done",
        scene_id=scene_id,
        audio_duration=actual_duration,
    )
    return audio_segment, image_asset, video_clip


async def _use_manual_audio(
    scene: Scene,
    audio_files: dict[str, str],
    output_dir: Path,
    selected_speakers: dict | None = None,
    generator: str = "dalle",
) -> tuple[AudioSegment, ImageAsset, VideoClip]:
    """Use manually recorded audio file for a scene, still generate images.

    *audio_files*: mapping of scene_id → source audio file path.
    *selected_speakers*: used to resolve participant ai_pic images.

    Image priority: static (cta) → ai_pic (participant) → AI generator.
    """
    import shutil

    scene_id = scene["scene_id"]
    audio_path = str(output_dir / "audio" / f"{scene_id}.mp3")
    image_path = str(output_dir / "images" / f"{scene_id}.png")

    # Copy manual audio file
    source_audio = audio_files.get(scene_id, "")
    if source_audio and os.path.isfile(source_audio):
        shutil.copy2(source_audio, audio_path)
    else:
        raise FileNotFoundError(f"Manual audio file not found for scene {scene_id}: {source_audio}")

    # Image selection: static → ai_pic → AI generator
    speaker = scene.get("speaker", "host")
    static_img = _get_static_image(scene_id)
    speaker_pic = _get_speaker_pic(speaker, selected_speakers)

    if static_img:
        shutil.copy2(static_img, image_path)
    elif speaker_pic:
        shutil.copy2(speaker_pic, image_path)
        logger.info("manual_audio.using_ai_pic", scene_id=scene_id, speaker=speaker, pic=speaker_pic)
    else:
        stype = _scene_type(scene_id)
        await _generate_image(
            prompt=scene["image_prompt"],
            output_path=image_path,
            scene_type=stype,
            generator=generator,
        )

    # Measure actual audio duration
    clip = AudioFileClip(audio_path)
    actual_duration = clip.duration
    clip.close()

    audio_segment: AudioSegment = {
        "scene_id": scene_id,
        "audio_path": audio_path,
        "duration": actual_duration,
    }
    image_asset: ImageAsset = {
        "scene_id": scene_id,
        "image_path": image_path,
        "prompt": scene["image_prompt"],
    }
    video_clip: VideoClip = {
        "scene_id": scene_id,
        "video_path": "",
        "duration": actual_duration,
    }

    logger.info(
        "manual_audio.done",
        scene_id=scene_id,
        audio_duration=actual_duration,
    )
    return audio_segment, image_asset, video_clip


def _concatenate_audio(audio_paths: list[str], output_path: str) -> str:
    """Concatenate multiple MP3 files into one using MoviePy.

    Returns the output_path on success.
    """
    clips = [AudioFileClip(p) for p in audio_paths]
    try:
        final = concatenate_audioclips(clips)
        final.write_audiofile(output_path, logger=None)
        final.close()
    finally:
        for c in clips:
            c.close()

    logger.info("concatenate_audio.done", output_path=output_path)
    return output_path


def _assess_quality(
    segments: list[AudioSegment],
    images: list[ImageAsset],
    clips: list[VideoClip],
    full_audio: str,
    expected_count: int,
) -> QualityAssessment:
    """File-existence and size-based quality assessment.

    Checks audio + image for every scene, video only when video_path is set,
    plus full_audio existence and count match.
    """
    # Count expected video clips (only those with a non-empty path)
    expected_videos = sum(1 for vc in clips if vc["video_path"])
    total_checks = expected_count * 2 + expected_videos + 2
    passed_checks = 0

    # Audio segments
    for seg in segments:
        if os.path.isfile(seg["audio_path"]) and os.path.getsize(seg["audio_path"]) > 0:
            passed_checks += 1

    # Images
    for img in images:
        if os.path.isfile(img["image_path"]) and os.path.getsize(img["image_path"]) > 0:
            passed_checks += 1

    # Video clips (only check those with a path)
    for vc in clips:
        if vc["video_path"] and os.path.isfile(vc["video_path"]) and os.path.getsize(vc["video_path"]) > 0:
            passed_checks += 1

    # Full audio
    if os.path.isfile(full_audio) and os.path.getsize(full_audio) > 0:
        passed_checks += 1

    # Count check (all scenes produced assets)
    if len(segments) == expected_count and len(images) == expected_count and len(clips) == expected_count:
        passed_checks += 1

    score = passed_checks / total_checks if total_checks > 0 else 0.0
    passed = score >= settings.quality_threshold

    feedback_parts = []
    if passed:
        feedback_parts.append(
            f"Media generation succeeded: {passed_checks}/{total_checks} checks passed."
        )
    else:
        feedback_parts.append(
            f"Media generation incomplete: {passed_checks}/{total_checks} checks passed."
        )
        missing_audio = expected_count - len(segments)
        missing_images = expected_count - len(images)
        if missing_audio > 0:
            feedback_parts.append(f"Missing {missing_audio} audio segments.")
        if missing_images > 0:
            feedback_parts.append(f"Missing {missing_images} images.")

    return {
        "node_name": "media_producer",
        "passed": passed,
        "score": round(score, 3),
        "feedback": " ".join(feedback_parts),
        "attempt": 0,  # caller sets this
    }


async def _generate_hook_video_prompt(script_data: dict) -> str:
    """Use GPT-4o to generate a Luma video prompt based on the full script content."""
    title = script_data.get("title", "")
    hook = script_data.get("hook", "")
    full_script = script_data.get("full_script", "")

    llm = ChatOpenAI(
        model=settings.reasoning_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
    )

    system_msg = (
        "You are a video prompt engineer. Given a podcast script, generate a single "
        "concise English prompt for Luma Dream Machine to create a short hook video. "
        "The prompt should visually represent the core topic and mood of the script. "
        "Output ONLY the prompt text, nothing else."
    )
    user_msg = (
        f"Script title: {title}\n"
        f"Hook text: {hook}\n"
        f"Full script summary: {full_script[:500]}\n\n"
        "Generate a visually compelling video prompt (in English) that captures "
        "the essence of this podcast topic. The video should be vertical (9:16 aspect ratio). "
        "Include the topic's key visual elements."
    )

    response = await llm.ainvoke([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ])

    prompt = response.content.strip()
    logger.info("hook_video_prompt.generated", prompt_len=len(prompt))
    return prompt


# ---------------------------------------------------------------------------
# Node implementation
# ---------------------------------------------------------------------------


async def media_producer(state: PipelineState) -> dict:
    """Generate audio (ElevenLabs), images (DALL-E 3), and video clips (Luma)
    for each scene in parallel. Retry only failed assets for cost optimization.
    """
    logger.info("media_producer.start", run_id=state.get("run_id"))

    retry_counts = state.get("retry_counts", {})
    attempt = retry_counts.get("media_producer", 0) + 1
    scenes: list[Scene] = (state.get("script_data") or {}).get("scenes", [])
    hook_video_prompt: str | None = None

    try:
        if not scenes:
            raise RuntimeError("No scenes found in script_data")

        # ── Setup output directories ─────────────────────────────────
        run_id = state.get("run_id", "default")
        output_dir = Path(settings.output_base_dir) / run_id
        for subdir in ("audio", "images", "video"):
            (output_dir / subdir).mkdir(parents=True, exist_ok=True)

        # ── Voice IDs from config (mapped per family member) ──
        _VOICE_ID_MAP: dict[str, str] = {
            "me": settings.voice_id_me,
            "wife": settings.voice_id_wife,
            "jiho": settings.voice_id_jiho,
            "jihyung": settings.voice_id_jihyung,
            "jiwon": settings.voice_id_jiwon,
            "grandfa": settings.voice_id_grandfa,
            "grandma": settings.voice_id_grandma,
            "unha": settings.voice_id_unha,
        }
        fallback_voice = settings.voice_id_me or "default_voice_id"

        selected_speakers = state.get("selected_speakers")
        if selected_speakers:
            host_key = selected_speakers.get("host", "me")
            # Use `or fallback_voice` to handle empty string voice IDs
            voice_ids: dict[str, str] = {
                "host": _VOICE_ID_MAP.get(host_key) or fallback_voice,
            }
            for i, p_key in enumerate(selected_speakers.get("participants", []), 1):
                voice_ids[f"participant_{i}"] = _VOICE_ID_MAP.get(p_key) or fallback_voice
        else:
            # Legacy fallback: 3-person family (아빠, 아들, 딸)
            voice_ids = {
                "host": _VOICE_ID_MAP.get("me") or fallback_voice,
                "son": _VOICE_ID_MAP.get("jiho") or fallback_voice,
                "daughter": _VOICE_ID_MAP.get("jiwon") or fallback_voice,
            }

        # ── Check audio source (TTS vs manual) ───────────────────────
        audio_source = state.get("audio_source", "tts")

        img_gen = state.get("image_generator") or settings.image_generator

        if audio_source == "manual":
            # Manual recording mode: copy user-provided audio files, generate images
            results = await asyncio.gather(
                *[
                    _use_manual_audio(
                        scene, state.get("audio_files", {}), output_dir,
                        selected_speakers=selected_speakers,
                        generator=img_gen,
                    )
                    for scene in scenes
                ],
                return_exceptions=True,
            )
        else:
            # TTS mode: generate audio via ElevenLabs + images via AI generator
            # Image priority: static (cta/cta_2) → ai_pic (participant) → DALL-E/Ideogram
            results = await asyncio.gather(
                *[
                    _generate_scene_assets(
                        scene, voice_ids, output_dir,
                        generate_video=False,
                        selected_speakers=selected_speakers,
                        generator=img_gen,
                    )
                    for scene in scenes
                ],
                return_exceptions=True,
            )

        # ── Collect successful results, log failures ─────────────────
        audio_segments: list[AudioSegment] = []
        images: list[ImageAsset] = []
        video_clips: list[VideoClip] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "media_producer.scene_failed",
                    scene_id=scenes[i]["scene_id"],
                    error=str(result),
                )
                continue
            seg, img, vid = result
            audio_segments.append(seg)
            images.append(img)
            video_clips.append(vid)

        if not audio_segments:
            raise RuntimeError(
                "All scene audio generations failed — cannot produce output"
            )

        # ── Concatenate audio ────────────────────────────────────────
        audio_paths = [seg["audio_path"] for seg in audio_segments]
        full_audio_path = str(output_dir / "audio" / "full_audio.mp3")
        _concatenate_audio(audio_paths, full_audio_path)

        # ── Build MediaAssets ────────────────────────────────────────
        media_assets: MediaAssets = {
            "audio_path": full_audio_path,
            "audio_segments": audio_segments,
            "images": images,
            "video_clips": video_clips,
            "voice_ids": voice_ids,
        }

        # ── Generate hook video prompt (for user review) ─────────────
        hook_video_prompt = await _generate_hook_video_prompt(
            state.get("script_data") or {}
        )

        # ── Quality assessment ───────────────────────────────────────
        quality = _assess_quality(
            segments=audio_segments,
            images=images,
            clips=video_clips,
            full_audio=full_audio_path,
            expected_count=len(scenes),
        )
        quality["attempt"] = attempt

        logger.info(
            "media_producer.done",
            num_scenes=len(scenes),
            audio_ok=len(audio_segments),
            images_ok=len(images),
            video_ok=len(video_clips),
            quality_score=quality["score"],
            attempt=attempt,
        )

    except Exception:
        logger.exception("media_producer.error", attempt=attempt)
        media_assets = {
            "audio_path": "",
            "audio_segments": [],
            "images": [],
            "video_clips": [],
            "voice_ids": {},
        }
        quality = {
            "node_name": "media_producer",
            "passed": False,
            "score": 0.0,
            "feedback": "Media production failed due to an error. Will retry.",
            "attempt": attempt,
        }

    retry_counts = {**retry_counts, "media_producer": attempt}

    return {
        "media_assets": media_assets,
        "quality": quality,
        "retry_counts": retry_counts,
        "hook_video_prompt": hook_video_prompt,
    }
