const fs = require("fs");
const path = require("path");

function findProjectRoot(startDir) {
  let current = path.resolve(startDir);
  while (true) {
    if (
      fs.existsSync(path.join(current, "package.json")) ||
      (fs.existsSync(path.join(current, "index.html")) && fs.existsSync(path.join(current, "app.js")))
    ) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return path.resolve(startDir, "..");
    }
    current = parent;
  }
}

function loadEnvFile(projectRoot) {
  const envPath = path.join(projectRoot, ".env");
  if (!fs.existsSync(envPath)) return;
  const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const index = line.indexOf("=");
    if (index <= 0) continue;
    const key = line.slice(0, index).trim();
    if (!key || process.env[key]) continue;
    let value = line.slice(index + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

const projectRoot = findProjectRoot(__dirname);
loadEnvFile(projectRoot);

const isWindows = process.platform === "win32";

function resolveFirstExisting(candidates, fallback) {
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) return candidate;
  }
  return fallback;
}

const defaultHermesBin = resolveFirstExisting([
  isWindows
    ? path.resolve(projectRoot, "..", "hermes-venv", "Scripts", "hermes.exe")
    : path.resolve(projectRoot, "..", "hermes-venv", "bin", "hermes"),
  isWindows
    ? path.resolve(projectRoot, "..", "..", "hermes-venv", "Scripts", "hermes.exe")
    : path.resolve(projectRoot, "..", "..", "hermes-venv", "bin", "hermes")
], isWindows
  ? path.resolve(projectRoot, "..", "hermes-venv", "Scripts", "hermes.exe")
  : path.resolve(projectRoot, "..", "hermes-venv", "bin", "hermes"));

const config = {
  projectRoot,
  hermesHome: process.env.BYDFI_HERMES_HOME || process.env.HERMES_HOME || resolveFirstExisting([
    path.resolve(projectRoot, "..", "hermes-home"),
    path.resolve(projectRoot, "..", "..", "hermes-home")
  ], path.resolve(projectRoot, "..", "hermes-home")),
  hermesBin: process.env.BYDFI_HERMES_BIN || process.env.HERMES_BIN || defaultHermesBin,
  hermesRepoRoot: process.env.BYDFI_HERMES_REPO_ROOT || resolveFirstExisting([
    path.resolve(projectRoot, "..", "hermes-agent"),
    path.resolve(projectRoot, "..", "5k", "hermes-agent")
  ], path.resolve(projectRoot, "..", "hermes-agent")),
  auditBotRoot: process.env.BYDFI_AUDIT_BOT_ROOT || resolveFirstExisting([
    path.resolve(projectRoot, "..", "bydfi-audit-bot"),
    path.resolve(projectRoot, "..", "5k", "bydfi-audit-bot")
  ], path.resolve(projectRoot, "..", "bydfi-audit-bot")),
  upstreamAgentBase: (process.env.BYDFI_UPSTREAM_AGENT_BASE || process.env.BYDFI_LIVE_BASE || "").trim(),
  sessionMapPath: "",
  pythonBin: process.env.BYDFI_PYTHON_BIN || process.env.PYTHON_BIN || "python"
};

config.sessionMapPath = path.join(config.hermesHome, "web-session-map.json");

module.exports = {
  config,
  findProjectRoot,
  loadEnvFile
};
