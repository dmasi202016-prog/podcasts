"use client";

import { AlertCircle, RotateCcw, X } from "lucide-react";
import { Button } from "./Button";

interface ErrorModalProps {
  error: string;
  onRetry: () => void;
  onClose: () => void;
}

export function ErrorModal({ error, onRetry, onClose }: ErrorModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="error-modal-title"
    >
      <div className="mx-4 w-full max-w-lg rounded-2xl border border-zinc-700/50 bg-zinc-900 p-6 shadow-xl">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="shrink-0 rounded-full bg-red-900/30 p-2.5">
              <AlertCircle size={24} className="text-red-400" />
            </div>
            <h2
              id="error-modal-title"
              className="text-lg font-semibold text-zinc-100"
            >
              파이프라인 오류
            </h2>
          </div>

          <div className="rounded-xl bg-zinc-800/50 border border-zinc-700/50 p-4 max-h-60 overflow-y-auto">
            <p className="text-sm text-zinc-300 whitespace-pre-wrap break-words leading-relaxed">
              {error}
            </p>
          </div>

          <div className="flex w-full gap-2 pt-1">
            <Button size="lg" className="flex-1" onClick={onRetry}>
              <RotateCcw size={16} className="mr-2" />
              처음부터 재시도
            </Button>
            <Button
              variant="ghost"
              size="lg"
              className="flex-1"
              onClick={onClose}
            >
              <X size={16} className="mr-2" />
              닫기
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
