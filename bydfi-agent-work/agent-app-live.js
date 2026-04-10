const STORAGE = {
  sessions: "bydfi-gpt:sessions",
  taskId: "bydfi-gpt:selected-task",
  clientId: "bydfi-gpt:client-id"
};

const MODE_LABELS = {
  company: "公司问答",
  delivery: "交付生成",
  code: "代码协作"
};

const OWNER_STATUS_LABELS = {
  missing: "缺失",
  partial: "部分明确",
  clear: "明确"
};

const state = {
  messages: [],
  sessions: readStoredJson(STORAGE.sessions, []),
  tasks: [],
  selectedTaskId: "",
  selectedTask: null,
  diagnosis: null,
  delivery: null,
  taskSnapshot: null,
  enterprise: null,
  lark: null,
  session: null,
  currentMode: "company",
  busy: false,
  panelOpen: false
};

const $ = (id) => document.getElementById(id);

function readStoredJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeStoredJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function summarizeText(text, max = 88) {
  const flat = String(text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}...` : flat;
}

function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value || "");
  }
}

function createId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  if (globalThis.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(bytes);
    const hex = [...bytes].map((value) => value.toString(16).padStart(2, "0")).join("");
    return `fallback-${hex}`;
  }

  return `fallback-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function getClientId() {
  const existing = localStorage.getItem(STORAGE.clientId);
  if (existing) return existing;
  const next = createId();
  localStorage.setItem(STORAGE.clientId, next);
  return next;
}

function getSelectedTask() {
  return state.tasks.find((task) => task.id === state.selectedTaskId) || null;
}

function formatOwnerStatus(value) {
  const key = String(value || "").trim().toLowerCase();
  return OWNER_STATUS_LABELS[key] || value || "未知";
}

function setSelectedTask(taskId) {
  state.selectedTaskId = String(taskId || "").trim();
  state.selectedTask = getSelectedTask();
  localStorage.setItem(STORAGE.taskId, state.selectedTaskId);
  renderTaskList();
  renderSelectedTask();
  renderComposerMeta();
}

function setBusy(busy) {
  state.busy = Boolean(busy);
  const send = $("btnSend");
  const diagnose = $("btnDiagnose");
  const generate = $("btnGenerate");
  const suggestions = document.querySelectorAll("[data-suggestion-index]");
  if (send) {
    send.disabled = state.busy;
    send.textContent = state.busy ? "发送中..." : "发送";
  }
  if (diagnose) diagnose.disabled = state.busy;
  if (generate) generate.disabled = state.busy;
  suggestions.forEach((node) => {
    node.disabled = state.busy;
  });
}

function autoResizePrompt() {
  const input = $("promptInput");
  if (!input) return;
  input.style.height = "0px";
  input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
}

function scrollFeedToBottom() {
  const feed = $("chatFeed");
  if (!feed) return;
  requestAnimationFrame(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });
}

function renderInlineText(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function renderTextSegment(segment) {
  const blocks = [];
  let listType = "";
  let listItems = [];

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push(`<${listType}>${listItems.map((item) => `<li>${renderInlineText(item)}</li>`).join("")}</${listType}>`);
    listType = "";
    listItems = [];
  };

  String(segment || "").split("\n").forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }

    const bulletMatch = line.match(/^[-*]\s+(.+)$/);
    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    const quoteMatch = line.match(/^>\s?(.*)$/);
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);

    if (bulletMatch) {
      if (listType !== "ul") {
        flushList();
        listType = "ul";
      }
      listItems.push(bulletMatch[1]);
      return;
    }

    if (orderedMatch) {
      if (listType !== "ol") {
        flushList();
        listType = "ol";
      }
      listItems.push(orderedMatch[1]);
      return;
    }

    flushList();

    if (headingMatch) {
      const level = Math.min(headingMatch[1].length + 1, 4);
      blocks.push(`<h${level}>${renderInlineText(headingMatch[2])}</h${level}>`);
      return;
    }

    if (quoteMatch) {
      blocks.push(`<blockquote>${renderInlineText(quoteMatch[1])}</blockquote>`);
      return;
    }

    blocks.push(`<p>${renderInlineText(line)}</p>`);
  });

  flushList();
  return blocks.join("");
}

function renderRichText(text) {
  const source = String(text || "").replace(/\r\n/g, "\n");
  if (!source.trim()) return "";
  return source.split(/```/).map((part, index) => {
    if (index % 2 === 0) return renderTextSegment(part);
    const lines = part.split("\n");
    const language = lines.length > 1 ? lines[0].trim() : "";
    const code = lines.length > 1 ? lines.slice(1).join("\n") : part;
    const languageClass = language ? ` class="language-${escapeHtml(language)}"` : "";
    return `<pre><code${languageClass}>${escapeHtml(code.trim())}</code></pre>`;
  }).join("");
}

function renderMessageActions(actions, index) {
  if (!Array.isArray(actions) || !actions.length) return "";
  return `
    <div class="message-actions">
      ${actions.map((action, actionIndex) => `
        <button class="action-btn" type="button" data-message-index="${index}" data-action-index="${actionIndex}">
          ${escapeHtml(action.label || "操作")}
        </button>
      `).join("")}
    </div>
  `;
}

function renderMetaChips(items) {
  if (!Array.isArray(items) || !items.length) return "";
  return `
    <div class="message-meta">
      ${items.map((item) => `<span class="message-chip">${escapeHtml(item)}</span>`).join("")}
    </div>
  `;
}

function renderCitations(citations) {
  if (!Array.isArray(citations) || !citations.length) return "";
  return `
    <details class="citation-disclosure">
      <summary class="citation-toggle">查看依据（${citations.length}）</summary>
      <div class="citation-list">
        ${citations.map((item) => `
          <article class="citation-card">
            <div class="citation-label">来源</div>
            <div class="citation-title">${escapeHtml(item.title || "")}</div>
            <div class="citation-path">${escapeHtml([item.sourceLabel, item.path].filter(Boolean).join(" · "))}</div>
            <div class="citation-snippet">${escapeHtml(summarizeText(item.snippet || "", 180))}</div>
          </article>
        `).join("")}
      </div>
    </details>
  `;
}

function renderStreamingState() {
  return `
    <div class="streaming-indicator">
      <span>正在回答</span>
      <span class="streaming-dots"><span></span><span></span><span></span></span>
    </div>
  `;
}

function renderMessage(message, index) {
  const role = message.role || "assistant";
  const isAssistantLike = role !== "user";
  const title = message.title || "BYDFI GPT";
  const subtitle = message.subtitle || "";
  const body = message.body ? renderRichText(message.body) : (message.streaming ? renderStreamingState() : "");

  return `
    <article class="message-row ${escapeHtml(role)}">
      ${isAssistantLike ? '<div class="assistant-avatar">B</div>' : ""}
      <div class="message-card ${escapeHtml(role)}">
        ${role === "user"
          ? `<div class="message-body">${body}</div>`
          : `
            <div class="message-title">${escapeHtml(title)}</div>
            ${subtitle ? `<div class="message-subtitle">${escapeHtml(subtitle)}</div>` : ""}
            <div class="message-body">${body}</div>
            ${renderMetaChips(message.meta)}
            ${renderCitations(message.citations)}
            ${renderMessageActions(message.actions, index)}
          `}
      </div>
    </article>
  `;
}

function renderChatFeed() {
  const feed = $("chatFeed");
  const emptyState = $("emptyState");
  if (!feed || !emptyState) return;

  if (!state.messages.length) {
    document.body.classList.remove("has-messages");
    feed.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }

  document.body.classList.add("has-messages");
  emptyState.classList.add("hidden");
  feed.innerHTML = state.messages.map((message, index) => renderMessage(message, index)).join("");
  feed.querySelectorAll("[data-message-index]").forEach((node) => {
    node.addEventListener("click", () => {
      const messageIndex = Number(node.dataset.messageIndex);
      const actionIndex = Number(node.dataset.actionIndex);
      const message = state.messages[messageIndex];
      const action = message?.actions?.[actionIndex];
      handleAction(action);
    });
  });
  scrollFeedToBottom();
}

function addMessage(message) {
  state.messages.push({
    role: "assistant",
    title: "BYDFI GPT",
    subtitle: "",
    body: "",
    meta: [],
    citations: [],
    actions: [],
    ...message
  });
  state.messages = state.messages.slice(-40);
  renderChatFeed();
  return state.messages.length - 1;
}

function updateMessage(index, patch) {
  const current = state.messages[index];
  if (!current) return;
  state.messages[index] = { ...current, ...patch };
  renderChatFeed();
}

function buildSuggestions() {
  const task = getSelectedTask();
  return [
    {
      label: "韩国活动卡住了怎么办",
      prompt: "韩国召回活动一直卡住，帮我判断问题、找出卡点，并给出最短的推进路径。"
    },
    {
      label: "帮我生成交付物",
      prompt: task
        ? `基于 ${task.title}，帮我先整理成可执行方案，再告诉我是否需要进入交付生成。`
        : "帮我把一个奖励活动需求整理成可以交付的结构化方案。"
    },
    {
      label: "我不知道找谁",
      prompt: "我现在只知道问题现象，不知道该找谁、先做什么，帮我压缩成最短处理路径。"
    },
    {
      label: "公司制度怎么查",
      prompt: "公司某个流程或历史决策我不知道，帮我用最短的话说明白，并告诉我下一步找谁。"
    }
  ];
}

function renderSuggestions() {
  const root = $("suggestionList");
  if (!root) return;
  const suggestions = buildSuggestions();
  root.innerHTML = suggestions.map((item, index) => `
    <button class="suggestion-chip" type="button" data-suggestion-index="${index}">${escapeHtml(item.label)}</button>
  `).join("");
  root.querySelectorAll("[data-suggestion-index]").forEach((node) => {
    node.addEventListener("click", () => {
      const suggestion = suggestions[Number(node.dataset.suggestionIndex)];
      const input = $("promptInput");
      if (!input || !suggestion) return;
      input.value = suggestion.prompt;
      input.focus();
      autoResizePrompt();
    });
  });
}

function renderComposerMeta() {
  const contextPill = $("contextPill");
  const taskPill = $("taskPill");
  if (contextPill) contextPill.textContent = "";
  if (taskPill) taskPill.textContent = "";
}

function renderSelectedTask() {
  const task = getSelectedTask();
  const root = $("selectedTaskMeta");
  if (!root) return;
  if (!task) {
    root.className = "info-box empty";
    root.textContent = "还没有选择案例。";
    return;
  }
  root.className = "info-box";
  root.innerHTML = `
    <div class="delivery-heading">${escapeHtml(task.title)}</div>
    <div class="delivery-subline">${escapeHtml(task.summary)}</div>
    <div class="info-tags">
      <span class="tag ${task.severity ? `severity-${String(task.severity).toLowerCase()}` : ""}">${escapeHtml(task.severity || "P1")}</span>
      <span class="tag">阻塞节点：${escapeHtml(task.block_node || "未知")}</span>
      <span class="tag">延迟：${escapeHtml(task.delay_hours || 0)} 小时</span>
      <span class="tag">Owner：${escapeHtml(formatOwnerStatus(task.owner_status))}</span>
    </div>
  `;
}

function renderTaskList() {
  const root = $("taskList");
  if (!root) return;
  if (!state.tasks.length) {
    root.innerHTML = '<div class="info-box empty">案例加载中...</div>';
    return;
  }
  root.innerHTML = state.tasks.map((task) => `
    <button class="task-card ${task.id === state.selectedTaskId ? "active" : ""}" type="button" data-task-id="${escapeHtml(task.id)}">
      <div class="task-head">
        <div class="task-title">${escapeHtml(task.title)}</div>
        <span class="tag ${task.severity ? `severity-${String(task.severity).toLowerCase()}` : ""}">${escapeHtml(task.severity || "P1")}</span>
      </div>
      <div class="task-summary">${escapeHtml(task.summary || "")}</div>
      <div class="task-tags">
        <span class="tag">${escapeHtml(task.team || "未知团队")}</span>
        <span class="tag">阻塞：${escapeHtml(task.block_node || "未知")}</span>
        <span class="tag">${escapeHtml(task.delay_hours || 0)} 小时</span>
      </div>
    </button>
  `).join("");
  root.querySelectorAll("[data-task-id]").forEach((node) => {
    node.addEventListener("click", () => {
      setSelectedTask(node.dataset.taskId);
    });
  });
}

function renderDiagnosis() {
  const root = $("diagnosisResult");
  if (!root) return;
  if (!state.diagnosis) {
    root.className = "info-box empty";
    root.textContent = "尚未运行诊断。";
    return;
  }

  const diagnosis = state.diagnosis;
  const logs = Array.isArray(diagnosis.log_lines) ? diagnosis.log_lines : [];
  root.className = "info-box";
  root.innerHTML = `
    <div class="delivery-heading">诊断已完成</div>
    <div class="info-tags">
      <span class="tag">阻塞节点：${escapeHtml(diagnosis.block_node || "未知")}</span>
      <span class="tag">Owner：${escapeHtml(formatOwnerStatus(diagnosis.owner_status))}</span>
      <span class="tag">延迟：${escapeHtml(diagnosis.delay_hours || 0)} 小时</span>
      <span class="tag">置信度：${escapeHtml(diagnosis.confidence || 0)}</span>
    </div>
    <div class="delivery-note">${escapeHtml(diagnosis.action_plan || "暂无动作")}</div>
    ${diagnosis.override_reason ? `<div class="delivery-subline">${escapeHtml(diagnosis.override_reason)}</div>` : ""}
    ${logs.length ? `<pre class="artifact-code">${escapeHtml(logs.join("\n"))}</pre>` : ""}
  `;
}

function renderDelivery() {
  const root = $("deliveryResult");
  if (!root) return;
  if (!state.delivery) {
    root.className = "info-box empty";
    root.textContent = "尚未生成交付物。";
    return;
  }

  const delivery = state.delivery;
  const jsonText = prettyJson(delivery.generated?.json || delivery.generated || {});
  root.className = "info-box";
  root.innerHTML = `
    <div class="delivery-group">
      <div>
        <div class="delivery-heading">JSON 交付物</div>
        <div class="delivery-subline">${escapeHtml(delivery.next_step || "本地交付物已生成")}</div>
      </div>
      <div class="delivery-toolbar">
        <span class="tag">来源：${escapeHtml(delivery.source || delivery.generated?.source || "enterprise-agent-local")}</span>
        <span class="tag">编译器：${escapeHtml(delivery.generated?.compiler_version || "enterprise-agent.override.v1")}</span>
      </div>
      <pre class="artifact-code">${escapeHtml(jsonText)}</pre>
      <div>
        <div class="delivery-heading">H5 预览</div>
        <div class="delivery-subline">这是实际接口返回的落地页预览。</div>
      </div>
      <iframe id="deliveryPreview" class="delivery-preview" title="交付物预览"></iframe>
      <pre class="delivery-note">${escapeHtml(delivery.delivery_note || delivery.local_handoff || "")}</pre>
    </div>
  `;

  const iframe = $("deliveryPreview");
  if (iframe) {
    iframe.srcdoc = String(delivery.generated?.html || "");
  }
}

function renderStatus() {
  const root = $("statusMetrics");
  if (!root) return;

  const cards = [];
  if (state.taskSnapshot?.metrics) {
    const metrics = state.taskSnapshot.metrics;
    cards.push(
      metricCard("结构化记录", metrics.structured_count),
      metricCard("无状态盲区", metrics.uncontrolled_rate),
      metricCard("平均损失天数", metrics.avg_loss_days),
      metricCard("已关联任务", metrics.linked_count)
    );
  }
  if (state.enterprise) {
    cards.push(
      metricCard("审计日志", state.enterprise.auditEvents),
      metricCard("监控日志", state.enterprise.monitorEvents),
      metricCard("版本事件", state.enterprise.versionEvents),
      metricCard("回滚快照", state.enterprise.rollbackSnapshots)
    );
  }

  if (!cards.length) {
    root.innerHTML = '<div class="info-box empty">系统状态加载中...</div>';
    return;
  }

  root.innerHTML = cards.join("");
}

function metricCard(label, value) {
  return `
    <article class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(value)}</div>
    </article>
  `;
}

function saveSession(prompt, answer) {
  state.sessions.unshift({
    id: createId(),
    timestamp: new Date().toISOString(),
    title: summarizeText(prompt, 28),
    summary: summarizeText(answer, 92),
    prompt,
    taskId: state.selectedTaskId
  });
  state.sessions = state.sessions.slice(0, 20);
  writeStoredJson(STORAGE.sessions, state.sessions);
  renderSessions();
}

function renderSessions() {
  const root = $("sessionList");
  if (!root) return;
  if (!state.sessions.length) {
    root.className = "session-list empty";
    root.textContent = "还没有历史对话。";
    return;
  }

  root.className = "session-list";
  root.innerHTML = state.sessions.map((session, index) => `
    <button class="session-card" type="button" data-session-index="${index}">
      <div class="session-row">
        <div class="task-title">${escapeHtml(session.title || "未命名对话")}</div>
        <div class="session-time">${escapeHtml(formatDateTime(session.timestamp))}</div>
      </div>
      <div class="session-summary">${escapeHtml(session.summary || session.prompt || "")}</div>
    </button>
  `).join("");
  root.querySelectorAll("[data-session-index]").forEach((node) => {
    node.addEventListener("click", () => {
      const session = state.sessions[Number(node.dataset.sessionIndex)];
      if (!session) return;
      const input = $("promptInput");
      if (session.taskId) setSelectedTask(session.taskId);
      if (input) {
        input.value = session.prompt || "";
        input.focus();
        autoResizePrompt();
      }
      addMessage({
        role: "assistant",
        title: "已恢复历史问题",
        subtitle: "你可以直接重新发送或先改写",
        body: `已把这条问题重新放回输入框。你可以直接发送，也可以先改写。\n\n${session.prompt || ""}`,
        meta: session.taskId ? ["已恢复上一条问题"] : []
      });
    });
  });
}

function formatDateTime(value) {
  try {
    return new Date(value).toLocaleString("zh-CN", { hour12: false });
  } catch {
    return String(value || "");
  }
}

function buildHistory() {
  return state.messages.slice(-8).map((message) => ({
    role: message.role === "user" ? "user" : "assistant",
    content: [message.title, message.body].filter(Boolean).join("\n")
  }));
}

function buildMessageActions(meta) {
  const actions = Array.isArray(meta?.actions)
    ? meta.actions.map((action) => ({
        label: action.label || "操作",
        type: action.type,
        url: action.url,
        taskId: action.taskId || action.task_id,
        prompt: action.prompt,
        demoId: action.demoId
      })).filter((action) => action.type)
    : [];
  const taskId = meta?.suggested_task_id || "";
  if (taskId) {
    actions.push({ label: "按这个问题继续", type: "task", taskId });
  }
  if (meta?.suggested_mode === "delivery" && taskId) {
    actions.push({ label: "开始诊断", type: "diagnose", taskId });
    if (state.diagnosis?.task_id === taskId) {
      actions.push({ label: "生成交付结果", type: "generate", taskId });
    }
  }
  if (meta?.suggested_mode === "code") {
    actions.push({ label: "看实现路径", type: "mode", mode: meta.suggested_mode });
  }
  return actions;
}

function handleAction(action) {
  if (!action) return;
  if (action.type === "task") {
    setSelectedTask(action.taskId);
    const input = $("promptInput");
    if (input) input.focus();
    return;
  }
  if (action.type === "diagnose") {
    runDiagnose(action.taskId);
    return;
  }
  if (action.type === "generate") {
    runGenerate(action.taskId);
    return;
  }
  if (action.type === "mode") {
    state.currentMode = action.mode || "company";
    renderComposerMeta();
    return;
  }
  if (action.type === "open_url" && action.url) {
    window.open(action.url, "_blank", "noopener");
    return;
  }
  if (action.type === "judge_demo") {
    runJudgeDemo(action.prompt, action.demoId);
    return;
  }
  if (action.type === "judge_export") {
    runJudgeExport(action.demoId, action.prompt);
    return;
  }
}

function parseEventStreamBlock(block) {
  const lines = String(block || "").split(/\r?\n/);
  let event = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  const raw = dataLines.join("\n").trim();
  if (!raw) return null;

  try {
    return { event, payload: JSON.parse(raw) };
  } catch {
    return null;
  }
}

function consumeEventStreamBuffer(buffer, onEvent) {
  let rest = buffer;
  let boundary = rest.indexOf("\n\n");
  while (boundary >= 0) {
    const block = rest.slice(0, boundary);
    rest = rest.slice(boundary + 2);
    const parsed = parseEventStreamBlock(block);
    if (parsed) onEvent(parsed);
    boundary = rest.indexOf("\n\n");
  }
  return rest;
}

async function sendPrompt(explicitPrompt) {
  const input = $("promptInput");
  const prompt = String(explicitPrompt || input?.value || "").trim();
  if (!prompt || state.busy) return;

  if (input) {
    input.value = "";
    autoResizePrompt();
  }

  addMessage({ role: "user", body: prompt });
  const assistantIndex = addMessage({
    role: "assistant",
    title: "BYDFI GPT",
    subtitle: "正在分析你的问题",
    body: "",
    streaming: true,
    meta: []
  });

  setBusy(true);
  let fullText = "";
  let meta = {};

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        clientId: getClientId(),
        message: prompt,
        selectedTask: getSelectedTask(),
        history: buildHistory()
      })
    });

    if (!response.ok || !response.body) {
      throw new Error(`请求失败：${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = consumeEventStreamBuffer(buffer, ({ event, payload }) => {
        if (event === "meta") {
          meta = payload || {};
          if (meta.suggested_mode) {
            state.currentMode = meta.suggested_mode;
            renderComposerMeta();
          }
          updateMessage(assistantIndex, {
            meta: buildMetaChips(meta),
            citations: Array.isArray(meta.citations) ? meta.citations : [],
            actions: buildMessageActions(meta)
          });
          return;
        }

        if (event === "delta") {
          fullText += String(payload?.delta || "");
          updateMessage(assistantIndex, {
            body: fullText,
            streaming: true,
            meta: buildMetaChips(meta),
            citations: Array.isArray(meta.citations) ? meta.citations : [],
            actions: buildMessageActions(meta)
          });
          return;
        }

        if (event === "done") {
          meta = payload || meta;
          fullText = String(payload?.answer || fullText || "").trim();
          updateMessage(assistantIndex, {
            title: inferAssistantTitle(meta),
            subtitle: inferAssistantSubtitle(meta),
            body: fullText || "未返回内容。",
            streaming: false,
            meta: buildMetaChips(meta),
            citations: Array.isArray(meta.citations) ? meta.citations : [],
            actions: buildMessageActions(meta)
          });
        }
      });
    }

    if (!fullText.trim()) {
      updateMessage(assistantIndex, {
        title: inferAssistantTitle(meta),
        subtitle: inferAssistantSubtitle(meta),
        body: "本次没有拿到有效内容，请重试一次。",
        streaming: false,
        meta: buildMetaChips(meta),
        citations: Array.isArray(meta.citations) ? meta.citations : [],
        actions: buildMessageActions(meta)
      });
      return;
    }

    saveSession(prompt, fullText);
  } catch (error) {
    updateMessage(assistantIndex, {
      role: "assistant",
      title: "这次没有连上服务",
      subtitle: "请再发一次，我会继续接着答",
      body: error instanceof Error ? error.message : "未知错误",
      streaming: false,
      meta: [],
      actions: []
    });
  } finally {
    setBusy(false);
  }
}

function inferAssistantTitle(meta) {
  const explicitTitle = String(meta?.title || "").trim();
  if (explicitTitle) return explicitTitle;
  if (meta?.suggested_mode === "delivery") return "BYDFI GPT · 问题推进";
  if (meta?.suggested_mode === "code") return "BYDFI GPT · 实现路径";
  return "BYDFI GPT";
}

function inferAssistantSubtitle(meta) {
  return "";
}

function buildMetaChips(meta = {}) {
  return [];
}

async function apiPost(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      clientId: getClientId(),
      ...(payload || {})
    })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

async function loadSupportData() {
  renderTaskList();
  renderStatus();
  try {
    const [tasksResponse, enterpriseResponse] = await Promise.all([
      apiPost("/api/lark-agent/tasks", {}),
      apiPost("/api/enterprise/status", {})
    ]);

    state.taskSnapshot = tasksResponse;
    state.tasks = Array.isArray(tasksResponse.tasks) ? tasksResponse.tasks : [];
    state.enterprise = enterpriseResponse.enterprise || null;
    state.lark = enterpriseResponse.lark || null;
    state.session = enterpriseResponse.whoami || null;

    state.selectedTask = getSelectedTask();
  } catch (error) {
    console.error("support data load failed", error);
  }

  renderTaskList();
  renderSelectedTask();
  renderStatus();
  renderSuggestions();
  renderComposerMeta();
}

async function runJudgeDemo(prompt, demoId) {
  setBusy(true);
  try {
    const data = await apiPost("/api/event-bypass/demo", {
      demoId: demoId || "",
      prompt: prompt || (getSelectedTask()?.action_prompt || getSelectedTask()?.summary || "韩国召回活动一直卡住，帮我生成评委演示。"),
      selectedTask: getSelectedTask(),
      history: buildHistory()
    });
    const demo = data.demo || {};
    addMessage({
      role: "assistant",
      title: "BYDFI GPT · Judge Demo",
      subtitle: demo?.task?.title || "评委演示",
      body: [
        "Judge Demo 已生成。",
        "",
        `- Demo ID：${demo.demoId || ""}`,
        `- 评委总分：${demo.judge?.total || 0}/100`,
        `- 判定：${demo.judge?.verdict || "待评估"}`,
        `- Presenter 标题：${demo.presenter?.headline || ""}`,
        "",
        "Presenter 脚本：",
        ...(demo.presenter?.script || []).map((item, index) => `${index + 1}. ${item}`)
      ].join("\n"),
      meta: ["已生成 Judge Demo"],
      actions: [
        { label: "打开 Judge Demo", type: "open_url", url: `/judge-demo.html?demoId=${encodeURIComponent(demo.demoId || "")}` },
        { label: "导出 Judge 报告", type: "judge_export", demoId: demo.demoId || "" }
      ]
    });
  } catch (error) {
    addMessage({
      role: "assistant",
      title: "Judge Demo 生成失败",
      subtitle: "请再试一次",
      body: error instanceof Error ? error.message : "未知错误"
    });
  } finally {
    setBusy(false);
  }
}

async function runJudgeExport(demoId, prompt) {
  setBusy(true);
  try {
    const data = await apiPost("/api/event-bypass/export", {
      demoId: demoId || "",
      prompt: prompt || (getSelectedTask()?.action_prompt || getSelectedTask()?.summary || "韩国召回活动一直卡住，帮我导出评委材料。"),
      selectedTask: getSelectedTask(),
      history: buildHistory()
    });
    const exported = data.exported || {};
    addMessage({
      role: "assistant",
      title: "BYDFI GPT · 导出完成",
      subtitle: data.demoId || "Judge Report",
      body: [
        "Judge 报告和 Session Pack 已导出。",
        "",
        ...(exported.files || []).map((item) => `- ${item.type}：${item.path}`)
      ].join("\n"),
      meta: ["已写入服务器导出目录"],
      actions: data.demoId ? [
        { label: "打开 Judge Demo", type: "open_url", url: `/judge-demo.html?demoId=${encodeURIComponent(data.demoId)}` }
      ] : []
    });
  } catch (error) {
    addMessage({
      role: "assistant",
      title: "导出失败",
      subtitle: "请再试一次",
      body: error instanceof Error ? error.message : "未知错误"
    });
  } finally {
    setBusy(false);
  }
}

async function runDiagnose(taskId) {
  if (taskId) setSelectedTask(taskId);
  const task = getSelectedTask() || state.tasks[0];
  if (!task) {
    addMessage({ role: "assistant", title: "还没有拿到可诊断的问题", subtitle: "请先稍后再试", body: "案例列表还没加载完成。" });
    return;
  }

  setBusy(true);
  try {
    const data = await apiPost("/api/diagnose", {
      task,
      taskText: task.summary
    });
    state.diagnosis = {
      ...(data.diagnosis || {}),
      task_id: task.id
    };
    renderDiagnosis();
    addMessage({
      role: "assistant",
      title: "BYDFI GPT · 诊断结果",
      subtitle: task.title,
      body: [
        `我已经把这个问题压成结构化诊断。`,
        "",
        `- 阻塞节点：${state.diagnosis?.block_node || task.block_node || "未知"}`,
        `- Owner 状态：${formatOwnerStatus(state.diagnosis?.owner_status || task.owner_status)}`,
        `- 延迟时长：${state.diagnosis?.delay_hours || task.delay_hours || 0} 小时`,
        `- 置信度：${state.diagnosis?.confidence || 0}`,
        "",
        `下一步建议：${state.diagnosis?.action_plan || "继续推进"}`,
        state.diagnosis?.override_reason ? `原因判断：${state.diagnosis.override_reason}` : ""
      ].filter(Boolean).join("\n"),
      meta: ["已完成结构化诊断"],
      actions: [{ label: "生成交付结果", type: "generate", taskId: task.id }]
    });
  } catch (error) {
    addMessage({ role: "assistant", title: "诊断没有完成", subtitle: task.title, body: error instanceof Error ? error.message : "未知错误" });
  } finally {
    setBusy(false);
  }
}

async function runGenerate(taskId) {
  if (taskId) setSelectedTask(taskId);
  const task = getSelectedTask() || state.tasks[0];
  if (!task) {
    addMessage({ role: "assistant", title: "还没有可生成的案例", subtitle: "请先锁定问题", body: "请先选择一个案例。" });
    return;
  }

  setBusy(true);
  try {
    const data = await apiPost("/api/force-override", {
      task,
      diagnosis: state.diagnosis || {},
      prompt: task.action_prompt || task.summary || "生成活动配置"
    });
    state.delivery = data;
    renderDelivery();
    const rewardJson = prettyJson(data.generated?.json || {});
    addMessage({
      role: "assistant",
      title: "BYDFI GPT · 交付结果",
      subtitle: task.title,
      body: [
        "我已经把这个问题压成交付结果。",
        "",
        `- 来源：${data.source || data.generated?.source || "enterprise-agent-local"}`,
        `- 编译器：${data.generated?.compiler_version || "enterprise-agent.override.v1"}`,
        `- 下一步：${data.next_step || "先检查生成结果，再决定导入或接 API"}`,
        "",
        "标准化 JSON：",
        "```json",
        rewardJson,
        "```"
      ].join("\n"),
      actions: [],
      meta: ["已生成标准化交付结果"]
    });
  } catch (error) {
    addMessage({ role: "assistant", title: "交付结果没有生成成功", subtitle: task.title, body: error instanceof Error ? error.message : "未知错误" });
  } finally {
    setBusy(false);
  }
}

function openPanel(forceOpen) {
  const panel = $("capabilityPanel");
  if (!panel) return;
  const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : !state.panelOpen;
  state.panelOpen = shouldOpen;
  document.body.classList.toggle("panel-open", shouldOpen);
  panel.classList.toggle("hidden", !shouldOpen);
  panel.setAttribute("aria-hidden", shouldOpen ? "false" : "true");
}

function initParticleCanvas() {
  const canvas = document.getElementById("particle-canvas");
  if (!canvas || typeof canvas.getContext !== "function") return;

  const context = canvas.getContext("2d");
  if (!context) return;

  const mouse = { x: -1000, y: -1000, radius: 180 };
  let particles = [];
  const palette = [
    { fill: "143,245,255", glow: "110,231,255" },
    { fill: "214,116,255", glow: "214,116,255" }
  ];

  const resize = () => {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(window.innerWidth * ratio);
    canvas.height = Math.floor(window.innerHeight * ratio);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.scale(ratio, ratio);
    particles = buildParticles(window.innerWidth, window.innerHeight);
  };

  const buildParticles = (width, height) => {
    const count = Math.min(1080, Math.max(260, Math.floor((width * height) / 1600)));
    return Array.from({ length: count }, () => {
      const tone = palette[Math.floor(Math.random() * palette.length)];
      const opacity = 0.1 + Math.random() * 0.22;
      const glow = 2 + Math.random() * 8;
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        baseX: Math.random() * width,
        baseY: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        size: Math.random() * 1.2 + 0.3,
        density: Math.random() * 30 + 1,
        glow,
        color: `rgba(${tone.fill},${opacity.toFixed(3)})`,
        glowColor: `rgba(${tone.glow},${Math.min(opacity + 0.12, 0.4).toFixed(3)})`
      };
    });
  };

  const updateParticle = (particle, width, height) => {
    const dx = mouse.x - particle.x;
    const dy = mouse.y - particle.y;
    const distance = Math.sqrt(dx * dx + dy * dy) || 1;

    if (distance < mouse.radius) {
      const force = (mouse.radius - distance) / mouse.radius;
      const dirX = (dx / distance) * force * particle.density;
      const dirY = (dy / distance) * force * particle.density;
      particle.vx += dirY * 0.05;
      particle.vy -= dirX * 0.05;
      particle.vx -= dirX * 0.1;
      particle.vy -= dirY * 0.1;
    }

    particle.vx *= 0.96;
    particle.vy *= 0.96;
    particle.x += particle.vx + (particle.baseX - particle.x) * 0.01;
    particle.y += particle.vy + (particle.baseY - particle.y) * 0.01;

    if (particle.x < 0) particle.x = width;
    if (particle.x > width) particle.x = 0;
    if (particle.y < 0) particle.y = height;
    if (particle.y > height) particle.y = 0;
  };

  const draw = () => {
    const width = window.innerWidth;
    const height = window.innerHeight;
    context.fillStyle = "rgba(0, 0, 0, 0.2)";
    context.fillRect(0, 0, width, height);

    for (const particle of particles) {
      updateParticle(particle, width, height);
      context.shadowBlur = particle.glow;
      context.shadowColor = particle.glowColor;
      context.fillStyle = particle.color;
      context.beginPath();
      context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
      context.fill();
    }
    context.shadowBlur = 0;
    context.shadowColor = "transparent";

    requestAnimationFrame(draw);
  };

  window.addEventListener("mousemove", (event) => {
    mouse.x = event.clientX;
    mouse.y = event.clientY;
  });

  window.addEventListener("mouseleave", () => {
    mouse.x = -1000;
    mouse.y = -1000;
  });

  window.addEventListener("mousedown", () => {
    mouse.radius = 320;
    window.setTimeout(() => {
      mouse.radius = 180;
    }, 400);
  });

  window.addEventListener("resize", resize);
  resize();
  draw();
}

function startNewChat() {
  state.messages = [];
  setSelectedTask("");
  state.currentMode = "company";
  state.diagnosis = null;
  state.delivery = null;
  renderComposerMeta();
  renderChatFeed();
  const input = $("promptInput");
  if (input) {
    input.value = "";
    input.focus();
    autoResizePrompt();
  }
}

function bindEvents() {
  $("btnSend")?.addEventListener("click", () => sendPrompt());
  $("btnNewChat")?.addEventListener("click", () => startNewChat());
  $("btnClosePanel")?.addEventListener("click", () => openPanel(false));
  $("panelBackdrop")?.addEventListener("click", () => openPanel(false));
  $("btnDiagnose")?.addEventListener("click", () => runDiagnose());
  $("btnGenerate")?.addEventListener("click", () => runGenerate());
  $("promptInput")?.addEventListener("input", autoResizePrompt);
  $("promptInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendPrompt();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.panelOpen) {
      openPanel(false);
    }
  });
}

function init() {
  initParticleCanvas();
  bindEvents();
  autoResizePrompt();
  renderSuggestions();
  renderSessions();
  renderTaskList();
  renderSelectedTask();
  renderDiagnosis();
  renderDelivery();
  renderStatus();
  renderComposerMeta();
  renderChatFeed();
  loadSupportData();
}

init();
