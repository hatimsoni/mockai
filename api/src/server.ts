import { createApp } from "./app.js";
import { config } from "./config.js";
import { httpAiClient } from "./lib/aiClient.js";
import { prismaRepo } from "./repo/prismaRepo.js";

if (config.jwtSecret === "dev-only-change-me" && process.env.NODE_ENV === "production") {
  throw new Error("JWT_SECRET must be set in production");
}

createApp({ repo: prismaRepo(), ai: httpAiClient() }).listen(config.port, () => {
  console.log(`api listening on http://localhost:${config.port}`);
});
