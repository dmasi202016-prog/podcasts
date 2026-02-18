# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered podcast shorts platform that automatically generates 1-3 minute podcast-style shorts from trending topics, using a user's cloned voice. Full automation from trend detection to final video output.

## Architecture (from Product_Requirement.md)

Multi-agent workflow built on **LangChain/LangGraph**, with four pipeline stages modeled as LangGraph nodes. If output quality is insufficient, the graph loops back to a previous node.

### Pipeline Stages (LangGraph Nodes)
1. **Trend Researcher** — pulls from Google Trends, YouTube trending, X/Twitter APIs; extracts keywords and analyzes *why* they're trending; filters by user interest categories
2. **Scriptwriter** — generates 1-3 min conversational scripts (hook → 3-part body → CTA closing); injects user persona (speech patterns, filler words); auto-extracts image-generation prompts per scene
3. **Voice & Media Producer** — ElevenLabs voice cloning + emotion-aware tone; DALL-E 3 / Midjourney for images; Luma/Runway for short background videos
4. **Auto-Editor** — MoviePy + FFmpeg for audio-video compositing; Whisper for auto-captioning; BGM mixing and SFX

### Cross-cutting Concerns
- **Memory**: `ReadOnlySharedMemory` shares context (user preferences, past video style) across all agents
- **Tool Calling**: agents dynamically invoke external APIs (Tavily search, image gen, etc.)
- **Human-in-the-loop**: script confirmation gate before expensive media API calls

## Tech Stack

- **Orchestration**: LangChain, LangGraph
- **LLMs**: GPT-4o (reasoning), Claude 3.5 Sonnet (creative writing)
- **Audio**: ElevenLabs API, Whisper API
- **Video/Image**: Luma Dream Machine API, DALL-E 3
- **Backend**: Python, FastAPI
- **Video Processing**: MoviePy, FFmpeg

## Data Flow

```
User input (keywords or auto-trend)
  → LLM pipeline: trend analysis → script → image prompts
  → External APIs: voice (.mp3) → images (.png) → video clips (.mp4)
  → MoviePy compositing: final rendered shorts + metadata (title, tags)
```

Target: full pipeline completes within 10 minutes.

## Language

Product requirements and user-facing content are in Korean. Code and technical docs should use English.
