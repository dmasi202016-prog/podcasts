import { API_BASE, FILES_BASE } from "./constants";
import type {
  PipelineStartResponse,
  PipelineStatusResponse,
  TopicSelectionResponse,
  SpeakerSelectionResponse,
  ScriptReviewResponse,
  HookPromptResponse,
  PipelineResultResponse,
} from "./types";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function startPipeline(
  userId: string,
  categories: string[],
  resolution: string = "720x1280",
  imageGenerator: string = "dalle",
  hookMode: string = "video",
  keywords: string[] = [],
): Promise<PipelineStartResponse> {
  return fetchJSON<PipelineStartResponse>(`${API_BASE}/start`, {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      keywords,
      user_preferences: { interest_categories: categories },
      resolution,
      image_generator: imageGenerator,
      hook_mode: hookMode,
    }),
  });
}

export async function getStatus(runId: string): Promise<PipelineStatusResponse> {
  return fetchJSON<PipelineStatusResponse>(`${API_BASE}/${runId}/status`);
}

export async function getTopics(runId: string): Promise<TopicSelectionResponse> {
  return fetchJSON<TopicSelectionResponse>(`${API_BASE}/${runId}/topics`);
}

export async function submitTopicSelection(
  runId: string,
  selectedTopic: string,
): Promise<TopicSelectionResponse> {
  return fetchJSON<TopicSelectionResponse>(`${API_BASE}/${runId}/topic-selection`, {
    method: "POST",
    body: JSON.stringify({ selected_topic: selectedTopic }),
  });
}

export async function getSpeakers(runId: string): Promise<SpeakerSelectionResponse> {
  return fetchJSON<SpeakerSelectionResponse>(`${API_BASE}/${runId}/speakers`);
}

export async function submitSpeakerSelection(
  runId: string,
  host: string,
  participants: string[],
): Promise<SpeakerSelectionResponse> {
  return fetchJSON<SpeakerSelectionResponse>(`${API_BASE}/${runId}/speaker-selection`, {
    method: "POST",
    body: JSON.stringify({ host, participants }),
  });
}

export async function getScript(runId: string): Promise<ScriptReviewResponse> {
  return fetchJSON<ScriptReviewResponse>(`${API_BASE}/${runId}/script`);
}

export async function submitReview(
  runId: string,
  approved: boolean,
  feedback?: string,
): Promise<{ run_id: string; status: string }> {
  return fetchJSON(`${API_BASE}/${runId}/review`, {
    method: "POST",
    body: JSON.stringify({ approved, feedback }),
  });
}

export interface UploadAudioResponse {
  run_id: string;
  audio_files: Record<string, string>;
}

export async function uploadAudioFiles(
  runId: string,
  files: Record<string, File>,
): Promise<UploadAudioResponse> {
  const formData = new FormData();
  for (const [sceneId, file] of Object.entries(files)) {
    formData.append(sceneId, file);
  }
  const res = await fetch(`${API_BASE}/${runId}/upload-audio`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<UploadAudioResponse>;
}

export async function uploadSingleAudioFile(
  runId: string,
  file: File,
): Promise<UploadAudioResponse> {
  const formData = new FormData();
  formData.append("audio", file);
  const res = await fetch(`${API_BASE}/${runId}/upload-full-audio`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<UploadAudioResponse>;
}

export async function submitAudioChoice(
  runId: string,
  audioSource: "tts" | "manual",
  audioFiles?: Record<string, string>,
): Promise<{ run_id: string; status: string }> {
  return fetchJSON(`${API_BASE}/${runId}/audio-choice`, {
    method: "POST",
    body: JSON.stringify({ audio_source: audioSource, audio_files: audioFiles }),
  });
}

export async function getHookPrompt(runId: string): Promise<HookPromptResponse> {
  return fetchJSON<HookPromptResponse>(`${API_BASE}/${runId}/hook-prompt`);
}

export async function submitHookPrompt(
  runId: string,
  prompt: string,
): Promise<{ run_id: string; status: string }> {
  return fetchJSON(`${API_BASE}/${runId}/hook-prompt`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function getResult(runId: string): Promise<PipelineResultResponse> {
  return fetchJSON<PipelineResultResponse>(`${API_BASE}/${runId}/result`);
}

export function toFileUrl(path: string): string {
  if (path.startsWith("http")) return path;
  if (path.startsWith("output/")) {
    return `${FILES_BASE}/${path}`;
  }
  if (path.startsWith("./output/")) {
    return `${FILES_BASE}/${path.slice(2)}`;
  }
  return `${FILES_BASE}/output/${path}`;
}
