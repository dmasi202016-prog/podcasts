"""Request/Response schemas for the FastAPI endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from podcast_shorts.models.output import EditorOutputModel
from podcast_shorts.models.script import ScriptDataModel


class PipelineStartRequest(BaseModel):
    user_id: str
    keywords: list[str] = Field(default_factory=list, description="Optional seed keywords")
    user_preferences: dict[str, Any] = Field(
        default_factory=dict, description="User interest categories, persona settings"
    )


class PipelineStartResponse(BaseModel):
    run_id: str
    status: str = "started"


class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str  # "running" | "waiting_for_review" | "waiting_for_audio_choice" | "waiting_for_hook_prompt" | "completed" | "failed"
    current_node: Optional[str] = None
    script_file_path: Optional[str] = None
    error: Optional[str] = None


class ScriptReviewResponse(BaseModel):
    run_id: str
    status: str  # "waiting_for_review" | "not_ready"
    script_data: Optional[ScriptDataModel] = None
    script_file_path: Optional[str] = None


class ReviewSubmitRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


class ReviewSubmitResponse(BaseModel):
    run_id: str
    status: str  # "resumed" | "revision_requested"


class TopicSelectionRequest(BaseModel):
    selected_topic: str


class TopicSelectionResponse(BaseModel):
    run_id: str
    status: str  # "resumed" | "waiting_for_topic_selection"
    topics: Optional[list[dict[str, Any]]] = None


class SpeakerSelectionRequest(BaseModel):
    host: str
    participants: list[str]


class SpeakerSelectionResponse(BaseModel):
    run_id: str
    status: str  # "resumed" | "waiting_for_speaker_selection"
    members: Optional[list[dict[str, Any]]] = None


class AudioChoiceRequest(BaseModel):
    audio_source: str = Field(description="'tts' or 'manual'")
    audio_files: Optional[dict[str, str]] = Field(
        default=None,
        description="Mapping of scene_id → audio file path (required when audio_source='manual')",
    )


class AudioChoiceResponse(BaseModel):
    run_id: str
    status: str  # "resumed"


class HookPromptResponse(BaseModel):
    run_id: str
    status: str  # "waiting_for_hook_prompt" | "not_ready"
    prompt: Optional[str] = None


class HookPromptSubmitRequest(BaseModel):
    prompt: str


class HookPromptSubmitResponse(BaseModel):
    run_id: str
    status: str  # "resumed"


class PipelineResultResponse(BaseModel):
    run_id: str
    status: str
    result: Optional[EditorOutputModel] = None
    error: Optional[str] = None
