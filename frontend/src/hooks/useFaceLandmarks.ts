"use client";

import { useEffect, useRef, useState } from "react";
import { toFrame } from "@/lib/landmarks";

// Runs Google's MediaPipe FaceLandmarker *in the browser* (WebAssembly/WebGL) on the webcam.
// Every `intervalMs` it calls onFrame with 45 numbers (or null if no face). The video itself
// never leaves the device — only these numbers are sent to the server.

const WASM_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.3/wasm";
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

export type CamStatus = "off" | "loading" | "running" | "error";

export function useFaceLandmarks({
  enabled,
  intervalMs = 500,
  onFrame,
}: {
  enabled: boolean;
  intervalMs?: number;
  onFrame: (frame: number[] | null) => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const onFrameRef = useRef(onFrame);
  const [status, setStatus] = useState<CamStatus>("off");
  const [error, setError] = useState("");

  useEffect(() => {
    onFrameRef.current = onFrame; // always call the latest callback without restarting the camera
  }, [onFrame]);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let stream: MediaStream | null = null;
    let timer: ReturnType<typeof setInterval> | null = null;
    let landmarker: { detectForVideo: (v: HTMLVideoElement, t: number) => { faceLandmarks: { x: number; y: number; z: number }[][] }; close: () => void } | null = null;

    (async () => {
      setStatus("loading");
      try {
        const { FaceLandmarker, FilesetResolver } = await import("@mediapipe/tasks-vision");
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" } });
        if (cancelled) return;
        const video = videoRef.current!;
        video.srcObject = stream;
        await video.play();

        const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
        const create = (delegate: "GPU" | "CPU") =>
          FaceLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: MODEL_URL, delegate },
            runningMode: "VIDEO",
            numFaces: 1,
          });
        landmarker = await create("GPU").catch(() => create("CPU")); // GPU (WebGL) if available
        if (cancelled) return;
        setStatus("running");

        timer = setInterval(() => {
          if (!landmarker || video.readyState < 2) return;
          const result = landmarker.detectForVideo(video, performance.now());
          const face = result.faceLandmarks[0];
          onFrameRef.current(face ? toFrame(face) : null);
        }, intervalMs);
      } catch (err) {
        if (cancelled) return;
        setStatus("error");
        setError(
          (err as Error).name === "NotAllowedError"
            ? "Camera permission denied — attention tracking is off (the interview still works)."
            : `Camera/face tracking unavailable: ${(err as Error).message}`,
        );
      }
    })();

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
      landmarker?.close();
      stream?.getTracks().forEach((t) => t.stop());
      setStatus("off");
    };
  }, [enabled, intervalMs]);

  return { videoRef, status, error };
}
