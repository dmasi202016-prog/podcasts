"""Speaker Selection Gate — pauses pipeline for user to select family member speakers."""

from __future__ import annotations

import structlog
from langgraph.types import interrupt

from podcast_shorts.graph.state import PipelineState

logger = structlog.get_logger()

FAMILY_MEMBERS = {
    "me": {"name": "나", "description": "아빠/진행자"},
    "grandma": {"name": "할머니", "description": "따뜻하고 지혜로운 할머니"},
    "grandfa": {"name": "할아버지", "description": "유머있고 경험 많은 할아버지"},
    "jiho": {"name": "지호", "description": "호기심 많은 아이"},
    "jihyung": {"name": "지형", "description": "똑똑하고 재치있는 아이"},
    "jiwon": {"name": "지원", "description": "활발하고 밝은 아이"},
    "wife": {"name": "아내", "description": "다정하고 센스있는 아내"},
    "unha": {"name": "은하", "description": "밝고 활발한 아이"},
}


async def speaker_selection_gate(state: PipelineState) -> dict:
    """Interrupt the pipeline and present family members for speaker selection.

    The user selects one host and one or more participants.

    On resume, the Command(resume=...) payload provides:
      {"host": "me", "participants": ["jiho", "jiwon"]}
    """
    logger.info("speaker_selection_gate.waiting", run_id=state.get("run_id"))

    # Present family members with photo URLs
    members_info = [
        {
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "photo_url": f"/files/assets/pic/{key}.jpeg",
        }
        for key, info in FAMILY_MEMBERS.items()
    ]

    selection_result = interrupt(
        {
            "type": "speaker_selection",
            "members": members_info,
            "message": "출연자를 선택해주세요. 사회자 1명과 참여자를 선택하세요.",
        }
    )

    host = selection_result.get("host", "me")
    participants = selection_result.get("participants", [])

    logger.info(
        "speaker_selection_gate.result",
        host=host,
        participants=participants,
    )

    selected_speakers = {"host": host, "participants": participants}

    return {
        "selected_speakers": selected_speakers,
        "speaker_selection_approved": True,
    }
