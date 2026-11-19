"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Records microphone audio in the browser with the MediaRecorder API.
// Output: a compressed webm/opus Blob (~10x smaller than WAV) uploaded to the API.

function pickMimeType(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return candidates.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) ?? "";
}

export type Recording = { blob: Blob; durationSec: number; mimeType: string };

export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const releaseMic = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop()); // turns the mic light off
    streamRef.current = null;
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  useEffect(() => releaseMic, [releaseMic]); // release on unmount

  const start = useCallback(async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      });
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      rec.start(1000); // emit a chunk every second so nothing is lost if the tab hiccups
      recorderRef.current = rec;
      startedAtRef.current = Date.now();
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((Date.now() - startedAtRef.current) / 1000), 250);
      setRecording(true);
    } catch (err) {
      setError(
        (err as Error).name === "NotAllowedError"
          ? "Microphone permission denied. Allow mic access in the browser address bar."
          : `Could not start microphone: ${(err as Error).message}`,
      );
    }
  }, []);

  const stop = useCallback(
    () =>
      new Promise<Recording | null>((resolve) => {
        const rec = recorderRef.current;
        if (!rec || rec.state === "inactive") return resolve(null);
        rec.onstop = () => {
          const mimeType = rec.mimeType || "audio/webm";
          const blob = new Blob(chunksRef.current, { type: mimeType });
          releaseMic();
          setRecording(false);
          resolve({ blob, durationSec: (Date.now() - startedAtRef.current) / 1000, mimeType });
        };
        rec.stop();
      }),
    [releaseMic],
  );

  return { recording, elapsed, error, start, stop };
}
