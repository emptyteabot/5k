const STORAGE_KEY = "bydfi-gpt-proxy:sessions";
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
    ${message.streaming ? '<div class="message-meta"><div class="streaming-indicator"><span>思考中</span><span class="streaming-dots"><span></span><span></span><span></span></span></div></div>' : ""}
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
  send.textContent = busy ? "发送中..." : "发送";
}

function autoResize() {
  const input = $("promptInput");
  input.style.height = "0px";
  input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
}

function addMessage(role, content, extra = {}) {
  const message = { role, content, citations: [], streaming: false, ...extra };
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
  } catch (error) {
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
  const particles = [];
  const mouse = { x: -1000, y: -1000, radius: 180 };

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    particles.length = 0;
    const area = canvas.width * canvas.height;
    const count = Math.min(2800, Math.max(600, Math.floor(area / 800)));
    for (let i = 0; i < count; i += 1) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        baseX: 0,
        baseY: 0,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        size: Math.random() * 1.2 + 0.3,
        density: Math.random() * 30 + 1,
        color: Math.random() > 0.78
          ? "rgba(143,245,255,0.42)"
          : Math.random() > 0.52
            ? "rgba(214,116,255,0.18)"
            : Math.random() > 0.3
              ? "rgba(101,175,255,0.2)"
              : "rgba(255,179,106,0.12)"
      });
      particles[particles.length - 1].baseX = particles[particles.length - 1].x;
      particles[particles.length - 1].baseY = particles[particles.length - 1].y;
    }
  }

  function tick() {
    ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (const p of particles) {
      const dx = mouse.x - p.x;
      const dy = mouse.y - p.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 0.0001;
      if (distance < mouse.radius) {
        const force = (mouse.radius - distance) / mouse.radius;
        const directionX = (dx / distance) * force * p.density;
        const directionY = (dy / distance) * force * p.density;
        p.vx += directionY * 0.05;
        p.vy -= directionX * 0.05;
        p.vx -= directionX * 0.1;
        p.vy -= directionY * 0.1;
      }

      p.vx *= 0.96;
      p.vy *= 0.96;
      p.x += p.vx;
      p.y += p.vy;

      p.x += (p.baseX - p.x) * 0.01;
      p.y += (p.baseY - p.y) * 0.01;

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

  window.addEventListener("resize", resize);
  window.addEventListener("mousemove", (event) => {
    mouse.x = event.clientX;
    mouse.y = event.clientY;
  });
  window.addEventListener("mouseleave", () => {
    mouse.x = -1000;
    mouse.y = -1000;
  });
  window.addEventListener("mousedown", () => {
    mouse.radius = 400;
    window.setTimeout(() => {
      mouse.radius = 180;
    }, 400);
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
