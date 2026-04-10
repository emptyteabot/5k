import { getAuditConsoleSnapshot } from "./_audit_console.js";
import {
  buildSessionPromptBlock,
  getRoleDefinition,
  getOrCreateSession,
  inferRoleChange,
  shouldAnswerIdentity,
  updateSession
} from "./_auth.js";
import {
  analyzeEnterpriseQuestion,
  buildEnterpriseAnalysisPromptBlock,
  maybeHandleEnterpriseAnalysis
} from "./_enterprise_analyst.js";
import { getEnterpriseSessionPolicy } from "./_enterprise_access.js";
import { getEnterpriseStatusSummary, readTextFileSafe } from "./_enterprise.js";
import { exportEventBypassBundle, generateEventBypassDemo } from "./_event_bypass.js";
import { buildKnowledgePromptBlock, getKnowledgePack } from "./_knowledge.js";
import { getEmbeddedDemoSnapshot } from "./_lark.js";
import { buildMemoryPromptBlock, getRecentMemories, rememberFact, searchMemories } from "./_memory.js";
import { buildSearchPromptBlock, searchEnterpriseIndex } from "./_search.js";
import { callOpenAIJson, listWorkspaceTree, normalizeWorkspacePath, summarizeWorkspaceTree } from "./_lib.js";

const COMPANY_KEYWORDS = ["\u516c\u53f8", "\u5458\u5de5", "\u6d41\u7a0b", "\u5236\u5ea6", "\u600e\u4e48\u7528", "\u63a8\u5e7f", "\u5165\u53e3", "\u767e\u4e8b\u901a", "\u77e5\u8bc6\u5e93"];
const DELIVERY_KEYWORDS = ["\u4ea4\u4ed8", "\u751f\u6210", "\u6d3b\u52a8", "\u5956\u52b1", "\u5bfc\u5165", "\u914d\u7f6e", "diagnose", "override", "\u5361\u4f4f"];
const CODE_KEYWORDS = ["\u4ee3\u7801", "\u4ed3\u5e93", "\u5b9e\u73b0", "\u524d\u7aef", "\u540e\u7aef", "\u5de5\u7a0b", "repo", "workspace", "git", "\u7ec8\u7aef"];
const AUDIT_KEYWORDS = ["\u5ba1\u8ba1", "\u98de\u4e66", "\u5468\u62a5", "\u7eaa\u8981", "\u770b\u677f", "\u62a5\u544a", "\u8001\u677f", "ceo"];
const PRODUCT_QUESTION_KEYWORDS = [
  "bydfi gpt",
  "这个产品",
  "这个系统",
  "这个网站",
  "这个网页",
  "怎么用",
  "是什么",
  "能做什么",
  "产品定位",
  "系统定位",
  "架构",
  "黑客松",
  "官网",
  "event-bypass",
  "judge demo",
  "presenter",
  "智能体"
];
const REQUIREMENT_LEAK_HINTS = [
  "冰山",
  "judge demo",
  "presenter",
  "event-bypass",
  "休克疗法",
  "零侵入",
  "产品边界",
  "交付物",
  "黑客松",
  "评委",
  "ppt 项目"
];
const LOW_SIGNAL_TASK_HINTS = new Set([
  "\u6d3b\u52a8",
  "\u5956\u52b1",
  "\u5361\u4f4f",
  "\u94fe\u8def",
  "\u6d41\u7a0b",
  "\u95ee\u9898",
  "\u63a8\u8fdb"
]);
const GENERIC_SCOPE_HINTS = [
  "\u67d0\u4e2a",
  "\u4e00\u4e2a",
  "\u67d0\u6bb5",
  "\u5386\u53f2\u51b3\u7b56",
  "\u6d41\u7a0b",
  "\u5236\u5ea6",
  "\u89c4\u5219",
  "\u89c4\u5b9a",
  "\u4e0d\u77e5\u9053",
  "\u8bf4\u660e\u767d",
  "\u6700\u77ed\u7684\u8bdd"
];
const GENERIC_SCOPE_RESPONSE_HINTS = [
  "\u5148\u544a\u8bc9\u6211",
  "\u5148\u7f29\u5c0f\u8303\u56f4",
  "\u54ea\u4e2a\u6d41\u7a0b",
  "\u54ea\u4e2a\u51b3\u7b56",
  "\u54ea\u6761\u4e1a\u52a1\u7ebf",
  "\u65f6\u95f4\u8303\u56f4"
];
const ALIGNMENT_IGNORE_TERMS = new Set([
  "\u516c\u53f8",
  "\u5185\u90e8",
  "\u5458\u5de5",
  "\u60c5\u51b5",
  "\u95ee\u9898",
  "\u4e8b\u60c5",
  "\u5de5\u4f5c",
  "\u63a8\u8fdb",
  "\u8fdb\u5c55",
  "\u6700\u8fd1",
  "\u76ee\u524d",
  "\u73b0\u5728",
  "\u65f6\u95f4",
  "\u65f6\u95f4\u7ebf",
  "\u98ce\u9669",
  "\u8d1f\u8d23",
  "\u8d1f\u8d23\u4eba",
  "bydfi",
  "gpt"
]);

export function buildStructuredSystemPrompt() {
  return [
    "You are BYDFI GPT, the internal enterprise agent for BYDFI employees.",
    "Your job is to expose organizational blind spots, trace responsibility chains, and compress issues into deliverable outcomes.",
    "Respond in the same language as the user.",
    "If the user writes in Simplified Chinese, answer entirely in Simplified Chinese.",
    "Do not sound like marketing copy and do not over-explain.",
    "Return exactly one JSON object with this schema:",
    "{",
    '  "title": string,',
    '  "answer": string,',
    '  "highlights": string[],',
    '  "follow_ups": string[],',
    '  "warnings": string[],',
    '  "suggested_mode": "company" | "delivery" | "code",',
    '  "suggested_task_id": string,',
    '  "actions": Array<{ "label": string, "type": string, "url"?: string, "taskId"?: string, "prompt"?: string }>',
    "}",
    "Rules:",
    "- title should be short.",
    "- answer should read like an internal operator reply.",
    "- answer must be final-answer-first; do not narrate retrieval, matching, confidence, or hidden reasoning.",
    "- never start with phrases like 我命中到、我检索到、围绕这件事、根据结构化证据.",
    "- highlights and follow_ups must be actionable.",
    "- suggested_mode should reflect the next useful layer.",
    "- Keep actions optional and short."
  ].join("\n");
}

export function buildStreamingSystemPrompt() {
  return [
    "You are BYDFI GPT, the internal enterprise agent for BYDFI employees.",
    "Your job is to expose organizational blind spots, trace responsibility chains, and compress issues into deliverable outcomes.",
    "Respond in the same language as the user.",
    "If the user writes in Simplified Chinese, answer entirely in Simplified Chinese.",
    "Be concise, concrete, and operational.",
    "Do not use English headings or filler when the user is writing in Chinese.",
    "Do not narrate your retrieval or reasoning process.",
    "Answer with the final conclusion first, then only the minimum evidence and next step if helpful.",
    "Focus on what the user can do next."
  ].join("\n");
}

export function prepareCompanyContext(body = {}) {
  const message = String(body.message || "").trim();
  const clientId = String(body.clientId || "public-web").trim();
  let session = getOrCreateSession(clientId);
  const roleChange = inferRoleChange(message);
  if (roleChange) {
    session = updateSession(clientId, { role: roleChange });
  }

  const snapshot = getEmbeddedDemoSnapshot();
  const explicitTask = resolveSelectedTask(body.selectedTask, snapshot.tasks);
  const inferredTask = inferTaskFromMessage(message, snapshot.tasks);
  const selectedTask = explicitTask || inferredTask;
  const selectedTaskSource = explicitTask ? "explicit" : inferredTask ? "inferred" : "none";
  const productQuestion = shouldUseKnowledgeCards(message);
  const sessionPolicy = getEnterpriseSessionPolicy(session, { productQuestion });
  const enterprise = getEnterpriseStatusSummary();
  const workspaceSummary = safeWorkspaceSummary(body.workspacePath);
  const history = normalizeHistory(body.history, message);
  const knowledge = productQuestion ? getKnowledgePack(message) : { surface: [], matched: [] };
  const searchResults = searchEnterpriseIndex(message, {
    limit: 4,
    allowBuild: true,
    scopes: sessionPolicy.searchScopes
  });
  const memoryMatches = searchMemories(clientId, message, 4, {
    includeShared: sessionPolicy.canReadSharedMemory
  });
  const recentMemories = memoryMatches.length
    ? memoryMatches
    : getRecentMemories(clientId, 4, { includeShared: sessionPolicy.canReadSharedMemory });
  const audit = matchesAny(message, AUDIT_KEYWORDS) ? getAuditConsoleSnapshot() : null;
  const enterpriseAnalysis = analyzeEnterpriseQuestion(message);
  const genericScopeQuestion = isGenericCompanyScopeQuestion(message);

  return {
    clientId,
    message,
    session,
    roleChange,
    sessionPolicy,
    snapshot,
    selectedTask,
    selectedTaskSource,
    productQuestion,
    enterprise,
    workspaceSummary,
    history,
    knowledge,
    searchResults,
    recentMemories,
    audit,
    enterpriseAnalysis,
    genericScopeQuestion
  };
}

export function maybeHandleEnterpriseCommand(context) {
  const { message, session, roleChange, clientId, selectedTask } = context;
  const trimmed = String(message || "").trim();
  if (!trimmed) return null;

  if (roleChange) {
    const role = getRoleDefinition(session.role);
    return {
      handled: true,
      title: "身份已切换",
      answer: `当前会话已切换为${role.label}角色。后续回答会按这个权限边界继续。`,
      highlights: [
        `当前角色：${role.label}`,
        `可用能力：${role.permissions.join("、")}`
      ],
      follow_ups: [
        "查看我的权限",
        "打开审计控制台",
        "生成评委演示"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: selectedTask?.id || "",
      actions: [
        { label: "打开审计控制台", type: "open_url", url: "/audit-console.html" },
        { label: "打开 Judge Demo", type: "open_url", url: "/judge-demo.html" }
      ]
    };
  }

  if (shouldAnswerIdentity(trimmed)) {
    const role = getRoleDefinition(session.role);
    return {
      handled: true,
      title: "当前会话身份",
      answer: `你现在以${role.label}角色使用 BYDFI GPT。这个会话会保留长期记忆、资料检索和对应权限边界。`,
      highlights: [
        `昵称：${session.displayName}`,
        `部门：${session.department}`,
        `权限：${role.permissions.join("、")}`
      ],
      follow_ups: [
        "切换为运营角色",
        "切换为评委角色",
        "查看审计控制台"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: selectedTask?.id || "",
      actions: [
        { label: "打开审计控制台", type: "open_url", url: "/audit-console.html" }
      ]
    };
  }

  if (/^(记住|请记住|帮我记住)/.test(trimmed)) {
    const text = trimmed.replace(/^(记住|请记住|帮我记住)\s*/u, "").trim();
    const item = rememberFact(clientId, text, {
      taskId: selectedTask?.id || "",
      source: "chat-memory"
    });
    return {
      handled: true,
      title: "长期记忆已更新",
      answer: item
        ? `我已经把这条信息写入当前会话的长期记忆，后续对话会优先参考它。`
        : "这次没有拿到可写入的内容。",
      highlights: item ? [item.text] : [],
      follow_ups: [
        "你记得我刚才说了什么",
        "基于这条记忆继续分析",
        "查看我的权限"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: selectedTask?.id || "",
      actions: []
    };
  }

  if (/(你记得|回忆一下|之前我说过|长期记忆)/.test(trimmed)) {
    const memories = searchMemories(clientId, trimmed, 6);
    return {
      handled: true,
      title: "已调出长期记忆",
      answer: memories.length
        ? `我在当前会话里找到了 ${memories.length} 条相关长期记忆。`
        : "当前会话还没有命中相关长期记忆。",
      highlights: memories.map((item) => item.text).slice(0, 6),
      follow_ups: [
        "基于这些记忆继续分析",
        "再帮我记住一条",
        "切换为产品角色"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: selectedTask?.id || "",
      actions: []
    };
  }

  const productQuestionResponse = maybeHandleProductQuestion(context);
  if (productQuestionResponse) {
    return productQuestionResponse;
  }

  const simpleUtilityResponse = maybeHandleSimpleUtilityQuestion(context);
  if (simpleUtilityResponse) {
    return simpleUtilityResponse;
  }

  const genericScopeResponse = maybeHandleGenericCompanyScopeQuestion(context);
  if (genericScopeResponse) {
    return genericScopeResponse;
  }

  const ambiguousResponsibilityResponse = maybeHandleAmbiguousResponsibilityQuery(context);
  if (ambiguousResponsibilityResponse) {
    return ambiguousResponsibilityResponse;
  }
  if (/(搜索|查找|检索|知识库|文档|资料)/.test(trimmed)) {
    const results = context.searchResults.slice(0, 6);
    return {
      handled: true,
      title: "已完成企业资料检索",
      answer: results.length
        ? `我已经从 03_business、审计材料和 Event-Bypass 相关资料里找到了 ${results.length} 条最相关结果。`
        : "这次没有检索到明确命中的资料。",
      highlights: results.map((item) => `${item.title}｜${item.path}`),
      follow_ups: [
        "基于这些资料直接回答问题",
        "继续看审计控制台",
        "生成评委演示"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: selectedTask?.id || "",
      actions: [
        { label: "打开审计控制台", type: "open_url", url: "/audit-console.html" }
      ]
    };
  }

  if (/(审计控制台|飞书控制台|审计看板|看板)/.test(trimmed)) {
    const snapshot = getAuditConsoleSnapshot();
    return {
      handled: true,
      title: "审计控制台已就绪",
      answer: "我已经把审计控制台背后的数据层接到了网页端隐藏页面里，你可以直接打开查看最新看板、SQLite 统计和报告列表。",
      highlights: [
        `最新看板：${snapshot.latestBoard?.title || "暂无"}`,
        `报告数：${snapshot.reports.length}`,
        `SQLite 入站消息：${snapshot.db.inboundMessages || 0}`,
        `SQLite 审计运行：${snapshot.db.auditRuns || 0}`
      ],
      follow_ups: [
        "打开审计控制台",
        "读取最新审计报告",
        "生成评委演示"
      ],
      warnings: snapshot.db.available ? [] : ["本地 SQLite 未就绪或不可读取，当前以文件报告为主。"],
      suggested_mode: "company",
      suggested_task_id: selectedTask?.id || "",
      actions: [
        { label: "打开审计控制台", type: "open_url", url: "/audit-console.html" }
      ]
    };
  }

  if (/(judge|评委演示|presenter|路演|event-bypass)/i.test(trimmed)) {
    const demo = generateEventBypassDemo({
      prompt: trimmed,
      selectedTask,
      history: context.history,
      session
    });
    return {
      handled: true,
      title: "评委演示已生成",
      answer: "我已经基于当前问题生成了 Judge Demo、Presenter 卡片和可导出的会话包。",
      highlights: [
        `Demo ID：${demo.demoId}`,
        `评委总分：${demo.judge.total}/100`,
        `判定：${demo.judge.verdict}`,
        `Presenter 标题：${demo.presenter.headline}`
      ],
      follow_ups: [
        "打开 Judge Demo 页面",
        "导出 Judge 报告",
        "继续生成交付结果"
      ],
      warnings: [],
      suggested_mode: "delivery",
      suggested_task_id: selectedTask?.id || demo.task?.id || "",
      actions: [
        { label: "打开 Judge Demo", type: "open_url", url: `/judge-demo.html?demoId=${encodeURIComponent(demo.demoId)}` },
        { label: "导出 Judge 报告", type: "judge_export", demoId: demo.demoId }
      ]
    };
  }

  if (/(导出 judge|导出报告|session pack|会话包|导出路演)/i.test(trimmed)) {
    const demo = generateEventBypassDemo({
      prompt: trimmed,
      selectedTask,
      history: context.history,
      session
    });
    const exported = exportEventBypassBundle(demo);
    return {
      handled: true,
      title: "导出已完成",
      answer: "Judge 报告和 Session Pack 都已经写到服务器状态目录，可以直接在页面继续查看或下载。",
      highlights: exported.files.map((item) => `${item.type}｜${item.path}`),
      follow_ups: [
        "打开 Judge Demo 页面",
        "继续补充演示话术",
        "打开审计控制台"
      ],
      warnings: [],
      suggested_mode: "delivery",
      suggested_task_id: selectedTask?.id || demo.task?.id || "",
      actions: [
        { label: "打开 Judge Demo", type: "open_url", url: `/judge-demo.html?demoId=${encodeURIComponent(demo.demoId)}` }
      ]
    };
  }

  return null;
}

export function buildCompanyUserPrompt(context) {
  return [
    `用户问题：${context.message}`,
    "",
    "回答要求：",
    "- 先直接回答用户真正想知道的事情。",
    "- 如果范围不足，就先要求补范围，不要硬猜。",
    "- 只保留证据支持的信息；证据不足就明确说缺口。",
    "- 不要暴露检索过程、匹配过程、置信度过程。",
    "",
    "企业证据摘要：",
    buildEvidenceDigest(context),
    "",
    "最近对话：",
    buildHistoryDigest(context.history),
    "",
    "附加约束：",
    buildHarnessPromptBlock(context)
  ].join("\n");
}

function buildEvidenceDigest(context) {
  const lines = [];
  if (context.selectedTask) {
    lines.push(`- 已锁定案例：${context.selectedTask.id} | ${context.selectedTask.title} | ${clipText(context.selectedTask.summary, 180)}`);
  } else {
    lines.push("- 已锁定案例：无");
  }
  if (context.enterpriseAnalysis?.confidence && context.enterpriseAnalysis.confidence !== "weak") {
    lines.push(`- 企业分析：${clipText(context.enterpriseAnalysis.summary || "", 240)}`);
  } else {
    lines.push("- 企业分析：暂无稳定结构化结论");
  }
  if (Array.isArray(context.searchResults) && context.searchResults.length) {
    lines.push("- 检索命中：");
    context.searchResults.slice(0, 3).forEach((item, index) => {
      lines.push(`  ${index + 1}. ${item.title} | ${item.sourceLabel} | ${clipText(item.snippet, 140)}`);
    });
  } else {
    lines.push("- 检索命中：暂无");
  }
  if (Array.isArray(context.knowledge?.matched) && context.knowledge.matched.length) {
    lines.push("- 产品知识：");
    context.knowledge.matched.slice(0, 2).forEach((item, index) => {
      lines.push(`  ${index + 1}. ${item.title} | ${clipText(item.summary, 140)}`);
    });
  }
  if (Array.isArray(context.recentMemories) && context.recentMemories.length) {
    lines.push("- 会话记忆：");
    context.recentMemories.slice(0, 2).forEach((item, index) => {
      lines.push(`  ${index + 1}. ${clipText(item.text, 120)}`);
    });
  }
  if (context.audit?.latestBoard?.title) {
    lines.push(`- 审计看板：${context.audit.latestBoard.title}`);
  }
  if (context.workspaceSummary) {
    lines.push(`- 工作区摘要：${clipText(context.workspaceSummary, 180)}`);
  }
  return lines.join("\n");
}

function buildHistoryDigest(history = []) {
  const items = Array.isArray(history) ? history.slice(-4) : [];
  if (!items.length) return "- 无";
  return items
    .map((item, index) => `${index + 1}. ${String(item.role || "user")}: ${clipText(item.content, 140)}`)
    .join("\n");
}

function buildAlignmentSystemPrompt() {
  return [
    "You are the final answer quality gate for BYDFI GPT.",
    "Check whether the draft directly answers the user's question and only uses supported evidence.",
    "Return exactly one JSON object with this schema:",
    "{",
    '  "pass": boolean,',
    '  "issues": string[],',
    '  "response": {',
    '    "title": string,',
    '    "answer": string,',
    '    "highlights": string[],',
    '    "follow_ups": string[],',
    '    "warnings": string[],',
    '    "suggested_mode": "company" | "delivery" | "code",',
    '    "suggested_task_id": string,',
    '    "actions": Array<{ "label": string, "type": string, "url"?: string, "taskId"?: string, "prompt"?: string }>',
    "  }",
    "}",
    "Rules:",
    "- Rewrite the response if the draft drifts away from the user's real question.",
    "- Remove unsupported names, dates, owners, projects, or internal phrasing.",
    "- If the question scope is insufficient, rewrite into a short scope-first answer.",
    "- Keep the final answer concise, direct, and final-answer-first.",
    "- Never expose retrieval process, matching process, confidence process, or internal system wording."
  ].join("\n");
}

function buildAlignmentUserPrompt(context, draft) {
  return [
    `用户问题：${context.message}`,
    "",
    "企业证据摘要：",
    buildEvidenceDigest(context),
    "",
    "草稿回答 JSON：",
    safeJsonStringify(draft),
    "",
    "校验要求：",
    "- 这是不是在直接回答用户问题？",
    "- 有没有答非所问、跑到别的项目、别的责任人、别的案例？",
    "- 有没有暴露检索过程、结构化命中过程、置信度过程？",
    "- 如果有问题，直接改写成最终可发给用户的版本。"
  ].join("\n");
}

function extractReviewedResponse(review, draft) {
  if (review && typeof review.response === "object" && review.response) {
    return review.response;
  }
  return draft;
}

function isResponseAligned(response, context) {
  if (!response || !String(response.answer || "").trim()) return false;
  if (context?.genericScopeQuestion) {
    return !hasGenericScopeMismatch(response.answer, context);
  }
  if (context?.productQuestion) {
    return /(首页|中文提问|bydfi gpt|直接在首页)/i.test(`${response.title}\n${response.answer}`);
  }
  const haystack = `${response.title || ""}\n${response.answer || ""}\n${(response.highlights || []).join("\n")}`.toLowerCase();
  const anchors = buildAlignmentAnchors(context);
  if (!anchors.length) return true;
  return anchors.some((anchor) => haystack.includes(anchor));
}

function buildAlignmentAnchors(context) {
  const raw = [
    ...(Array.isArray(context?.enterpriseAnalysis?.plan?.topicKeywords) ? context.enterpriseAnalysis.plan.topicKeywords : []),
    ...(Array.isArray(context?.enterpriseAnalysis?.plan?.focusTerms) ? context.enterpriseAnalysis.plan.focusTerms : []),
    context?.selectedTask?.title || "",
    context?.message || ""
  ];
  return uniqueStrings(raw.flatMap((item) => extractAlignmentTokens(item))).slice(0, 8);
}

function extractAlignmentTokens(value) {
  const text = String(value || "").toLowerCase();
  const ascii = text.match(/[a-z][a-z0-9_-]{1,}/g) || [];
  const cjk = text.match(/[\u4e00-\u9fff]{2,}/g) || [];
  const tokens = [];
  for (const item of [...ascii, ...cjk]) {
    const token = String(item || "").trim().toLowerCase();
    if (!token || ALIGNMENT_IGNORE_TERMS.has(token)) continue;
    tokens.push(token);
    if (/^[\u4e00-\u9fff]{5,}$/u.test(token)) {
      tokens.push(token.slice(0, 4));
      tokens.push(token.slice(-4));
    }
  }
  return tokens;
}

function uniqueStrings(items = []) {
  return [...new Set(items.map((item) => String(item || "").trim().toLowerCase()).filter(Boolean))];
}

function safeJsonStringify(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value || "");
  }
}

function buildSeedStructuredResponse(context) {
  if (context?.enterpriseAnalysis?.response && context.enterpriseAnalysis.confidence !== "weak") {
    return context.enterpriseAnalysis.response;
  }
  const structured = buildStructuredSearchFallback(context?.searchResults, null, { includeWarnings: false });
  if (!structured) return null;
  return {
    ...structured,
    suggested_mode: "company",
    suggested_task_id: context?.selectedTask?.id || "",
    actions: []
  };
}

export async function runStructuredChatPipeline(context) {
  const seed = buildSeedStructuredResponse(context);
  let draft = seed;
  try {
    draft = await withTimeout(callOpenAIJson({
      systemPrompt: buildStructuredSystemPrompt(),
      userPrompt: buildCompanyUserPrompt(context)
    }), 18000, "draft");
  } catch (error) {
    if (!seed) throw error;
  }

  let reviewed = null;
  try {
    reviewed = await withTimeout(callOpenAIJson({
      systemPrompt: buildAlignmentSystemPrompt(),
      userPrompt: buildAlignmentUserPrompt(context, draft)
    }), 10000, "review");
  } catch {
    reviewed = null;
  }

  const candidates = [
    extractReviewedResponse(reviewed, null),
    draft,
    seed
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (shouldRejectStructuredResponse(candidate, context)) continue;
    if (!isResponseAligned(candidate, context)) continue;
    return humanizeStructuredResponse(candidate);
  }

  const issueText = Array.isArray(reviewed?.issues) ? reviewed.issues.join(" | ") : "";
  throw new Error(issueText || "answer alignment rejected");
}

function withTimeout(promise, timeoutMs, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(`${label || "request"} timeout`)), Number(timeoutMs) || 15000);
    })
  ]);
}

function humanizeStructuredResponse(response) {
  if (!response || typeof response !== "object") return response;
  return {
    ...response,
    title: humanizeEnterpriseText(response.title),
    answer: humanizeEnterpriseText(response.answer),
    highlights: Array.isArray(response.highlights)
      ? response.highlights.map((item) => humanizeEnterpriseText(item)).filter(Boolean)
      : [],
    follow_ups: Array.isArray(response.follow_ups)
      ? response.follow_ups.map((item) => humanizeEnterpriseText(item)).filter(Boolean)
      : [],
    warnings: Array.isArray(response.warnings)
      ? response.warnings.map((item) => humanizeEnterpriseText(item)).filter(Boolean)
      : []
  };
}

function humanizeEnterpriseText(text) {
  let value = String(text || "").trim();
  if (!value) return "";

  value = value.replace(
    /全局结构化任务里约\s*\d+(?:\.\d+)?%\s*缺少状态字段[，,]?\s*这会(?:影响判断稳定性|拖低企业问答的确定性)[。.]?/g,
    "当前还有一部分任务状态没填完整，这条判断需要再和负责人确认。"
  );

  value = value.replace(
    /全局结构化任务里约\s*\d+(?:\.\d+)?%\s*缺少状态字段[。.]?/g,
    "当前还有一部分任务状态没填完整。"
  );

  value = value.replace(
    /这会(?:影响判断稳定性|拖低企业问答的确定性)[。.]?/g,
    "这会让个别结论还需要人工复核。"
  );

  return value.replace(/\n{3,}/g, "\n\n").trim();
}

export function buildHarnessPromptBlock(context) {
  const harness = deriveHarnessState(context);
  return [
    "Harness Engineering Guardrails:",
    "- execution_order: classify -> retrieve -> cross-check -> answer -> cite gaps",
    `- intent: ${harness.intent}`,
    `- evidence_level: ${harness.evidenceLevel}`,
    `- task_binding: ${harness.taskBinding}`,
    `- answer_policy: ${harness.answerPolicy}`,
    "- Prefer active structured records, linked evidence, and current blockers over generic documents or legacy completed tasks.",
    "- If enterprise evidence is already strong, do not switch into product-intro mode.",
    "- Every concrete owner, timeline, blocker, or risk must be supported by retrieved evidence, or be omitted.",
    "- If the model call is weak or empty, fall back to deterministic evidence synthesis instead of generic copy.",
    "- Do not invent a policy, owner, timeline, API, or document when evidence is weak.",
    "- If no task is locked, do not drag the answer into Korean recall, SEO, or invite-code cases.",
    "- If the user is asking a generic company question, answer generically and give the shortest retrieval path.",
    "- If the user is asking about an unspecified process, policy, or historical decision, ask for scope first instead of forcing a specific case.",
    "- Never expose hidden reasoning, retrieval process, confidence calibration, or system-internal phrasing in the final answer.",
    "- If evidence is missing, say the gap explicitly and convert the reply into next-step retrieval or escalation."
  ].join("\n");
}

export function buildFallbackStructuredResponse({ message, snapshot, selectedTask, workspaceSummary, knowledge, searchResults, error }) {
  const task = selectedTask || null;
  const suggestedMode = inferSuggestedMode(message, workspaceSummary);
  if (isGenericCompanyScopeQuestion(message)) {
    return buildGenericCompanyScopeResponse();
  }
  const evidenceFallback = !task ? buildEvidenceFirstFallback(searchResults, error) : null;
  if (evidenceFallback) {
    return {
      title: evidenceFallback.title,
      answer: evidenceFallback.answer,
      highlights: evidenceFallback.highlights,
      follow_ups: evidenceFallback.follow_ups,
      warnings: evidenceFallback.warnings,
      suggested_mode: "company",
      suggested_task_id: "",
      actions: [{ label: "\u6253\u5f00\u5ba1\u8ba1\u63a7\u5236\u53f0", type: "open_url", url: "/audit-console.html" }]
    };
  }
  if (needsScopeFirst({ message, selectedTask, searchResults, knowledge })) {
    return {
      title: "\u9700\u8981\u5148\u7f29\u5c0f\u95ee\u9898\u8303\u56f4",
      answer: "\u8fd9\u7c7b\u95ee\u9898\u4e0d\u80fd\u76f4\u63a5\u7ed9\u4eba\u540d\u3002\u5148\u544a\u8bc9\u6211\u662f\u54ea\u6761\u4e1a\u52a1\u7ebf\u3001\u54ea\u4e2a\u9879\u76ee\u3001\u54ea\u4e2a\u7fa4\u6216\u54ea\u6bb5\u65f6\u95f4\uff0c\u6211\u518d\u6309\u8d23\u4efb\u94fe\u5e2e\u4f60\u627e\u51fa\u5361\u70b9\u3001\u8d1f\u8d23\u4eba\u548c\u6700\u77ed\u63a8\u8fdb\u8def\u5f84\u3002",
      highlights: [
        "\u53ef\u76f4\u63a5\u8865\u5145\uff1a\u4e1a\u52a1\u7ebf / \u9879\u76ee\u540d / \u7fa4\u540d / \u65f6\u95f4\u8303\u56f4",
        "\u5982\u679c\u4f60\u53ea\u77e5\u9053\u73b0\u8c61\uff0c\u4e5f\u53ef\u4ee5\u76f4\u63a5\u8bf4\u201c\u97e9\u56fd\u6d3b\u52a8\u4e00\u76f4\u5361\u4f4f\u201d\u6216\u201c\u7ffb\u8bd1\u5de5\u4f5c\u6700\u8fd1\u8c01\u5728\u63a8\u8fdb\u201d",
        "\u6211\u4f1a\u4f18\u5148\u7ed9\u51fa\u8d23\u4efb\u94fe\u3001\u5361\u70b9\u548c\u4e0b\u4e00\u6b65\uff0c\u4e0d\u4f1a\u7a7a\u62a5\u4eba\u540d"
      ],
      follow_ups: [
        "\u97e9\u56fd\u53ec\u56de\u6d3b\u52a8\u8c01\u5728\u63a8\u8fdb\uff0c\u5361\u5728\u54ea\u4e00\u6b65\uff1f",
        "\u7ffb\u8bd1\u5de5\u4f5c\u6700\u8fd1\u8c01\u5728\u8d1f\u8d23\uff0c\u98ce\u9669\u662f\u4ec0\u4e48\uff1f",
        "\u4e2d\u5fc3\u7814\u53d1\u4efb\u52a1\u6700\u8fd1\u8c01\u5728\u8ddf\uff0c\u65f6\u95f4\u7ebf\u5230\u54ea\u4e86\uff1f"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: "",
      actions: [{ label: "\u6253\u5f00\u5ba1\u8ba1\u63a7\u5236\u53f0", type: "open_url", url: "/audit-console.html" }]
    };
  }
  return {
    title: suggestedMode === "delivery"
      ? "\u7ee7\u7eed\u63a8\u8fdb\u8fd9\u4e2a\u95ee\u9898"
      : suggestedMode === "code"
        ? "\u53ef\u4ee5\u4e0b\u6f5c\u5230\u5b9e\u73b0\u5c42"
        : "\u5148\u628a\u95ee\u9898\u95ee\u6e05\u695a",
    answer: suggestedMode === "delivery"
      ? "\u8fd9\u4e2a\u95ee\u9898\u66f4\u9002\u5408\u8d70\u4ea4\u4ed8\u94fe\u3002\u5148\u9501\u5b9a\u6848\u4f8b\uff0c\u518d\u505a\u8bca\u65ad\uff0c\u6700\u540e\u76f4\u63a5\u751f\u6210 JSON \u548c H5 \u4ea4\u4ed8\u7269\u3002"
      : suggestedMode === "code"
        ? "\u8fd9\u4e2a\u95ee\u9898\u5df2\u7ecf\u63a5\u8fd1\u5b9e\u73b0\u5c42\uff0c\u9700\u8981\u7ed3\u5408\u5de5\u4f5c\u533a\u6216\u4ed3\u5e93\u7ed9\u51fa\u6700\u5c0f\u6539\u52a8\u8def\u5f84\u3002"
        : "\u5f53\u524d\u6700\u7a33\u7684\u7528\u6cd5\u662f\u76f4\u63a5\u7528\u4e2d\u6587\u628a\u95ee\u9898\u95ee\u51fa\u6765\uff0c\u6211\u4f1a\u5728\u5bf9\u8bdd\u91cc\u7ee7\u7eed\u4e0b\u6f5c\u5230\u8d44\u6599\u3001\u5ba1\u8ba1\u3001\u8d23\u4efb\u94fe\u548c\u4ea4\u4ed8\u5c42\u3002",
    highlights: [
      task ? `\u5f53\u524d\u76f8\u5173\u6848\u4f8b\uff1a${task.title}` : "\u5f53\u524d\u8fd8\u6ca1\u6709\u9501\u5b9a\u5b9e\u4f53\u6848\u4f8b",
      searchResults?.[0]
        ? `\u5df2\u547d\u4e2d\u76f8\u5173\u8d44\u6599\uff1a${searchResults[0].title}`
        : knowledge?.matched?.[0]?.title
          ? `\u5df2\u547d\u4e2d\u4ea7\u54c1\u77e5\u8bc6\uff1a${knowledge.matched[0].title}`
          : "\u8fd9\u8f6e\u8fd8\u6ca1\u6709\u62ff\u5230\u7a33\u5b9a\u8bc1\u636e",
      task
        ? "\u53ef\u4ee5\u76f4\u63a5\u987a\u7740\u8fd9\u4e2a\u6848\u4f8b\u7ee7\u7eed\u8bca\u65ad\u548c\u4ea4\u4ed8"
        : "\u5efa\u8bae\u5148\u8865\u5145\u95ee\u9898\u8303\u56f4\uff0c\u518d\u7ee7\u7eed\u4e0b\u6f5c"
    ],
    follow_ups: suggestedMode === "delivery"
      ? ["\u5f00\u59cb\u8bca\u65ad", "\u751f\u6210\u4ea4\u4ed8\u7ed3\u679c", "\u6253\u5f00 Judge Demo"]
      : suggestedMode === "code"
        ? ["\u770b\u5b9e\u73b0\u8def\u5f84", "\u52a0\u8f7d\u5de5\u4f5c\u533a", "\u7ee7\u7eed\u8bf4\u660e\u4ee3\u7801\u6539\u52a8\u76ee\u6807"]
        : ["\u641c\u7d22\u76f8\u5173\u8d44\u6599", "\u6253\u5f00\u5ba1\u8ba1\u63a7\u5236\u53f0", "\u5207\u6362\u4e3a\u8bc4\u59d4\u89d2\u8272"],
    warnings: error ? [formatErrorMessage(error)] : [],
    suggested_mode: suggestedMode,
    suggested_task_id: task?.id || "",
    actions: suggestedMode === "delivery"
      ? [{ label: "\u6253\u5f00 Judge Demo", type: "open_url", url: "/judge-demo.html" }]
      : [{ label: "\u6253\u5f00\u5ba1\u8ba1\u63a7\u5236\u53f0", type: "open_url", url: "/audit-console.html" }]
  };
}

export function buildStreamingMeta({ message, snapshot, selectedTask, workspaceSummary, commandResponse }) {
  if (commandResponse) {
    return {
      title: commandResponse.title || "BYDFI GPT",
      suggested_mode: normalizeMode(commandResponse.suggested_mode),
      suggested_task_id: normalizeTaskId(commandResponse.suggested_task_id, snapshot.tasks),
      actions: Array.isArray(commandResponse.actions) ? commandResponse.actions : []
    };
  }
  const suggestedMode = inferSuggestedMode(message, workspaceSummary);
  return {
    title: "BYDFI GPT",
    suggested_mode: suggestedMode,
    suggested_task_id: selectedTask?.id || "",
    actions: []
  };
}

function normalizeCitationItems(items = []) {
  const seen = new Set();
  return items
    .filter(Boolean)
    .map((item) => ({
      title: String(item.title || "").trim(),
      sourceLabel: String(item.sourceLabel || item.source_label || "").trim(),
      path: String(item.path || "").trim(),
      snippet: String(item.snippet || item.summary || "").replace(/\s+/g, " ").trim()
    }))
    .filter((item) => item.title && item.snippet)
    .filter((item) => {
      const key = `${item.title}|${item.sourceLabel}|${item.path}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 4);
}

export function buildResponseCitations(context, response = null) {
  if (Array.isArray(response?.citations) && response.citations.length) {
    return normalizeCitationItems(response.citations);
  }

  if (shouldSuppressCitations(context, response)) {
    return [];
  }

  const citations = [];
  if (context?.productQuestion) {
    for (const entry of context?.knowledge?.matched || []) {
      citations.push({
        title: entry.title,
        sourceLabel: "产品知识",
        path: entry.layer,
        snippet: entry.summary
      });
    }
    return normalizeCitationItems(citations);
  }

  for (const item of context?.searchResults || []) {
    citations.push({
      title: item.title,
      sourceLabel: item.sourceLabel,
      path: item.path,
      snippet: item.snippet
    });
  }

  return normalizeCitationItems(citations);
}

function shouldSuppressCitations(context, response) {
  if (context?.genericScopeQuestion) return true;
  if (needsScopeFirst(context)) return true;
  const title = String(response?.title || "").trim();
  return title === "\u9700\u8981\u5148\u7f29\u5c0f\u8303\u56f4" || title === "\u9700\u8981\u5148\u7f29\u5c0f\u95ee\u9898\u8303\u56f4";
}

export function buildStreamingFallbackText({ message, snapshot, selectedTask, workspaceSummary, searchResults, error }) {
  const structured = buildFallbackStructuredResponse({
    message,
    snapshot,
    selectedTask,
    workspaceSummary,
    knowledge: shouldUseKnowledgeCards(message) ? getKnowledgePack(message) : { surface: [], matched: [] },
    searchResults,
    error
  });
  return String(structured.answer || "").trim();
}


export function shouldRejectStructuredResponse(response, context) {
  if (!response || !String(response.answer || "").trim()) return true;
  const combined = [
    response.title,
    response.answer,
    ...(Array.isArray(response.highlights) ? response.highlights : []),
    ...(Array.isArray(response.follow_ups) ? response.follow_ups : []),
    ...(Array.isArray(response.warnings) ? response.warnings : [])
  ].join("\n");
  return hasTaskLeak(combined, context) || hasRequirementLeak(combined, context) || hasGenericScopeMismatch(combined, context);
}

export function shouldRejectStreamingAnswer(answer, context) {
  if (!String(answer || "").trim()) return true;
  return hasTaskLeak(answer, context) || hasRequirementLeak(answer, context) || hasGenericScopeMismatch(answer, context);
}

export function normalizeMode(value) {
  const mode = String(value || "company").trim().toLowerCase();
  return mode === "delivery" || mode === "code" ? mode : "company";
}

export function normalizeTaskId(value, tasks) {
  const taskId = String(value || "").trim();
  if (!taskId) return "";
  return tasks.some((task) => task.id === taskId) ? taskId : "";
}

function inferSuggestedMode(message, workspaceSummary) {
  const text = String(message || "").toLowerCase();
  if (workspaceSummary || CODE_KEYWORDS.some((keyword) => text.includes(keyword))) return "code";
  if (DELIVERY_KEYWORDS.some((keyword) => text.includes(keyword))) return "delivery";
  if (COMPANY_KEYWORDS.some((keyword) => text.includes(keyword))) return "company";
  return "company";
}

function shouldUseKnowledgeCards(message) {
  const text = String(message || "").toLowerCase();
  if (!text) return false;
  if (/(?:bydfi gpt|\u8fd9\u4e2a\u4ea7\u54c1|\u8fd9\u4e2a\u7cfb\u7edf|\u8fd9\u4e2a\u7f51\u7ad9|\u8fd9\u4e2a\u7f51\u9875).{0,12}(?:\u600e\u4e48\u7528|\u5982\u4f55\u4f7f\u7528|\u662f\u4ec0\u4e48|\u80fd\u505a\u4ec0\u4e48|\u6709\u4ec0\u4e48\u7528|\u600e\u4e48\u5f00\u59cb|\u5982\u4f55\u5f00\u59cb)/.test(text)) return true;
  const directKeywords = [
    "bydfi gpt",
    "\u4ea7\u54c1\u5b9a\u4f4d",
    "\u7cfb\u7edf\u5b9a\u4f4d",
    "\u5b98\u7f51",
    "\u4e2d\u6587\u5bf9\u8bdd\u5165\u53e3",
    "\u4f01\u4e1a agent"
  ];
  return directKeywords.some((keyword) => text.includes(keyword))
    || PRODUCT_QUESTION_KEYWORDS.some((keyword) => text.includes(keyword));
}

function isGenericCompanyScopeQuestion(message) {
  const text = String(message || "").trim();
  if (!text) return false;
  const hasGenericHint = GENERIC_SCOPE_HINTS.some((item) => text.includes(item));
  const mentionsProcessLikeThing = /(\u6d41\u7a0b|\u5236\u5ea6|\u89c4\u5219|\u89c4\u5b9a|\u5386\u53f2\u51b3\u7b56|\u5386\u53f2\u65b9\u6848|\u4ee5\u524d\u600e\u4e48\u5b9a)/.test(text);
  const lacksSpecificBusinessAnchor = !/(\u97e9\u56fd|\u7ffb\u8bd1|seo|\u4ea7\u7814|\u7814\u53d1|\u6d3b\u52a8|\u9080\u8bf7\u7801|\u53ec\u56de|\u6c38\u7eed|kater|codeforce|moonx)/i.test(text);
  return Boolean(hasGenericHint && mentionsProcessLikeThing && lacksSpecificBusinessAnchor);
}

function buildGenericCompanyScopeResponse() {
  return {
    handled: true,
    title: "\u9700\u8981\u5148\u7f29\u5c0f\u8303\u56f4",
    answer: "\u8fd9\u7c7b\u95ee\u9898\u73b0\u5728\u8fd8\u592a\u6cdb\u3002\u5148\u544a\u8bc9\u6211\u662f\u54ea\u4e2a\u6d41\u7a0b\u3001\u54ea\u4e2a\u5386\u53f2\u51b3\u7b56\u3001\u54ea\u6761\u4e1a\u52a1\u7ebf\uff0c\u6216\u8005\u7ed9\u6211\u4e00\u4e2a\u65f6\u95f4\u8303\u56f4\uff0c\u6211\u5c31\u7528\u6700\u77ed\u7684\u8bdd\u8bf4\u660e\u767d\uff0c\u5e76\u544a\u8bc9\u4f60\u4e0b\u4e00\u6b65\u8be5\u627e\u8c01\u3002",
    highlights: [
      "\u6700\u597d\u76f4\u63a5\u8865\u5145\uff1a\u6d41\u7a0b\u540d / \u4e1a\u52a1\u7ebf / \u9879\u76ee\u540d / \u65f6\u95f4\u8303\u56f4",
      "\u4f60\u4e5f\u53ef\u4ee5\u76f4\u63a5\u8bf4\uff1a\u201c\u5e2e\u52a9\u4e2d\u5fc3\u7ffb\u8bd1\u8fd9\u6761\u7ebf\u4ee5\u524d\u600e\u4e48\u5b9a\u7684\uff1f\u201d",
      "\u8303\u56f4\u8db3\u591f\u660e\u786e\u540e\uff0c\u6211\u4f1a\u7ed9\u4f60\uff1a\u4e00\u53e5\u8bdd\u8bf4\u660e + \u4e0b\u4e00\u6b65\u8be5\u627e\u8c01"
    ],
    follow_ups: [
      "\u5e2e\u52a9\u4e2d\u5fc3\u7ffb\u8bd1\u8fd9\u6761\u7ebf\u4ee5\u524d\u600e\u4e48\u5b9a\u7684\uff1f",
      "\u97e9\u56fd\u53ec\u56de\u6d3b\u52a8\u8fd9\u6761\u6d41\u7a0b\u73b0\u5728\u5e94\u8be5\u627e\u8c01\uff1f",
      "\u4e2d\u5fc3\u7814\u53d1\u4efb\u52a1\u8fd9\u6761\u7ebf\u6700\u8fd1\u7684\u63a8\u8fdb\u8def\u5f84\u662f\u4ec0\u4e48\uff1f"
    ],
    warnings: [],
    suggested_mode: "company",
    suggested_task_id: "",
    actions: []
  };
}

function maybeHandleGenericCompanyScopeQuestion(context) {
  if (!context?.genericScopeQuestion) return null;
  return buildGenericCompanyScopeResponse();
}

function maybeHandleProductQuestion(context) {
  const text = String(context?.message || "").trim();
  if (!context?.productQuestion || !text) return null;
  if (!/(\u600e\u4e48\u7528|\u5982\u4f55\u4f7f\u7528|\u662f\u4ec0\u4e48|\u80fd\u505a\u4ec0\u4e48|\u6709\u4ec0\u4e48\u7528|\u600e\u4e48\u5f00\u59cb|\u5982\u4f55\u5f00\u59cb)/.test(text)) {
    return null;
  }
  return {
    handled: true,
    title: "BYDFI GPT \u7528\u6cd5",
    answer: "\u76f4\u63a5\u5728\u9996\u9875\u7528\u4e2d\u6587\u63d0\u95ee\u5373\u53ef\u3002\u4f60\u53ef\u4ee5\u95ee\u516c\u53f8\u73b0\u72b6\u3001\u8d23\u4efb\u4eba\u3001\u65f6\u95f4\u7ebf\u3001\u98ce\u9669\u3001\u63a8\u8fdb\u8def\u5f84\uff0c\u7cfb\u7edf\u4f1a\u5148\u68c0\u7d22\u4f01\u4e1a\u8bc1\u636e\uff0c\u518d\u5728\u5bf9\u8bdd\u91cc\u7ed9\u51fa\u7ed3\u8bba\u548c\u4e0b\u4e00\u6b65\u3002",
    highlights: [
      "\u5165\u53e3\u53ea\u6709\u4e00\u4e2a\u4e2d\u6587\u5bf9\u8bdd\u6846\uff0c\u4e0d\u9700\u8981\u5148\u5207\u6a21\u5f0f",
      "\u666e\u901a\u95ee\u9898\u4f18\u5148\u8fd4\u56de\u4e8b\u5b9e\u3001owner\u3001\u65f6\u95f4\u70b9\u548c\u98ce\u9669",
      "\u95ee\u5230\u4ea4\u4ed8\u6216\u8425\u8fd0\u573a\u666f\u65f6\uff0c\u4f1a\u5728\u540c\u4e00\u8f6e\u5bf9\u8bdd\u91cc\u7ee7\u7eed\u4e0b\u6f5c"
    ],
    follow_ups: [
      "\u8c01\u5728\u8d1f\u8d23\u63a8\u8fdb\u5e2e\u52a9\u4e2d\u5fc3\u7ffb\u8bd1\uff1f",
      "\u4e2d\u5fc3\u7814\u53d1\u4efb\u52a1\u6700\u8fd1\u5728\u505a\u4ec0\u4e48\uff1f",
      "\u8fd9\u4e2a\u6d3b\u52a8\u5361\u5728\u54ea\u4e00\u6b65\uff1f"
    ],
    warnings: ["\u7ed3\u8bba\u53ea\u57fa\u4e8e\u5f53\u524d\u5df2\u91c7\u96c6\u7684\u6570\u636e\uff0c\u7f3a\u53e3\u4f1a\u76f4\u63a5\u8bf4\u660e\u3002"],
    suggested_mode: "company",
    suggested_task_id: context.selectedTask?.id || "",
    actions: []
  };
}

function hasGenericScopeMismatch(text, context) {
  if (!context?.genericScopeQuestion) return false;
  const haystack = String(text || "").trim();
  if (!haystack) return true;
  const answeredWithScope = GENERIC_SCOPE_RESPONSE_HINTS.some((item) => haystack.includes(item));
  if (answeredWithScope) return false;
  const hasTooManyConcreteDetails = /(\u8d1f\u8d23\u4eba|\u8d23\u4efb\u4eba|\u9879\u76ee|\u4f1a\u8bae|\u6d3b\u52a8|Miya|Kevin|Jacky|Kater|CodeForce|MoonX)/i.test(haystack);
  return hasTooManyConcreteDetails;
}

function hasRequirementLeak(text, context) {
  if (context?.productQuestion) return false;
  const haystack = String(text || "").toLowerCase();
  const userText = String(context?.message || "").toLowerCase();
  const leakHints = [
    ...REQUIREMENT_LEAK_HINTS,
    "\u51b0\u5c71",
    "judge demo",
    "presenter",
    "event-bypass",
    "\u4f11\u514b\u7597\u6cd5",
    "\u96f6\u4fb5\u5165",
    "\u4ea7\u54c1\u8fb9\u754c",
    "\u4ea4\u4ed8\u7269",
    "\u9ed1\u5ba2\u677e",
    "\u8bc4\u59d4",
    "ppt \u9879\u76ee"
  ];
  return leakHints.some((keyword) => {
    const normalized = keyword.toLowerCase();
    return haystack.includes(normalized) && !userText.includes(normalized);
  });
}


function deriveHarnessState(context) {
  const intent = inferSuggestedMode(context.message, context.workspaceSummary);
  const hasStructuredEvidence = Boolean(
    buildStructuredSearchFallback(context.searchResults, null, { includeWarnings: false })
  );
  const evidenceLevel = context.enterpriseAnalysis?.confidence === "strong" || hasStructuredEvidence
    ? "strong"
    : context.enterpriseAnalysis?.confidence === "medium"
      ? "medium"
      : context.searchResults?.length || context.audit || context.knowledge?.matched?.length
      ? "medium"
      : "weak";
  const taskBinding = context.selectedTask
    ? `${context.selectedTaskSource || "explicit"}:${context.selectedTask.id}`
    : "none";
  const answerPolicy = intent === "delivery"
    ? "diagnose-before-deliverable"
    : intent === "code"
      ? "implementation-path-only-with-context"
      : evidenceLevel === "weak"
        ? "retrieval-first-no-hallucination"
        : "answer-with-evidence-and-next-step";
  return {
    intent,
    evidenceLevel,
    taskBinding,
    answerPolicy
  };
}

function buildEvidenceFirstFallback(searchResults, error) {
  const results = Array.isArray(searchResults) ? searchResults.filter(Boolean) : [];
  if (!results.length) return null;

  const structured = buildStructuredSearchFallback(results, error);
  if (structured) return structured;

  const topResults = results.slice(0, 3);
  return {
    title: "\u5df2\u627e\u5230\u76f8\u5173\u8d44\u6599",
    answer: `\u6211\u5df2\u7ecf\u5148\u547d\u4e2d\u4e86 ${topResults.map((item) => item.title).join("\u3001")}\u3002\u8fd9\u8f6e\u6a21\u578b\u6ca1\u6709\u7a33\u5b9a\u8fd4\u56de\uff0c\u6240\u4ee5\u5148\u6309\u8d44\u6599\u5c42\u7ed9\u4f60\u6536\u53e3\uff0c\u907f\u514d\u7a7a\u8bdd\u3002`,
    highlights: topResults.map((item) => `${item.title} | ${shortenSnippet(item.snippet)}`),
    follow_ups: ["\u7ee7\u7eed\u5c55\u5f00\u7b2c\u4e00\u6761\u8d44\u6599", "\u53ea\u770b\u6700\u8fd1 7 \u5929", "\u6309\u8d1f\u8d23\u4eba\u7ee7\u7eed\u8ffd"],
    warnings: [formatErrorMessage(error)]
  };
}

function maybeHandleStructuredEvidenceQuery(context) {
  const text = String(context?.message || "").trim();
  if (context?.genericScopeQuestion) return null;
  if (!/(\u6700\u8fd1|\u8fdb\u5c55|\u66f4\u65b0|\u5728\u505a\u4ec0\u4e48|\u5728\u63a8\u4ec0\u4e48|\u8c01\u5728\u505a|\u8d1f\u8d23\u4eba|\u8c01\u5728\u63a8\u8fdb|\u8c01\u5728\u8ddf|\u8c01\u5728\u62d6\u540e\u817f|\u8c01\u62d6\u540e\u817f|\u5361\u70b9|\u963b\u585e|\u74f6\u9888|\u6392\u671f|\u4efb\u52a1)/.test(text)) {
    return null;
  }
  const structured = buildStructuredSearchFallback(context?.searchResults, null, { includeWarnings: false });
  if (!structured) return null;
  return {
    handled: true,
    ...structured,
    suggested_mode: "company",
    suggested_task_id: context?.selectedTask?.id || "",
    actions: [
      { label: "打开审计控制台", type: "open_url", url: "/audit-console.html" }
    ]
  };
}

function buildStructuredSearchFallback(results, error, options = {}) {
  for (const item of results) {
    const absolutePath = String(item?.absolutePath || "").trim();
    if (!absolutePath || !absolutePath.toLowerCase().endsWith(".json")) continue;
    const raw = readTextFileSafe(absolutePath, "");
    if (!raw) continue;
    try {
      const payload = JSON.parse(raw);
      if (!Array.isArray(payload?.requirements) || !payload.requirements.length) continue;

      const deduped = [];
      const seen = new Set();
      for (const requirement of payload.requirements) {
        const quote = String(requirement?.evidence_quote || "").trim();
        const what = String(requirement?.what || requirement?.title || "").trim();
        const line = quote || what;
        if (!line || seen.has(line)) continue;
        seen.add(line);
        deduped.push({
          line,
          owner: String(requirement?.owner_hint || "").trim(),
          deadline: String(requirement?.deadline_hint || "").trim()
        });
      }
      if (!deduped.length) continue;

      return {
        title: "\u5df2\u63d0\u53d6\u5230\u660e\u786e\u8981\u6c42",
        answer: `\u6211\u5df2\u7ecf\u547d\u4e2d ${item.title}\u3002\u6309\u73b0\u6709\u8d44\u6599\uff0c\u6700\u8fd1\u660e\u786e\u63a8\u8fdb\u7684\u4e8b\u9879\u4e3b\u8981\u662f\uff1a${deduped.slice(0, 3).map((entry, index) => `${index + 1}. ${entry.line}`).join("; ")}\u3002`,
        highlights: deduped.slice(0, 4).map((entry) => {
          const suffix = [
            entry.owner ? `\u8d1f\u8d23\u4eba\u63d0\u793a\uff1a${entry.owner}` : "",
            entry.deadline ? `\u65f6\u70b9\uff1a${entry.deadline}` : ""
          ].filter(Boolean).join(" | ");
          return suffix ? `${entry.line} | ${suffix}` : entry.line;
        }),
        follow_ups: ["\u7ee7\u7eed\u6309\u8d1f\u8d23\u4eba\u8ffd\u8e2a", "\u53ea\u770b\u6700\u8fd1\u4e00\u5468\u7684\u65b0\u589e\u8981\u6c42", "\u628a\u8fd9\u4e9b\u8981\u6c42\u538b\u6210\u5f85\u529e\u5217\u8868"],
        warnings: options.includeWarnings === false ? [] : [formatErrorMessage(error)]
      };
    } catch {
      continue;
    }
  }
  return null;
}

function shortenSnippet(snippet) {
  const value = String(snippet || "")
    .replace(/\s+/g, " ")
    .replace(/^#+\s*/g, "")
    .trim();
  if (!value) return "\u6682\u65e0\u6458\u8981";
  return value.length > 72 ? `${value.slice(0, 72)}...` : value;
}

function clipText(text, max = 160) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  if (!value) return "";
  return value.length > max ? `${value.slice(0, max - 1)}...` : value;
}

function formatErrorMessage(error) {
  if (!error) return "\u5df2\u542f\u7528\u8bc1\u636e\u4f18\u5148\u515c\u5e95\u56de\u7b54\u3002";
  return "\u8fd9\u8f6e\u6a21\u578b\u56de\u7b54\u4e0d\u591f\u7a33\u5b9a\uff0c\u5df2\u5207\u6362\u4e3a\u8bc1\u636e\u4f18\u5148\u56de\u7b54\u3002";
}

function isResponsibilityPressureQuestion(message) {
  const text = String(message || "").trim();
  return /(\u8c01\u5728\u62d6\u540e\u817f|\u8c01\u62d6\u540e\u817f|\u8c01\u5728\u5361|\u8c01\u5361\u4f4f\u4e86|\u8c01\u6ca1\u63a8\u8fdb|\u8c01\u6ca1\u8ddf\u8fdb|\u8c01\u5728\u963b\u585e|\u8c01\u5728\u8017\u7740)/.test(text);
}

function needsScopeFirst({ message, selectedTask, searchResults, knowledge }) {
  if (selectedTask) return false;
  if (Array.isArray(searchResults) && searchResults.length) return false;
  if (Array.isArray(knowledge?.matched) && knowledge.matched.length) return false;
  return isResponsibilityPressureQuestion(message);
}

function maybeHandleAmbiguousResponsibilityQuery(context) {
  if (!needsScopeFirst(context)) return null;
  return {
    handled: true,
    title: "\u9700\u8981\u5148\u7f29\u5c0f\u8303\u56f4",
    answer: "\u201c\u8c01\u5728\u62d6\u540e\u817f\u201d\u8fd9\u79cd\u95ee\u6cd5\u8fd8\u4e0d\u8db3\u4ee5\u76f4\u63a5\u6307\u5411\u4e2a\u4eba\u3002\u5148\u544a\u8bc9\u6211\u662f\u54ea\u6761\u4e1a\u52a1\u7ebf\u3001\u54ea\u4e2a\u9879\u76ee\u3001\u54ea\u4e2a\u7fa4\u6216\u54ea\u6bb5\u65f6\u95f4\uff0c\u6211\u5c31\u6309\u8d23\u4efb\u94fe\u5e2e\u4f60\u627e\u51fa\u6700\u53ef\u80fd\u7684\u5361\u70b9\u3001\u8d1f\u8d23\u4eba\u548c\u4e0b\u4e00\u6b65\u3002",
    highlights: [
      "\u5148\u7ed9\u8303\u56f4\uff1a\u4e1a\u52a1\u7ebf / \u9879\u76ee\u540d / \u7fa4\u540d / \u65f6\u95f4\u8303\u56f4",
      "\u6709\u8303\u56f4\u540e\uff0c\u6211\u4f1a\u4f18\u5148\u8fd4\u56de\u8d23\u4efb\u94fe\u3001\u963b\u585e\u70b9\u548c\u63a8\u8fdb\u8def\u5f84",
      "\u6ca1\u6709\u8bc1\u636e\u65f6\uff0c\u6211\u4e0d\u4f1a\u76f4\u63a5\u7a7a\u62a5\u4eba\u540d"
    ],
    follow_ups: [
      "\u97e9\u56fd\u53ec\u56de\u6d3b\u52a8\u8c01\u5728\u63a8\u8fdb\uff0c\u5361\u5728\u54ea\u4e00\u6b65\uff1f",
      "\u7ffb\u8bd1\u5de5\u4f5c\u6700\u8fd1\u8c01\u5728\u8ddf\uff0c\u98ce\u9669\u662f\u4ec0\u4e48\uff1f",
      "\u4e2d\u5fc3\u7814\u53d1\u4efb\u52a1\u6700\u8fd1\u8c01\u5728\u8d1f\u8d23\uff0c\u65f6\u95f4\u7ebf\u5230\u54ea\u4e86\uff1f"
    ],
    warnings: [],
    suggested_mode: "company",
    suggested_task_id: "",
    actions: [{ label: "\u6253\u5f00\u5ba1\u8ba1\u63a7\u5236\u53f0", type: "open_url", url: "/audit-console.html" }]
  };
}

function maybeHandleSimpleUtilityQuestion(context) {
  const text = String(context?.message || "").trim();
  if (!text) return null;

  if (/(今天.*(星期几|周几)|今天几号|今天日期|现在几点|现在时间)/.test(text)) {
    const now = new Date();
    const weekday = `星期${"日一二三四五六"[now.getDay()]}`;
    const dateText = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`;
    const timeText = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    return {
      handled: true,
      title: "时间",
      answer: `现在是 ${dateText} ${weekday} ${timeText}。`,
      highlights: [
        `日期：${dateText}`,
        `星期：${weekday}`,
        `时间：${timeText}`
      ],
      follow_ups: [
        "帮我写一封催进度的邮件",
        "帮我把问题压成最短推进路径"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: context?.selectedTask?.id || "",
      actions: []
    };
  }

  if (/(写(一封)?(中文)?邮件|邮件草稿|起草邮件|催一下.*进度)/.test(text)) {
    const topic = extractEmailTopic(text);
    const subject = topic ? `关于${topic}的进度跟进` : "事项进度跟进";
    const body = [
      `主题：${subject}`,
      "",
      "你好，",
      "",
      `想跟进一下${topic || "相关事项"}的当前进展。请帮我确认：`,
      "1. 现在进展到哪一步；",
      "2. 当前卡点是什么；",
      "3. 下一时间点和负责人是谁。",
      "",
      "如果今天方便，也请直接给我一个最短推进路径。",
      "",
      "谢谢。"
    ].join("\n");
    return {
      handled: true,
      title: "邮件草稿",
      answer: body,
      highlights: [
        "默认语气：直接、礼貌、可执行",
        "如果你给我具体事项名，我可以继续改成定向版本"
      ],
      follow_ups: [
        "把这封邮件改得更强硬一点",
        topic ? `把这封邮件改成围绕${topic}的版本` : "把这封邮件改成围绕翻译进度的版本"
      ],
      warnings: [],
      suggested_mode: "company",
      suggested_task_id: context?.selectedTask?.id || "",
      actions: []
    };
  }

  return null;
}

function extractEmailTopic(text) {
  const value = String(text || "")
    .replace(/帮我|请|写(一封)?(中文)?邮件|邮件草稿|起草邮件|催一下/gu, " ")
    .replace(/[，。,.!！?？]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return value || "";
}

function resolveSelectedTask(rawTask, tasks) {
  const taskId = String(rawTask?.id || "").trim();
  if (!taskId) return null;
  return tasks.find((task) => task.id === taskId) || null;
}

function inferTaskFromMessage(message, tasks) {
  const normalized = String(message || "").trim().toLowerCase();
  if (!normalized) return null;
  const ranked = (Array.isArray(tasks) ? tasks : [])
    .map((task) => ({
      task,
      ...analyzeTaskMatch(normalized, task)
    }))
    .sort((left, right) => right.score - left.score);
  const best = ranked[0];
  if (!best) return null;
  if (best.strongMatches < 2 || best.score < 8) return null;
  if (ranked[1] && best.score - ranked[1].score < 2) return null;
  return best.task;
}

function scoreTask(text, task) {
  return analyzeTaskMatch(text, task).score;
}

function analyzeTaskMatch(text, task) {
  const hints = [
    task?.id,
    task?.title,
    task?.summary,
    task?.block_node,
    ...(Array.isArray(task?.keyword_hints) ? task.keyword_hints : [])
  ]
    .map((item) => String(item || "").trim().toLowerCase())
    .filter(Boolean);

  let score = 0;
  let strongMatches = 0;
  let matchCount = 0;
  for (const hint of hints) {
    if (text.includes(hint)) {
      matchCount += 1;
      const isLowSignal = LOW_SIGNAL_TASK_HINTS.has(hint);
      if (!isLowSignal && hint.length >= 4) {
        score += 4;
        strongMatches += 1;
      } else if (!isLowSignal && hint.length >= 2) {
        score += 3;
        strongMatches += 1;
      } else if (isLowSignal) {
        score += 1;
      } else {
        score += 2;
      }
    }
  }
  return {
    score,
    strongMatches,
    matchCount
  };
}


function hasTaskLeak(text, context) {
  if (context.selectedTask) return false;
  const answerText = String(text || "").trim().toLowerCase();
  if (!answerText) return false;
  const userText = String(context.message || "").trim().toLowerCase();
  return (Array.isArray(context.snapshot?.tasks) ? context.snapshot.tasks : []).some((task) => {
    const answerMatch = analyzeTaskMatch(answerText, task);
    const userMatch = analyzeTaskMatch(userText, task);
    return answerMatch.strongMatches >= 1 && answerMatch.score >= 6 && userMatch.score < 6;
  });
}

function matchesAny(message, keywords) {
  const text = String(message || "").toLowerCase();
  return keywords.some((keyword) => text.includes(String(keyword).toLowerCase()));
}

function normalizeHistory(history, message = "") {
  const normalized = (Array.isArray(history) ? history : [])
    .map((item) => ({
      role: String(item.role || "user").trim().slice(0, 20),
      content: String(item.content || "").trim().slice(0, 500)
    }))
    .filter((item) => item.content)
    .slice(-8);

  const currentMessage = String(message || "").trim();
  if (currentMessage && normalized.length) {
    const last = normalized[normalized.length - 1];
    if (last.role === "user" && last.content === currentMessage) {
      normalized.pop();
    }
  }
  return normalized;
}

function safeWorkspaceSummary(workspacePath) {
  const candidate = String(workspacePath || "").trim();
  if (!candidate) return "";
  try {
    const workspaceRoot = normalizeWorkspacePath(candidate);
    const tree = listWorkspaceTree(workspaceRoot, { maxDepth: 3, maxFiles: 140 });
    return summarizeWorkspaceTree(tree.tree).slice(0, 3000);
  } catch {
    return "";
  }
}
