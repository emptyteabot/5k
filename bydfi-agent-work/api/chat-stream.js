import { recordAuditEvent, recordMonitorEvent } from "./_enterprise.js";
import { recordConversationTurn } from "./_memory.js";
import { readJsonBody, requireMethod, setCors } from "./_lib.js";
import {
  buildResponseCitations,
  buildStreamingFallbackText,
  buildStreamingMeta,
  maybeHandleEnterpriseCommand,
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
  if (!context.message) {
    res.status(400).json({ error: "message is required" });
    return;
  }

  const commandResponse = maybeHandleEnterpriseCommand(context);
  const meta = buildStreamingMeta({
    message: context.message,
    snapshot: context.snapshot,
    selectedTask: context.selectedTask,
    workspaceSummary: context.workspaceSummary,
    commandResponse
  });
  meta.citations = buildResponseCitations(context, commandResponse);

  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no"
  });
  res.flushHeaders?.();

  writeSse(res, "meta", meta);

  let answer = "";
  let structuredResponse = commandResponse || null;
  try {
    if (commandResponse) {
      answer = String(commandResponse.answer || "").trim();
    } else {
      structuredResponse = await runStructuredChatPipeline(context);
      meta.title = String(structuredResponse?.title || meta.title || "BYDFI GPT").trim() || "BYDFI GPT";
      meta.citations = buildResponseCitations(context, structuredResponse);
      meta.actions = Array.isArray(structuredResponse?.actions) ? structuredResponse.actions : meta.actions || [];
      answer = String(structuredResponse?.answer || "").trim();
    }

    for (const chunk of chunkText(answer)) {
      writeSse(res, "delta", { delta: chunk });
    }

    writeSse(res, "done", {
      ...meta,
      answer,
      actions: Array.isArray(structuredResponse?.actions) ? structuredResponse.actions : meta.actions || [],
      citations: Array.isArray(structuredResponse?.citations)
        ? structuredResponse.citations
        : meta.citations || []
    });
    res.end();

    recordAuditEvent("company_chat_stream", {
      selectedTaskId: context.selectedTask?.id || "",
      suggestedMode: meta.suggested_mode
    });
    recordMonitorEvent("company_chat_stream", "ok", {
      selectedTaskId: context.selectedTask?.id || ""
    });
  } catch (error) {
    const fallback = buildStreamingFallbackText({
      message: context.message,
      snapshot: context.snapshot,
      selectedTask: context.selectedTask,
      workspaceSummary: context.workspaceSummary,
      searchResults: context.searchResults,
      error
    });

    for (const chunk of chunkText(fallback)) {
      answer += chunk;
      writeSse(res, "delta", { delta: chunk });
    }

    writeSse(res, "done", {
      ...meta,
      answer,
      actions: meta.actions || [],
      citations: meta.citations || [],
      warning: "已启用证据优先兜底回答。"
    });
    res.end();

    recordMonitorEvent("company_chat_stream", "warn", {
      selectedTaskId: context.selectedTask?.id || "",
      fallback: true
    });
  } finally {
    if (context.message) {
      recordConversationTurn(context.clientId, "user", context.message, {
        taskId: context.selectedTask?.id || "",
        mode: meta.suggested_mode
      });
      if (answer) {
        recordConversationTurn(context.clientId, "assistant", answer, {
          taskId: context.selectedTask?.id || "",
          mode: meta.suggested_mode
        });
      }
    }
  }
}

function writeSse(res, eventName, payload) {
  res.write(`event: ${eventName}\n`);
  res.write(`data: ${JSON.stringify(payload)}\n\n`);
}

function chunkText(text, size = 48) {
  const value = String(text || "");
  const chunks = [];
  for (let index = 0; index < value.length; index += size) {
    chunks.push(value.slice(index, index + size));
  }
  return chunks;
}
