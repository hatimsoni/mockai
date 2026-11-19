"use client";

import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";
import { summarizeAttention, type AttentionSample, type AttentionSummary } from "@/lib/attention";
import { useFaceLandmarks } from "./useFaceLandmarks";

type Prediction = { probabilities: number[]; attentive: boolean[]; model: string };

const BATCH = 4; // 4 frames x 500 ms = one request every ~2 s

// Landmarks -> batched POST /sessions/:id/attention -> PyTorch model -> live score + per-answer samples.
export function useAttention(sessionId: string, enabled: boolean) {
  const [live, setLive] = useState<number | null>(null); // latest P(attentive)
  const [model, setModel] = useState("");
  const samplesRef = useRef<AttentionSample[]>([]);
  const queueRef = useRef<(number[] | null)[]>([]);
  const inflight = useRef(false);

  const flush = useCallback(async () => {
    if (inflight.current) return;
    const batch = queueRef.current.splice(0);
    const frames = batch.filter((f): f is number[] => f !== null);
    if (frames.length === 0) {
      batch.forEach(() => samplesRef.current.push(null));
      setLive(null);
      return;
    }
    inflight.current = true;
    try {
      const r = await api<Prediction>(`/sessions/${sessionId}/attention`, {
        method: "POST",
        body: JSON.stringify({ frames }),
      });
      let k = 0;
      for (const f of batch) samplesRef.current.push(f === null ? null : r.probabilities[k++]);
      setLive(r.probabilities.at(-1) ?? null);
      setModel(r.model);
    } catch {
      /* attention is optional: drop the batch on network errors */
    } finally {
      inflight.current = false;
    }
  }, [sessionId]);

  const onFrame = useCallback(
    (frame: number[] | null) => {
      queueRef.current.push(frame);
      if (queueRef.current.length >= BATCH) void flush();
    },
    [flush],
  );

  const cam = useFaceLandmarks({ enabled, onFrame });

  /** Start a fresh collection window (call when recording starts). */
  const reset = useCallback(() => {
    samplesRef.current = [];
    queueRef.current = [];
  }, []);

  /** Summary of the current window (call when recording stops). */
  const summary = useCallback((): AttentionSummary | null => {
    if (samplesRef.current.length === 0) return null;
    return { ...summarizeAttention(samplesRef.current), model };
  }, [model]);

  return { ...cam, live, model, reset, summary };
}
