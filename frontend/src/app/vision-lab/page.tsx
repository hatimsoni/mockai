"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, Button, Card } from "@/components/ui";
import { useFaceLandmarks } from "@/hooks/useFaceLandmarks";

// Data collection for the attention classifier, using the exact same browser landmark
// extractor as the live interview (no train/serve skew). Hold A or L to label frames.
// Output CSV columns: recording,label,t_ms,f0..f44  -> save into ml/vision/data/

type Row = { label: 0 | 1; t: number; frame: number[] };

export default function VisionLabPage() {
  const [on, setOn] = useState(false);
  const [label, setLabel] = useState<0 | 1 | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const labelRef = useRef<0 | 1 | null>(null);
  const startRef = useRef(0);
  const [recording, setRecording] = useState("");

  useEffect(() => {
    labelRef.current = label;
  }, [label]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.repeat) return;
      if (e.key === "a" || e.key === "A") setLabel(1);
      if (e.key === "l" || e.key === "L") setLabel(0);
    };
    const up = () => setLabel(null);
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, []);

  const onFrame = useCallback((frame: number[] | null) => {
    const l = labelRef.current;
    if (frame && l !== null) {
      setRows((r) => [...r, { label: l, t: Math.round(performance.now() - startRef.current), frame }]);
    }
  }, []);

  const { videoRef, status, error } = useFaceLandmarks({ enabled: on, onFrame });

  function toggleCamera() {
    if (!on) {
      startRef.current = performance.now();
      if (!recording) setRecording(`browser_${new Date().toISOString().replace(/[:.]/g, "-")}`);
    }
    setOn((v) => !v);
  }

  function download() {
    const header = ["recording", "label", "t_ms", ...Array.from({ length: 45 }, (_, i) => `f${i}`)].join(",");
    const lines = rows.map((r) => [recording, r.label, r.t, ...r.frame.map((v) => v.toFixed(5))].join(","));
    const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${recording}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const attentive = rows.filter((r) => r.label === 1).length;
  const away = rows.length - attentive;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Vision lab — record attention training data</h1>
        <p className="mt-1 text-slate-500">
          Hold <kbd className="rounded bg-slate-200 px-1">A</kbd> while looking at the screen, hold{" "}
          <kbd className="rounded bg-slate-200 px-1">L</kbd> while looking away (phone, notes, other monitor, window).
          Aim for 500+ frames of each, across several sessions. See <code>ml/vision/README.md</code>.
        </p>
      </div>
      <Card className="space-y-4">
        <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-slate-900">
          <video ref={videoRef} muted playsInline className="h-full w-full -scale-x-100 object-cover" />
          <div className="absolute left-3 top-3">
            <Badge tone={label === 1 ? "green" : label === 0 ? "amber" : "slate"}>
              {label === 1 ? "recording: ATTENTIVE" : label === 0 ? "recording: LOOKING AWAY" : "paused"}
            </Badge>
          </div>
          {status !== "running" && (
            <p className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">
              {status === "loading" ? "Starting…" : error || "Camera off"}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant={on ? "secondary" : "primary"} onClick={toggleCamera}>
            {on ? "Stop camera" : "Start camera"}
          </Button>
          <Button variant="secondary" onClick={download} disabled={rows.length === 0}>Download CSV</Button>
          <Button variant="ghost" onClick={() => setRows([])} disabled={rows.length === 0}>Clear</Button>
          <span className="text-sm text-slate-600">attentive: {attentive} · away: {away}</span>
        </div>
      </Card>
    </div>
  );
}
