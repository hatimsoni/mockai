import request from "supertest";
import { describe, expect, it, vi } from "vitest";
import { answer, createSession, registerUser, setup } from "./helpers.js";

describe("GET /dashboard", () => {
  it("returns an empty dashboard without calling the AI service", async () => {
    const { app, ai } = setup();
    const token = await registerUser(app);
    const res = await request(app).get("/dashboard").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.timeline).toEqual([]);
    expect(ai.progress).not.toHaveBeenCalled();
  });

  it("sends only scored turns of the caller's sessions to the analytics service", async () => {
    const { app, ai } = setup();
    const token = await registerUser(app);
    const other = await registerUser(app, "bob@example.com");
    const { session } = (await createSession(app, token, 2)).body;
    await answer(app, token, session.id);
    await createSession(app, other, 1);

    const res = await request(app).get("/dashboard").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    const sent = vi.mocked(ai.progress).mock.calls[0][0] as { turns: { score: number }[] }[];
    expect(sent).toHaveLength(1);
    expect(sent[0].turns).toHaveLength(1); // the unanswered 2nd question is excluded
    expect(sent[0].turns[0]).toMatchObject({ score: 3.5, baseline_score: 3.2 });
  });

  it("requires auth", async () => {
    expect((await request(setup().app).get("/dashboard")).status).toBe(401);
  });
});
