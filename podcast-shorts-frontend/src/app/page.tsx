"use client";

import { PipelineProvider } from "@/context/PipelineContext";
import { WizardLayout } from "@/components/wizard/WizardLayout";

export default function Home() {
  return (
    <PipelineProvider>
      <WizardLayout />
    </PipelineProvider>
  );
}
