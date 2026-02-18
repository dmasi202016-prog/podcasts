"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # LLM API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Trend Research
    tavily_api_key: str = ""
    youtube_api_key: str = ""
    twitter_bearer_token: str = ""

    # Media Generation
    elevenlabs_api_key: str = ""
    luma_api_key: str = ""

    # ElevenLabs Voice IDs per family member
    voice_id_me: str = ""
    voice_id_wife: str = ""
    voice_id_jiho: str = ""
    voice_id_jihyung: str = ""
    voice_id_jiwon: str = ""
    voice_id_grandfa: str = ""
    voice_id_grandma: str = ""
    voice_id_unha: str = ""

    # LLM Model Configuration
    reasoning_model: str = "gpt-4o"
    creative_model: str = "claude-sonnet-4-5-20250929"

    # Pipeline Settings
    quality_threshold: float = 0.7
    max_retries: int = 2

    # Database
    database_url: str = "sqlite:///./podcast_shorts.db"

    # Output
    output_base_dir: str = "./output"

    # Video Output
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30


settings = Settings()
