// Turns per-frame attention predictions into one summary per answer.
// A sample is the model's P(attentive) for one 500 ms frame, or null when no face was found.

export type AttentionSample = number | null;

export type AttentionSummary = {
  samples: number;
  attentive_ratio: number; // share of face-visible frames classified attentive
  looking_away_events: number; // separate glances away lasting >= minAwayFrames
  face_missing_ratio: number;
  model?: string;
};

export function summarizeAttention(
  samples: AttentionSample[],
  { threshold = 0.5, minAwayFrames = 2 } = {},
): AttentionSummary {
  const visible = samples.filter((s): s is number => s !== null);
  const attentive = visible.filter((p) => p >= threshold).length;

  // Count runs of consecutive "away" frames; ignore 1-frame blips (500 ms) as noise.
  let events = 0;
  let run = 0;
  for (const s of samples) {
    if (s !== null && s < threshold) {
      run += 1;
      if (run === minAwayFrames) events += 1;
    } else if (s !== null) {
      run = 0;
    } // a missing face neither starts nor ends a glance
  }

  const round = (x: number) => Math.round(x * 1000) / 1000;
  return {
    samples: samples.length,
    attentive_ratio: visible.length ? round(attentive / visible.length) : 0,
    looking_away_events: events,
    face_missing_ratio: samples.length ? round((samples.length - visible.length) / samples.length) : 0,
  };
}
