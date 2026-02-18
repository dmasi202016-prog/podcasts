"use client";

import { Check } from "lucide-react";
import { STEP_LABELS } from "@/lib/constants";
import type { WizardStep } from "@/lib/types";

interface StepIndicatorProps {
  currentStep: WizardStep;
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  const steps = [1, 2, 3, 4, 5, 6, 7] as WizardStep[];

  return (
    <div className="flex items-center justify-center gap-1 sm:gap-2 mb-8">
      {steps.map((step, idx) => {
        const isCompleted = step < currentStep;
        const isCurrent = step === currentStep;

        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex items-center justify-center w-9 h-9 rounded-full text-sm font-semibold transition-all ${
                  isCompleted
                    ? "bg-violet-600 text-white"
                    : isCurrent
                      ? "bg-violet-600 text-white ring-4 ring-violet-500/30"
                      : "bg-zinc-800 text-zinc-500 border border-zinc-700"
                }`}
              >
                {isCompleted ? <Check size={16} /> : step}
              </div>
              <span
                className={`mt-1.5 text-xs ${
                  isCurrent ? "text-violet-400 font-medium" : "text-zinc-500"
                }`}
              >
                {STEP_LABELS[step]}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`w-6 sm:w-10 h-0.5 mx-1 mt-[-16px] ${
                  isCompleted ? "bg-violet-600" : "bg-zinc-700"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
