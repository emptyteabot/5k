const { runHarness } = require("./harness/runtime");
const { validateHarnessResult } = require("./harness/validators");
const { buildHermesAnswer } = require("./hermes_bridge");
const { config } = require("./_config");

const LIVE_BASE = config.upstreamAgentBase;

const LEAKY_PHRASES = [
  "我已经先命中到",
  "知识卡命中",
  "本轮走了本地兜底",
  "Harness rejected",
  "当前没有锁定明确案例",
  "已启用证据优先兜底回答",
  "围绕某个",
  "命中到可用的结构化证据"
];

const TRANSLATION_PACK = {
  title: "翻译推进状态",
  answer: [
    "当前能看到的主线结论是：翻译相关资料基本收齐，但不能承诺 100% 无遗漏。",
    "真正卡点不在有没有人提，而在确认链条没有完全闭环。",
    "Stone 负责冲突术语口径，Christina 负责小语种 UI 约束，法务口径还需要统一收口。",
    "如果你现在就要推进，顺序应该是：先锁 Stone 的术语结论，再锁 Christina 的界面约束，最后让法务一次性确认法律文案。"
  ].join("\n"),
  citations: [
    {
      title: "翻译任务年度核验",
      sourceLabel: "本地翻译核验",
      path: "BYDFI/output/translation_final_check_20260409.md",
      snippet: "主线资料基本收齐，但私聊可见性和个别群的增量同步仍然存在边界。"
    },
    {
      title: "AI 翻译群近一年采集结果",
      sourceLabel: "本地翻译采集",
      path: "BYDFI/output/collect_ai_translation_1y_20260408.json",
      snippet: "4 月 2 日群内已明确 P0/P1 分层，术语、UI 约束、法务口径是当前关键节点。"
    }
  ]
};

function nowText() {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(new Date());
}

function normalizeMessage(message) {
  return String(message || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "");
}

function withTimeout(factory, timeoutMs = 12000) {
  return Promise.race([
    factory(),
    new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), timeoutMs))
  ]);
}

async function fetchJson(apiPath, body = {}, timeoutMs = 12000) {
  if (!LIVE_BASE) throw new Error("live_base_not_configured");
  return withTimeout(async () => {
    const response = await fetch(`${LIVE_BASE}${apiPath}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`${apiPath} ${response.status}`);
    return response.json();
  }, timeoutMs);
}

function parseSseBlock(block) {
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

function sanitizeLiveAnswer(payload) {
  if (!payload || typeof payload !== "object") return null;
  let answer = String(payload.answer || "").trim();
  if (!answer) return null;
  for (const phrase of LEAKY_PHRASES) {
    answer = answer.replaceAll(phrase, "");
  }
  answer = answer.replace(/^[:：\s]+/, "").trim();
  if (!answer) return null;
  if (/README\.md|ngrok|FEISHU_VERIFICATION_TOKEN|Claude Audit|Harness rejected/i.test(answer)) {
    return null;
  }
  return {
    title: String(payload.title || "BYDFI GPT").trim() || "BYDFI GPT",
    answer,
    citations: Array.isArray(payload.citations) ? payload.citations.slice(0, 4) : []
  };
}

async function fetchLiveChatAnswer(message, clientId) {
  if (!LIVE_BASE) return null;
  return withTimeout(async () => {
    const response = await fetch(`${LIVE_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clientId, message })
    });
    if (!response.ok || !response.body) throw new Error(`chat_stream_${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let donePayload = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const parsed = parseSseBlock(block);
        if (parsed.event === "done") donePayload = parsed.payload;
        boundary = buffer.indexOf("\n\n");
      }
    }

    return sanitizeLiveAnswer(donePayload);
  }, 22000);
}

function isGreeting(message) {
  return /^(你好|您好|hi|hello|hey|在吗|有人吗|哈喽)$/.test(normalizeMessage(message));
}

function isTimeQuestion(message) {
  return /(星期几|周几|今天几号|今天日期|几点|时间|现在几点)/.test(message);
}

function isUsageQuestion(message) {
  const normalized = normalizeMessage(message);
  return /(你可以做什么|你能做什么|怎么用|如何用|这个网站怎么用|bydfigpt是什么|你是什么|有什么能力)/.test(normalized);
}

function isEmailQuestion(message) {
  return /(写一封.*邮件|写封邮件|催一下进度|发个邮件)/.test(message);
}

function isTriageQuestion(message) {
  return /(群聊|工单|行动清单|优先级|责任人|帮我整理|整理这段|整理下面|消息整理)/.test(message);
}

function isScopeQuestion(message) {
  return /(某个流程|历史决策|最短的话说明白|流程或历史决策|下一步找谁)/.test(message);
}

function isBlameQuestion(message) {
  return /(谁在拖后腿|谁的问题|谁该背锅)/.test(message);
}

function isTranslationQuestion(message) {
  return /(翻译|术语|小语种|法律页|footer|法务文案)/i.test(message);
}

function inferTopic(message) {
  if (/翻译|术语|小语种/.test(message)) return "翻译推进";
  if (/韩国|活动|召回|奖励/.test(message)) return "活动推进";
  if (/seo|收录|热点页/i.test(message)) return "SEO 推进";
  return "当前事项";
}

function buildGreetingAnswer() {
  return {
    title: "BYDFI GPT",
    answer: "你好。我在。直接问具体问题，或者贴群聊、文档、数据，我会先给结论，再给证据和下一步。",
    citations: []
  };
}

function buildTimeAnswer() {
  return {
    title: "当前时间",
    answer: `现在是 ${nowText()}。`,
    citations: []
  };
}

function buildUsageAnswer() {
  return {
    title: "怎么用",
    answer: [
      "直接把事发出来，不用先组织格式。",
      "我现在比较稳的是四类：",
      "- 查流程、历史决策、责任链",
      "- 整理群聊、文档、需求，压成行动清单",
      "- 根据现有资料判断卡点、下一步找谁",
      "- 起草邮件、汇报、推进文案",
      "如果你手里有原始材料，直接贴进来最准。"
    ].join("\n"),
    citations: []
  };
}

function buildEmailAnswer(message) {
  const topic = inferTopic(message);
  return {
    title: "邮件草稿",
    answer: [
      `主题：请确认并推进${topic}`,
      "",
      "你好，",
      "",
      `想跟进一下 ${topic} 的当前进度。为了避免继续卡住，麻烦今天帮我确认三件事：`,
      "1. 当前责任人是谁；",
      "2. 还缺哪些前置确认；",
      "3. 预计何时能给出明确结论或下一版结果。",
      "",
      "如果需要我这边补资料或协调，也请直接说，我会同步跟进。",
      "",
      "谢谢。"
    ].join("\n"),
    citations: []
  };
}

function buildScopeAnswer() {
  return {
    title: "先给范围",
    answer: "把业务线、项目名、时间范围发我。我拿到这三个信息后，才能用最短的话说明白，并告诉你下一步找谁。",
    citations: []
  };
}

function buildBlameAnswer() {
  return {
    title: "先别泛问",
    answer: "这个问题不能空问。先给我具体到业务线、项目名和时间范围，我再按责任链告诉你卡点在哪、该找谁，不会直接把系统性问题硬扣到某个人头上。",
    citations: []
  };
}

function buildTranslationAnswer() {
  return TRANSLATION_PACK;
}

function buildTriageAnswer(message) {
  const text = String(message || "");
  const issues = [];
  const owners = [];
  const actions = [];

  if (/产品|排期/.test(text)) {
    issues.push("产品排期还没锁死");
    owners.push("产品");
    actions.push("今天先锁产品责任人和排期结论");
  }
  if (/研发|技术|eta/i.test(text)) {
    issues.push("研发 ETA 还不明确");
    owners.push("研发");
    actions.push("把研发 ETA 收口到一个确定时间点");
  }
  if (/法务|法律|条款|口径/.test(text)) {
    issues.push("法务口径还没闭环");
    owners.push("法务");
    actions.push("把法务口径和最终文案一次性确认掉");
  }
  if (/运营|上线|明天要结果|交付/.test(text)) {
    issues.push("业务侧有明确交付压力");
    owners.push("运营");
    actions.push("由运营统一收口当前状态并给出对外版本");
  }

  if (!issues.length) {
    issues.push("这件事还在多人协作，但责任链和时间点没有完全锁定");
    actions.push("先把责任人、时间点和验收口径收进同一个执行单");
  }

  const uniqueOwners = [...new Set(owners)];
  const uniqueActions = [...new Set(actions)];
  const priority = /(今天|明天|马上|上线|卡住|紧急)/.test(text) ? "P0" : "P1";

  return {
    title: "整理结果",
    answer: [
      `优先级：${priority}`,
      `问题：${issues.join("；")}。`,
      `责任人：${uniqueOwners.length ? uniqueOwners.join(" / ") : "当前材料里还没完全锁定，建议先补责任人"}。`,
      "下一步：",
      ...uniqueActions.map((item) => `- ${item}`),
      "- 把上面几项收口到同一个执行单里，避免继续来回追人"
    ].join("\n"),
    citations: []
  };
}

function findStaticTaskByMessage(message, tasks = []) {
  const text = String(message || "");
  if (/韩国|召回/.test(text)) return tasks.find((task) => task.id === "korean-bonus-stall") || null;
  if (/邀请码|404|返佣|奖励派发|链路断裂/.test(text)) return tasks.find((task) => task.id === "agent-link-break") || null;
  if (/seo|收录|热点页|假进度/i.test(text)) return tasks.find((task) => task.id === "seo-fake-progress") || null;
  return null;
}

function findTask(message, tasks = []) {
  const lower = String(message || "").toLowerCase();
  let best = null;
  let bestScore = 0;
  for (const task of tasks) {
    let score = 0;
    if (lower.includes(String(task.title || "").toLowerCase())) score += 5;
    for (const hint of task.keyword_hints || []) {
      if (lower.includes(String(hint).toLowerCase())) score += 2;
    }
    if (score > bestScore) {
      best = task;
      bestScore = score;
    }
  }
  return bestScore > 0 ? best : null;
}

function formatTaskAnswer(task) {
  const ownerLine = task.owner_status === "missing"
    ? "当前最大问题不是没人提，而是责任人和 ETA 还没被锁死。"
    : `当前责任清晰度：${task.owner_status}。`;

  return {
    title: task.title || "任务诊断",
    answer: [
      `${task.title} 目前主要卡在 ${task.block_node || "未知节点"}，属于 ${task.severity || "待定"} 级问题。`,
      `涉及团队：${task.team || "待确认"}。累计延迟大约 ${task.delay_hours || 0} 小时。`,
      ownerLine,
      "最短推进路径：先锁产品/研发负责人，再把验收口径、ETA 和风险边界写进同一张执行单。"
    ].join("\n"),
    citations: [
      {
        title: task.title || "任务快照",
        sourceLabel: "任务快照",
        path: "embedded_demo.tasks",
        snippet: `${task.summary || ""} ${task.evidence_excerpt || ""}`.trim()
      }
    ]
  };
}

function buildFallbackAnswer(status) {
  const indexed = status?.enterprise?.indexedDocs;
  const prefix = indexed ? `当前底座里可用的索引资料大约有 ${indexed} 份。` : "我这边可以继续调内部资料。";
  return {
    title: "先把问题说具体",
    answer: [
      prefix,
      "你这句还太泛。直接补这三个信息就行：",
      "- 具体是哪件事",
      "- 涉及哪个项目或业务线",
      "- 你现在最想要的是结论、责任链，还是下一步",
      "你也可以直接贴原始群聊、文档或数据。"
    ].join("\n"),
    citations: []
  };
}

function memoizeAsync(factory) {
  let started = false;
  let promise = null;
  return () => {
    if (!started) {
      started = true;
      promise = Promise.resolve().then(factory);
    }
    return promise;
  };
}

function createToolset(message, clientId) {
  const loadStatus = memoizeAsync(() => fetchJson("/api/enterprise/status", {}, 12000).catch(() => null));
  const loadTasks = memoizeAsync(async () => {
    const payload = await fetchJson("/api/lark-agent/tasks", {}, 12000).catch(() => null);
    return payload?.tasks || [];
  });
  const loadTask = memoizeAsync(async () => {
    const tasks = await loadTasks();
    return findStaticTaskByMessage(message, tasks) || findTask(message, tasks);
  });
  const loadLive = memoizeAsync(() => fetchLiveChatAnswer(message, clientId).catch(() => null));

  return {
    getStatus: loadStatus,
    getTasks: loadTasks,
    getTask: loadTask,
    getLiveAnswer: loadLive
  };
}

async function buildAnswer(message, clientId = "public-web", options = {}) {
  const normalizedMessage = String(message || "").trim();

  if (!options.skipHermes) {
    const hermesAnswer = await buildHermesAnswer(normalizedMessage, clientId).catch(() => null);
    if (hermesAnswer?.answer) return hermesAnswer;
  }

  const context = {
    message: normalizedMessage,
    clientId,
    leakyPhrases: LEAKY_PHRASES,
    tools: createToolset(normalizedMessage, clientId)
  };

  const skills = [
    {
      id: "greeting",
      priority: 100,
      match: (ctx) => isGreeting(ctx.message),
      run: async () => buildGreetingAnswer(),
      shouldContainAny: ["你好", "直接问", "下一步"]
    },
    {
      id: "time",
      priority: 96,
      match: (ctx) => isTimeQuestion(ctx.message),
      run: async () => buildTimeAnswer(),
      shouldContainAny: ["现在是"]
    },
    {
      id: "usage",
      priority: 94,
      match: (ctx) => isUsageQuestion(ctx.message),
      run: async () => buildUsageAnswer(),
      shouldContainAny: ["直接把事发出来", "责任链"]
    },
    {
      id: "email",
      priority: 92,
      match: (ctx) => isEmailQuestion(ctx.message),
      run: async (ctx) => buildEmailAnswer(ctx.message),
      shouldContainAny: ["主题：", "责任人"]
    },
    {
      id: "triage",
      priority: 90,
      match: (ctx) => isTriageQuestion(ctx.message),
      run: async (ctx) => buildTriageAnswer(ctx.message),
      shouldContainAny: ["优先级", "下一步"]
    },
    {
      id: "scope",
      priority: 88,
      match: (ctx) => isScopeQuestion(ctx.message),
      run: async () => buildScopeAnswer(),
      shouldContainAny: ["业务线", "项目名", "时间范围"]
    },
    {
      id: "blame",
      priority: 86,
      match: (ctx) => isBlameQuestion(ctx.message),
      run: async () => buildBlameAnswer(),
      shouldContainAny: ["业务线", "项目名", "时间范围"]
    },
    {
      id: "translation",
      priority: 84,
      match: (ctx) => isTranslationQuestion(ctx.message),
      run: async () => buildTranslationAnswer(),
      shouldContainAny: ["Stone", "Christina", "法务"]
    },
    {
      id: "task-diagnosis",
      priority: 60,
      match: async (ctx) => !!(await ctx.tools.getTask()),
      run: async (ctx) => formatTaskAnswer(await ctx.tools.getTask()),
      shouldContainAny: ["推进", "责任"]
    },
    {
      id: "live-chat",
      priority: 10,
      match: async () => true,
      run: async (ctx) => ctx.tools.getLiveAnswer()
    }
  ];

  return runHarness({
    context,
    skills,
    validateResult: validateHarnessResult,
    fallback: async (ctx) => buildFallbackAnswer(await ctx.tools.getStatus())
  });
}

function chunkText(text, size = 36) {
  const chunks = [];
  const value = String(text || "");
  for (let index = 0; index < value.length; index += size) {
    chunks.push(value.slice(index, index + size));
  }
  return chunks;
}

function setCors(req, res) {
  const origin = req.headers.origin || "*";
  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

module.exports = {
  buildAnswer,
  chunkText,
  setCors
};
