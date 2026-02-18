"use client";

import { Download, RotateCcw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";
import { toFileUrl } from "@/lib/api";

export function Step6VideoResult() {
  const { state, reset } = usePipeline();
  const result = state.result;

  if (!result) return null;

  const videoUrl = toFileUrl(result.final_video_path);
  const thumbnailUrl = toFileUrl(result.thumbnail_path);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">영상이 완성되었습니다!</h2>
      <p className="text-zinc-400 text-sm mb-6">
        생성된 팟캐스트 쇼츠를 확인하세요.
      </p>

      {/* Video Player */}
      <div className="max-w-md mx-auto mb-8">
        <div className="relative aspect-[9/16] bg-black rounded-2xl overflow-hidden">
          <video
            src={videoUrl}
            poster={thumbnailUrl}
            controls
            className="w-full h-full object-contain"
          >
            브라우저가 비디오 재생을 지원하지 않습니다.
          </video>
        </div>
      </div>

      {/* Metadata */}
      <Card className="mb-6 max-w-2xl mx-auto">
        <h3 className="font-semibold mb-3">{result.metadata.title}</h3>
        <p className="text-zinc-400 text-sm mb-3">{result.metadata.description}</p>
        <div className="flex flex-wrap gap-2 mb-3">
          {result.metadata.tags.map((tag) => (
            <Badge key={tag}>{tag}</Badge>
          ))}
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <span>카테고리: {result.metadata.category}</span>
          <span>길이: {Math.round(result.duration_sec)}초</span>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex justify-center gap-3">
        <a
          href={videoUrl}
          download
          className="inline-flex items-center justify-center font-medium rounded-xl px-8 py-3.5 text-lg bg-violet-600 hover:bg-violet-500 text-white transition-colors"
        >
          <Download size={18} className="mr-2" />
          다운로드
        </a>
        <Button size="lg" variant="secondary" onClick={reset}>
          <RotateCcw size={18} className="mr-2" />
          새로 시작
        </Button>
      </div>
    </div>
  );
}
