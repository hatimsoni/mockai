import { describe, expect, it } from "vitest";
import { summarizeAttention } from "./attention";
import { KEY_LANDMARKS, toFrame } from "./landmarks";

describe("summarizeAttention", () => {
  it("computes ratios over visible frames", () => {
    const s = summarizeAttention([0.9, 0.8, 0.2, null]);
    expect(s).toEqual({ samples: 4, attentive_ratio: 0.667, looking_away_events: 0, face_missing_ratio: 0.25 });
  });

  it("counts a glance away only if it lasts at least 2 frames", () => {
    const s = summarizeAttention([0.9, 0.1, 0.9, 0.1, 0.1, 0.1, 0.9, 0.2, 0.2]);
    expect(s.looking_away_events).toBe(2);
  });

  it("a missing face does not split a glance", () => {
    expect(summarizeAttention([0.1, null, 0.1]).looking_away_events).toBe(1);
  });

  it("handles no samples", () => {
    expect(summarizeAttention([])).toEqual({ samples: 0, attentive_ratio: 0, looking_away_events: 0, face_missing_ratio: 0 });
  });
});

describe("toFrame", () => {
  it("picks 15 landmarks -> 45 numbers in order", () => {
    const all = Array.from({ length: 478 }, (_, i) => ({ x: i, y: i + 0.1, z: i + 0.2 }));
    const frame = toFrame(all);
    expect(frame).toHaveLength(45);
    expect(frame.slice(0, 3)).toEqual([1, 1.1, 1.2]); // nose tip = index 1
    expect(KEY_LANDMARKS).toHaveLength(15);
  });
});
