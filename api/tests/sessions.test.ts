import request from "supertest";
import { describe, expect, it } from "vitest";
import { HttpError } from "../src/lib/httpError.js";
import { createSession, registerUser, setup } from "./helpers.js";

describe("POST /sessions", () => {
  it("ingests, plans questions and creates the first turn", async () => {
    const { app, ai } = setup();
    const token = await registerUser(app);
    const res = await createSession(app, token, 3);

    expect(res.status).toBe(201);
    const s = res.body.session;
    expect(s.jobTitle).toBe("Backend Engineer");
    expect(s.plan).toHaveLength(3);
    expect(s.resumeKey).toMatch(/^resumes\//);
    expect(s.turns).toHaveLength(1);
    expect(s.turns[0]).toMatchObject({ index: 0, question: "Question number 1?", kind: "main" });
    expect(ai.ingest).toHaveBeenCalledOnce();
    expect(ai.planQuestions).toHaveBeenCalledWith({ sessionId: s.id, jobTitle: "Backend Engineer", numQuestions: 3 });
  });

  it("validates input", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const noFile = await request(app)
      .post("/sessions")
      .set("Authorization", `Bearer ${token}`)
      .field("jobTitle", "Dev")
      .field("jdText", "x".repeat(40));
    expect(noFile.status).toBe(400);

    const shortJd = await request(app)
      .post("/sessions")
      .set("Authorization", `Bearer ${token}`)
      .field("jobTitle", "Dev")
      .field("jdText", "too short")
      .attach("resume", Buffer.from("%PDF"), { filename: "cv.pdf", contentType: "application/pdf" });
    expect(shortJd.status).toBe(400);
    expect(shortJd.body.error).toContain("jdText");
  });

  it("rolls back the session if the AI service fails", async () => {
    const { app, repo } = setup({
      ingest: async () => {
        throw new HttpError(502, "AI service unreachable");
      },
    });
    const token = await registerUser(app);
    const res = await createSession(app, token);
    expect(res.status).toBe(502);
    expect(repo.sessions).toHaveLength(0);
  });
});

describe("GET /sessions", () => {
  it("lists only the caller's sessions", async () => {
    const { app } = setup();
    const jane = await registerUser(app, "jane@example.com");
    const bob = await registerUser(app, "bob@example.com");
    const created = await createSession(app, jane);

    const janes = await request(app).get("/sessions").set("Authorization", `Bearer ${jane}`);
    expect(janes.body.sessions).toHaveLength(1);
    expect(janes.body.sessions[0].jdText).toBeUndefined();

    const bobs = await request(app).get("/sessions").set("Authorization", `Bearer ${bob}`);
    expect(bobs.body.sessions).toHaveLength(0);

    const peek = await request(app).get(`/sessions/${created.body.session.id}`).set("Authorization", `Bearer ${bob}`);
    expect(peek.status).toBe(404); // can't read someone else's interview
  });
});
