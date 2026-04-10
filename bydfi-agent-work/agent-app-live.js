const state = {
  busy: false,
  clientId: getClientId(),
  trace: [],
  result: "",
  title: "Result Stream",
  citations: [],
  pdfUrl: ""
};

const QUICK_ACTIONS = [
  "帮我审计上周的交易，生成一份 CEO 级别的盈亏分析。",
  "帮我执行 6 周年策略检查，并给出风险边界。",
  "韩国活动为什么卡住了，给出责任链和下一步。"
];

const $ = (id) => document.getElementById(id);

function createId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  if (globalThis.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(bytes);
    return Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("");
  }
  return `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getClientId() {
  const key = "bydfi-sentinel:client-id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const next = createId();
  localStorage.setItem(key, next);
  return next;
}

function setBusy(flag) {
  state.busy = Boolean(flag);
  const send = $("btnSend");
  send.disabled = state.busy;
  send.textContent = state.busy ? "Running..." : "Activate BYDFI Sentinel";
}

function autoResizeInput() {
  const input = $("promptInput");
  input.style.height = "0px";
  input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
}

function scrollToEnd(node) {
  if (!node) return;
  node.scrollTop = node.scrollHeight;
}

function sanitize(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function resetState() {
  state.trace = [];
  state.result = "等待任务开始...";
  state.title = "Result Stream";
  state.citations = [];
  state.pdfUrl = "";
  render();
}

function renderTrace() {
  const root = $("traceBox");
  if (!state.trace.length) {
    root.innerHTML = '<div class="trace-empty">等待 Agent 日志...</div>';
    return;
  }

  root.innerHTML = state.trace
    .slice(-120)
    .map((item) => {
      const level = sanitize(item.level || "info");
      const stage = sanitize(item.stage || "trace");
      const message = sanitize(item.message || "");
      return `
        <article class="trace-row ${level}">
          <div class="trace-stage">${stage}</div>
          <div class="trace-msg">${message}</div>
        </article>
      `;
    })
    .join("");
  scrollToEnd(root);
}

function renderCitations() {
  const root = $("citationBox");
  if (!state.citations.length) {
    root.innerHTML = "";
    return;
  }

  root.innerHTML = state.citations
    .slice(0, 6)
    .map((item) => `
      <article class="citation-card">
        <div class="citation-source">${sanitize(item.sourceLabel || "Source")}</div>
        <div class="citation-title">${sanitize(item.title || item.path || "引用")}</div>
        <div class="citation-path">${sanitize(item.path || "")}</div>
      </article>
    `)
    .join("");
}

function render() {
  $("resultTitle").textContent = state.title || "Result Stream";
  $("resultBox").textContent = state.result || "";
  renderTrace();
  renderCitations();
  $("btnPreviewPdf").disabled = !state.pdfUrl;
}

function consumeEventBlock(block) {
  const lines = String(block || "").split("\n");
  let event = "message";
  let raw = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) raw += `${line.slice(5).trim()}\n`;
  }
  if (!raw.trim()) return;

  let payload;
  try {
    payload = JSON.parse(raw.trim());
  } catch {
    return;
  }

  if (event === "meta") {
    state.title = payload.title || state.title;
    render();
    return;
  }

  if (event === "trace") {
    state.trace.push(payload || {});
    renderTrace();
    return;
  }

  if (event === "delta") {
    if (state.result === "等待任务开始...") state.result = "";
    state.result += payload.delta || "";
    $("resultBox").textContent = state.result;
    scrollToEnd($("resultBox"));
    return;
  }

  if (event === "done") {
    state.result = payload.answer || state.result;
    state.title = payload.title || state.title;
    state.citations = Array.isArray(payload.citations) ? payload.citations : [];

    const pdfCitation = state.citations.find((item) => /\.pdf($|\?)/i.test(String(item.path || "")));
    state.pdfUrl = pdfCitation ? String(pdfCitation.path) : "";

    render();
  }
}

async function sendPrompt() {
  if (state.busy) return;
  const input = $("promptInput");
  const message = String(input.value || "").trim();
  if (!message) return;

  setBusy(true);
  state.trace = [];
  state.result = "";
  state.citations = [];
  state.pdfUrl = "";
  render();

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clientId: state.clientId, message })
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
        consumeEventBlock(block);
        boundary = buffer.indexOf("\n\n");
      }
    }

    if (buffer.trim()) consumeEventBlock(buffer);
  } catch {
    state.trace.push({
      stage: "network-error",
      message: "SSE 请求失败，请确认 Live Server 与 /api/chat/stream 代理可用。",
      level: "error"
    });
    state.result = "这次没有连上服务。请再发一次，我会继续接着答。";
    render();
  } finally {
    setBusy(false);
  }
}

function initQuickActions() {
  const root = $("quickActions");
  root.innerHTML = QUICK_ACTIONS.map((item, index) => `
    <button class="chip" type="button" data-index="${index}">${sanitize(item)}</button>
  `).join("");

  root.querySelectorAll("[data-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const value = QUICK_ACTIONS[Number(button.dataset.index)] || "";
      const input = $("promptInput");
      input.value = value;
      autoResizeInput();
      input.focus();
    });
  });
}

function initPdfModal() {
  const modal = $("pdfModal");
  const frame = $("pdfFrame");

  $("btnPreviewPdf").addEventListener("click", () => {
    if (!state.pdfUrl) return;
    frame.src = state.pdfUrl;
    modal.showModal();
  });

  $("btnClosePdf").addEventListener("click", () => {
    modal.close();
  });

  modal.addEventListener("click", (event) => {
    const rect = modal.getBoundingClientRect();
    const inside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;
    if (!inside) modal.close();
  });
}

function initParticles() {
  const canvas = $("particle-canvas");
  const ctx = canvas.getContext("2d");
  const particles = [];
  const mouse = { x: -9999, y: -9999, radius: 200 };

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    particles.length = 0;
    const count = Math.max(260, Math.floor((canvas.width * canvas.height) / 6200));
    for (let i = 0; i < count; i += 1) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 1.8 + 0.4,
        color: Math.random() > 0.2 ? "rgba(243,186,47,0.44)" : "rgba(143,245,255,0.25)"
      });
    }
  }

  function tick() {
    ctx.fillStyle = "rgba(4, 7, 11, 0.25)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const p of particles) {
      const dx = mouse.x - p.x;
      const dy = mouse.y - p.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;
      if (distance < mouse.radius) {
        const force = (mouse.radius - distance) / mouse.radius;
        p.vx -= (dx / distance) * force * 0.026;
        p.vy -= (dy / distance) * force * 0.026;
      }

      p.vx *= 0.985;
      p.vy *= 0.985;
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = canvas.width;
      if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height;
      if (p.y > canvas.height) p.y = 0;

      ctx.beginPath();
      ctx.fillStyle = p.color;
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }

    requestAnimationFrame(tick);
  }

  window.addEventListener("mousemove", (event) => {
    mouse.x = event.clientX;
    mouse.y = event.clientY;
  });

  window.addEventListener("resize", resize);
  resize();
  tick();
}

function bind() {
  $("btnSend").addEventListener("click", sendPrompt);
  $("btnReset").addEventListener("click", () => {
    $("promptInput").value = "";
    autoResizeInput();
    resetState();
  });

  $("promptInput").addEventListener("input", autoResizeInput);
  $("promptInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendPrompt();
    }
  });
}

bind();
initQuickActions();
initPdfModal();
initParticles();
autoResizeInput();
resetState();
