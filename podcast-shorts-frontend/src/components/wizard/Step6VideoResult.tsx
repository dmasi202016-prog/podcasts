"use client";

import { useState } from "react";
import { Download, RotateCcw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";
import { toFileUrl } from "@/lib/api";

export function Step6VideoResult() {
  const { state, reset } = usePipeline();
  const result = state.result;
  const [downloading, setDownloading] = useState(false);

  if (!result) return null;

  const videoUrl = toFileUrl(result.final_video_path);
  const thumbnailUrl = toFileUrl(result.thumbnail_path);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(videoUrl);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `podcast_shorts_${result.metadata.title || "video"}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      alert("다운로드에 실패했습니다. 영상을 우클릭하여 저장해 주세요.");
    } finally {
      setDownloading(false);
    }
  };

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
        <Button size="lg" onClick={handleDownload} disabled={downloading}>
          <Download size={18} className="mr-2" />
          {downloading ? "다운로드 중..." : "다운로드"}
        </Button>
        <Button size="lg" variant="secondary" onClick={reset}>
          <RotateCcw size={18} className="mr-2" />
          새로 시작
        </Button>
      </div>
    </div>
  );
}
