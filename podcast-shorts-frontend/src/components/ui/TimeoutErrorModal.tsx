"use client";

import { AlertCircle, Clock, RotateCcw, X } from "lucide-react";
import { Button } from "./Button";

interface TimeoutErrorModalProps {
  message: string;
  onRetry: () => void;
  onExtend: () => void;
  onClose: () => void;
}

export function TimeoutErrorModal({
  message,
  onRetry,
  onExtend,
  onClose,
}: TimeoutErrorModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="timeout-error-title"
    >
      <div className="mx-4 w-full max-w-md rounded-2xl border border-zinc-700/50 bg-zinc-900 p-6 shadow-xl">
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-full bg-amber-900/30 p-3">
            <Clock size={32} className="text-amber-400" />
          </div>
          <h2
            id="timeout-error-title"
            className="text-lg font-semibold text-zinc-100"
          >
            응답 시간 초과
          </h2>
          <p className="text-center text-sm text-zinc-400">{message}</p>
          <div className="flex w-full flex-col gap-2 pt-2">
            <Button size="lg" className="w-full" onClick={onExtend}>
              <Clock size={16} className="mr-2" />
              추가 10분 대기
            </Button>
            <div className="flex w-full gap-2">
              <Button
                variant="secondary"
                size="lg"
                className="flex-1"
                onClick={onRetry}
              >
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
    </div>
  );
}
