"use client";

import { useState } from "react";
import {
  Monitor, Film, Users, TrendingUp, Trophy,
  Landmark, Palette, Atom, Heart, GraduationCap,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { usePipeline } from "@/lib/hooks/usePipeline";
import { CATEGORIES } from "@/lib/constants";

const ICON_MAP: Record<string, React.ReactNode> = {
  Monitor: <Monitor size={28} />,
  Film: <Film size={28} />,
  Users: <Users size={28} />,
  TrendingUp: <TrendingUp size={28} />,
  Trophy: <Trophy size={28} />,
  Landmark: <Landmark size={28} />,
  Palette: <Palette size={28} />,
  Atom: <Atom size={28} />,
  Heart: <Heart size={28} />,
  GraduationCap: <GraduationCap size={28} />,
};

const RESOLUTIONS = [
  { value: "720x1280", label: "HD (720x1280)", desc: "빠른 생성, 낮은 메모리" },
  { value: "1080x1920", label: "Full HD (1080x1920)", desc: "고화질, 더 많은 메모리 필요" },
];

const IMAGE_GENERATORS = [
  { value: "dalle", label: "DALL-E 3", desc: "OpenAI · 안정적, 빠름" },
  { value: "ideogram", label: "Ideogram V2", desc: "4:5 비율 지원, 텍스트 없는 이미지" },
];

const HOOK_MODES = [
  { value: "video", label: "AI 영상 (Luma)", desc: "Luma Dream Machine · 5~9초 동영상" },
  { value: "image", label: "정적 이미지", desc: "DALL-E / Ideogram · 빠른 생성" },
];

export function Step1Category() {
  const { state, startPipeline } = usePipeline();
  const [selected, setSelected] = useState<string[]>([]);
  const [resolution, setResolution] = useState("720x1280");
  const [imageGenerator, setImageGenerator] = useState("dalle");
  const [hookMode, setHookMode] = useState("video");
  const [starting, setStarting] = useState(false);

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleStart = async () => {
    if (selected.length === 0) return;
    setStarting(true);
    await startPipeline(selected, resolution, imageGenerator, hookMode);
  };

  if (starting && state.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Spinner size="lg" label="트렌드를 분석하고 있습니다..." />
        <p className="text-sm text-zinc-500">
          약 20-30초 소요됩니다. 5분 초과 시 재시도할 수 있습니다.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">관심 카테고리를 선택하세요</h2>
      <p className="text-zinc-400 text-sm mb-6">
        여러 개를 선택할 수 있습니다. 선택한 카테고리에서 트렌드를 분석합니다.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 mb-8">
        {CATEGORIES.map((cat) => (
          <Card
            key={cat.id}
            selected={selected.includes(cat.id)}
            hoverable
            onClick={() => toggle(cat.id)}
            className="flex flex-col items-center gap-2 py-6"
          >
            <div className={selected.includes(cat.id) ? "text-violet-400" : "text-zinc-400"}>
              {ICON_MAP[cat.icon]}
            </div>
            <span className="text-sm font-medium">{cat.label}</span>
          </Card>
        ))}
      </div>

      <div className="mb-6">
        <h3 className="text-sm font-medium text-zinc-300 mb-3">영상 해상도</h3>
        <div className="flex gap-3">
          {RESOLUTIONS.map((r) => (
            <button
              key={r.value}
              onClick={() => setResolution(r.value)}
              className={`flex-1 rounded-lg border px-4 py-3 text-left transition-colors ${
                resolution === r.value
                  ? "border-violet-500 bg-violet-500/10 text-white"
                  : "border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:border-zinc-500"
              }`}
            >
              <div className="text-sm font-medium">{r.label}</div>
              <div className="text-xs mt-1 opacity-70">{r.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <h3 className="text-sm font-medium text-zinc-300 mb-3">이미지 생성기</h3>
        <div className="flex gap-3">
          {IMAGE_GENERATORS.map((g) => (
            <button
              key={g.value}
              onClick={() => setImageGenerator(g.value)}
              className={`flex-1 rounded-lg border px-4 py-3 text-left transition-colors ${
                imageGenerator === g.value
                  ? "border-emerald-500 bg-emerald-500/10 text-white"
                  : "border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:border-zinc-500"
              }`}
            >
              <div className="text-sm font-medium">{g.label}</div>
              <div className="text-xs mt-1 opacity-70">{g.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-sm font-medium text-zinc-300 mb-3">훅(Hook) 장면 방식</h3>
        <div className="flex gap-3">
          {HOOK_MODES.map((h) => (
            <button
              key={h.value}
              onClick={() => setHookMode(h.value)}
              className={`flex-1 rounded-lg border px-4 py-3 text-left transition-colors ${
                hookMode === h.value
                  ? "border-amber-500 bg-amber-500/10 text-white"
                  : "border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:border-zinc-500"
              }`}
            >
              <div className="text-sm font-medium">{h.label}</div>
              <div className="text-xs mt-1 opacity-70">{h.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-center">
        <Button
          size="lg"
          disabled={selected.length === 0}
          onClick={handleStart}
        >
          트렌드 분석 시작 ({selected.length}개 선택)
        </Button>
      </div>
    </div>
  );
}
