"use client";

import { useEffect, useRef, useCallback } from "react";
import { usePipelineContext } from "@/context/PipelineContext";
import * as api from "@/lib/api";
import { POLLING_INTERVAL, POLLING_TIMEOUT_MS } from "@/lib/constants";
import type { PipelineStatus } from "@/lib/types";

const NODE_LABELS: Record<string, string> = {
  trend_researcher: "트렌드 분석",
  scriptwriter: "대본 생성",
  media_producer: "오디오/이미지 생성",
  hook_prompt_gate: "Hook 영상 프롬프트",
  auto_editor: "영상 편집",
};

export function usePolling() {
  const { state, dispatch } = usePipelineContext();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isPollingRef = useRef(false);
  const startTimeRef = useRef<number>(0);
  const runIdRef = useRef<string | null>(null);
  const skipStatusRef = useRef<PipelineStatus | null>(null);
  const lastNodeRef = useRef<string | null>(null);

  // Keep ref in sync with context state
  useEffect(() => {
    if (state.runId) {
      runIdRef.current = state.runId;
    }
  }, [state.runId]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    isPollingRef.current = false;
    skipStatusRef.current = null;
  }, []);

  const scheduleTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    startTimeRef.current = Date.now();
    timeoutRef.current = setTimeout(() => {
      const nodeName = lastNodeRef.current;
      const label = nodeName ? NODE_LABELS[nodeName] ?? nodeName : "작업";
      stopPolling();
      dispatch({
        type: "SET_TIMEOUT_ERROR",
        error: `'${label}' 단계에서 10분이 지났지만 결과를 받지 못했습니다. 서버가 아직 처리 중일 수 있습니다.`,
      });
    }, POLLING_TIMEOUT_MS);
  }, [stopPolling, dispatch]);

  const poll = useCallback(async () => {
    const runId = runIdRef.current;
    if (!runId) return;

    try {
      const statusRes = await api.getStatus(runId);

      // Track current node for timeout message
      if (statusRes.current_node) {
        lastNodeRef.current = statusRes.current_node;
      }

      // Skip status we've already handled (e.g. just submitted topic selection
      // but backend hasn't processed the resume yet)
      if (skipStatusRef.current && statusRes.status === skipStatusRef.current) {
        return; // continue polling, don't react
      }
      // Once we see a different status, clear the skip
      skipStatusRef.current = null;

      dispatch({ type: "SET_STATUS", status: statusRes.status as PipelineStatus, currentNode: statusRes.current_node ?? undefined });

      if (statusRes.status === "waiting_for_topic_selection") {
        stopPolling();
        try {
          const topicsRes = await api.getTopics(runId);
          dispatch({ type: "SET_TOPICS", topics: topicsRes.topics ?? [] });
        } catch (topicsErr) {
          console.error("getTopics failed:", topicsErr);
          dispatch({ type: "SET_ERROR", error: (topicsErr as Error).message });
        }
      } else if (statusRes.status === "waiting_for_speaker_selection") {
        stopPolling();
        dispatch({ type: "SET_STEP", step: 3 });
        dispatch({ type: "SET_LOADING", isLoading: false });
      } else if (statusRes.status === "waiting_for_review") {
        stopPolling();
        const scriptRes = await api.getScript(runId);
        if (scriptRes.script_data) {
          dispatch({ type: "SET_SCRIPT", scriptData: scriptRes.script_data });
        }
      } else if (statusRes.status === "waiting_for_audio_choice") {
        stopPolling();
        dispatch({ type: "SET_STEP", step: 5 });
        dispatch({ type: "SET_LOADING", isLoading: false });
      } else if (statusRes.status === "waiting_for_hook_prompt") {
        stopPolling();
        try {
          const hookRes = await api.getHookPrompt(runId);
          dispatch({ type: "SET_HOOK_PROMPT", prompt: hookRes.prompt ?? "" });
        } catch (hookErr) {
          console.error("getHookPrompt failed:", hookErr);
          dispatch({ type: "SET_ERROR", error: (hookErr as Error).message });
        }
      } else if (statusRes.status === "completed") {
        stopPolling();
        const resultRes = await api.getResult(runId);
        if (resultRes.result) {
          dispatch({ type: "SET_RESULT", result: resultRes.result });
        }
      } else if (statusRes.status === "failed") {
        stopPolling();
        dispatch({ type: "SET_ERROR", error: statusRes.error ?? "파이프라인 실행 실패" });
      }
    } catch (err) {
      console.error("Polling error:", err);
      stopPolling();
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [dispatch, stopPolling]);

  const startPolling = useCallback((runId?: string, skipStatus?: PipelineStatus) => {
    // Allow passing runId directly to avoid stale closure
    if (runId) {
      runIdRef.current = runId;
    }
    // Skip a status we've already handled (avoid race condition after gate submission)
    if (skipStatus) {
      skipStatusRef.current = skipStatus;
    }
    if (isPollingRef.current) return;
    isPollingRef.current = true;
    dispatch({ type: "SET_LOADING", isLoading: true });

    poll();
    intervalRef.current = setInterval(poll, POLLING_INTERVAL);
    scheduleTimeout();
  }, [poll, dispatch, scheduleTimeout]);

  const extendPolling = useCallback(() => {
    dispatch({ type: "CLEAR_TIMEOUT_ERROR" });
    dispatch({ type: "SET_LOADING", isLoading: true });

    if (!isPollingRef.current) {
      // Restart polling if it was stopped by timeout
      isPollingRef.current = true;
      poll();
      intervalRef.current = setInterval(poll, POLLING_INTERVAL);
    }
    scheduleTimeout();
  }, [poll, dispatch, scheduleTimeout]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return { startPolling, stopPolling, extendPolling };
}
