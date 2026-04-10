const CLIENT_KEY = "bydfi-gpt-proxy:client";

const state = {
  messages: [],
  busy: false,
  clientId: getClientId()
};

const $ = (id) => document.getElementById(id);

function createId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  if (globalThis.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  return `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getClientId() {
  const current = localStorage.getItem(CLIENT_KEY);
  if (current) return current;
  const next = createId();
  localStorage.setItem(CLIENT_KEY, next);
  return next;
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderRichText(text) {
  const lines = String(text || "").replace(/\r/g, "").split("\n");
  const html = [];
  let inList = false;

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      continue;
    }

    if (/^[-*•]\s+/.test(line)) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${escapeHtml(line.replace(/^[-*•]\s+/, ""))}</li>`);
      continue;
    }

    if (inList) {
      html.push("</ul>");
      inList = false;
    }
    html.push(`<p>${escapeHtml(line)}</p>`);
  }

  if (inList) html.push("</ul>");
  return html.join("") || "<p></p>";
}

function renderCitations(citations) {
  if (!Array.isArray(citations) || !citations.length) return "";
  const cards = citations
    .slice(0, 4)
    .map((item) => {
      const title = escapeHtml(item.title || item.path || "引用");
      const label = escapeHtml(item.sourceLabel || "内部资料");
      const path = escapeHtml(item.path || "");
      const snippet = escapeHtml(item.snippet || "");
      return `
        <article class="citation-card">
          <div class="citation-label">${label}</div>
          <div class="citation-title">${title}</div>
          ${path ? `<div class="citation-path">${path}</div>` : ""}
          ${snippet ? `<div class="citation-snippet">${snippet}</div>` : ""}
        </article>
      `;
    })
    .join("");

  return `
    <details class="citation-disclosure">
      <summary class="citation-toggle">引用 ${citations.length}</summary>
      <div class="citation-list">${cards}</div>
    </details>
  `;
}

function renderTrace(trace) {
  if (!Array.isArray(trace) || !trace.length) return "";
  const rows = trace
    .slice(-8)
    .map((item) => {
      const stage = escapeHtml(item.stage || "trace");
      const message = escapeHtml(item.message || "");
      const level = /warn|error/i.test(String(item.level || "")) ? "warn" : "info";
      return `
        <div class="trace-row ${level}">
          <div class="trace-stage">${stage}</div>
          <div class="trace-text">${message}</div>
        </div>
      `;
    })
    .join("");

  return `
    <section class="trace-panel">
      <div class="trace-header">执行轨迹</div>
      <div class="trace-list">${rows}</div>
    </section>
  `;
}

function renderMessage(message) {
  const row = document.createElement("article");
  row.className = `message-row ${message.role}`;

  if (message.role !== "user") {
    const avatar = document.createElement("div");
    avatar.className = "assistant-avatar";
    avatar.textContent = "B";
    row.appendChild(avatar);
  }

  const card = document.createElement("section");
  card.className = `message-card ${message.role === "user" ? "user" : "assistant"}`;
  card.innerHTML = `
    <div class="message-body">${renderRichText(message.content)}</div>
    ${message.streaming ? '<div class="message-meta"><div class="streaming-indicator"><span>想</span><span class="streaming-dots"><span></span><span></span><span></span></span></div></div>' : ""}
    ${renderTrace(message.trace)}
    ${renderCitations(message.citations)}
  `;
  row.appendChild(card);
  return row;
}

function render() {
  const feed = $("chatFeed");
  const emptyState = $("emptyState");
  const hasMessages = state.messages.length > 0;
  document.body.classList.toggle("has-messages", hasMessages);
  emptyState.style.display = hasMessages ? "none" : "block";
  feed.innerHTML = "";
  state.messages.forEach((message) => feed.appendChild(renderMessage(message)));
  feed.scrollTop = feed.scrollHeight;
}

function setBusy(busy) {
  state.busy = busy;
  const send = $("btnSend");
  send.disabled = busy;
  send.textContent = busy ? "发送中" : "发送";
}

function autoResize() {
  const input = $("promptInput");
  input.style.height = "0px";
  input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
}

function addMessage(role, content, extra = {}) {
  const message = { role, content, citations: [], trace: [], streaming: false, ...extra };
  state.messages.push(message);
  render();
  return message;
}

function resetConversation() {
  state.messages = [];
  render();
}

function applyPrompt(prompt) {
  const input = $("promptInput");
  input.value = String(prompt || "");
  autoResize();
  input.focus();
}

async function sendPrompt() {
  if (state.busy) return;
  const input = $("promptInput");
  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  input.value = "";
  autoResize();
  setBusy(true);

  const assistant = addMessage("assistant", "", { streaming: true });

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
        consumeEventBlock(block, assistant);
        boundary = buffer.indexOf("\n\n");
      }
    }

    if (buffer.trim()) consumeEventBlock(buffer, assistant);
  } catch {
    assistant.content = "这次没有连上服务。请再发一次，我会继续接着答。";
    assistant.streaming = false;
  } finally {
    render();
    setBusy(false);
  }
}

function consumeEventBlock(block, assistant) {
  const lines = block.split("\n");
  let eventName = "message";
  let dataText = "";
  for (const line of lines) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    if (line.startsWith("data:")) dataText += `${line.slice(5).trim()}\n`;
  }
  if (!dataText.trim()) return;

  let payload;
  try {
    payload = JSON.parse(dataText.trim());
  } catch {
    return;
  }

  if (eventName === "delta") {
    assistant.content += payload.delta || "";
    render();
    return;
  }

  if (eventName === "trace") {
    if (!Array.isArray(assistant.trace)) assistant.trace = [];
    assistant.trace.push(payload || {});
    assistant.trace = assistant.trace.slice(-12);
    render();
    return;
  }

  if (eventName === "done") {
    assistant.content = payload.answer || assistant.content;
    assistant.citations = Array.isArray(payload.citations) ? payload.citations : [];
    assistant.streaming = false;
    render();
  }
}

function initParticles() {
  const canvas = $("particle-canvas");
  const ctx = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let particles = [];
  const connectionDistance = 100;
  const mouse = { x: -1000, y: -1000 };
  const forceRadius = 200;
  const repulsionStrength = 15;

  class Particle {
    constructor() {
      this.init();
    }

    init() {
      this.x = Math.random() * width;
      this.y = Math.random() * height;
      this.vx = (Math.random() - 0.5) * 1.2;
      this.vy = (Math.random() - 0.5) * 1.2;
      this.size = Math.random() * 1.5 + 0.5;
      this.baseColor = Math.random() > 0.5 ? "#22D3EE" : "#06B6D4";
      this.opacity = Math.random() * 0.4 + 0.1;
      this.glow = 0;
    }

    update() {
      this.x += this.vx;
      this.y += this.vy;

      if (this.x < 0) this.x = width;
      if (this.x > width) this.x = 0;
      if (this.y < 0) this.y = height;
      if (this.y > height) this.y = 0;

      const dx = mouse.x - this.x;
      const dy = mouse.y - this.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance < forceRadius) {
        const force = (forceRadius - distance) / forceRadius;
        const angle = Math.atan2(dy, dx);
        this.x -= Math.cos(angle) * force * repulsionStrength;
        this.y -= Math.sin(angle) * force * repulsionStrength;
        this.glow = force * 0.8;
      } else {
        this.glow *= 0.9;
      }
    }

    draw() {
      const currentOpacity = Math.min(1, this.opacity + this.glow);
      ctx.beginPath();
      ctx.fillStyle = this.baseColor;
      ctx.globalAlpha = currentOpacity;
      ctx.arc(this.x, this.y, this.size + this.glow * 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    const particleCount = Math.max(500, Math.min(1200, Math.floor((width * height) / 1800)));
    particles = [];
    for (let i = 0; i < particleCount; i += 1) {
      particles.push(new Particle());
    }
  }

  function drawLines() {
    const stride = 2;
    for (let i = 0; i < particles.length; i += stride) {
      for (let j = i + 1; j < i + 10 && j < particles.length; j += 1) {
        const p1 = particles[i];
        const p2 = particles[j];
        const dx = p1.x - p2.x;
        const dy = p1.y - p2.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < connectionDistance * connectionDistance) {
          const dist = Math.sqrt(distSq);
          const opacity = (1 - dist / connectionDistance) * 0.15;
          const combinedGlow = (p1.glow + p2.glow) * 0.5;
          ctx.beginPath();
          ctx.strokeStyle = `rgba(34, 211, 238, ${opacity + combinedGlow * 0.4})`;
          ctx.lineWidth = 0.5;
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }
    }
  }

  function tick() {
    ctx.fillStyle = "rgba(13, 14, 19, 0.2)";
    ctx.fillRect(0, 0, width, height);

    particles.forEach((particle) => {
      particle.update();
      particle.draw();
    });

    drawLines();
    requestAnimationFrame(tick);
  }

  window.addEventListener("resize", resize);
  window.addEventListener("mousemove", (event) => {
    mouse.x = event.clientX;
    mouse.y = event.clientY;
  });
  window.addEventListener("mouseleave", () => {
    mouse.x = -1000;
    mouse.y = -1000;
  });

  resize();
  tick();
}

function bind() {
  $("btnSend").addEventListener("click", sendPrompt);
  $("btnNewChat").addEventListener("click", resetConversation);
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => applyPrompt(button.dataset.prompt || ""));
  });
  $("promptInput").addEventListener("input", autoResize);
  $("promptInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendPrompt();
    }
  });
}

bind();
autoResize();
render();
initParticles();
