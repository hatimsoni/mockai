import request from "supertest";
import { describe, expect, it, vi } from "vitest";
import { HttpError } from "../src/lib/httpError.js";
import { EVAL, answer, createSession, registerUser, setup } from "./helpers.js";

describe("interview loop", () => {
  it("transcribes, stores the evaluation and asks the next planned question", async () => {
    const { app, ai } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 2)).body;

    const a1 = await answer(app, token, session.id);
    expect(a1.status).toBe(200);
    expect(a1.body.turn.transcript).toContain("question 1");
    expect(a1.body.turn.durationSec).toBe(42); // ASR duration wins over client timer
    expect(a1.body.turn.score).toBe(3.5);
    expect(a1.body.turn.evaluation.improvements).toEqual(["add a metric"]);
    expect(a1.body.next).toMatchObject({ index: 1, question: "Question number 2?", kind: "main" });

    expect(a1.body.turn.nlp).toMatchObject({ wpm: 130, filler_count: 1 });
    expect(vi.mocked(ai.transcribe).mock.calls[0][0].jdText).toContain("Backend engineer");

    // the agents received the transcript + NLP metrics we just stored (stateless AI service)
    const req = vi.mocked(ai.step).mock.calls[0][0];
    expect(req.turns.at(-1)?.transcript).toContain("question 1");
    expect(req.turns.at(-1)?.nlp).toMatchObject({ wpm: 130 });
    expect(req.plan).toHaveLength(2);

    const a2 = await answer(app, token, session.id);
    expect(a2.body.done).toBe(true);
    expect((await answer(app, token, session.id)).status).toBe(409);
  });

  it("creates a follow-up turn when the interviewer agent asks for one", async () => {
    const { app } = setup({
      step: vi.fn(async () => ({
        evaluation: { ...EVAL, needs_follow_up: true },
        next_question: { question: "What was your exact role?", kind: "followup" as const, topic: "topic 1", sources: [] },
        done: false,
        report: null,
      })),
    });
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 2)).body;
    const res = await answer(app, token, session.id);
    expect(res.body.next).toMatchObject({ index: 1, kind: "followup", question: "What was your exact role?" });
  });

  it("rolls back the transcript if the agents fail, so the user can re-answer", async () => {
    const { app, repo } = setup({
      step: vi.fn(async () => {
        throw new HttpError(502, "AI service unreachable");
      }),
    });
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 2)).body;
    expect((await answer(app, token, session.id)).status).toBe(502);
    expect(repo.turns[0].transcript).toBeNull();
  });

  it("finish stores the coach report and overall score", async () => {
    const { app, ai } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 3)).body;

    const early = await request(app).post(`/sessions/${session.id}/finish`).set("Authorization", `Bearer ${token}`);
    expect(early.status).toBe(400); // nothing answered yet

    await answer(app, token, session.id);
    const fin = await request(app).post(`/sessions/${session.id}/finish`).set("Authorization", `Bearer ${token}`);
    expect(fin.status).toBe(200);
    expect(fin.body.session).toMatchObject({ status: "COMPLETED", overallScore: 3.5 });
    expect(fin.body.session.report.coach.summary).toBe("Solid.");
    // only answered turns are sent to the coach
    const finishReq = vi.mocked(ai.step).mock.calls.at(-1)![0];
    expect(finishReq.finish).toBe(true);
    expect(finishReq.turns).toHaveLength(1);
    expect((await answer(app, token, session.id)).status).toBe(409);
  });

  it("rejects non-audio uploads", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 1)).body;
    const res = await request(app)
      .post(`/sessions/${session.id}/answer`)
      .set("Authorization", `Bearer ${token}`)
      .attach("audio", Buffer.from("hello"), { filename: "x.txt", contentType: "text/plain" });
    expect(res.status).toBe(400);
  });
});
