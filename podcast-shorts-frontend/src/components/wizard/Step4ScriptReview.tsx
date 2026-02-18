"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";

const SPEAKER_COLORS: Record<string, string> = {
  host: "bg-violet-900/60 text-violet-300",
  participant_1: "bg-emerald-900/60 text-emerald-300",
  participant_2: "bg-blue-900/60 text-blue-300",
  participant_3: "bg-amber-900/60 text-amber-300",
  participant_4: "bg-rose-900/60 text-rose-300",
  participant_5: "bg-cyan-900/60 text-cyan-300",
  participant_6: "bg-pink-900/60 text-pink-300",
  son: "bg-emerald-900/60 text-emerald-300",
  daughter: "bg-blue-900/60 text-blue-300",
};

function getSectionLabel(sceneId: string): string | null {
  if (sceneId === "hook") return "Hook";
  if (sceneId.startsWith("body_1")) return "Body 1";
  if (sceneId.startsWith("body_2")) return "Body 2";
  if (sceneId.startsWith("body_3")) return "Body 3";
  if (sceneId.startsWith("cta")) return "CTA";
  return null;
}

export function Step4ScriptReview() {
  const { state, submitReview, goBack } = usePipeline();
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);

  const script = state.scriptData;
  if (!script) return null;

  const handleApprove = () => submitReview(true);
  const handleReject = () => {
    if (feedback.trim()) {
      submitReview(false, feedback);
    }
  };

  let lastSection = "";

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <button
          onClick={goBack}
          className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="이전 단계"
        >
          <ArrowLeft size={20} />
        </button>
        <h2 className="text-xl font-semibold">{script.title}</h2>
      </div>
      <p className="text-zinc-400 text-sm mb-6 ml-11">
        대본을 검토하고 승인하거나 수정을 요청하세요. (예상 시간: {script.estimated_duration_sec}초)
      </p>

      <div className="space-y-2 mb-8">
        {script.scenes.map((scene) => {
          const section = getSectionLabel(scene.scene_id);
          const showHeader = section && section !== lastSection;
          if (section) lastSection = section;

          return (
            <div key={scene.scene_id}>
              {showHeader && (
                <div className="mt-4 mb-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                  {section}
                </div>
              )}
              <Card className="py-3 px-4">
                <div className="flex items-start gap-3">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium shrink-0 mt-0.5 ${
                      SPEAKER_COLORS[scene.speaker] ?? "bg-zinc-700 text-zinc-300"
                    }`}
                  >
                    {scene.speaker}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed">{scene.text}</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <Badge variant="emotion">{scene.emotion}</Badge>
                      <span className="text-xs text-zinc-500">{scene.duration}s</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col items-center gap-4">
        <div className="flex gap-3">
          <Button size="lg" onClick={handleApprove}>
            대본 승인
          </Button>
          <Button
            size="lg"
            variant="secondary"
            onClick={() => setShowFeedback(!showFeedback)}
          >
            수정 요청
          </Button>
        </div>

        {showFeedback && (
          <div className="w-full max-w-xl">
            <textarea
              className="w-full h-28 bg-zinc-900 border border-zinc-700 rounded-xl p-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
              placeholder="수정 요청 사항을 입력하세요..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
            <div className="flex justify-end mt-2">
              <Button
                disabled={!feedback.trim()}
                onClick={handleReject}
              >
                피드백 제출
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
