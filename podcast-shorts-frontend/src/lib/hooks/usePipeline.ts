"use client";

import { useCallback } from "react";
import { usePipelineContext } from "@/context/PipelineContext";
import { usePolling } from "./usePolling";
import * as api from "@/lib/api";

export function usePipeline() {
  const { state, dispatch } = usePipelineContext();
  const { startPolling, extendPolling } = usePolling();

  const startPipeline = useCallback(async (categories: string[]) => {
    try {
      dispatch({ type: "SET_CATEGORIES", categories });
      const res = await api.startPipeline("default_user", categories);
      dispatch({ type: "START_PIPELINE", runId: res.run_id });
      startPolling(res.run_id);
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [dispatch, startPolling]);

  const selectTopic = useCallback(async (topic: string) => {
    if (!state.runId) return;
    try {
      dispatch({ type: "SELECT_TOPIC", topic });
      dispatch({ type: "SET_LOADING", isLoading: true });
      await api.submitTopicSelection(state.runId, topic);
      startPolling(undefined, "waiting_for_topic_selection");
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [state.runId, dispatch, startPolling]);

  const selectSpeakers = useCallback(async (host: string, participants: string[]) => {
    if (!state.runId) return;
    try {
      dispatch({ type: "SET_HOST", host });
      dispatch({ type: "SET_PARTICIPANTS", participants });
      dispatch({ type: "SET_LOADING", isLoading: true });
      await api.submitSpeakerSelection(state.runId, host, participants);
      startPolling(undefined, "waiting_for_speaker_selection");
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [state.runId, dispatch, startPolling]);

  const submitReview = useCallback(async (approved: boolean, feedback?: string) => {
    if (!state.runId) return;
    try {
      dispatch({ type: "SET_LOADING", isLoading: true });
      await api.submitReview(state.runId, approved, feedback);
      startPolling(undefined, "waiting_for_review");
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [state.runId, dispatch, startPolling]);

  const selectAudio = useCallback(async (audioSource: "tts" | "manual", audioFiles?: Record<string, string>) => {
    if (!state.runId) return;
    try {
      dispatch({ type: "SET_AUDIO_SOURCE", audioSource });
      dispatch({ type: "SET_LOADING", isLoading: true });
      await api.submitAudioChoice(state.runId, audioSource, audioFiles);
      startPolling(undefined, "waiting_for_audio_choice");
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [state.runId, dispatch, startPolling]);

  const submitHookPrompt = useCallback(async (prompt: string) => {
    if (!state.runId) return;
    try {
      dispatch({ type: "SET_LOADING", isLoading: true });
      await api.submitHookPrompt(state.runId, prompt);
      startPolling(undefined, "waiting_for_hook_prompt");
    } catch (err) {
      dispatch({ type: "SET_ERROR", error: (err as Error).message });
    }
  }, [state.runId, dispatch, startPolling]);

  const goBack = useCallback(() => {
    const { step } = state;
    if (step <= 1) return;
    if (step === 2) {
      dispatch({ type: "RESET" });
    } else {
      dispatch({ type: "SET_STEP", step: (step - 1) as 1 | 2 | 3 | 4 | 5 | 6 | 7 });
    }
  }, [state, dispatch]);

  const reset = useCallback(() => {
    dispatch({ type: "RESET" });
  }, [dispatch]);

  const retryFromTimeout = useCallback(() => {
    dispatch({ type: "CLEAR_TIMEOUT_ERROR" });
    dispatch({ type: "RESET" });
    if (state.selectedCategories.length > 0) {
      startPipeline(state.selectedCategories);
    }
  }, [dispatch, state.selectedCategories, startPipeline]);

  const extendTimeout = useCallback(() => {
    extendPolling();
  }, [extendPolling]);

  const clearTimeoutError = useCallback(() => {
    dispatch({ type: "CLEAR_TIMEOUT_ERROR" });
  }, [dispatch]);

  const clearError = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
  }, [dispatch]);

  const retryFromError = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
    dispatch({ type: "RESET" });
  }, [dispatch]);

  return {
    state,
    startPipeline,
    selectTopic,
    selectSpeakers,
    submitReview,
    selectAudio,
    submitHookPrompt,
    goBack,
    reset,
    retryFromTimeout,
    extendTimeout,
    clearTimeoutError,
    clearError,
    retryFromError,
  };
}
