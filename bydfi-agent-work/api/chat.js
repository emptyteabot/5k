import { recordAuditEvent, recordMonitorEvent } from "./_enterprise.js";
import { recordConversationTurn } from "./_memory.js";
import { readJsonBody, requireMethod, setCors } from "./_lib.js";
import {
  buildResponseCitations,
  buildCompanyUserPrompt,
  buildFallbackStructuredResponse,
  maybeHandleEnterpriseCommand,
  normalizeMode,
  normalizeTaskId,
  prepareCompanyContext,
  runStructuredChatPipeline
} from "./_chat.js";

export default async function handler(req, res) {
  const cors = setCors(req, res);
  if (!cors.allowed) {
    res.status(403).json({ error: "CORS origin denied" });
    return;
  }
  if (!requireMethod(req, res, "POST")) return;

  const body = await readJsonBody(req);
  const context = prepareCompanyContext(body);
  recordMonitorEvent("company_chat_context", "info", {
    clientId: context.clientId,
    messagePreview: context.message.slice(0, 120),
    selectedTaskId: context.selectedTask?.id || "",
    searchHitCount: context.searchResults.length
  });
  if (!context.message) {
    res.status(400).json({ error: "message is required" });
    return;
  }

  let response;
  const commandResponse = maybeHandleEnterpriseCommand(context);
  try {
    response = commandResponse || await runStructuredChatPipeline(context);
  } catch (error) {
    response = buildFallbackStructuredResponse({
      message: context.message,
      snapshot: context.snapshot,
      selectedTask: context.selectedTask,
      workspaceSummary: context.workspaceSummary,
      knowledge: context.knowledge,
      searchResults: context.searchResults,
      error
    });
  }

  const normalized = {
    title: String(response.title || "BYDFI Agent").trim() || "BYDFI Agent",
    answer: String(response.answer || "").trim(),
    highlights: Array.isArray(response.highlights)
      ? response.highlights.map((item) => String(item).trim()).filter(Boolean).slice(0, 6)
      : [],
    follow_ups: Array.isArray(response.follow_ups)
      ? response.follow_ups.map((item) => String(item).trim()).filter(Boolean).slice(0, 6)
      : [],
    warnings: Array.isArray(response.warnings)
      ? response.warnings.map((item) => String(item).trim()).filter(Boolean).slice(0, 4)
      : [],
    suggested_mode: normalizeMode(response.suggested_mode),
    suggested_task_id: normalizeTaskId(response.suggested_task_id, context.snapshot.tasks),
    actions: Array.isArray(response.actions)
      ? response.actions.map((item) => ({
          label: String(item.label || "操作").trim(),
          type: String(item.type || "").trim(),
          url: String(item.url || "").trim(),
          taskId: String(item.taskId || item.task_id || "").trim(),
          prompt: String(item.prompt || "").trim(),
          demoId: String(item.demoId || "").trim()
        })).filter((item) => item.type)
      : [],
    citations: buildResponseCitations(context, response)
  };

  res.status(200).json({
    ok: true,
    response: normalized,
    context: {
      selectedTaskId: context.selectedTask?.id || "",
      workspaceLoaded: Boolean(context.workspaceSummary),
      enterprise: context.enterprise
    }
  });

  recordAuditEvent("company_chat", {
    selectedTaskId: context.selectedTask?.id || "",
    suggestedMode: normalized.suggested_mode
  });
  recordMonitorEvent("company_chat", "ok", {
    selectedTaskId: context.selectedTask?.id || ""
  });
  recordConversationTurn(context.clientId, "user", context.message, {
    taskId: context.selectedTask?.id || "",
    mode: normalized.suggested_mode
  });
  recordConversationTurn(context.clientId, "assistant", normalized.answer, {
    taskId: context.selectedTask?.id || "",
    mode: normalized.suggested_mode
  });
}
