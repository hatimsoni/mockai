import request from "supertest";
import { describe, expect, it } from "vitest";
import { AUDIO, createSession, registerUser, setup } from "./helpers.js";

const frame = () => Array.from({ length: 45 }, (_, i) => i / 100);

describe("attention", () => {
  it("proxies landmark frames to the vision model", async () => {
    const { app, ai } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token)).body;
    const res = await request(app)
      .post(`/sessions/${session.id}/attention`)
      .set("Authorization", `Bearer ${token}`)
      .send({ frames: [frame(), frame()] });
    expect(res.status).toBe(200);
    expect(res.body.attentive).toEqual([true, true]);
    expect(ai.predictAttention).toHaveBeenCalledOnce();
  });

  it("validates frame shape", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token)).body;
    const res = await request(app)
      .post(`/sessions/${session.id}/attention`)
      .set("Authorization", `Bearer ${token}`)
      .send({ frames: [[1, 2, 3]] });
    expect(res.status).toBe(400);
  });

  it("stores the attention summary sent with an answer", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token)).body;
    const summary = { samples: 80, attentive_ratio: 0.85, looking_away_events: 2, face_missing_ratio: 0.05, model: "mlp" };
    const res = await request(app)
      .post(`/sessions/${session.id}/answer`)
      .set("Authorization", `Bearer ${token}`)
      .field("attention", JSON.stringify(summary))
      .attach("audio", AUDIO, { filename: "a.webm", contentType: "audio/webm" });
    expect(res.status).toBe(200);
    expect(res.body.turn.attention).toEqual(summary);
  });

  it("rejects a malformed attention summary", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token)).body;
    const res = await request(app)
      .post(`/sessions/${session.id}/answer`)
      .set("Authorization", `Bearer ${token}`)
      .field("attention", JSON.stringify({ samples: 3, attentive_ratio: 7 }))
      .attach("audio", AUDIO, { filename: "a.webm", contentType: "audio/webm" });
    expect(res.status).toBe(400);
  });
});
