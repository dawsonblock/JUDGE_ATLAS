#!/usr/bin/env node

import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const artifactsDir = path.resolve(frontendDir, "..", "artifacts", "proof");
const logPath = path.join(artifactsDir, "frontend_build.log");
const timeoutMs = Number(process.env.JTA_FRONTEND_BUILD_TIMEOUT_MS || "900000");
const expectedNodeMajor = Number(process.env.JTA_FRONTEND_NODE_MAJOR || "20");

fs.mkdirSync(artifactsDir, { recursive: true });

const nodeVersion = process.versions.node;
let npmVersion = "unknown";
try {
  const npmVersionRaw = spawn("npm", ["--version"], {
    cwd: frontendDir,
    env: { ...process.env },
    stdio: ["ignore", "pipe", "ignore"],
  });
  let npmStdout = "";
  npmVersionRaw.stdout.on("data", (d) => {
    npmStdout += String(d);
  });
  await new Promise((resolve) => npmVersionRaw.on("close", resolve));
  npmVersion = npmStdout.trim() || "unknown";
} catch {
  npmVersion = "unknown";
}

const nodeMajor = Number(nodeVersion.split(".")[0] || "0");
const nodeVersionMismatch = Number.isFinite(nodeMajor) && nodeMajor !== expectedNodeMajor;

const logHeader = [
  "FRONTEND BUILD PROOF",
  `started_at_utc=${new Date().toISOString()}`,
  `cwd=${frontendDir}`,
  `timeout_ms=${timeoutMs}`,
  `platform=${os.platform()}`,
  `node_version=v${nodeVersion}`,
  `npm_version=${npmVersion}`,
  `expected_node_major=${expectedNodeMajor}`,
  `node_version_mismatch=${nodeVersionMismatch}`,
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

if (nodeVersionMismatch) {
  append(
    `[proof_frontend_build] WARN Node major mismatch: expected ${expectedNodeMajor}, got ${nodeMajor}\n`
  );
}

child.stdout.on("data", (d) => append(String(d)));
child.stderr.on("data", (d) => append(String(d)));

let timedOut = false;
let killTimeoutHandle = null;
const timeoutHandle = setTimeout(() => {
  timedOut = true;
  append(`\n[proof_frontend_build] TIMEOUT after ${timeoutMs}ms\n`);
  child.kill("SIGTERM");
  killTimeoutHandle = setTimeout(() => {
    append("[proof_frontend_build] escalating to SIGKILL\n");
    child.kill("SIGKILL");
  }, 5000);
}, timeoutMs);

child.on("close", (code, signal) => {
  clearTimeout(timeoutHandle);
  if (killTimeoutHandle !== null) {
    clearTimeout(killTimeoutHandle);
    killTimeoutHandle = null;
  }

  let outcome = "build_failure";
  if (timedOut) {
    outcome = "timeout";
  } else if (typeof code === "number" && code === 0) {
    outcome = "success";
  }

  const footer = [
    "",
    `[proof_frontend_build] finished_at_utc=${new Date().toISOString()}`,
    `[proof_frontend_build] exit_code=${code ?? "null"}`,
    `[proof_frontend_build] signal=${signal ?? "none"}`,
    `[proof_frontend_build] timeout=${timedOut}`,
    `[proof_frontend_build] outcome=${outcome}`,
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
