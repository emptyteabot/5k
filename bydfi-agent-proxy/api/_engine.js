const { runHarness } = require("./harness/runtime");
const { validateHarnessResult } = require("./harness/validators");
const { buildHermesAnswer } = require("./hermes_bridge");

const LIVE_BASE = "http://43.135.51.214";

const COMPANY_PACK = {
  positioning: "BYDFI AgentOS 的定位不是聊天工具，而是面向公司内部的增长执行代理入口。",
  value: [
    "把分散在群聊、任务、纪要和报告里的信息，压成一个统一执行入口。",
    "员工不用先到处问人、翻群、翻文档，直接把事情丢进来就能先得到一轮结果。",
    "管理层关心的不是模型名，而是能不能更快发现卡点、锁责任链、推进增长项目上线。",
    "遇到推进类问题时，它不只解释，还能继续给出动作稿、推进路径和交付草案。",
    "前台保持极简，复杂能力下沉到底层记忆、技能、工具和审批逻辑。"
  ],
  usageExamples: [
    "这个流程到底怎么走？",
    "这件事现在卡在哪，下一步找谁？",
    "帮我用最短的话讲清楚某次历史决策。",
    "帮我写一封中文邮件催进度。",
    "某个项目为什么迟迟没推进？"
  ]
};

const CUSTOMER_PACK = {
  positioning: "当前阶段先不强行把叙事放到官网和客户侧，优先把全公司内部普及这件事做透。",
  products: [
    "先把流程问答、责任链诊断、资料检索、动作起草做成全员可用的基础能力。",
    "再把部门技能做成可调用的 skill，而不是散落在个人经验里。",
    "等内部入口跑顺之后，再考虑把外部客户场景接进同一套 runtime。 "
  ],
  customerValue: [
    "先把公司内部的重复沟通和重复检索压下来。",
    "先把关键人的经验沉淀成 skill 和记忆资产。",
    "先让网页对话框成为全员统一入口，再扩展到其他场景。"
  ]
};

const TRANSLATION_PACK = {
  updatedAt: "2026-04-09 15:59（Asia/Shanghai）",
  conclusion: "近一年翻译主线相关的 Lark 证据，在当前账号可见范围内已经基本收齐，关键群和关键链路没有明显漏口。",
  caution: "不能承诺近一年所有相关消息 100% 无遗漏。",
  coverage: "正式注册必需群 8 个，当前主线覆盖没有 missing 和 unverified。",
  evidence: "4 月 2 日群内同步明确：当前先推 P0，重点是专业术语、footer 和法律页术语；3500+ 缺口清单已经准备好，Stone 和 Christina 的确认是主要卡点。",
  citations: [
    {
      title: "BYDFI翻译任务近一年Lark最终核验版",
      sourceLabel: "本地翻译核验",
      path: "BYDFI/output/translation_final_check_20260409.md",
      snippet: "结论是主线基本收齐，但不能承诺 100% 无遗漏；剩余边界集中在少数私聊可见性和个别群的自动重进稳定性。"
    },
    {
      title: "AI翻译交流近一年采集结果",
      sourceLabel: "本地翻译采集",
      path: "BYDFI/output/collect_ai_translation_1y_20260408.json",
      snippet: "4 月 2 日同步中明确了 P0/P1 分层、Stone 负责冲突词确认、Christina 负责小语种 UI 约束确认，法务词条待定。"
    }
  ]
};

const LEAKY_PHRASES = [
  "我已经先命中了",
  "知识卡命中",
  "本轮走了本地兜底",
  "Harness rejected",
  "当前没有锁定明确案例",
  "已启用证据优先兜底回答",
  "围绕某个",
  "命中到可用的结构化证据"
];

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
    .replace(/\s+/g, "")
    .replace(/[!！?？,，。:：;；"'`]/g, "");
}

function withTimeout(factory, timeoutMs = 12000) {
  return Promise.race([
    factory(),
    new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), timeoutMs))
  ]);
}

async function fetchJson(path, body = {}, timeoutMs = 12000) {
  return withTimeout(async () => {
    const response = await fetch(`${LIVE_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`${path} ${response.status}`);
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
  if (/README\.md|ngrok|FEISHU_VERIFICATION_TOKEN|Claude Audit|知识卡命中|兜底/i.test(answer)) {
    return null;
  }
  return {
    title: String(payload.title || "BYDFI AgentOS").trim() || "BYDFI AgentOS",
    answer,
    citations: Array.isArray(payload.citations) ? payload.citations.slice(0, 3) : []
  };
}

async function fetchLiveChatAnswer(message, clientId) {
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

function isTranslationQuestion(message) {
  return /翻译|术语|小语种|法律页|footer|法务词条/i.test(message);
}

function isWholeCompanyQuestion(message) {
  return /整个公司|全公司|公司级|对公司有用|对整个公司有用|为什么全员都能用|适合全员|百事通/i.test(message);
}

function isValueQuestion(message) {
  return /有价值吗|有没有价值|值不值|这个东西值钱吗/.test(normalizeMessage(message));
}

function isGreeting(message) {
  return /^(你好|您好|hi|hello|哈喽|嗨|在吗|有人吗|hey)$/i.test(normalizeMessage(message));
}

function isHackathonQuestion(message) {
  return /黑客松|做了什么|到底做了什么|项目说明|项目介绍|作品说明|我做了什么/.test(message);
}

function isInfrastructureQuestion(message) {
  return /底层金融基础设施|基础设施|harness|hareness|agentos|skillmesh|多agent|multi-agent|金融agent/i.test(normalizeMessage(message));
}

function isCustomerQuestion(message) {
  return /客户|用户|官网|官网结合|充值|提币|KYC|跟单|合约|现货|机器人|MoonX|返佣|邀请|Affiliate|API|Proof of Reserves/i.test(message);
}

function isProductUsageQuestion(message) {
  return /怎么用|如何用|这玩意怎么用|这个产品怎么用|这个网站怎么用|bydfigpt是什么|你可以做什么|你能做什么|你会做什么|能帮我什么|有什么能力|做什么|能做什么|会做什么/.test(normalizeMessage(message).toLowerCase());
}

function isScopeQuestion(message) {
  return /某个流程|历史决策|说不明白|最短的话说明白|流程或历史决策/i.test(message);
}

function isTriageQuestion(message) {
  return /群聊|工单|行动清单|优先级|责任人|帮我整理|整理这段|整理下面|消息整理/i.test(message);
}

function isBlameQuestion(message) {
  return /谁在拖后腿|谁的问题|谁该背锅/i.test(message);
}

function isWeekdayQuestion(message) {
  return /星期几|周几|今天几号|今天日期|几点|时间|现在几点/.test(message);
}

function isEmailQuestion(message) {
  return /写一封.*邮件|写封邮件|催一下.*进度|发个邮件/i.test(message);
}

function inferTopic(message) {
  if (isTranslationQuestion(message)) return "翻译进度";
  if (/韩国|召回|奖励/.test(message)) return "韩国召回活动";
  if (/SEO|收录|热点页/i.test(message)) return "SEO 进度";
  return "当前事项";
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
    ? "当前最大问题不是没人做，而是责任人和 ETA 还没有被锁定。"
    : `当前责任清晰度是 ${task.owner_status}。`;
  return {
    title: task.title,
    answer: [
      `${task.title}目前仍然卡在 ${task.block_node}，属于 ${task.severity} 级问题。`,
      `涉及团队：${task.team}。累计延迟大约 ${task.delay_hours} 小时。`,
      ownerLine,
      "最短推进路径：今天先锁定产品负责人和技术负责人，再把验收口径、ETA 和风险边界一次性写进同一个执行单。"
    ].join("\n"),
    citations: [
      {
        title: task.title,
        sourceLabel: "企业任务快照",
        path: "embedded_demo.tasks",
        snippet: `${task.summary} ${task.evidence_excerpt}`.trim()
      }
    ]
  };
}

function buildWholeCompanyAnswer() {
  return {
    title: "公司级入口",
    answer: [
      COMPANY_PACK.positioning,
      ...COMPANY_PACK.value.map((item) => `- ${item}`),
      "",
      "适合全员直接问的典型问题：",
      ...COMPANY_PACK.usageExamples.map((item) => `- ${item}`)
    ].join("\n"),
    citations: []
  };
}

function buildValueAnswer() {
  return {
    title: "有价值",
    answer: [
      "有价值，但前提是把它定义成增长执行系统，而不是普通聊天网页。",
      "- 如果它只是回答问题，它很容易同质化。",
      "- 如果它能把项目卡点、责任链和推进动作压进一个统一网页入口，它就有真实价值。",
      "- 对员工，它降低找流程、找责任人、找历史决策的时间成本。",
      "- 对管理层，它缩短从发现问题到锁定下一步的链路。",
      "- 对业务，它能让活动、增长、协作这类项目更快推进到可交付结果。"
    ].join("\n"),
    citations: []
  };
}

function buildGreetingAnswer() {
  return {
    title: "BYDFI AgentOS",
    answer: [
      "你好。我是 BYDFI AgentOS。",
      "直接把问题、项目名、群聊、材料或数据发给我。",
      "我会先帮你整理问题、判断责任链、给出下一步，必要时直接起草动作稿。"
    ].join("\n"),
    citations: []
  };
}

function buildCustomerAnswer(message) {
  const text = String(message || "");
  let lead = CUSTOMER_PACK.positioning;

  if (/充值|提币|KYC/i.test(text)) {
    lead = "这些场景当然能接，但当前黑客松阶段不建议先把重点放在官网客户路径上。";
  } else if (/跟单|合约|现货|机器人|MoonX/i.test(text)) {
    lead = "这些业务词先不要硬塞进首页叙事。当前更稳的策略是先把内部工作入口跑顺。";
  } else if (/返佣|邀请|affiliate/i.test(text)) {
    lead = "增长和活动场景可以后接，但不该成为这次黑客松的主叙事。";
  } else if (/api|proof of reserves|储备金|安全/i.test(text)) {
    lead = "技术接入和安全透明度可以留作后续扩展，但当前先不要分散主线。";
  }

  return {
    title: "先做内部入口",
    answer: [
      lead,
      "",
      "当前更稳的推进顺序：",
      ...CUSTOMER_PACK.products.map((item) => `- ${item}`),
      "",
      "这么做的直接价值：",
      ...CUSTOMER_PACK.customerValue.map((item) => `- ${item}`)
    ].join("\n"),
    citations: []
  };
}

function buildHackathonAnswer() {
  return {
    title: "黑客松项目",
    answer: [
      "这次黑客松我做的不是一个套壳聊天网页，而是一个部署在云服务器上的内部执行代理。",
      "- 水面上，它是一个极简中文对话框，任何员工都可以直接提问。",
      "- 水面下，它接任务快照、专项资料、长期记忆和工具调用，形成一个执行内核。",
      "- 它解决的不是单纯问答，而是项目卡住、信息分散、责任不清、推进太慢的问题。",
      "- 首版我把范围收在三类最常见任务：项目诊断、整理消息和文档、生成推进内容。",
      "- 它真正的差异化不在聊天，而在执行下潜：先判断问题属于谁、卡在哪，再继续给责任链、推进路径和可交付结果。"
    ].join("\n"),
    citations: []
  };
}

function buildInfrastructureAnswer() {
  return {
    title: "BYDFI AgentOS",
    answer: [
      "这套东西的方向不是聊天玩具，而是部署在云服务器上的内部执行代理。",
      "我参考的是 Hermes Agent 这类自托管 agent 的思路：记忆、skills、工具调用、持续执行。",
      "前台保持极简中文对话框，后台切到 harness-first：Skill 层、Tool 层、Memory 层、Approval 层分开。",
      "Tool 层负责查资料、查任务、查文档、整理结果、生成动作稿。",
      "Memory 层负责把群聊、文档、周报、专项 PDF 压成统一记忆，而不是散在聊天记录里。",
      "Approval 层负责把高风险动作拦住，确保它能长期放在公司里跑。"
    ].join("\n"),
    citations: []
  };
}

function buildUsageAnswer() {
  return {
    title: "BYDFI AgentOS 用法",
    answer: [
      "你可以把我当成一个直接干活的网页入口，不只是聊天。",
      "首版我先做三类事：整理消息和文档、分析数据、生成内容。",
      "你直接把群聊、需求、工单、指标、背景材料丢进来就行。",
      "我会先给你结论、责任链和下一步，必要时继续写成邮件、报告或行动清单。",
      "",
      "常见问法：",
      "- 这件事现在卡在哪，下一步找谁？",
      "- 帮我整理这段群聊，给我行动清单。",
      "- 帮我分析这组数据，告诉我异常和建议动作。",
      "- 帮我写一封中文邮件催进度。"
    ].join("\n"),
    citations: []
  };
}

function buildWeekdayAnswer() {
  return {
    title: "当前时间",
    answer: `现在是 ${nowText()}。`,
    citations: []
  };
}

function buildScopeAnswer() {
  return {
    title: "先缩小范围",
    answer: "先告诉我具体是哪个业务线、哪个流程或哪次决策，最好再带上时间范围。我拿到这三个信息后，才能用最短的话给你讲清楚，并告诉你下一步找谁。",
    citations: []
  };
}

function buildBlameAnswer() {
  return {
    title: "先定范围",
    answer: "这个问题不能泛问。先给我具体到业务线、项目名和时间范围，我再按责任链告诉你卡点在哪、该找谁，不会直接把系统性阻塞硬算到某个人头上。",
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
      `想跟进一下 ${topic} 的当前进度。为了避免后续继续卡住，麻烦今天帮我确认三件事：`,
      "1. 当前责任人是谁；",
      "2. 还缺什么前置确认；",
      "3. 预计何时可以给出明确结论或下一版结果。",
      "",
      "如果有我这边需要配合补充的资料，也请直接告诉我，我这边会同步跟进。",
      "",
      "谢谢。"
    ].join("\n"),
    citations: []
  };
}

function buildTriageAnswer(message) {
  const text = String(message || "");
  const signals = [];
  const owners = [];
  const actions = [];

  if (/产品|排期/.test(text)) {
    signals.push("产品排期没有锁定");
    owners.push("产品");
    actions.push("今天确认产品负责人和排期结论");
  }
  if (/技术|研发|ETA/.test(text)) {
    signals.push("技术 ETA 还没有确认");
    owners.push("研发");
    actions.push("把研发 ETA 收口到一个明确时间点");
  }
  if (/法务|词条|口径/.test(text)) {
    signals.push("法务口径还没有收口");
    owners.push("法务");
    actions.push("把法务口径和最终文案一次性确认");
  }
  if (/运营|明天要给结果|上线/.test(text)) {
    signals.push("业务侧存在明确交付时间压力");
    owners.push("运营");
    actions.push("由运营统一收口当前状态并对外同步一个版本");
  }

  if (!signals.length) {
    signals.push("当前材料里能看出这件事还在多人协作状态，但责任链和时间点没有完全锁定");
    actions.push("先锁定负责人、时间点和验收口径");
  }

  const uniqueOwners = [...new Set(owners)];
  const uniqueActions = [...new Set(actions)];
  const priority = /今天|明天|马上|上线|卡住/.test(text) ? "P0" : "P1";

  return {
    title: "整理结果",
    answer: [
      `优先级：${priority}`,
      `问题：${signals.join("；")}。`,
      `责任人：${uniqueOwners.length ? uniqueOwners.join(" / ") : "当前材料里还没有完全锁定，建议先补负责人。"}。`,
      "下一步：",
      ...uniqueActions.map((item) => `- ${item}`),
      "- 把以上三项收口到同一个执行单里，避免继续来回追人"
    ].join("\n"),
    citations: []
  };
}

function buildTranslationAnswer(message) {
  const wantsOwner = /谁在负责|谁在推进|找谁|责任人/.test(message);
  const wantsStatus = /怎么样|进度|做得怎么样|情况/.test(message);
  const wantsBlame = /谁在拖后腿|谁卡住了/.test(message);

  let answer = TRANSLATION_PACK.conclusion;
  if (wantsStatus || !wantsOwner) {
    answer += `\n${TRANSLATION_PACK.caution}`;
    answer += `\n${TRANSLATION_PACK.coverage}`;
  }
  if (wantsOwner || wantsBlame) {
    answer += "\n当前推进主要卡在三类确认：Stone 负责冲突词口径，Christina 负责小语种 UI 约束，法务负责法律词条口径。Yohan 在做统筹、补齐和同步。";
    if (wantsBlame) {
      answer += "\n这更像确认链条未闭环，不建议直接把它描述成某个人在拖后腿。";
    }
  }
  answer += `\n最近的明确信号是：${TRANSLATION_PACK.evidence}`;
  answer += "\n如果你现在就要推进，优先顺序是：先找 Stone 确认冲突词，再找 Christina 确认小语种长度约束，法律词条再拉法务收口。";

  return {
    title: "翻译进度",
    answer,
    citations: TRANSLATION_PACK.citations
  };
}

function buildFallbackAnswer(status) {
  const indexed = status?.enterprise?.indexedDocs;
  const base = indexed
    ? `我这边现在能继续调到大约 ${indexed} 份内部资料。`
    : "我这边现在能继续调内部资料。";
  return {
    title: "先把事情说具体",
    answer: [
      `${base}`,
      "你这句还太泛。我建议你直接补这四个信息：",
      "- 具体是哪件事",
      "- 涉及哪个项目或业务线",
      "- 大概是什么时间范围",
      "- 你现在最想要的是结论、责任链，还是下一步",
      "",
      "你也可以直接点下面那三种常见入口开始。"
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

async function buildAnswer(message, clientId = "public-web") {
  const normalizedMessage = String(message || "").trim();
  const hermesAnswer = await buildHermesAnswer(normalizedMessage, clientId).catch(() => null);
  if (hermesAnswer?.answer) {
    return hermesAnswer;
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
      shouldContainAny: ["你好", "BYDFI AgentOS"]
    },
    {
      id: "weekday",
      priority: 98,
      match: (ctx) => isWeekdayQuestion(ctx.message),
      run: async () => buildWeekdayAnswer()
    },
    {
      id: "infrastructure",
      priority: 96,
      match: (ctx) => isInfrastructureQuestion(ctx.message),
      run: async () => buildInfrastructureAnswer(),
      shouldContainAny: ["harness-first", "Skill", "Memory", "Approval"]
    },
    {
      id: "value",
      priority: 95,
      match: (ctx) => isValueQuestion(ctx.message),
      run: async () => buildValueAnswer(),
      shouldContainAny: ["执行系统", "价值"]
    },
    {
      id: "hackathon",
      priority: 94,
      match: (ctx) => isHackathonQuestion(ctx.message),
      run: async () => buildHackathonAnswer(),
      shouldContainAny: ["执行代理", "网页入口", "云服务器"]
    },
    {
      id: "whole-company",
      priority: 92,
      match: (ctx) => isWholeCompanyQuestion(ctx.message),
      run: async () => buildWholeCompanyAnswer(),
      shouldContainAny: ["全员", "公司"]
    },
    {
      id: "customer",
      priority: 90,
      match: (ctx) => isCustomerQuestion(ctx.message),
      run: async (ctx) => buildCustomerAnswer(ctx.message),
      shouldContainAny: ["内部入口", "全公司", "skill"]
    },
    {
      id: "usage",
      priority: 88,
      match: (ctx) => isProductUsageQuestion(ctx.message),
      run: async () => buildUsageAnswer(),
      shouldContainAny: ["能做", "流程", "责任链", "推进"]
    },
    {
      id: "email",
      priority: 86,
      match: (ctx) => isEmailQuestion(ctx.message),
      run: async (ctx) => buildEmailAnswer(ctx.message),
      shouldContainAny: ["主题：", "确认", "进度"]
    },
    {
      id: "triage",
      priority: 85,
      match: (ctx) => isTriageQuestion(ctx.message),
      run: async (ctx) => buildTriageAnswer(ctx.message),
      shouldContainAny: ["优先级", "责任人", "下一步"]
    },
    {
      id: "scope",
      priority: 84,
      match: (ctx) => isScopeQuestion(ctx.message),
      run: async () => buildScopeAnswer()
    },
    {
      id: "blame",
      priority: 82,
      match: (ctx) => isBlameQuestion(ctx.message) && !isTranslationQuestion(ctx.message),
      run: async () => buildBlameAnswer(),
      shouldContainAny: ["业务线", "责任链", "时间范围"]
    },
    {
      id: "translation",
      priority: 80,
      match: (ctx) => isTranslationQuestion(ctx.message),
      run: async (ctx) => buildTranslationAnswer(ctx.message),
      shouldContainAny: ["Stone", "Christina", "翻译"]
    },
    {
      id: "task-diagnosis",
      priority: 50,
      match: async (ctx) => !!(await ctx.tools.getTask()),
      run: async (ctx) => formatTaskAnswer(await ctx.tools.getTask()),
      shouldContainAny: ["责任", "推进", "卡在"]
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
