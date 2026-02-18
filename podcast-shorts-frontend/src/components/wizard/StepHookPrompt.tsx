"use client";

import { useState } from "react";
import { ArrowLeft, Video, Pencil } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";

export function StepHookPrompt() {
  const { state, submitHookPrompt, goBack } = usePipeline();
  const [editedPrompt, setEditedPrompt] = useState(state.hookPrompt ?? "");
  const [isEditing, setIsEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await submitHookPrompt(editedPrompt);
    } finally {
      setSubmitting(false);
    }
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
        <h2 className="text-xl font-semibold">Hook 영상 프롬프트 검토</h2>
      </div>
      <p className="text-zinc-400 text-sm mb-8 ml-11">
        AI가 생성한 Hook 영상 프롬프트를 검토하세요. 그대로 사용하거나 수정할 수 있습니다.
      </p>

      <Card className="p-6 max-w-2xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <Video size={20} className="text-violet-400" />
          <h3 className="text-lg font-semibold">영상 프롬프트</h3>
        </div>

        {isEditing ? (
          <textarea
            className="w-full bg-zinc-900 border border-zinc-700 rounded-xl p-4 text-zinc-200 text-sm min-h-[160px] focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-y"
            value={editedPrompt}
            onChange={(e) => setEditedPrompt(e.target.value)}
          />
        ) : (
          <div className="bg-zinc-900 border border-zinc-700/50 rounded-xl p-4 text-zinc-300 text-sm whitespace-pre-wrap min-h-[80px]">
            {editedPrompt || "(프롬프트 없음)"}
          </div>
        )}

        <div className="flex gap-3 justify-end mt-6">
          {!isEditing ? (
            <>
              <Button
                variant="secondary"
                onClick={() => setIsEditing(true)}
              >
                <Pencil size={16} className="mr-1.5" />
                수정
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting || !editedPrompt.trim()}
              >
                {submitting ? "제출 중..." : "승인 후 영상 생성"}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                onClick={() => {
                  setEditedPrompt(state.hookPrompt ?? "");
                  setIsEditing(false);
                }}
              >
                취소
              </Button>
              <Button
                onClick={() => setIsEditing(false)}
              >
                수정 완료
              </Button>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}
