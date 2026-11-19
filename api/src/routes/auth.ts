import bcrypt from "bcryptjs";
import { Router } from "express";
import { z } from "zod";
import { HttpError } from "../lib/httpError.js";
import { currentUserId, requireAuth, signToken } from "../middleware/auth.js";
import type { Repo, User } from "../repo/types.js";

const credentials = z.object({
  email: z.string().email().transform((e) => e.toLowerCase()),
  password: z.string().min(8, "password must be at least 8 characters").max(200),
});
const registerBody = credentials.extend({ name: z.string().max(100).optional() });

// Never send the password hash to the client.
const publicUser = (u: User) => ({ id: u.id, email: u.email, name: u.name });

export function authRouter(repo: Repo) {
  const r = Router();

  r.post("/register", async (req, res) => {
    const body = registerBody.parse(req.body);
    if (await repo.findUserByEmail(body.email)) throw new HttpError(409, "email already registered");
    // bcrypt: slow, salted hash -> brute-forcing leaked hashes is expensive
    const passwordHash = await bcrypt.hash(body.password, 10);
    const user = await repo.createUser({ email: body.email, passwordHash, name: body.name ?? null });
    res.status(201).json({ token: signToken(user.id), user: publicUser(user) });
  });

  r.post("/login", async (req, res) => {
    const body = credentials.parse(req.body);
    const user = await repo.findUserByEmail(body.email);
    // same message for unknown email and wrong password: don't leak which emails exist
    if (!user || !(await bcrypt.compare(body.password, user.passwordHash))) {
      throw new HttpError(401, "invalid email or password");
    }
    res.json({ token: signToken(user.id), user: publicUser(user) });
  });

  r.get("/me", requireAuth, async (_req, res) => {
    const user = await repo.findUserById(currentUserId(res));
    if (!user) throw new HttpError(404, "user not found");
    res.json({ user: publicUser(user) });
  });

  return r;
}
