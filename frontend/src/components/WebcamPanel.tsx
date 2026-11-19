"use client";

import type { RefObject } from "react";
import { Badge, Card } from "@/components/ui";
import type { CamStatus } from "@/hooks/useFaceLandmarks";

export function WebcamPanel({
  videoRef,
  status,
  error,
  live,
  model,
  enabled,
  onToggle,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  status: CamStatus;
  error: string;
  live: number | null;
  model: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  const attentive = live !== null && live >= 0.5;
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-medium">Eye contact</p>
        <button onClick={onToggle} className="text-xs text-indigo-600 hover:underline">
          {enabled ? "Turn camera off" : "Turn camera on"}
        </button>
      </div>
      <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-slate-900">
        {/* mirrored preview; the stream is only read locally by MediaPipe */}
        <video ref={videoRef} muted playsInline className="h-full w-full -scale-x-100 object-cover" />
        {status === "running" && (
          <div className="absolute bottom-2 left-2">
            <Badge tone={live === null ? "slate" : attentive ? "green" : "amber"}>
              {live === null ? "no face" : attentive ? `looking at screen ${Math.round(live * 100)}%` : "looking away"}
            </Badge>
          </div>
        )}
        {status !== "running" && (
          <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-xs text-slate-400">
            {status === "loading" ? "Starting camera + face tracker…" : enabled ? error : "Camera off"}
          </p>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Video never leaves your browser — only 45 face-landmark numbers are sent.
        {model && ` Model: ${model}.`}
      </p>
    </Card>
  );
}
