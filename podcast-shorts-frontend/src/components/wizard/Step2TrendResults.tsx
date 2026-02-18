"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";

const SOURCE_LABELS: Record<string, string> = {
  google_trends: "Google",
  youtube: "YouTube",
  twitter: "X/Twitter",
  tavily: "Tavily",
};

export function Step2TrendResults() {
  const { state, selectTopic, goBack } = usePipeline();
  const [selected, setSelected] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!selected) return;
    await selectTopic(selected);
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-2">
        <button
          onClick={goBack}
          className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="이전 단계"
        >
          <ArrowLeft size={20} />
        </button>
        <h2 className="text-xl font-semibold">트렌드 주제를 선택하세요</h2>
      </div>
      <p className="text-zinc-400 text-sm mb-6 ml-11">
        AI가 분석한 트렌딩 주제 중 하나를 선택하세요.
      </p>

      <div className="space-y-3 mb-8">
        {state.topics.map((topic) => (
          <Card
            key={topic.keyword}
            selected={selected === topic.keyword}
            hoverable
            onClick={() => setSelected(topic.keyword)}
            className="flex flex-col gap-2"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-lg">{topic.keyword}</h3>
              <Badge variant="source">
                {SOURCE_LABELS[topic.source] ?? topic.source}
              </Badge>
            </div>
            <p className="text-zinc-400 text-sm">{topic.summary}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-zinc-500">트렌드 점수</span>
              <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-violet-500 rounded-full transition-all"
                  style={{ width: `${Math.min(topic.trending_score * 100, 100)}%` }}
                />
              </div>
              <span className="text-xs text-zinc-400">
                {(topic.trending_score * 100).toFixed(0)}
              </span>
            </div>
          </Card>
        ))}
      </div>

      {state.topics.length === 0 && (
        <p className="text-center text-zinc-500 py-8">
          트렌드 결과가 없습니다.
        </p>
      )}

      <div className="flex justify-center">
        <Button size="lg" disabled={!selected} onClick={handleSubmit}>
          이 주제로 진행
        </Button>
      </div>
    </div>
  );
}
