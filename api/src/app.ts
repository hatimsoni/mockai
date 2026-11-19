import cors from "cors";
import express, { type NextFunction, type Request, type Response } from "express";
import multer from "multer";
import { ZodError } from "zod";
import { config } from "./config.js";
import type { AiClient } from "./lib/aiClient.js";
import { HttpError } from "./lib/httpError.js";
import type { Repo } from "./repo/types.js";
import { authRouter } from "./routes/auth.js";
import { sessionsRouter } from "./routes/sessions.js";

export type Deps = { repo: Repo; ai: AiClient };

// createApp() builds the Express app without listening, so tests can use supertest.
// Dependencies are injected: real Prisma + HTTP AI client in server.ts, fakes in tests.
export function createApp(deps: Deps) {
  const app = express();
  app.use(cors({ origin: config.corsOrigin }));
  app.use(express.json({ limit: "2mb" }));

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", service: "api" });
  });

  app.use("/auth", authRouter(deps.repo));
  app.use("/sessions", sessionsRouter(deps.repo, deps.ai));

  app.use((_req, _res, next) => next(new HttpError(404, "not found")));

  // Central error handler. Express 5 forwards rejected promises here automatically.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ZodError) {
      return res.status(400).json({ error: err.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ") });
    }
    if (err instanceof multer.MulterError) {
      return res.status(400).json({ error: err.message });
    }
    const status = err instanceof HttpError ? err.status : 500;
    if (status >= 500) console.error(err);
    const message = err instanceof Error ? err.message : "internal error";
    res.status(status).json({ error: status === 500 ? "internal error" : message });
  });

  return app;
}
