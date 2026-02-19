"""Scriptwriter node — generates multi-speaker family podcast scripts."""

from __future__ import annotations

from pathlib import Path

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

from podcast_shorts.config import settings
from podcast_shorts.graph.state import PipelineState, QualityAssessment, ScriptData
from podcast_shorts.models.script import ScriptGenerationResult, ScriptQualityEvaluation
from podcast_shorts.nodes.speaker_selection import FAMILY_MEMBERS

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM_PROMPT_TEMPLATE = """\
당신은 한국 가족 팟캐스트 쇼츠 전문 작가입니다. 트렌딩 주제를 기반으로 1-3분 분량의 \
**{speaker_count}인 가족 대화형** 팟캐스트 대본을 작성합니다.

## 등장인물
{characters_section}

## 대화 흐름 규칙
1. **화자가 바뀔 때마다 반드시 새 장면(scene)으로 분리**하세요.
2. 기본 흐름: 사회자 설명 → 참여자 질문/반응 → 사회자 답변 → 참여자 감탄/추가 질문
3. 참여자의 질문과 반응이 자연스럽게 대화를 이끌어야 합니다.
4. 각 장면의 `speaker` 필드를 반드시 지정하세요 ({speaker_keys}).

## 대본 구조
1. 모든 대사는 한국어로 작성하세요.
2. 대화체(구어체)로 자연스럽게 — 실제 가족 대화처럼 작성하세요.
3. 다음 구조를 반드시 따르세요:
   - **Hook**: 사회자가 흥미롭고 강렬하게 주제를 꺼내며 시작 (5-10초, speaker: host)
   - **Body 파트 1 (아이스브레이킹)**: 이 주제가 왜 지금 이슈인지 쉽고 재미있게 설명. 사회자가 트렌드 배경을 풀어주고 참여자가 "아 그래?" 반응 (15-25초)
   - **Body 파트 2 (전문가 Q&A)**: 참여자가 전문 기자처럼 날카롭고 구체적인 질문을 던지고 사회자가 심층 분석으로 답변 (20-30초)
   - **Body 파트 3 (심화 Q&A)**: 참여자가 더 도발적이고 핵심을 찌르는 후속 질문, 사회자가 인사이트 있는 답변과 의미 해석 (15-25초)
   - **CTA**: 사회자가 마무리 + 참여자 인사 (5-10초)
4. 장면별 image_prompt는 반드시 영어로 작성하세요 (DALL-E 3 용도).
   - **반드시 세로 구도(portrait orientation)** 로 묘사하세요.
   - **스크립트의 주제(topic)를 프롬프트에 반드시 포함**하세요.
     예: 주제가 "AI 기술"이면 모든 이미지에 AI/기술 관련 시각 요소를 포함.
   - 스크립트 대사 내용과 직접적으로 관련된 장면을 묘사하세요.
5. 전체 분량: 60-180초 (1-3분).

## 장면 구성 (중요!)
- 화자가 바뀔 때마다 새 장면으로 분리합니다. 하나의 장면 = 한 명의 화자.
- Hook: 1개 장면 (scene_id: "hook", speaker: "host")
- Body 파트 1 (아이스브레이킹): 화자별 분리 (scene_id: "body_1_1", "body_1_2", ...)
- Body 파트 2 (기자 Q&A): 참여자 질문 → 사회자 답변 형식 (scene_id: "body_2_1", "body_2_2", ...) — 참여자 질문은 전문 기자처럼 날카롭고 구체적으로
- Body 파트 3 (심화 Q&A): 참여자 심화 질문 → 사회자 인사이트 답변 (scene_id: "body_3_1", "body_3_2", ...) — 더 도발적이고 핵심을 찌르는 질문
- CTA: 1-2개 장면 (scene_id: "cta" 또는 "cta_1", "cta_2")
- 각 장면마다 **서로 다른 image_prompt**를 생성하여 시각적으로 다양하게 만드세요.
- 전체 장면 수는 10-20개 정도가 적절합니다.

## 화자 분배 가이드
{speaker_distribution}"""


def _build_system_prompt(selected_speakers: dict | None) -> tuple[str, dict[str, str]]:
    """Build dynamic system prompt and speaker_label mapping based on selected speakers.

    Returns (system_prompt, speaker_label) where speaker_label maps
    speaker keys like "host", "participant_1" to display names.
    """
    if not selected_speakers:
        # Fallback: default 3-person family (아빠, 아들, 딸)
        speaker_label = {"host": "아빠", "son": "아들", "daughter": "딸"}
        return SCRIPT_SYSTEM_PROMPT_TEMPLATE.format(
            speaker_count=3,
            characters_section=(
                '- **host** (아빠/진행자): 주제를 설명하고 대화를 이끄는 역할. 친근하고 쉬운 말투.\n'
                '- **son** (아들): 호기심 많은 초등학생. "아빠 그게 뭐야?", "진짜?" 등 질문을 던짐.\n'
                '- **daughter** (딸): 똑똑하고 재치있는 초등학생. 자기 생각을 덧붙이거나 재미있는 반응을 보임.'
            ),
            speaker_keys='"host", "son", "daughter"',
            speaker_distribution=(
                "- host(아빠): 전체의 50-60%\n"
                "- son(아들): 전체의 20-25%\n"
                "- daughter(딸): 전체의 20-25%"
            ),
        ), speaker_label

    host_key = selected_speakers.get("host", "me")
    participants = selected_speakers.get("participants", [])
    host_info = FAMILY_MEMBERS.get(host_key, {"name": "나", "description": "진행자"})

    # Build characters section
    characters = [
        f'- **host** ({host_info["name"]}/사회자): 주제를 설명하고 대화를 이끄는 역할. {host_info["description"]}.'
    ]
    speaker_label = {"host": host_info["name"]}
    speaker_keys = ['"host"']

    for i, p_key in enumerate(participants, 1):
        p_info = FAMILY_MEMBERS.get(p_key, {"name": p_key, "description": ""})
        role_key = f"participant_{i}"
        characters.append(
            f'- **{role_key}** ({p_info["name"]}): {p_info["description"]}. 자연스럽게 대화에 참여.'
        )
        speaker_label[role_key] = p_info["name"]
        speaker_keys.append(f'"{role_key}"')

    total_speakers = 1 + len(participants)
    host_pct = "50-60%" if total_speakers <= 3 else "40-50%"
    participant_pct = f"{max(10, (100 - 55) // len(participants))}-{max(15, (100 - 45) // len(participants))}%" if participants else "0%"

    distribution_lines = [f"- host({host_info['name']}): 전체의 {host_pct}"]
    for i, p_key in enumerate(participants, 1):
        p_info = FAMILY_MEMBERS.get(p_key, {"name": p_key})
        distribution_lines.append(f"- participant_{i}({p_info['name']}): 전체의 {participant_pct}")

    prompt = SCRIPT_SYSTEM_PROMPT_TEMPLATE.format(
        speaker_count=total_speakers,
        characters_section="\n".join(characters),
        speaker_keys=", ".join(speaker_keys),
        speaker_distribution="\n".join(distribution_lines),
    )

    return prompt, speaker_label

SCRIPT_USER_PROMPT = """\
아래 트렌딩 주제에 대한 **가족 팟캐스트 쇼츠** 대본을 작성해 주세요.

## 주제 정보
- 선정 주제: {selected_topic}
- 카테고리: {category}
- 트렌드 요약:
{topic_summaries}

## 최신 뉴스 (Tavily 검색 결과)
{latest_news}

## 사용자 페르소나 (진행자)
{persona_info}

## 이미지 프롬프트 가이드
- 주제 "{selected_topic}"를 모든 image_prompt에 시각적 요소로 포함하세요.
- 세로 구도(portrait, vertical composition)로 묘사하세요.

## 대본 작성 지침
- Body 1(아이스브레이킹): 위 최신 뉴스를 바탕으로 "왜 지금 이슈인지"를 쉽고 재미있게 설명하세요.
- Body 2(전문가 Q&A): 참여자가 전문 기자처럼 구체적이고 날카로운 질문 → 사회자 심층 분석 답변. 최신 데이터나 사실을 활용하세요.
- Body 3(심화 Q&A): 더 도발적이고 핵심을 찌르는 심화 질문 → 인사이트 있는 답변과 의미 해석.

위 정보를 바탕으로 Hook → Body(3파트) → CTA 구조의 가족 대화형 대본을 작성해 주세요.
각 장면에 반드시 speaker 필드를 포함하세요."""

SCRIPT_REVISION_PROMPT = """\
아래 트렌딩 주제에 대한 **가족 팟캐스트 쇼츠** 대본을 **수정**해 주세요.

## 주제 정보
- 선정 주제: {selected_topic}
- 카테고리: {category}
- 주제 요약:
{topic_summaries}

## 사용자 페르소나 (아빠/진행자)
{persona_info}

## 이미지 프롬프트 가이드
- 주제 "{selected_topic}"를 모든 image_prompt에 시각적 요소로 포함하세요.
- 세로 구도(portrait, vertical composition)로 묘사하세요.

## 수정 요청 사항
{human_feedback}

위 수정 요청을 반영하여 Hook → Body(3파트) → CTA 구조의 가족 대화형 대본을 다시 작성해 주세요.
각 장면에 반드시 speaker 필드를 포함하세요."""

QUALITY_SYSTEM_PROMPT = """\
당신은 가족 팟캐스트 쇼츠 파이프라인의 품질 평가자입니다. 작성된 스크립트를 평가하여 \
다음 단계(미디어 생성)로 넘어가기에 충분한 품질인지 판단해야 합니다.

**중요: feedback을 반드시 한국어로 작성하세요.**

평가 기준:
- Hook이 시청자의 관심을 효과적으로 끌 수 있는가
- 본문 3파트가 논리적으로 구성되어 있는가
- CTA가 자연스럽게 마무리되는가
- 전체적으로 대화체(구어체)가 유지되는가
- 1-3분 분량에 적합한 길이인가
- 장면별 image_prompt가 영어로 적절하게 작성되어 있는가
- **화자 분배가 균형적인가**: 사회자가 전체의 40-60%, 참여자들이 나머지를 고르게 분배
- **화자 교체 시 자연스러운 대화 흐름**이 유지되는가 (사회자 설명 → 참여자 질문 → 사회자 답변)
- 각 장면에 speaker 필드가 올바르게 지정되어 있는가"""

QUALITY_USER_PROMPT = """\
다음 팟캐스트 쇼츠 스크립트의 품질을 평가해 주세요.

제목: {title}
예상 시간: {duration}초

## Hook
{hook}

## Body
{body}

## CTA
{cta}

## 장면별 이미지 프롬프트
{image_prompts}"""


# ---------------------------------------------------------------------------
# Node implementation
# ---------------------------------------------------------------------------


async def scriptwriter(state: PipelineState) -> dict:
    """Generate a Hook → 3-part Body → CTA structured script with per-scene
    image prompts, using user persona (speech patterns, filler words).
    """
    logger.info("scriptwriter.start", run_id=state.get("run_id"))

    retry_counts = state.get("retry_counts", {})
    attempt = retry_counts.get("scriptwriter", 0) + 1
    human_feedback = state.get("human_feedback")

    try:
        # ── Step 1: Prepare inputs ───────────────────────────────────────
        trend_data = state.get("trend_data") or {}
        selected_topic = trend_data.get("selected_topic", "")
        category = trend_data.get("category", "")
        topic_summaries_raw = trend_data.get("topic_summaries", [])

        topic_summaries_text = "\n".join(
            f"- {ts.get('keyword', '')}: {ts.get('summary', '')}"
            for ts in topic_summaries_raw
        ) or "(요약 정보 없음)"

        user_prefs = state.get("user_preferences", {})
        persona_parts = []
        if user_prefs.get("name"):
            persona_parts.append(f"- 이름/채널명: {user_prefs['name']}")
        if user_prefs.get("speech_style"):
            persona_parts.append(f"- 말투 스타일: {user_prefs['speech_style']}")
        if user_prefs.get("filler_words"):
            fillers = ", ".join(user_prefs["filler_words"])
            persona_parts.append(f"- 자주 사용하는 필러워드: {fillers}")
        if user_prefs.get("tone"):
            persona_parts.append(f"- 톤: {user_prefs['tone']}")
        if user_prefs.get("target_audience"):
            persona_parts.append(f"- 타겟 시청자: {user_prefs['target_audience']}")

        persona_info = "\n".join(persona_parts) if persona_parts else "(페르소나 정보 없음 — 일반적인 친근한 말투로 작성)"

        # ── Step 1b: Tavily latest news search ───────────────────────
        latest_news_text = ""
        if settings.tavily_api_key:
            try:
                tavily = TavilyClient(api_key=settings.tavily_api_key)
                search_results = tavily.search(
                    query=f"{selected_topic} 최신 뉴스 이슈",
                    search_depth="advanced",
                    max_results=5,
                    include_answer=True,
                )
                news_items = []
                if search_results.get("answer"):
                    news_items.append(f"요약: {search_results['answer']}")
                for r in search_results.get("results", [])[:4]:
                    content = r.get("content", "")[:300]
                    news_items.append(f"- {r.get('title', '')}: {content}")
                latest_news_text = "\n".join(news_items)
                logger.info("scriptwriter.tavily_search_done", results=len(search_results.get("results", [])))
            except Exception:
                logger.warning("scriptwriter.tavily_search_failed")

        # ── Step 1c: Build dynamic speaker prompt ─────────────────────
        selected_speakers = state.get("selected_speakers")
        system_prompt, speaker_label = _build_system_prompt(selected_speakers)

        logger.info(
            "scriptwriter.input_prepared",
            topic=selected_topic,
            has_feedback=human_feedback is not None,
            speakers=selected_speakers,
        )

        # ── Step 2: Generate script with Claude Sonnet ───────────────────
        creative_llm = ChatAnthropic(
            model=settings.creative_model,
            api_key=settings.anthropic_api_key,
            temperature=0.7,
            max_tokens=4096,
        )

        script_llm = creative_llm.with_structured_output(ScriptGenerationResult)

        if human_feedback:
            user_content = SCRIPT_REVISION_PROMPT.format(
                selected_topic=selected_topic,
                category=category,
                topic_summaries=topic_summaries_text,
                persona_info=persona_info,
                human_feedback=human_feedback,
            )
            logger.info("scriptwriter.revision", feedback=human_feedback)
        else:
            user_content = SCRIPT_USER_PROMPT.format(
                selected_topic=selected_topic,
                category=category,
                topic_summaries=topic_summaries_text,
                latest_news=latest_news_text or "(최신 뉴스 검색 결과 없음)",
                persona_info=persona_info,
            )

        result: ScriptGenerationResult = await script_llm.ainvoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        )

        logger.info(
            "scriptwriter.script_generated",
            title=result.title,
            scene_count=len(result.scenes),
            duration=result.estimated_duration_sec,
        )

        # ── Step 3: Convert to ScriptData TypedDict ──────────────────────
        full_script = " ".join(
            [result.hook_text]
            + [bp.text for bp in result.body_parts]
            + [result.cta_text]
        )

        # speaker_label already built dynamically by _build_system_prompt

        script_data: ScriptData = {
            "title": result.title,
            "full_script": full_script,
            "scenes": [
                {
                    "scene_id": scene.scene_id,
                    "text": scene.text,
                    "duration": scene.duration,
                    "emotion": scene.emotion,
                    "image_prompt": scene.image_prompt,
                    "speaker": scene.speaker,
                }
                for scene in result.scenes
            ],
            "hook": result.hook_text,
            "cta": result.cta_text,
            "estimated_duration_sec": result.estimated_duration_sec,
        }

        # ── Step 3b: Export script to readable text file ──────────────
        run_id = state.get("run_id", "default")
        script_dir = Path(settings.output_base_dir) / run_id
        script_dir.mkdir(parents=True, exist_ok=True)
        script_file_path = str(script_dir / "script.txt")

        lines = [f"# {result.title}", f"# 예상 시간: {result.estimated_duration_sec}초", ""]
        for scene in result.scenes:
            label = speaker_label.get(scene.speaker, scene.speaker)
            lines.append(f"[{scene.scene_id}] ({label}) {scene.text}")
        lines.append("")

        Path(script_file_path).write_text("\n".join(lines), encoding="utf-8")
        logger.info("scriptwriter.script_file_exported", path=script_file_path)

        # ── Step 4: Self quality evaluation ──────────────────────────────
        reasoning_llm = ChatOpenAI(
            model=settings.reasoning_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )

        quality_llm = reasoning_llm.with_structured_output(ScriptQualityEvaluation)

        body_text = "\n".join(
            f"파트 {i+1} [{bp.emotion}]: {bp.text}\n  핵심: {bp.key_point}"
            for i, bp in enumerate(result.body_parts)
        )

        image_prompts_text = "\n".join(
            f"- {scene.scene_id}: {scene.image_prompt}"
            for scene in result.scenes
        )

        quality_eval: ScriptQualityEvaluation = await quality_llm.ainvoke(
            [
                {"role": "system", "content": QUALITY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": QUALITY_USER_PROMPT.format(
                        title=result.title,
                        duration=result.estimated_duration_sec,
                        hook=result.hook_text,
                        body=body_text,
                        cta=result.cta_text,
                        image_prompts=image_prompts_text,
                    ),
                },
            ]
        )

        passed = quality_eval.score >= settings.quality_threshold

        quality: QualityAssessment = {
            "node_name": "scriptwriter",
            "passed": passed,
            "score": quality_eval.score,
            "feedback": quality_eval.feedback,
            "attempt": attempt,
        }

        logger.info(
            "scriptwriter.done",
            title=script_data["title"],
            quality_score=quality_eval.score,
            passed=passed,
            attempt=attempt,
        )

    except Exception:
        logger.exception("scriptwriter.error", attempt=attempt)
        script_data = {
            "title": "",
            "full_script": "",
            "scenes": [],
            "hook": "",
            "cta": "",
            "estimated_duration_sec": 0.0,
        }
        quality = {
            "node_name": "scriptwriter",
            "passed": False,
            "score": 0.0,
            "feedback": "Script generation failed due to an error. Will retry.",
            "attempt": attempt,
        }
        script_file_path = None

    retry_counts = {**retry_counts, "scriptwriter": attempt}

    return {
        "script_data": script_data,
        "quality": quality,
        "retry_counts": retry_counts,
        "human_approved": None,
        "human_feedback": None,
        "script_file_path": script_file_path,
    }
