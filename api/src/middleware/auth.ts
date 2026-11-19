import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
import { config } from "../config.js";
import { HttpError } from "../lib/httpError.js";

// JWT = a signed JSON payload ({ sub: userId, exp }). The server can verify the
// signature with its secret, so no session table lookup is needed per request.
export function signToken(userId: string): string {
  return jwt.sign({ sub: userId }, config.jwtSecret, { expiresIn: config.jwtExpiresIn } as jwt.SignOptions);
}

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : null;
  if (!token) return next(new HttpError(401, "missing bearer token"));
  try {
    const payload = jwt.verify(token, config.jwtSecret) as jwt.JwtPayload;
    res.locals.userId = payload.sub;
    next();
  } catch {
    next(new HttpError(401, "invalid or expired token"));
  }
}

/** The authenticated user's id (only valid after requireAuth). */
export const currentUserId = (res: Response): string => res.locals.userId as string;
