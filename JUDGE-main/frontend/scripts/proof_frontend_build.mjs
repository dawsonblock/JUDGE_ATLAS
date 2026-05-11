#!/usr/bin/env node

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const artifactsDir = path.resolve(frontendDir, "..", "artifacts", "proof");
const logPath = path.join(artifactsDir, "frontend_build.log");
const timeoutMs = Number(process.env.JTA_FRONTEND_BUILD_TIMEOUT_MS || "900000");

fs.mkdirSync(artifactsDir, { recursive: true });

const logHeader = [
  "FRONTEND BUILD PROOF",
  `started_at_utc=${new Date().toISOString()}`,
  `cwd=${frontendDir}`,
  `timeout_ms=${timeoutMs}`,
  "command=npm run build",
  "",
].join("\n");

fs.writeFileSync(logPath, logHeader, "utf8");

const child = spawn("npm", ["run", "build"], {
  cwd: frontendDir,
  env: { ...process.env, NEXT_TELEMETRY_DISABLED: "1", CI: "1" },
  stdio: ["ignore", "pipe", "pipe"],
});

const append = (chunk) => {
  fs.appendFileSync(logPath, chunk, "utf8");
};

child.stdout.on("data", (d) => append(String(d)));
child.stderr.on("data", (d) => append(String(d)));

let timedOut = false;
const timeoutHandle = setTimeout(() => {
  timedOut = true;
  append(`\n[proof_frontend_build] TIMEOUT after ${timeoutMs}ms\n`);
  child.kill("SIGTERM");
  setTimeout(() => child.kill("SIGKILL"), 5000).unref();
}, timeoutMs);

child.on("close", (code, signal) => {
  clearTimeout(timeoutHandle);
  const footer = [
    "",
    `[proof_frontend_build] finished_at_utc=${new Date().toISOString()}`,
    `[proof_frontend_build] exit_code=${code ?? "null"}`,
    `[proof_frontend_build] signal=${signal ?? "none"}`,
    `[proof_frontend_build] timeout=${timedOut}`,
    `[proof_frontend_build] log_path=${logPath}`,
    "",
  ].join("\n");
  append(footer);

  if (timedOut) {
    process.exit(124);
  }
  if (typeof code === "number") {
    process.exit(code);
  }
  process.exit(1);
});
