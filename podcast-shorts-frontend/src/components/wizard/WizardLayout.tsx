"use client";

import { StepIndicator } from "./StepIndicator";
import { Spinner } from "@/components/ui/Spinner";
import { TimeoutErrorModal } from "@/components/ui/TimeoutErrorModal";
import { ErrorModal } from "@/components/ui/ErrorModal";
import { usePipeline } from "@/lib/hooks/usePipeline";
import { Step1Category } from "./Step1Category";
import { Step2TrendResults } from "./Step2TrendResults";
import { Step3Speakers } from "./Step3Speakers";
import { Step4ScriptReview } from "./Step4ScriptReview";
import { Step5AudioChoice } from "./Step5AudioChoice";
import { StepHookPrompt } from "./StepHookPrompt";
import { Step6VideoResult } from "./Step6VideoResult";

const LOADING_LABELS: Record<string, string> = {
  trend_researcher: "트렌드를 분석하고 있습니다...",
  scriptwriter: "대본을 생성하고 있습니다...",
  media_producer: "오디오와 이미지를 생성하고 있습니다... (수 분 소요)",
  auto_editor: "영상을 편집하고 있습니다... (수 분 소요)",
};

export function WizardLayout() {
  const {
    state,
    retryFromTimeout,
    extendTimeout,
    clearTimeoutError,
    clearError,
    retryFromError,
  } = usePipeline();
  const { step, isLoading, error, timeoutError, currentNode } = state;

  const loadingLabel =
    (currentNode && LOADING_LABELS[currentNode]) ?? "파이프라인 처리 중...";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-center mb-2">
          팟캐스트 쇼츠 생성기
        </h1>
        <p className="text-zinc-400 text-center mb-8 text-sm">
          AI가 트렌딩 주제로 팟캐스트 쇼츠를 자동 생성합니다
        </p>

        <StepIndicator currentStep={step} />

        {error && (
          <ErrorModal
            error={error}
            onRetry={retryFromError}
            onClose={clearError}
          />
        )}

        {timeoutError && (
          <TimeoutErrorModal
            message={timeoutError}
            onRetry={retryFromTimeout}
            onExtend={extendTimeout}
            onClose={clearTimeoutError}
          />
        )}

        {isLoading && step !== 1 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Spinner size="lg" label={loadingLabel} />
            {(currentNode === "media_producer" || currentNode === "auto_editor") && (
              <p className="text-xs text-zinc-600">
                오디오/이미지/영상 생성은 외부 API를 사용하므로 시간이 걸릴 수 있습니다
              </p>
            )}
          </div>
        ) : (
          <div className="animate-in fade-in duration-300">
            {step === 1 && <Step1Category />}
            {step === 2 && <Step2TrendResults />}
            {step === 3 && <Step3Speakers />}
            {step === 4 && <Step4ScriptReview />}
            {step === 5 && <Step5AudioChoice />}
            {step === 6 && <StepHookPrompt />}
            {step === 7 && <Step6VideoResult />}
          </div>
        )}
      </div>
    </div>
  );
}
