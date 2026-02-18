"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { usePipeline } from "@/lib/hooks/usePipeline";
import { FAMILY_MEMBERS } from "@/lib/constants";

export function Step3Speakers() {
  const { selectSpeakers, goBack } = usePipeline();
  const [host, setHost] = useState<string | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);

  const toggleParticipant = (key: string) => {
    if (key === host) return; // Host can't be participant
    setParticipants((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    );
  };

  const selectHost = (key: string) => {
    setHost(key);
    // Remove from participants if already selected
    setParticipants((prev) => prev.filter((p) => p !== key));
  };

  const handleSubmit = async () => {
    if (!host || participants.length === 0) return;
    await selectSpeakers(host, participants);
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
        <h2 className="text-xl font-semibold">출연자를 선택하세요</h2>
      </div>
      <p className="text-zinc-400 text-sm mb-6 ml-11">
        사회자 1명과 참여자를 선택하세요. (참여자 최소 1명)
      </p>

      {/* Host selection */}
      <div className="mb-8">
        <h3 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-wider">
          사회자 (1명 선택)
        </h3>
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-7 gap-3">
          {FAMILY_MEMBERS.map((member) => (
            <button
              key={`host-${member.key}`}
              onClick={() => selectHost(member.key)}
              className={`flex flex-col items-center gap-2 p-3 rounded-2xl border transition-all ${
                host === member.key
                  ? "border-violet-500 bg-violet-500/10 ring-2 ring-violet-500/30"
                  : "border-zinc-700/50 hover:border-zinc-500 bg-zinc-900"
              }`}
            >
              <div className="relative w-16 h-16 rounded-full overflow-hidden bg-zinc-800">
                <img
                  src={member.photo_url}
                  alt={member.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-sm font-medium">{member.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Participants selection */}
      <div className="mb-8">
        <h3 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-wider">
          참여자 (다중 선택)
        </h3>
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-7 gap-3">
          {FAMILY_MEMBERS.filter((m) => m.key !== host).map((member) => (
            <button
              key={`part-${member.key}`}
              onClick={() => toggleParticipant(member.key)}
              className={`flex flex-col items-center gap-2 p-3 rounded-2xl border transition-all ${
                participants.includes(member.key)
                  ? "border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30"
                  : "border-zinc-700/50 hover:border-zinc-500 bg-zinc-900"
              }`}
            >
              <div className="relative w-16 h-16 rounded-full overflow-hidden bg-zinc-800">
                <img
                  src={member.photo_url}
                  alt={member.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-sm font-medium">{member.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-center">
        <Button
          size="lg"
          disabled={!host || participants.length === 0}
          onClick={handleSubmit}
        >
          출연자 확정 (사회자: {host ? FAMILY_MEMBERS.find(m => m.key === host)?.name : "미선택"}, 참여자: {participants.length}명)
        </Button>
      </div>
    </div>
  );
}
