const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const HERMES_HOME = process.env.BYDFI_HERMES_HOME || "C:\\temp\\hermes-home";
const HERMES_BIN =
  process.env.BYDFI_HERMES_BIN || "C:\\temp\\hermes-venv\\Scripts\\hermes.exe";
const SESSION_MAP_PATH = path.join(HERMES_HOME, "web-session-map.json");

function readSessionMap() {
  try {
    return JSON.parse(fs.readFileSync(SESSION_MAP_PATH, "utf8"));
  } catch {
    return {};
  }
}

function writeSessionMap(map) {
  fs.mkdirSync(path.dirname(SESSION_MAP_PATH), { recursive: true });
  fs.writeFileSync(SESSION_MAP_PATH, JSON.stringify(map, null, 2), "utf8");
}

function sanitizeAnswer(text) {
  const value = String(text || "")
    .replace(/\r/g, "")
    .replace(/\nsession_id:\s*[^\n]+$/i, "")
    .trim();
  return value;
}

function parseHermesOutput(stdout) {
  const raw = String(stdout || "").trim();
  if (!raw) return { answer: "", sessionId: "" };
  const match = raw.match(/session_id:\s*([^\s]+)/i);
  return {
    answer: sanitizeAnswer(raw),
    sessionId: match ? match[1].trim() : ""
  };
}

function execHermes(args, options = {}) {
  return new Promise((resolve, reject) => {
    execFile(
      HERMES_BIN,
      args,
      {
        windowsHide: true,
        timeout: options.timeoutMs || 240000,
        maxBuffer: 1024 * 1024 * 8,
        cwd: options.cwd || path.dirname(path.dirname(__filename)),
        env: {
          ...process.env,
          HERMES_HOME,
          PYTHONUTF8: "1",
          PYTHONIOENCODING: "utf-8"
        }
      },
      (error, stdout, stderr) => {
        if (error) {
          error.stdout = stdout;
          error.stderr = stderr;
          reject(error);
          return;
        }
        resolve({ stdout, stderr });
      }
    );
  });
}

async function callHermes(message, sessionId = "") {
  const args = ["chat", "-q", message, "-Q"];
  if (sessionId) {
    args.push("--resume", sessionId);
  }
  return execHermes(args);
}

async function buildHermesAnswer(message, clientId = "public-web") {
  if (!fs.existsSync(HERMES_BIN)) {
    return null;
  }

  const cleanMessage = String(message || "").trim();
  if (!cleanMessage) {
    return {
      title: "BYDFI AgentOS",
      answer: "直接把问题发出来。",
      citations: [],
      engine: "hermes-empty"
    };
  }

  const sessions = readSessionMap();
  const previousSessionId = sessions[clientId] || "";

  let result;
  try {
    result = await callHermes(cleanMessage, previousSessionId);
  } catch (error) {
    if (!previousSessionId) {
      throw error;
    }
    result = await callHermes(cleanMessage, "");
  }

  const parsed = parseHermesOutput(result.stdout || "");
  if (!parsed.answer) {
    throw new Error(`hermes_empty_response:${result.stderr || ""}`.trim());
  }

  if (parsed.sessionId) {
    sessions[clientId] = parsed.sessionId;
    writeSessionMap(sessions);
  }

  return {
    title: "BYDFI AgentOS",
    answer: parsed.answer,
    citations: [],
    engine: "hermes",
    sessionId: parsed.sessionId || previousSessionId || ""
  };
}

module.exports = {
  buildHermesAnswer,
  parseHermesOutput
};
