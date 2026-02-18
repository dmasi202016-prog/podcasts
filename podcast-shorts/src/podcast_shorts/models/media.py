"""Pydantic models for media assets."""

from pydantic import BaseModel


class AudioSegmentModel(BaseModel):
    scene_id: str
    audio_path: str
    duration: float


class ImageAssetModel(BaseModel):
    scene_id: str
    image_path: str
    prompt: str


class VideoClipModel(BaseModel):
    scene_id: str
    video_path: str
    duration: float


class MediaAssetsModel(BaseModel):
    audio_path: str
    audio_segments: list[AudioSegmentModel]
    images: list[ImageAssetModel]
    video_clips: list[VideoClipModel]
    voice_ids: dict[str, str]  # {"host": "...", "son": "...", "daughter": "..."}
