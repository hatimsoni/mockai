// All configuration comes from environment variables so the same image runs
// locally, in docker-compose and in Kubernetes.
export const config = {
  port: Number(process.env.PORT ?? 4000),
  jwtSecret: process.env.JWT_SECRET ?? "dev-only-change-me",
  jwtExpiresIn: "7d",
  aiServiceUrl: process.env.AI_SERVICE_URL ?? "http://localhost:8000",
  internalApiKey: process.env.INTERNAL_API_KEY ?? "",
  corsOrigin: process.env.CORS_ORIGIN ?? "http://localhost:3000",
  // Questions per interview (excluding follow-ups decided by the Interviewer agent)
  defaultQuestionCount: Number(process.env.DEFAULT_QUESTION_COUNT ?? 5),
};
