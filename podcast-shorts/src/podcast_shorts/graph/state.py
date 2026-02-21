"""Central pipeline state definition for the LangGraph workflow."""

from __future__ import annotations

from typing import Annotated, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TopicSummary(TypedDict):
    keyword: str
    summary: str
    source: str  # "google_trends" | "youtube" | "twitter"
    trending_score: float


class TrendData(TypedDict):
    keywords: list[str]
    topic_summaries: list[TopicSummary]
    selected_topic: str
    category: str


class Scene(TypedDict):
    scene_id: str
    text: str
    duration: float
    emotion: str
    image_prompt: str
    speaker: str  # "host" | "son" | "daughter"


class ScriptData(TypedDict):
    title: str
    full_script: str
    scenes: list[Scene]
    hook: str
    cta: str
    estimated_duration_sec: float


class AudioSegment(TypedDict):
    scene_id: str
    audio_path: str
    duration: float


class ImageAsset(TypedDict):
    scene_id: str
    image_path: str
    prompt: str


class VideoClip(TypedDict):
    scene_id: str
    video_path: str
    duration: float


class MediaAssets(TypedDict):
    audio_path: str
    audio_segments: list[AudioSegment]
    images: list[ImageAsset]
    video_clips: list[VideoClip]
    voice_ids: dict[str, str]  # {"host": "...", "son": "...", "daughter": "..."}


class VideoMetadata(TypedDict):
    title: str
    description: str
    tags: list[str]
    category: str


class EditorOutput(TypedDict):
    final_video_path: str
    caption_srt_path: str
    thumbnail_path: str
    metadata: VideoMetadata
    duration_sec: float


class QualityAssessment(TypedDict):
    node_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    feedback: str
    attempt: int


class PipelineState(TypedDict):
    """Central state shared across all LangGraph nodes."""

    # LLM conversation log (accumulated via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    # Node outputs
    trend_data: Optional[TrendData]
    script_data: Optional[ScriptData]
    media_assets: Optional[MediaAssets]
    editor_output: Optional[EditorOutput]

    # Quality control
    quality: Optional[QualityAssessment]
    retry_counts: dict[str, int]

    # Human-in-the-loop
    human_approved: Optional[bool]
    human_feedback: Optional[str]

    # Topic selection gate
    topic_selected: Optional[str]
    topic_selection_approved: Optional[bool]

    # Speaker selection gate
    selected_speakers: Optional[dict]  # {"host": "me", "participants": ["grandma", "jiho"]}
    speaker_selection_approved: Optional[bool]

    # Audio source selection
    audio_source: Optional[str]  # "tts" | "manual"
    audio_choice_approved: Optional[bool]
    audio_files: Optional[dict[str, str]]  # scene_id → audio file path (manual mode)

    # Script file
    script_file_path: Optional[str]

    # Run configuration (set once at start)
    user_id: str
    user_preferences: dict
    run_id: str

    # Hook video prompt gate
    hook_video_prompt: Optional[str]
    hook_prompt_approved: Optional[bool]

    # Video resolution ("1080x1920" | "720x1280")
    video_resolution: Optional[str]

    # Image generator ("dalle" | "ideogram")
    image_generator: Optional[str]

    # Error tracking
    error: Optional[str]
