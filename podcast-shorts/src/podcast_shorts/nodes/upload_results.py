"""Upload node — uploads pipeline outputs to Supabase Storage after auto_editor."""

from __future__ import annotations

import structlog

from podcast_shorts.config import settings
from podcast_shorts.graph.state import PipelineState
from podcast_shorts.tools.supabase_storage import (
    save_pipeline_result,
    upload_pipeline_outputs,
)

logger = structlog.get_logger()


async def upload_results(state: PipelineState) -> dict:
    """Upload auto_editor outputs to Supabase Storage and save metadata to DB.

    Skips silently when supabase_url is not configured (local development).
    On upload success, replaces editor_output paths with Supabase public URLs.
    """
    if not settings.supabase_url:
        logger.info("upload_results.skipped", reason="supabase_url not configured")
        return {}

    editor_output = state.get("editor_output")
    if editor_output is None:
        logger.warning("upload_results.skipped", reason="no editor_output")
        return {}

    run_id = state["run_id"]
    user_id = state["user_id"]

    try:
        urls = await upload_pipeline_outputs(run_id, editor_output)

        # Save metadata to DB
        metadata = editor_output.get("metadata", {})
        duration_sec = editor_output.get("duration_sec", 0.0)
        await save_pipeline_result(run_id, user_id, urls, metadata, duration_sec)

        # Replace local paths with Supabase URLs in editor_output
        updated_output = dict(editor_output)
        if urls.get("final_video_url"):
            updated_output["final_video_path"] = urls["final_video_url"]
        if urls.get("caption_srt_url"):
            updated_output["caption_srt_path"] = urls["caption_srt_url"]
        if urls.get("thumbnail_url"):
            updated_output["thumbnail_path"] = urls["thumbnail_url"]

        logger.info("upload_results.completed", run_id=run_id)
        return {"editor_output": updated_output}

    except Exception:
        logger.exception("upload_results.failed", run_id=run_id)
        # Don't fail the pipeline — local files still exist
        return {}
