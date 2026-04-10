const { buildAnswer, chunkText, setCors } = require("../_engine");
const { streamHermesAnswer } = require("../hermes_bridge");

async function readBody(req) {
  if (Buffer.isBuffer(req.body)) {
    const raw = req.body.toString("utf8").trim();
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  }
  if (req.body instanceof Uint8Array) {
    const raw = Buffer.from(req.body).toString("utf8").trim();
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  }
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string" && req.body.trim()) {
    try {
      return JSON.parse(req.body);
    } catch {
      return {};
    }
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

module.exports = async function handler(req, res) {
  setCors(req, res);
  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no"
  });
  res.flushHeaders?.();

  const abortController = new AbortController();
  req.on("close", () => abortController.abort());

  const send = (event, payload) => {
    res.write(`event: ${event}\n`);
    res.write(`data: ${JSON.stringify(payload)}\n\n`);
  };

  try {
    const body = await readBody(req);
    const message = body.message || "";
    const clientId = body.clientId || "public-web";
    send("meta", { title: "BYDFI GPT" });

    const hermesAnswer = await streamHermesAnswer(message, clientId, {
      signal: abortController.signal,
      onEvent: (payload) => send("trace", payload)
    }).catch((error) => {
      send("trace", {
        type: "trace",
        stage: "bridge-error",
        message: String(error?.message || "Hermes bridge failed"),
        level: "warn",
        ts: new Date().toISOString()
      });
      return null;
    });

    const answer = hermesAnswer?.answer
      ? hermesAnswer
      : await buildAnswer(message, clientId, { skipHermes: true });

    send("meta", { title: answer.title || "BYDFI GPT" });
    for (const part of chunkText(answer.answer || "")) {
      send("delta", { delta: part });
    }
    send("done", answer);
    res.end();
  } catch {
    const fallback = "这次没有连上服务。请再发一次，我会继续接着答。";
    send("meta", { title: "BYDFI GPT" });
    for (const part of chunkText(fallback)) {
      send("delta", { delta: part });
    }
    send("done", { title: "BYDFI GPT", answer: fallback, citations: [] });
    res.end();
  }
};
