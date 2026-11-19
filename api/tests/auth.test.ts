import request from "supertest";
import { describe, expect, it } from "vitest";
import { registerUser, setup } from "./helpers.js";

describe("auth", () => {
  it("registers, logs in and reads /me", async () => {
    const { app, repo } = setup();
    const reg = await request(app)
      .post("/auth/register")
      .send({ email: "Jane@Example.com", password: "supersecret", name: "Jane" });
    expect(reg.status).toBe(201);
    expect(reg.body.user).toEqual({ id: expect.any(String), email: "jane@example.com", name: "Jane" });
    expect(repo.users[0].passwordHash).not.toBe("supersecret"); // hashed

    const login = await request(app).post("/auth/login").send({ email: "jane@example.com", password: "supersecret" });
    expect(login.status).toBe(200);

    const me = await request(app).get("/auth/me").set("Authorization", `Bearer ${login.body.token}`);
    expect(me.body.user.email).toBe("jane@example.com");
    expect(me.body.user.passwordHash).toBeUndefined();
  });

  it("rejects duplicate email, wrong password, short password", async () => {
    const { app } = setup();
    await registerUser(app);
    expect((await request(app).post("/auth/register").send({ email: "jane@example.com", password: "supersecret" })).status).toBe(409);
    expect((await request(app).post("/auth/login").send({ email: "jane@example.com", password: "wrongpass1" })).status).toBe(401);
    expect((await request(app).post("/auth/register").send({ email: "a@b.co", password: "short" })).status).toBe(400);
  });

  it("protects routes", async () => {
    const { app } = setup();
    expect((await request(app).get("/auth/me")).status).toBe(401);
    expect((await request(app).get("/sessions").set("Authorization", "Bearer garbage")).status).toBe(401);
  });
});
