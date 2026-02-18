export interface TopicSummary {
  keyword: string;
  summary: string;
  source: string; // "google_trends" | "youtube" | "twitter"
  trending_score: number;
}

export interface Scene {
  scene_id: string;
  text: string;
  duration: number;
  emotion: string;
  image_prompt: string;
  speaker: string;
}

export interface ScriptData {
  title: string;
  full_script: string;
  scenes: Scene[];
  hook: string;
  cta: string;
  estimated_duration_sec: number;
}

export interface VideoMetadata {
  title: string;
  description: string;
  tags: string[];
  category: string;
}

export interface EditorOutput {
  final_video_path: string;
  caption_srt_path: string;
  thumbnail_path: string;
  metadata: VideoMetadata;
  duration_sec: number;
}

export interface FamilyMember {
  key: string;
  name: string;
  description: string;
  photo_url: string;
}

export type PipelineStatus =
  | "idle"
  | "running"
  | "waiting_for_topic_selection"
  | "waiting_for_speaker_selection"
  | "waiting_for_review"
  | "waiting_for_audio_choice"
  | "waiting_for_hook_prompt"
  | "completed"
  | "failed";

export interface PipelineStatusResponse {
  run_id: string;
  status: PipelineStatus;
  current_node?: string;
  script_file_path?: string;
  error?: string;
}

export interface PipelineStartResponse {
  run_id: string;
  status: string;
}

export interface TopicSelectionResponse {
  run_id: string;
  status: string;
  topics?: TopicSummary[];
}

export interface SpeakerSelectionResponse {
  run_id: string;
  status: string;
  members?: FamilyMember[];
}

export interface ScriptReviewResponse {
  run_id: string;
  status: string;
  script_data?: ScriptData;
  script_file_path?: string;
}

export interface PipelineResultResponse {
  run_id: string;
  status: string;
  result?: EditorOutput;
  error?: string;
}

export interface HookPromptResponse {
  run_id: string;
  status: string;
  prompt?: string;
}

export type WizardStep = 1 | 2 | 3 | 4 | 5 | 6 | 7;
