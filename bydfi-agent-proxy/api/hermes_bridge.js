const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const { config } = require("./_config");

function isPathLike(value) {
  return /[\\/]/.test(String(value || "")) || /^[A-Za-z]:/.test(String(value || ""));
}

function hasHermesRuntime() {
  if (!config.hermesBin) return false;
  if (!isPathLike(config.hermesBin)) return true;
  return fs.existsSync(config.hermesBin);
}

function readSessionMap() {
  try {
    return JSON.parse(fs.readFileSync(config.sessionMapPath, "utf8"));
  } catch {
    return {};
  }
}

function writeSessionMap(map) {
  fs.mkdirSync(path.dirname(config.sessionMapPath), { recursive: true });
  fs.writeFileSync(config.sessionMapPath, JSON.stringify(map, null, 2), "utf8");
}

function sanitizeAnswer(text) {
  return String(text || "")
    .replace(/\r/g, "")
    .replace(/\n+\s*session_id:\s*[^\n]+$/i, "")
    .trim();
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

function emitTrace(onEvent, stage, message, extra = {}) {
  if (typeof onEvent !== "function") return;
  onEvent({
    type: "trace",
    stage,
    message,
    level: extra.level || "info",
    ts: new Date().toISOString(),
    ...extra
  });
}

function summarizeChunk(chunk, fallback) {
  const text = sanitizeAnswer(chunk)
    .replace(/\s*session_id:\s*\S+\s*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) return fallback;
  return text.length > 160 ? `${text.slice(0, 157)}...` : text;
}

function waitForChild(child, { onEvent, signal } = {}) {
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    let finished = false;

    const cleanupAbort = () => {
      if (signal) signal.removeEventListener("abort", onAbort);
    };

    const finish = (fn, value) => {
      if (finished) return;
      finished = true;
      cleanupAbort();
      fn(value);
    };

    const onAbort = () => {
      emitTrace(onEvent, "abort", "前端连接已关闭，已终止 Hermes 子进程。", { level: "warn" });
      child.kill();
    };

    if (signal) signal.addEventListener("abort", onAbort, { once: true });

    child.stdout?.setEncoding("utf8");
    child.stderr?.setEncoding("utf8");

    child.stdout?.on("data", (chunk) => {
      stdout += chunk;
      if (!String(chunk || "").trim()) return;
      emitTrace(onEvent, "stdout", summarizeChunk(chunk, "Hermes 有新输出。"), {
        source: "stdout"
      });
    });

    child.stderr?.on("data", (chunk) => {
      stderr += chunk;
      if (!String(chunk || "").trim()) return;
      emitTrace(onEvent, "stderr", summarizeChunk(chunk, "Hermes 有新错误输出。"), {
        source: "stderr",
        level: "warn"
      });
    });

    child.on("error", (error) => finish(reject, error));

    child.on("close", (code, closeSignal) => {
      if (code === 0) {
        finish(resolve, { stdout, stderr, code, signal: closeSignal || "" });
        return;
      }

      const error = new Error(`hermes_exit_${code ?? "unknown"}`);
      error.code = code;
      error.signal = closeSignal || "";
      error.stdout = stdout;
      error.stderr = stderr;
      finish(reject, error);
    });
  });
}

function spawnHermes(args, { onEvent, signal, cwd } = {}) {
  emitTrace(onEvent, "spawn", "正在启动 Hermes 进程。", {
    cwd: cwd || config.projectRoot,
    command: `${config.hermesBin} chat -q <message> -Q --source tool`
  });

  const child = spawn(config.hermesBin, args, {
    cwd: cwd || config.projectRoot,
    windowsHide: true,
    env: {
      ...process.env,
      HERMES_HOME: config.hermesHome,
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8"
    }
  });

  return waitForChild(child, { onEvent, signal });
}

async function runHermesQuery(message, sessionId = "", options = {}) {
  const args = ["chat", "-q", message, "-Q", "--source", "tool"];
  if (sessionId) args.push("--resume", sessionId);
  return spawnHermes(args, options);
}

async function streamHermesAnswer(message, clientId = "public-web", options = {}) {
  if (!hasHermesRuntime()) {
    emitTrace(options.onEvent, "missing-runtime", "本地 Hermes 运行时未找到，已跳过桥接。", {
      level: "warn"
    });
    return null;
  }

  const cleanMessage = String(message || "").trim();
  if (!cleanMessage) {
    return {
      title: "BYDFI GPT",
      answer: "直接把问题发出来。",
      citations: [],
      engine: "hermes-empty"
    };
  }

  const sessions = readSessionMap();
  const previousSessionId = sessions[clientId] || "";
  emitTrace(
    options.onEvent,
    previousSessionId ? "resume" : "session",
    previousSessionId ? `准备恢复会话 ${previousSessionId}` : "准备创建新的 Hermes 会话。"
  );

  let result;
  try {
    result = await runHermesQuery(cleanMessage, previousSessionId, options);
  } catch (error) {
    if (!previousSessionId) throw error;
    emitTrace(options.onEvent, "resume-failed", "恢复旧会话失败，回退到新会话。", {
      level: "warn",
      stderr: String(error.stderr || "").trim()
    });
    result = await runHermesQuery(cleanMessage, "", options);
  }

  const parsed = parseHermesOutput(result.stdout || "");
  if (!parsed.answer) {
    const error = new Error(`hermes_empty_response:${result.stderr || ""}`.trim());
    error.stdout = result.stdout || "";
    error.stderr = result.stderr || "";
    throw error;
  }

  if (parsed.sessionId) {
    sessions[clientId] = parsed.sessionId;
    writeSessionMap(sessions);
  }

  emitTrace(options.onEvent, "complete", "Hermes 响应完成，准备回传前端。", {
    sessionId: parsed.sessionId || previousSessionId || ""
  });

  return {
    title: "BYDFI GPT",
    answer: parsed.answer,
    citations: [],
    engine: "hermes",
    sessionId: parsed.sessionId || previousSessionId || ""
  };
}

async function buildHermesAnswer(message, clientId = "public-web") {
  return streamHermesAnswer(message, clientId);
}

module.exports = {
  buildHermesAnswer,
  hasHermesRuntime,
  parseHermesOutput,
  streamHermesAnswer
};
