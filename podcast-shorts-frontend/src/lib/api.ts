import { API_BASE, FILES_BASE } from "./constants";
import type {
  PipelineStartResponse,
  PipelineStatusResponse,
  TopicSelectionResponse,
  SpeakerSelectionResponse,
  ScriptReviewResponse,
  PipelineResultResponse,
} from "./types";

// Per-request timeout — without this, a hung backend request can sit in flight
// indefinitely and pile up across polling intervals.
const DEFAULT_REQUEST_TIMEOUT_MS = 20_000;
// Status polling needs a longer ceiling: Railway cold-starts (and Supabase pool
// warm-up after restart) can legitimately take 30-40s on the first request.
const STATUS_REQUEST_TIMEOUT_MS = 45_000;

async function fetchJSON<T>(
  url: string,
  options?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, ...rest } = options ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...rest,
      signal: rest.signal ?? controller.signal,
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`API error ${res.status}: ${body}`);
    }
    return (await res.json()) as T;
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new Error(`요청 시간 초과 (${timeoutMs}ms): ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function startPipeline(
  userId: string,
  categories: string[],
  resolution: string = "720x1280",
  imageGenerator: string = "dalle",
  hookMode: string = "image",
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
  return fetchJSON<PipelineStatusResponse>(`${API_BASE}/${runId}/status`, {
    timeoutMs: STATUS_REQUEST_TIMEOUT_MS,
  });
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
