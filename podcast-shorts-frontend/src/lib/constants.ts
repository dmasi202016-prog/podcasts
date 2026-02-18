import type { FamilyMember } from "./types";

export const API_BASE = "http://localhost:8000/api/v1/pipeline";
export const FILES_BASE = "http://localhost:8000/files";

export const CATEGORIES = [
  { id: "기술", label: "기술", icon: "Monitor" },
  { id: "엔터테인먼트", label: "엔터테인먼트", icon: "Film" },
  { id: "사회", label: "사회", icon: "Users" },
  { id: "경제", label: "경제", icon: "TrendingUp" },
  { id: "스포츠", label: "스포츠", icon: "Trophy" },
  { id: "정치", label: "정치", icon: "Landmark" },
  { id: "문화", label: "문화", icon: "Palette" },
  { id: "과학", label: "과학", icon: "Atom" },
  { id: "건강", label: "건강", icon: "Heart" },
  { id: "교육", label: "교육", icon: "GraduationCap" },
] as const;

export const FAMILY_MEMBERS: FamilyMember[] = [
  { key: "me", name: "나", description: "아빠/진행자", photo_url: `${FILES_BASE}/assets/pic/me.jpeg` },
  { key: "grandma", name: "할머니", description: "따뜻하고 지혜로운 할머니", photo_url: `${FILES_BASE}/assets/pic/grandma.jpeg` },
  { key: "grandfa", name: "할아버지", description: "유머있고 경험 많은 할아버지", photo_url: `${FILES_BASE}/assets/pic/grandfa.jpeg` },
  { key: "jiho", name: "지호", description: "호기심 많은 아이", photo_url: `${FILES_BASE}/assets/pic/jiho.jpeg` },
  { key: "jihyung", name: "지형", description: "똑똑하고 재치있는 아이", photo_url: `${FILES_BASE}/assets/pic/jihyung.jpeg` },
  { key: "jiwon", name: "지원", description: "활발하고 밝은 아이", photo_url: `${FILES_BASE}/assets/pic/jiwon.jpeg` },
  { key: "wife", name: "아내", description: "다정하고 센스있는 아내", photo_url: `${FILES_BASE}/assets/pic/wife.jpeg` },
  { key: "unha", name: "은하", description: "밝고 활발한 아이", photo_url: `${FILES_BASE}/assets/pic/unha.jpeg` },
];

export const POLLING_INTERVAL = 2000;
export const POLLING_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes

export const STEP_LABELS: Record<number, string> = {
  1: "카테고리",
  2: "트렌드",
  3: "출연자",
  4: "대본",
  5: "오디오",
  6: "Hook",
  7: "영상",
};
