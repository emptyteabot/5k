"use client";

import { useMemo, useRef, useState } from "react";

const SUGGESTIONS = [
  "帮我执行 6 周年策略检查",
  "韩国活动为什么一直卡住，给我责任链和下一步",
  "下面是一段群聊，帮我整理问题、责任人和行动清单"
];

function parseEventBlock(block) {
  const lines = String(block || "").split("\n");
  let event = "message";
  let raw = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) raw += `${line.slice(5).trim()}\n`;
  }
  try {
    return { event, payload: JSON.parse(raw.trim()) };
  } catch {
    return { event, payload: null };
  }
}

export default function Page() {
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [trace, setTrace] = useState([]);
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("BYDFI Sentinel");
  const [citations, setCitations] = useState([]);
  const traceRef = useRef(null);
  const resultRef = useRef(null);

  const endpoint = useMemo(() => {
    const base = process.env.NEXT_PUBLIC_AGENT_API_BASE || "";
    return `${base}/api/chat/stream`;
  }, []);

  async function runPrompt(text) {
    const clean = String(text || "").trim();
    if (!clean || busy) return;

    setBusy(true);
    setAnswer("");
    setTrace([]);
    setCitations([]);
    setTitle("BYDFI Sentinel");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId: "dashboard-demo", message: clean })
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary = buffer.indexOf("\n\n");
        while (boundary >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const parsed = parseEventBlock(block);
          if (parsed.event === "meta" && parsed.payload?.title) {
            setTitle(parsed.payload.title);
          }
          if (parsed.event === "trace" && parsed.payload) {
            setTrace((current) => {
              const next = [...current, parsed.payload].slice(-18);
              queueMicrotask(() => {
                traceRef.current?.scrollTo({ top: traceRef.current.scrollHeight, behavior: "smooth" });
              });
              return next;
            });
          }
          if (parsed.event === "delta" && parsed.payload?.delta) {
            setAnswer((current) => {
              const next = current + parsed.payload.delta;
              queueMicrotask(() => {
                resultRef.current?.scrollTo({ top: resultRef.current.scrollHeight, behavior: "smooth" });
              });
              return next;
            });
          }
          if (parsed.event === "done" && parsed.payload) {
            setAnswer(parsed.payload.answer || "");
            setCitations(Array.isArray(parsed.payload.citations) ? parsed.payload.citations : []);
          }
          boundary = buffer.indexOf("\n\n");
        }
      }
    } catch (error) {
      setTrace((current) => [
        ...current,
        {
          stage: "dashboard-error",
          message: String(error?.message || "network error"),
          level: "warn"
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="dashboard-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="eyebrow">BYDFI AgentOS</div>
          <h1>BYDFI Sentinel</h1>
          <p>左侧输入任务，右侧实时看 Hermes 桥接日志和返回结果。</p>
        </div>
        <div className="hero-actions">
          {SUGGESTIONS.map((item) => (
            <button key={item} type="button" className="chip" onClick={() => setPrompt(item)}>
              {item}
            </button>
          ))}
        </div>
      </section>

      <section className="board">
        <div className="panel input-panel">
          <div className="panel-title">Intent Console</div>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="输入一个 BYDFI 任务，让 Agent 直接开始跑。"
          />
          <button type="button" className="run-btn" disabled={busy} onClick={() => runPrompt(prompt)}>
            {busy ? "Running..." : "Activate BYDFI Sentinel"}
          </button>
        </div>

        <div className="panel result-panel">
          <div className="panel-title">Result Stream</div>
          <div className="result-title">{title}</div>
          <div className="result-body" ref={resultRef}>{answer || "等待结果..."}</div>
          <div className="citation-wrap">
            {citations.map((item, index) => (
              <article key={`${item.path || item.title || 'citation'}-${index}`} className="citation-card">
                <div className="citation-source">{item.sourceLabel || "内部资料"}</div>
                <div className="citation-title">{item.title || item.path || "引用"}</div>
                <div className="citation-path">{item.path || ""}</div>
              </article>
            ))}
          </div>
        </div>

        <div className="panel trace-panel">
          <div className="panel-title">Agent Thought Trace</div>
          <div className="trace-list" ref={traceRef}>
            {trace.length ? trace.map((item, index) => (
              <div key={`${item.stage || 'trace'}-${index}`} className={`trace-row ${item.level || 'info'}`}>
                <div className="trace-stage">{item.stage || 'trace'}</div>
                <div className="trace-message">{item.message || ''}</div>
              </div>
            )) : <div className="trace-empty">等待任务开始...</div>}
          </div>
        </div>
      </section>
    </main>
  );
}
