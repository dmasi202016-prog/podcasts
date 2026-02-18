"""Pydantic models for final output."""

from pydantic import BaseModel


class VideoMetadataModel(BaseModel):
    title: str
    description: str
    tags: list[str]
    category: str


class EditorOutputModel(BaseModel):
    final_video_path: str
    caption_srt_path: str
    thumbnail_path: str
    metadata: VideoMetadataModel
    duration_sec: float
