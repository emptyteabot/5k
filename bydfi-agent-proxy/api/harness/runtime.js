function sortSkills(skills = []) {
  return [...skills].sort((left, right) => (right.priority || 0) - (left.priority || 0));
}

async function runHarness({ context, skills = [], validateResult, fallback }) {
  const ordered = sortSkills(skills);
  const trace = [];

  for (const skill of ordered) {
    let matched = false;
    try {
      matched = await skill.match(context);
    } catch (error) {
      trace.push({ skillId: skill.id, stage: "match", accepted: false, reason: error.message || "match_failed" });
      continue;
    }

    if (!matched) continue;

    let rawResult = null;
    try {
      rawResult = await skill.run(context);
    } catch (error) {
      trace.push({ skillId: skill.id, stage: "run", accepted: false, reason: error.message || "run_failed" });
      continue;
    }

    const verdict = validateResult
      ? validateResult(context, rawResult, skill)
      : { accepted: !!rawResult, result: rawResult, reason: rawResult ? "accepted" : "empty_result" };

    trace.push({
      skillId: skill.id,
      stage: "validate",
      accepted: !!verdict.accepted,
      reason: verdict.reason || ""
    });

    if (verdict.accepted) {
      return {
        ...verdict.result,
        harness: {
          selectedSkill: skill.id,
          mode: "harness",
          trace
        }
      };
    }
  }

  if (typeof fallback === "function") {
    const result = await fallback(context, trace);
    return {
      ...result,
      harness: {
        selectedSkill: "fallback",
        mode: "harness",
        trace
      }
    };
  }

  throw new Error("no_skill_resolved");
}

module.exports = {
  runHarness
};
