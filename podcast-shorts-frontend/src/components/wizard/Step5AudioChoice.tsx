"use client";

import { useState, useRef } from "react";
import { ArrowLeft, Mic, Upload, Volume2, X } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";
import * as api from "@/lib/api";

export function Step5AudioChoice() {
  const { state, selectAudio, goBack } = usePipeline();
  const [showFilePicker, setShowFilePicker] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleManualClick = () => {
    setShowFilePicker(true);
    setSelectedFile(null);
    setError(null);
  };

  const handleUploadAndSubmit = async () => {
    if (!state.runId || !selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      const { audio_files } = await api.uploadSingleAudioFile(state.runId, selectedFile);
      await selectAudio("manual", audio_files);
      setShowFilePicker(false);
      setSelectedFile(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const closeFilePicker = () => {
    setShowFilePicker(false);
    setSelectedFile(null);
    setError(null);
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
        <h2 className="text-xl font-semibold">오디오 소스를 선택하세요</h2>
      </div>
      <p className="text-zinc-400 text-sm mb-8 ml-11">
        AI 음성(TTS)으로 자동 생성하거나, 직접 녹음한 파일을 사용할 수 있습니다.
      </p>

      {!showFilePicker ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
          <Card
            hoverable
            className="flex flex-col items-center gap-4 py-10 cursor-pointer"
            onClick={() => selectAudio("tts")}
          >
            <div className="p-4 rounded-full bg-violet-500/20 text-violet-400">
              <Volume2 size={40} />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-1">AI 음성 (TTS)</h3>
              <p className="text-zinc-400 text-sm">
                ElevenLabs를 사용하여
                <br />
                자동으로 음성을 생성합니다
              </p>
            </div>
          </Card>

          <Card
            hoverable
            className="flex flex-col items-center gap-4 py-10 cursor-pointer"
            onClick={handleManualClick}
          >
            <div className="p-4 rounded-full bg-emerald-500/20 text-emerald-400">
              <Mic size={40} />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-1">수동 녹음</h3>
              <p className="text-zinc-400 text-sm">
                로컬 오디오 파일을 선택하여
                <br />
                업로드합니다
              </p>
            </div>
          </Card>
        </div>
      ) : (
        <Card className="p-6 max-w-2xl mx-auto border-emerald-500/30">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2">
              <Upload size={20} />
              오디오 파일 선택
            </h3>
            <button
              onClick={closeFilePicker}
              className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400"
              title="닫기"
            >
              <X size={20} />
            </button>
          </div>
          <p className="text-zinc-500 text-sm mb-6">
            팟캐스트 전체 녹음 파일 하나를 선택하세요. (mp3, wav 등)
            <br />
            자동으로 장면별로 분할하여 처리됩니다.
          </p>

          <div className="mb-6">
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={(e) => {
                setSelectedFile(e.target.files?.[0] ?? null);
                setError(null);
              }}
            />
            <div
              className="flex items-center gap-3 p-4 rounded-xl bg-zinc-900 border border-zinc-700/50 cursor-pointer hover:border-emerald-500/50 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={20} className="text-zinc-400 flex-shrink-0" />
              <span className={selectedFile ? "text-zinc-200 text-sm" : "text-zinc-500 text-sm"}>
                {selectedFile ? selectedFile.name : "클릭하여 파일 선택"}
              </span>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-900/20 border border-red-700/50 text-red-300 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <Button variant="ghost" onClick={closeFilePicker}>
              취소
            </Button>
            <Button
              onClick={handleUploadAndSubmit}
              disabled={!selectedFile || uploading}
            >
              {uploading ? "업로드 중…" : "업로드 후 진행"}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
