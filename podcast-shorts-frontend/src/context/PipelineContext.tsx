"use client";

import React, { createContext, useContext, useReducer, type ReactNode } from "react";
import type {
  WizardStep,
  PipelineStatus,
  TopicSummary,
  FamilyMember,
  ScriptData,
  EditorOutput,
} from "@/lib/types";

interface PipelineState {
  step: WizardStep;
  runId: string | null;
  status: PipelineStatus;
  currentNode: string | null;
  error: string | null;
  timeoutError: string | null;
  isLoading: boolean;

  // Step 1
  selectedCategories: string[];

  // Step 2
  topics: TopicSummary[];
  selectedTopic: string | null;

  // Step 3
  host: string | null;
  participants: string[];

  // Step 4
  scriptData: ScriptData | null;

  // Step 5
  audioSource: "tts" | "manual" | null;

  // Step 6 (hook prompt)
  hookPrompt: string | null;

  // Step 7
  result: EditorOutput | null;
}

type PipelineAction =
  | { type: "SET_STEP"; step: WizardStep }
  | { type: "SET_CATEGORIES"; categories: string[] }
  | { type: "START_PIPELINE"; runId: string }
  | { type: "SET_STATUS"; status: PipelineStatus; currentNode?: string }
  | { type: "SET_LOADING"; isLoading: boolean }
  | { type: "SET_ERROR"; error: string }
  | { type: "SET_TIMEOUT_ERROR"; error: string }
  | { type: "CLEAR_TIMEOUT_ERROR" }
  | { type: "CLEAR_ERROR" }
  | { type: "SET_TOPICS"; topics: TopicSummary[] }
  | { type: "SELECT_TOPIC"; topic: string }
  | { type: "SET_HOST"; host: string }
  | { type: "SET_PARTICIPANTS"; participants: string[] }
  | { type: "SET_SCRIPT"; scriptData: ScriptData }
  | { type: "SET_AUDIO_SOURCE"; audioSource: "tts" | "manual" }
  | { type: "SET_HOOK_PROMPT"; prompt: string }
  | { type: "SET_RESULT"; result: EditorOutput }
  | { type: "RESET" };

const initialState: PipelineState = {
  step: 1,
  runId: null,
  status: "idle",
  currentNode: null,
  error: null,
  timeoutError: null,
  isLoading: false,
  selectedCategories: [],
  topics: [],
  selectedTopic: null,
  host: null,
  participants: [],
  scriptData: null,
  audioSource: null,
  hookPrompt: null,
  result: null,
};

function pipelineReducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step };
    case "SET_CATEGORIES":
      return { ...state, selectedCategories: action.categories };
    case "START_PIPELINE":
      return { ...state, runId: action.runId, status: "running", isLoading: true, error: null };
    case "SET_STATUS":
      return { ...state, status: action.status, currentNode: action.currentNode ?? state.currentNode };
    case "SET_LOADING":
      return { ...state, isLoading: action.isLoading };
    case "SET_ERROR":
      return { ...state, error: action.error, isLoading: false };
    case "SET_TIMEOUT_ERROR":
      return { ...state, timeoutError: action.error, isLoading: false };
    case "CLEAR_TIMEOUT_ERROR":
      return { ...state, timeoutError: null };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    case "SET_TOPICS":
      return { ...state, topics: action.topics, step: 2, isLoading: false };
    case "SELECT_TOPIC":
      return { ...state, selectedTopic: action.topic };
    case "SET_HOST":
      return { ...state, host: action.host };
    case "SET_PARTICIPANTS":
      return { ...state, participants: action.participants };
    case "SET_SCRIPT":
      return { ...state, scriptData: action.scriptData, step: 4, isLoading: false };
    case "SET_AUDIO_SOURCE":
      return { ...state, audioSource: action.audioSource };
    case "SET_HOOK_PROMPT":
      return { ...state, hookPrompt: action.prompt, step: 6, isLoading: false };
    case "SET_RESULT":
      return { ...state, result: action.result, step: 7, isLoading: false };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

interface PipelineContextType {
  state: PipelineState;
  dispatch: React.Dispatch<PipelineAction>;
}

const PipelineContext = createContext<PipelineContextType | null>(null);

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(pipelineReducer, initialState);

  return (
    <PipelineContext.Provider value={{ state, dispatch }}>
      {children}
    </PipelineContext.Provider>
  );
}

export function usePipelineContext() {
  const context = useContext(PipelineContext);
  if (!context) {
    throw new Error("usePipelineContext must be used within a PipelineProvider");
  }
  return context;
}
