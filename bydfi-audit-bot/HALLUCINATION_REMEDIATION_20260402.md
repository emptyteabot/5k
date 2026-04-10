# BYDFI Report Hallucination Remediation

Date: 2026-04-02

## Scope

This repo snapshot is not a full source checkout. It contains the live data store, autopilot state, and failure logs, but the main pipeline entrypoints are missing. The diagnosis below is therefore based on the current evidence store and the latest management memo, not on a runnable end-to-end code path.

## Current Reality

The reporting problem is structural, not stylistic.

1. The autopilot pipeline is broken at the entrypoint level.
   - `data/reports/autopilot_state.json` shows the latest retry and backfill both failed because `run_incremental_cycle.py` and `run_history_backfill.py` could not be opened.
   - `data/logs/autopilot/autopilot.log` shows timeout, retry, degraded health, and a failed backfill.
2. The evidence layer and judgment layer are mixed together.
   - `audit_records` contains raw documents, system noise, and AI-written summary content in the same table.
   - A record such as `id=1280` already stores a complete "群汇总分析" narrative inside the evidence store.
   - A record such as `id=2326` stores strong CEO-facing management judgments without a claim-to-evidence map.
3. The audit trail is incomplete.
   - `audit_runs` is empty.
   - `inbound_messages` can be `replied` with `ANALYZED::...` markers, but there is no durable prompt, model, citation, or output lineage.
4. The history layer is polluted.
   - `dept_meeting_history` contains many near-empty records with content lengths of `4`, `5`, `9`, `22`, `36`.
   - These records are too weak to support trend analysis, delay calls, or department evaluation.
5. Document extraction quality is unsafe.
   - `source_documents` includes UI chrome and noise such as `上传日志`, `联系客服`, `帮助中心`, `加载中...`.
   - Encoding pollution is present, for example titles like `3.17\x01会议总结\x01`.

## Why This Produces Hallucinations

1. Broken pipelines keep the system from knowing whether the latest report is truly current.
2. AI summaries written back into the main evidence store create feedback loops.
3. Weak or noisy records are treated as if they were real business evidence.
4. The current storage model preserves conclusions but not the reasoning chain that produced them.
5. When a report generator sees partial evidence, it can still produce a complete management narrative instead of stopping with "insufficient evidence".

## Management-Level Risk

If the current system keeps producing CEO-style reports without hard gating, the likely failure mode is not a small wording error. The likely failure mode is false management intervention:

1. Wrong person gets blamed because "department/individual assessment" is inferred from stale or partial records.
2. Delay risk is reported from missing ETA fields or recycled history, not from current execution evidence.
3. Business direction calls are made off AI summaries of AI summaries instead of first-order source material.
4. The team starts optimizing for report appearance instead of evidence quality.

## What Must Change

### P0: Stop unsupported reporting

Do not generate management analysis when any of the following is true:

1. Pipeline entrypoint missing.
2. Autopilot health is degraded.
3. `audit_runs` is empty for the reporting window.
4. Latest business evidence is older than the report claim window.
5. Evidence set contains AI-generated summary artifacts that are not explicitly excluded.

### P0: Separate evidence from judgment

Split storage into at least three layers:

1. Raw evidence:
   - original message
   - original document extract
   - immutable source metadata
2. Normalized evidence:
   - cleaned正文
   - business/system classification
   - confidence and extraction quality fields
3. Analysis output:
   - report claim
   - supporting source ids
   - unsupported / inferred flags
   - model / prompt / run id

No analysis output should be written back into the raw evidence tables.

### P0: Force citation and uncertainty

Every non-trivial claim in a report must carry:

1. source ids
2. source timestamps
3. source types
4. confidence label
5. whether the claim is direct, inferred, or blocked by missing evidence

If these fields are absent, the report should refuse to state the claim.

### P1: Clean the evidence set before analysis

Before any department or CEO report:

1. remove system messages
2. remove UI chrome / extraction garbage
3. mark AI-generated meeting notes as secondary evidence
4. reject department history records below a minimum content threshold
5. reject records with broken encoding until repaired

### P1: Tighten scope

The latest management memo already implies the right direction:

1. focus on a few high-priority issues
2. require owner, ETA, and acceptance criteria
3. refuse process theater

This should become a hard output rule, not a prompt suggestion.

## Immediate Operating Rules

Until the full pipeline is restored, use these manual rules:

1. Treat all CEO/department judgments as provisional unless they cite first-order evidence.
2. Do not call delay risk unless there is a named owner, baseline date, and current state.
3. Do not score personal efficiency from meeting attendance or recycled history.
4. Do not merge AI meeting summaries and raw meeting notes into one evidence bucket.
5. If the latest business evidence is mostly historical documents imported on one day, state that explicitly.

## Deliverables Added Today

1. `evidence_guard_audit.py`
   - audits the local evidence store
   - checks pipeline health, stale evidence, noisy records, weak history, and AI-summary contamination
   - writes a markdown and json report under `data/reports`
2. This remediation memo

## Next Step

The next real fix is not "better wording". It is restoring a runnable pipeline and inserting hard evidence gates before any management report can be published.
