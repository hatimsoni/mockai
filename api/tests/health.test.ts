import request from "supertest";
import { describe, expect, it } from "vitest";
import { setup } from "./helpers.js";

describe("GET /health", () => {
  it("returns ok", async () => {
    const res = await request(setup().app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok", service: "api" });
  });

  it("unknown routes return JSON 404", async () => {
    const res = await request(setup().app).get("/nope");
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("not found");
  });
});
