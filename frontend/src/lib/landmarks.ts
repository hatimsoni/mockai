// The 15 MediaPipe FaceMesh points we send to the AI service (x, y, z each = 45 numbers).
// MUST match KEY_LANDMARKS in ai/app/vision/features.py — ai/tests/test_vision.py parses
// this file and fails if the two lists ever differ (prevents train/serve skew).
export const KEY_LANDMARKS: [string, number][] = [
  ["nose_tip", 1],
  ["chin", 152],
  ["forehead", 10],
  ["left_eye_outer", 33],
  ["left_eye_inner", 133],
  ["left_eye_top", 159],
  ["left_eye_bottom", 145],
  ["right_eye_outer", 263],
  ["right_eye_inner", 362],
  ["right_eye_top", 386],
  ["right_eye_bottom", 374],
  ["left_iris", 468],
  ["right_iris", 473],
  ["left_cheek", 234],
  ["right_cheek", 454],
];

export type Point = { x: number; y: number; z: number };

/** 478 MediaPipe landmarks -> flat array of 45 numbers. */
export function toFrame(landmarks: Point[]): number[] {
  return KEY_LANDMARKS.flatMap(([, i]) => {
    const p = landmarks[i];
    return [p.x, p.y, p.z];
  });
}
