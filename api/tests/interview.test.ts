import request from "supertest";
import { describe, expect, it } from "vitest";
import { answer, createSession, registerUser, setup } from "./helpers.js";

describe("interview loop", () => {
  it("answers questions in order, then reports done", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 2)).body;

    const a1 = await answer(app, token, session.id);
    expect(a1.status).toBe(200);
    expect(a1.body.turn.transcript).toContain("question 1");
    expect(a1.body.turn.durationSec).toBe(42); // ASR duration wins over client timer
    expect(a1.body.next).toMatchObject({ index: 1, question: "Question number 2?" });
    expect(a1.body.done).toBe(false);

    const a2 = await answer(app, token, session.id);
    expect(a2.body.done).toBe(true);
    expect(a2.body.next).toBeNull();

    // nothing left to answer
    expect((await answer(app, token, session.id)).status).toBe(409);
  });

  it("finishes an interview and blocks further answers", async () => {
    const { app } = setup();
    const token = await registerUser(app);
    const { session } = (await createSession(app, token, 3)).body;

    const early = await request(app).post(`/sessions/${session.id}/finish`).set("Authorization", `Bearer ${token}`);
    expect(early.status).toBe(400); // nothing answered yet

    await answer(app, token, session.id);
    const fin = await request(app).post(`/sessions/${session.id}/finish`).set("Authorization", `Bearer ${token}`);
    expect(fin.status).toBe(200);
    expect(fin.body.session.status).toBe("COMPLETED");
    expect(fin.body.droppedLastQuestion).toBe(true);
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
