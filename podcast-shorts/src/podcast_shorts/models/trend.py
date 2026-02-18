"""Pydantic models for trend data."""

from pydantic import BaseModel, Field


class TopicSummaryModel(BaseModel):
    keyword: str
    summary: str
    source: str
    trending_score: float = Field(ge=0.0, le=1.0)


class TrendDataModel(BaseModel):
    keywords: list[str]
    topic_summaries: list[TopicSummaryModel]
    selected_topic: str
    category: str


# ---------------------------------------------------------------------------
# LLM Structured Output models (used by trend_researcher node)
# ---------------------------------------------------------------------------


class TrendKeywordAnalysis(BaseModel):
    """단일 트렌드 키워드 분석 결과."""

    keyword: str = Field(description="트렌딩 키워드 또는 주제")
    why_trending: str = Field(description="이 키워드가 현재 트렌딩인 이유 (2-3문장)")
    category: str = Field(description="카테고리 (예: 기술, 엔터테인먼트, 사회, 경제, 스포츠, 정치, 문화)")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="팟캐스트 쇼츠 주제로서의 적합도 점수 (0.0~1.0)"
    )
    summary: str = Field(description="이 트렌드에 대한 간결한 요약 (1-2문장)")
    source: str = Field(description="트렌드 출처 (tavily, google_trends 등)")


class TrendAnalysisResult(BaseModel):
    """GPT-4o가 반환하는 전체 트렌드 분석 결과."""

    analyses: list[TrendKeywordAnalysis] = Field(
        description="각 키워드에 대한 상세 분석 리스트"
    )
    recommended_topic: str = Field(description="팟캐스트 쇼츠에 가장 적합한 추천 주제")
    recommended_category: str = Field(description="추천 주제의 카테고리")
    reasoning: str = Field(description="이 주제를 추천하는 이유 (2-3문장)")


class QualityEvaluation(BaseModel):
    """트렌드 분석 결과의 자체 품질 평가."""

    score: float = Field(ge=0.0, le=1.0, description="전체 품질 점수 (0.0~1.0)")
    is_topic_relevant: bool = Field(description="추천 주제가 사용자 관심사와 관련이 있는가")
    is_analysis_thorough: bool = Field(description="분석이 충분히 깊이 있는가")
    has_enough_context: bool = Field(description="스크립트 작성에 충분한 맥락 정보가 있는가")
    feedback: str = Field(description="품질 개선을 위한 구체적 피드백")
