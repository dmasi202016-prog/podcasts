"""Supabase Storage upload and PostgreSQL metadata persistence."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog
from supabase import create_client

from podcast_shorts.config import settings
from podcast_shorts.models.output import EditorOutputModel

logger = structlog.get_logger()


def _get_supabase_client():
    """Create a Supabase client using service_role key."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _upload_file_sync(client, run_id: str, local_path: str) -> str:
    """Upload a single file to Supabase Storage (sync, runs in thread pool)."""
    path = Path(local_path)
    if not path.exists():
        logger.warning("supabase.upload.file_not_found", path=local_path)
        return ""

    storage_path = f"{run_id}/{path.name}"
    bucket = settings.supabase_storage_bucket

    with open(path, "rb") as f:
        client.storage.from_(bucket).upload(
            storage_path,
            f,
            file_options={"upsert": "true"},
        )

    public_url = f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{storage_path}"
    logger.info("supabase.upload.success", storage_path=storage_path)
    return public_url


async def upload_pipeline_outputs(run_id: str, editor_output: dict) -> dict[str, str]:
    """Upload final_video, caption_srt, and thumbnail to Supabase Storage.

    Runs sync Supabase SDK calls in a thread pool to avoid blocking the event loop.
    """
    client = _get_supabase_client()
    urls: dict[str, str] = {}

    for key, url_key in [
        ("final_video_path", "final_video_url"),
        ("caption_srt_path", "caption_srt_url"),
        ("thumbnail_path", "thumbnail_url"),
    ]:
        local_path = editor_output.get(key, "")
        if local_path:
            urls[url_key] = await asyncio.to_thread(
                _upload_file_sync, client, run_id, local_path
            )
        else:
            urls[url_key] = ""

    return urls


def _create_pipeline_run_sync(run_id: str, user_id: str) -> None:
    """Insert a new pipeline_runs row (sync, runs in thread pool)."""
    client = _get_supabase_client()
    client.table("pipeline_runs").insert({
        "run_id": run_id,
        "user_id": user_id,
        "status": "started",
    }).execute()
    logger.info("supabase.pipeline_run.created", run_id=run_id)


async def create_pipeline_run(run_id: str, user_id: str) -> None:
    """Insert a new pipeline_runs row with status='started'."""
    await asyncio.to_thread(_create_pipeline_run_sync, run_id, user_id)


def _save_pipeline_result_sync(
    run_id: str,
    user_id: str,
    urls: dict[str, str],
    metadata: dict[str, Any],
    duration_sec: float,
) -> None:
    """Upsert pipeline_runs row (sync, runs in thread pool)."""
    client = _get_supabase_client()
    client.table("pipeline_runs").upsert(
        {
            "run_id": run_id,
            "user_id": user_id,
            "status": "completed",
            "final_video_url": urls.get("final_video_url", ""),
            "caption_srt_url": urls.get("caption_srt_url", ""),
            "thumbnail_url": urls.get("thumbnail_url", ""),
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "category": metadata.get("category", ""),
            "duration_sec": duration_sec,
            "completed_at": "now()",
        },
        on_conflict="run_id",
    ).execute()
    logger.info("supabase.pipeline_result.saved", run_id=run_id)


async def save_pipeline_result(
    run_id: str,
    user_id: str,
    urls: dict[str, str],
    metadata: dict[str, Any],
    duration_sec: float,
) -> None:
    """Upsert pipeline_runs row with completed status, URLs, and metadata."""
    await asyncio.to_thread(
        _save_pipeline_result_sync, run_id, user_id, urls, metadata, duration_sec
    )


def _get_pipeline_result_sync(run_id: str) -> dict | None:
    """Fetch a completed pipeline result from DB (sync, runs in thread pool)."""
    client = _get_supabase_client()
    response = (
        client.table("pipeline_runs")
        .select("*")
        .eq("run_id", run_id)
        .eq("status", "completed")
        .maybe_single()
        .execute()
    )
    return response.data


async def get_pipeline_result_from_db(run_id: str) -> EditorOutputModel | None:
    """Fetch a completed pipeline result from DB (fallback when checkpointer state is lost)."""
    row = await asyncio.to_thread(_get_pipeline_result_sync, run_id)

    if not row:
        return None

    return EditorOutputModel(
        final_video_path=row.get("final_video_url", ""),
        caption_srt_path=row.get("caption_srt_url", ""),
        thumbnail_path=row.get("thumbnail_url", ""),
        metadata={
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "tags": row.get("tags", []),
            "category": row.get("category", ""),
        },
        duration_sec=row.get("duration_sec", 0.0),
    )
