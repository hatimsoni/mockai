import { Router } from "express";
import multer from "multer";
import { z } from "zod";
import { config } from "../config.js";
import type { AiClient, PlannedQuestion } from "../lib/aiClient.js";
import { HttpError } from "../lib/httpError.js";
import { currentUserId, requireAuth } from "../middleware/auth.js";
import type { Repo } from "../repo/types.js";

// Files are kept in memory (max 5 MB) and streamed on to the AI service.
const pdfUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (_req, file, cb) =>
    file.mimetype === "application/pdf"
      ? cb(null, true)
      : cb(new HttpError(400, "resume must be a PDF")),
});

const createBody = z.object({
  jobTitle: z.string().trim().min(2).max(120),
  jdText: z.string().trim().min(30, "paste the full job description").max(20000),
  numQuestions: z.coerce.number().int().min(1).max(10).default(config.defaultQuestionCount),
});

export function sessionsRouter(repo: Repo, ai: AiClient) {
  const r = Router();
  r.use(requireAuth);

  /** Create an interview: upload resume + JD -> RAG ingest -> question plan -> first turn. */
  r.post("/", pdfUpload.single("resume"), async (req, res) => {
    if (!req.file) throw new HttpError(400, "resume PDF is required (field 'resume')");
    const body = createBody.parse(req.body);
    const userId = currentUserId(res);

    const session = await repo.createSession({
      userId,
      jobTitle: body.jobTitle,
      jdText: body.jdText,
      resumeFileName: req.file.originalname,
      maxQuestions: body.numQuestions,
    });

    let questions: PlannedQuestion[];
    try {
      const ingest = await ai.ingest({
        sessionId: session.id,
        jdText: body.jdText,
        file: { buffer: req.file.buffer, filename: req.file.originalname, mimetype: req.file.mimetype },
      });
      ({ questions } = await ai.planQuestions({
        sessionId: session.id,
        jobTitle: body.jobTitle,
        numQuestions: body.numQuestions,
      }));
      if (questions.length === 0) throw new HttpError(502, "AI service returned no questions");
      await repo.updateSession(session.id, { plan: questions, resumeKey: ingest.resume_key });
    } catch (err) {
      await repo.deleteSession(session.id); // don't leave half-created interviews around
      throw err;
    }

    const first = questions[0];
    await repo.createTurn({
      sessionId: session.id,
      index: 0,
      question: first.question,
      kind: "main",
      topic: first.topic,
      sources: first.sources,
    });

    res.status(201).json({ session: await repo.getSession(session.id, userId) });
  });

  r.get("/", async (_req, res) => {
    const sessions = await repo.listSessions(currentUserId(res));
    res.json({
      sessions: sessions.map(({ turns, jdText: _jd, plan: _plan, ...s }) => ({
        ...s,
        answeredCount: turns.filter((t) => t.transcript !== null).length,
      })),
    });
  });

  r.get("/:id", async (req, res) => {
    const session = await repo.getSession(req.params.id, currentUserId(res));
    if (!session) throw new HttpError(404, "session not found");
    res.json({ session });
  });

  return r;
}
