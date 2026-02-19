"""FastAPI route handlers for the pipeline API."""

from __future__ import annotations

import uuid

import structlog
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from langgraph.types import Command
from sse_starlette.sse import EventSourceResponse

from podcast_shorts.api.dependencies import get_compiled_graph
from podcast_shorts.config import settings
from podcast_shorts.api.schemas import (
    AudioChoiceRequest,
    AudioChoiceResponse,
    HookPromptResponse,
    HookPromptSubmitRequest,
    HookPromptSubmitResponse,
    PipelineResultResponse,
    PipelineStartRequest,
    PipelineStartResponse,
    PipelineStatusResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    ScriptReviewResponse,
    SpeakerSelectionRequest,
    SpeakerSelectionResponse,
    TopicSelectionRequest,
    TopicSelectionResponse,
)
from podcast_shorts.nodes.speaker_selection import FAMILY_MEMBERS
from podcast_shorts.models.output import EditorOutputModel
from podcast_shorts.models.script import ScriptDataModel
from podcast_shorts.tools.supabase_storage import (
    create_pipeline_run,
    get_pipeline_result_from_db,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/pipeline")


async def _set_error_state(run_id: str, error_msg: str) -> None:
    """Write error to pipeline state so the frontend can detect it."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}
    try:
        await graph.aupdate_state(config, {"error": error_msg})
    except Exception:
        logger.exception("pipeline.set_error_state.failed", run_id=run_id)


async def _run_pipeline(run_id: str, user_id: str, keywords: list[str], user_preferences: dict):
    """Execute the pipeline graph in the background."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    initial_state = {
        "messages": [],
        "trend_data": None,
        "script_data": None,
        "media_assets": None,
        "editor_output": None,
        "quality": None,
        "retry_counts": {},
        "topic_selected": None,
        "topic_selection_approved": None,
        "selected_speakers": None,
        "speaker_selection_approved": None,
        "human_approved": None,
        "human_feedback": None,
        "audio_source": None,
        "audio_choice_approved": None,
        "audio_files": None,
        "script_file_path": None,
        "hook_video_prompt": None,
        "hook_prompt_approved": None,
        "user_id": user_id,
        "user_preferences": user_preferences,
        "run_id": run_id,
        "error": None,
    }

    try:
        await graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        logger.exception("pipeline.failed", run_id=run_id)
        await _set_error_state(run_id, f"파이프라인 실행 실패: {exc}")


@router.post("/start", response_model=PipelineStartResponse)
async def start_pipeline(request: PipelineStartRequest, background_tasks: BackgroundTasks):
    """Start a new pipeline run in the background."""
    run_id = str(uuid.uuid4())

    # Record pipeline start in Supabase DB (if configured)
    if settings.supabase_url:
        try:
            await create_pipeline_run(run_id, request.user_id)
        except Exception:
            logger.exception("pipeline.db_create_failed", run_id=run_id)

    background_tasks.add_task(
        _run_pipeline,
        run_id=run_id,
        user_id=request.user_id,
        keywords=request.keywords,
        user_preferences=request.user_preferences,
    )

    logger.info("pipeline.started", run_id=run_id, user_id=request.user_id)
    return PipelineStartResponse(run_id=run_id)


@router.get("/{run_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(run_id: str):
    """Get the current status of a pipeline run."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        # Transient DB error — return running so frontend keeps polling
        logger.warning("pipeline.status.db_error", run_id=run_id, exc_info=True)
        return PipelineStatusResponse(run_id=run_id, status="running")

    if state.values is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    # Determine status from state
    error = state.values.get("error")
    if error:
        return PipelineStatusResponse(run_id=run_id, status="failed", error=error)

    if state.values.get("editor_output") is not None:
        return PipelineStatusResponse(run_id=run_id, status="completed")

    script_file_path = state.values.get("script_file_path")

    # Check if waiting for any interrupt gate
    if state.next:
        if "topic_selection_gate" in state.next:
            return PipelineStatusResponse(
                run_id=run_id, status="waiting_for_topic_selection",
                current_node="topic_selection_gate",
                script_file_path=script_file_path,
            )
        if "speaker_selection_gate" in state.next:
            return PipelineStatusResponse(
                run_id=run_id, status="waiting_for_speaker_selection",
                current_node="speaker_selection_gate",
                script_file_path=script_file_path,
            )
        if "human_review_gate" in state.next:
            return PipelineStatusResponse(
                run_id=run_id, status="waiting_for_review",
                current_node="human_review_gate",
                script_file_path=script_file_path,
            )
        if "audio_choice_gate" in state.next:
            return PipelineStatusResponse(
                run_id=run_id, status="waiting_for_audio_choice",
                current_node="audio_choice_gate",
                script_file_path=script_file_path,
            )
        if "hook_prompt_gate" in state.next:
            return PipelineStatusResponse(
                run_id=run_id, status="waiting_for_hook_prompt",
                current_node="hook_prompt_gate",
                script_file_path=script_file_path,
            )
        return PipelineStatusResponse(
            run_id=run_id, status="running", current_node=state.next[0],
            script_file_path=script_file_path,
        )

    return PipelineStatusResponse(run_id=run_id, status="running")


@router.get("/{run_id}/topics", response_model=TopicSelectionResponse)
async def get_topics(run_id: str):
    """Get trending topics waiting for user selection."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "topic_selection_gate" not in state.next:
        return TopicSelectionResponse(run_id=run_id, status="not_ready")

    trend_data = state.values.get("trend_data") or {}
    topics = trend_data.get("topic_summaries", [])

    return TopicSelectionResponse(
        run_id=run_id, status="waiting_for_topic_selection", topics=topics
    )


@router.post("/{run_id}/topic-selection", response_model=TopicSelectionResponse)
async def submit_topic_selection(
    run_id: str, request: TopicSelectionRequest, background_tasks: BackgroundTasks
):
    """Submit user's topic selection."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "topic_selection_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for topic selection")

    resume_value = {"selected_topic": request.selected_topic}

    async def _resume():
        try:
            await graph.ainvoke(Command(resume=resume_value), config=config)
        except Exception as exc:
            logger.exception("pipeline.topic_selection_resume_failed", run_id=run_id)
            await _set_error_state(run_id, f"주제 선택 후 처리 실패: {exc}")

    background_tasks.add_task(_resume)

    logger.info("pipeline.topic_selected", run_id=run_id, topic=request.selected_topic)
    return TopicSelectionResponse(run_id=run_id, status="resumed")


@router.get("/{run_id}/speakers", response_model=SpeakerSelectionResponse)
async def get_speakers(run_id: str):
    """Get family member list for speaker selection."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "speaker_selection_gate" not in state.next:
        return SpeakerSelectionResponse(run_id=run_id, status="not_ready")

    members = [
        {
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "photo_url": f"/files/assets/pic/{key}.jpeg",
        }
        for key, info in FAMILY_MEMBERS.items()
    ]

    return SpeakerSelectionResponse(
        run_id=run_id, status="waiting_for_speaker_selection", members=members
    )


@router.post("/{run_id}/speaker-selection", response_model=SpeakerSelectionResponse)
async def submit_speaker_selection(
    run_id: str, request: SpeakerSelectionRequest, background_tasks: BackgroundTasks
):
    """Submit user's speaker selection (host + participants)."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "speaker_selection_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for speaker selection")

    resume_value = {"host": request.host, "participants": request.participants}

    async def _resume():
        try:
            await graph.ainvoke(Command(resume=resume_value), config=config)
        except Exception as exc:
            logger.exception("pipeline.speaker_selection_resume_failed", run_id=run_id)
            await _set_error_state(run_id, f"출연자 선택 후 처리 실패: {exc}")

    background_tasks.add_task(_resume)

    logger.info(
        "pipeline.speakers_selected",
        run_id=run_id,
        host=request.host,
        participants=request.participants,
    )
    return SpeakerSelectionResponse(run_id=run_id, status="resumed")


@router.get("/{run_id}/script", response_model=ScriptReviewResponse)
async def get_script_for_review(run_id: str):
    """Get the script that's waiting for human review."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "human_review_gate" not in state.next:
        return ScriptReviewResponse(run_id=run_id, status="not_ready")

    script_data = state.values.get("script_data")
    if script_data is None:
        return ScriptReviewResponse(run_id=run_id, status="not_ready")

    return ScriptReviewResponse(
        run_id=run_id,
        status="waiting_for_review",
        script_data=ScriptDataModel(**script_data),
        script_file_path=state.values.get("script_file_path"),
    )


@router.post("/{run_id}/review", response_model=ReviewSubmitResponse)
async def submit_review(run_id: str, request: ReviewSubmitRequest, background_tasks: BackgroundTasks):
    """Submit human review decision (approve or reject with feedback)."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "human_review_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for review")

    resume_value = {"approved": request.approved, "feedback": request.feedback}

    async def _resume():
        try:
            await graph.ainvoke(Command(resume=resume_value), config=config)
        except Exception as exc:
            logger.exception("pipeline.resume_failed", run_id=run_id)
            await _set_error_state(run_id, f"리뷰 처리 실패: {exc}")

    background_tasks.add_task(_resume)

    status = "resumed" if request.approved else "revision_requested"
    logger.info("pipeline.review_submitted", run_id=run_id, approved=request.approved)
    return ReviewSubmitResponse(run_id=run_id, status=status)


@router.post("/{run_id}/upload-audio")
async def upload_audio_files(run_id: str, request: Request):
    """Upload manual audio files for each scene. Form field name = scene_id (e.g. hook, body_1_1, cta)."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}
    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    if not state.next or "audio_choice_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for audio choice")
    script_data = state.values.get("script_data") or {}
    scenes = script_data.get("scenes", [])
    scene_ids = {s["scene_id"] for s in scenes}
    base = Path(settings.output_base_dir).resolve() / run_id / "uploaded_audio"
    base.mkdir(parents=True, exist_ok=True)
    form = await request.form()
    audio_files: dict[str, str] = {}
    for key in form.keys():
        if key not in scene_ids:
            continue
        value = form[key]
        if hasattr(value, "read"):
            upload = value
            ext = Path(getattr(upload, "filename", "audio.mp3") or "audio.mp3").suffix or ".mp3"
            dest = base / f"{key}{ext}"
            content = await upload.read()
            dest.write_bytes(content)
            audio_files[key] = str(dest)
    return {"run_id": run_id, "audio_files": audio_files}


@router.get("/{run_id}/audio-choice", response_model=AudioChoiceResponse)
async def get_audio_choice_status(run_id: str):
    """Check if pipeline is waiting for audio source selection."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "audio_choice_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for audio choice")

    return AudioChoiceResponse(run_id=run_id, status="waiting_for_audio_choice")


@router.post("/{run_id}/audio-choice", response_model=AudioChoiceResponse)
async def submit_audio_choice(run_id: str, request: AudioChoiceRequest, background_tasks: BackgroundTasks):
    """Submit audio source selection (TTS or manual recording)."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "audio_choice_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for audio choice")

    resume_value = {"audio_source": request.audio_source}
    if request.audio_files:
        resume_value["audio_files"] = request.audio_files

    async def _resume():
        try:
            await graph.ainvoke(Command(resume=resume_value), config=config)
        except Exception as exc:
            logger.exception("pipeline.audio_choice_resume_failed", run_id=run_id)
            await _set_error_state(run_id, f"오디오 선택 처리 실패: {exc}")

    background_tasks.add_task(_resume)

    logger.info("pipeline.audio_choice_submitted", run_id=run_id, audio_source=request.audio_source)
    return AudioChoiceResponse(run_id=run_id, status="resumed")


@router.get("/{run_id}/hook-prompt", response_model=HookPromptResponse)
async def get_hook_prompt(run_id: str):
    """Get the hook video prompt waiting for user review."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "hook_prompt_gate" not in state.next:
        return HookPromptResponse(run_id=run_id, status="not_ready")

    prompt = state.values.get("hook_video_prompt", "")
    return HookPromptResponse(
        run_id=run_id, status="waiting_for_hook_prompt", prompt=prompt
    )


@router.post("/{run_id}/hook-prompt", response_model=HookPromptSubmitResponse)
async def submit_hook_prompt(
    run_id: str, request: HookPromptSubmitRequest, background_tasks: BackgroundTasks
):
    """Submit approved or edited hook video prompt."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    if not state.next or "hook_prompt_gate" not in state.next:
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for hook prompt review")

    resume_value = {"prompt": request.prompt}

    async def _resume():
        try:
            await graph.ainvoke(Command(resume=resume_value), config=config)
        except Exception as exc:
            logger.exception("pipeline.hook_prompt_resume_failed", run_id=run_id)
            await _set_error_state(run_id, f"Hook 프롬프트 처리 실패: {exc}")

    background_tasks.add_task(_resume)

    logger.info("pipeline.hook_prompt_submitted", run_id=run_id)
    return HookPromptSubmitResponse(run_id=run_id, status="resumed")


@router.get("/{run_id}/result", response_model=PipelineResultResponse)
async def get_pipeline_result(run_id: str):
    """Get the final result of a completed pipeline run.

    Tries LangGraph checkpointer state first, falls back to Supabase DB
    (useful after server restart when in-memory state is lost).
    """
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        state = None

    # Try checkpointer state first
    if state and state.values:
        error = state.values.get("error")
        if error:
            return PipelineResultResponse(run_id=run_id, status="failed", error=error)

        editor_output = state.values.get("editor_output")
        if editor_output is not None:
            return PipelineResultResponse(
                run_id=run_id,
                status="completed",
                result=EditorOutputModel(**editor_output),
            )

    # Fallback: query Supabase DB for persisted results
    if settings.supabase_url:
        try:
            db_result = await get_pipeline_result_from_db(run_id)
            if db_result is not None:
                return PipelineResultResponse(
                    run_id=run_id, status="completed", result=db_result
                )
        except Exception:
            logger.exception("pipeline.db_fallback_failed", run_id=run_id)

    if state and state.values:
        return PipelineResultResponse(run_id=run_id, status="not_completed")

    raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")


@router.get("/{run_id}/stream")
async def stream_pipeline_status(run_id: str):
    """SSE endpoint for real-time pipeline progress updates."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": run_id}}

    async def event_generator():
        try:
            async for event in graph.astream_events(
                None, config=config, version="v2"
            ):
                kind = event.get("event", "")
                if kind in ("on_chain_start", "on_chain_end"):
                    yield {
                        "event": kind,
                        "data": str(
                            {"name": event.get("name", ""), "run_id": run_id}
                        ),
                    }
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
