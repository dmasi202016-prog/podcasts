"""StateGraph definition — assembles nodes, edges, and conditional routing."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from podcast_shorts.graph.edges import (
    route_after_editor,
    route_after_media,
    route_after_review,
    route_after_script,
    route_after_trend,
)
from podcast_shorts.graph.state import PipelineState
from podcast_shorts.nodes.audio_choice import audio_choice_gate
from podcast_shorts.nodes.auto_editor import auto_editor
from podcast_shorts.nodes.hook_prompt import hook_prompt_gate
from podcast_shorts.nodes.human_review import human_review_gate
from podcast_shorts.nodes.media_producer import media_producer
from podcast_shorts.nodes.scriptwriter import scriptwriter
from podcast_shorts.nodes.speaker_selection import speaker_selection_gate
from podcast_shorts.nodes.topic_selection import topic_selection_gate
from podcast_shorts.nodes.trend_researcher import trend_researcher


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Build and compile the podcast shorts pipeline graph.

    Args:
        checkpointer: Optional checkpoint saver for persistence and resume.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("trend_researcher", trend_researcher)
    graph.add_node("topic_selection_gate", topic_selection_gate)
    graph.add_node("speaker_selection_gate", speaker_selection_gate)
    graph.add_node("scriptwriter", scriptwriter)
    graph.add_node("human_review_gate", human_review_gate)
    graph.add_node("audio_choice_gate", audio_choice_gate)
    graph.add_node("media_producer", media_producer)
    graph.add_node("hook_prompt_gate", hook_prompt_gate)
    graph.add_node("auto_editor", auto_editor)

    # Entry point
    graph.set_entry_point("trend_researcher")

    # Conditional edges with quality-based routing
    graph.add_conditional_edges(
        "trend_researcher",
        route_after_trend,
        {
            "topic_selection_gate": "topic_selection_gate",
            "trend_researcher": "trend_researcher",
            END: END,
        },
    )

    # topic_selection_gate → speaker_selection_gate → scriptwriter
    graph.add_edge("topic_selection_gate", "speaker_selection_gate")
    graph.add_edge("speaker_selection_gate", "scriptwriter")

    graph.add_conditional_edges(
        "scriptwriter",
        route_after_script,
        {
            "human_review_gate": "human_review_gate",
            "scriptwriter": "scriptwriter",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "human_review_gate",
        route_after_review,
        {
            "audio_choice_gate": "audio_choice_gate",
            "scriptwriter": "scriptwriter",
        },
    )

    # audio_choice_gate always proceeds to media_producer
    graph.add_edge("audio_choice_gate", "media_producer")

    graph.add_conditional_edges(
        "media_producer",
        route_after_media,
        {
            "hook_prompt_gate": "hook_prompt_gate",
            "media_producer": "media_producer",
            END: END,
        },
    )

    # hook_prompt_gate always proceeds to auto_editor
    graph.add_edge("hook_prompt_gate", "auto_editor")

    graph.add_conditional_edges(
        "auto_editor",
        route_after_editor,
        {
            "auto_editor": "auto_editor",
            END: END,
        },
    )

    return graph.compile(checkpointer=checkpointer)
