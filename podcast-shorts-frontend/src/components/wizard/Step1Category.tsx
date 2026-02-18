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

export function Step1Category() {
  const { state, startPipeline } = usePipeline();
  const [selected, setSelected] = useState<string[]>([]);
  const [starting, setStarting] = useState(false);

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleStart = async () => {
    if (selected.length === 0) return;
    setStarting(true);
    await startPipeline(selected);
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
