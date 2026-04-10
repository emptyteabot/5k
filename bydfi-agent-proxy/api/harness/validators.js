const DEFAULT_FORBIDDEN_PATTERNS = [
  /README\.md/i,
  /ngrok/i,
  /FEISHU_VERIFICATION_TOKEN/i,
  /Claude Audit/i,
  /知识卡命中/i,
  /兜底/i,
  /Harness rejected/i
];

function sanitizeAnswerText(text, leakyPhrases = []) {
  let answer = String(text || "").trim();
  if (!answer) return "";
  for (const phrase of leakyPhrases) {
    answer = answer.replaceAll(phrase, "");
  }
  return answer.replace(/^[:：\s]+/, "").trim();
}

function containsAny(text, patterns = []) {
  return patterns.some((pattern) => {
    if (!pattern) return false;
    if (pattern instanceof RegExp) return pattern.test(text);
    return text.includes(String(pattern));
  });
}

function validateHarnessResult(context, rawResult, skill = {}) {
  if (!rawResult || typeof rawResult !== "object") {
    return { accepted: false, reason: "empty_result" };
  }

  const sanitized = sanitizeAnswerText(rawResult.answer, context.leakyPhrases || []);
  if (!sanitized) {
    return { accepted: false, reason: "empty_answer" };
  }

  const forbidden = [...DEFAULT_FORBIDDEN_PATTERNS, ...(skill.forbiddenPatterns || [])];
  if (containsAny(sanitized, forbidden)) {
    return { accepted: false, reason: "forbidden_phrase" };
  }

  if (skill.shouldContainAny?.length && !containsAny(sanitized, skill.shouldContainAny)) {
    return { accepted: false, reason: "keyword_mismatch" };
  }

  return {
    accepted: true,
    reason: "accepted",
    result: {
      ...rawResult,
      answer: sanitized
    }
  };
}

module.exports = {
  sanitizeAnswerText,
  validateHarnessResult,
  DEFAULT_FORBIDDEN_PATTERNS
};
