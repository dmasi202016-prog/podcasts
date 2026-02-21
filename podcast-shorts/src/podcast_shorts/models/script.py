"""Pydantic models for script data."""

from pydantic import BaseModel, Field


class SceneModel(BaseModel):
    scene_id: str
    text: str
    duration: float = Field(gt=0)
    emotion: str
    image_prompt: str
    speaker: str = Field(default="host", description="화자 (host, son, daughter)")


class ScriptDataModel(BaseModel):
    title: str
    full_script: str
    scenes: list[SceneModel]
    hook: str
    cta: str
    estimated_duration_sec: float = Field(gt=0)


# ---------------------------------------------------------------------------
# LLM Structured Output models (used by scriptwriter node)
# ---------------------------------------------------------------------------


class BodyPart(BaseModel):
    """본문 3파트 중 하나의 세부 내용."""

    text: str = Field(description="이 파트의 대사 텍스트")
    key_point: str = Field(description="이 파트에서 전달하려는 핵심 포인트 (1문장)")
    emotion: str = Field(description="이 파트의 감정 톤 (예: informative, curious, excited, thoughtful)")


class SceneOutput(BaseModel):
    """장면별 출력 — LLM이 생성하는 개별 장면 정보."""

    scene_id: str = Field(description="장면 식별자 (예: hook, body_1, body_2, body_3, cta)")
    text: str = Field(description="이 장면의 대사 텍스트")
    duration: float = Field(gt=0, description="이 장면의 예상 소요 시간 (초)")
    emotion: str = Field(description="이 장면의 감정 톤")
    image_prompt: str = Field(
        description="이 장면에 사용할 배경 이미지 생성 프롬프트 (영어, DALL-E 3용)"
    )
    speaker: str = Field(
        description="이 장면의 화자 (host=아빠/진행자, son=아들, daughter=딸)"
    )


class ScriptGenerationResult(BaseModel):
    """Claude가 반환하는 전체 스크립트 생성 결과."""

    title: str = Field(description="영상 제목 (한국어, 흥미를 끄는 제목)")
    hook_text: str = Field(description="오프닝 훅 대사 — 시청자를 사로잡는 첫 마디")
    body_parts: list[BodyPart] = Field(
        description="본문 3개 파트 리스트 (반드시 3개)", min_length=3, max_length=3
    )
    cta_text: str = Field(description="클로징 CTA 대사 — 구독/좋아요 유도")
    scenes: list[SceneOutput] = Field(
        description="장면별 상세 정보 리스트. 본문의 각 문장마다 별도 장면을 생성합니다. "
        "hook 1개 + body 문장별 N개 + cta 1개. scene_id는 hook, body_1_1, body_1_2, body_2_1, ... , cta 형식.",
        min_length=5,
        max_length=30,
    )
    trend_banner_text: str = Field(
        description="상단 트렌드 배너에 표시될 한 문장 (한국어, 25자 이내, 핵심 궁금증 유발 — 예: '이걸 모르면 손해본다?')"
    )
    estimated_duration_sec: float = Field(
        gt=0, description="전체 스크립트 예상 소요 시간 (초, 60~180초 권장)"
    )


class ConversationTurn(BaseModel):
    """대화 턴 — 화자별 발화 단위."""

    speaker: str = Field(description="화자 (host, son, daughter)")
    text: str = Field(description="발화 텍스트")
    emotion: str = Field(description="감정 톤")


class ScriptQualityEvaluation(BaseModel):
    """스크립트 품질 자체 평가 결과."""

    score: float = Field(ge=0.0, le=1.0, description="전체 품질 점수 (0.0~1.0)")
    has_hook: bool = Field(description="효과적인 오프닝 훅이 있는가")
    has_three_body_parts: bool = Field(description="본문이 3개 파트로 구성되어 있는가")
    has_cta: bool = Field(description="클로징 CTA가 있는가")
    is_conversational: bool = Field(description="대화체로 작성되어 자연스러운가")
    duration_appropriate: bool = Field(description="1~3분 분량에 적합한 길이인가")
    has_multi_speaker_balance: bool = Field(
        description="host/son/daughter 화자 분배가 균형적인가 (host 50-60%, 아이들 각 20-25%)"
    )
    feedback: str = Field(description="품질 개선을 위한 구체적 피드백")
