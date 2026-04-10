---
name: bydfi-sentinel
description: Run BYDFI-local audit, digest, and CEO brief workflows from Hermes. Use when the user asks for a BYDFI audit report, daily or weekly ops digest, McKinsey-style CEO brief, evidence guard check, or wants the agent to operate the local BYDFI audit bot workspace instead of only summarizing.
version: 1.0.0
author: local
license: Proprietary
metadata:
  hermes:
    tags: [BYDFI, Audit, Ops, CEO-Brief, Reporting, Productivity]
---

# bydfi-sentinel

This skill turns the local `bydfi-audit-bot` workspace into a callable execution layer for Hermes.

## When To Use

Use this skill when the user asks for any of the following:

- Run a BYDFI daily ops digest
- Run a BYDFI weekly ops digest
- Generate or refresh a McKinsey-style CEO report
- Run an evidence guard / hallucination risk audit
- Operate the local BYDFI reporting bot instead of only answering in chat

## Expected Local Layout

By default this skill expects a sibling repo layout:

```text
<workspace>/
  hermes-agent/
  bydfi-audit-bot/
```

If your layout is different, set:

```bash
export BYDFI_AUDIT_BOT_ROOT=/absolute/path/to/bydfi-audit-bot
export BYDFI_AUDIT_BOT_PYTHON=python
```

## Primary Entry Point

Use the wrapper:

```bash
python skills/productivity/bydfi-sentinel/scripts/bydfi_sentinel.py <action> [args...]
```

## Supported Actions

### 1. Daily ops digest

```bash
python skills/productivity/bydfi-sentinel/scripts/bydfi_sentinel.py daily --render-digest-pdf --render-ceo
```

Use when the user wants today's digest, today's internal report, or a daily BYDFI ops snapshot.

### 2. Weekly ops digest

```bash
python skills/productivity/bydfi-sentinel/scripts/bydfi_sentinel.py weekly --render-digest-pdf --render-ceo
```

Use when the user wants a weekly summary, weekly digest, or a heavier coverage pass.

### 3. McKinsey CEO cycle

```bash
python skills/productivity/bydfi-sentinel/scripts/bydfi_sentinel.py mckinsey --period daily
python skills/productivity/bydfi-sentinel/scripts/bydfi_sentinel.py mckinsey --period weekly --render-final-pdf
```

Use when the user explicitly wants a CEO brief, management report, or the McKinsey workflow.

### 4. Evidence guard / hallucination audit

```bash
python skills/productivity/bydfi-sentinel/scripts/bydfi_sentinel.py evidence-guard
```

Use when the user wants to know whether the latest report is safe to trust, whether the evidence base is degraded, or whether the reporting pipeline is hallucinating.

## Output Discipline

- Prefer returning the generated file paths, status, and the most important blocking facts.
- Do not dump entire raw logs into the user-facing answer unless asked.
- If a runner fails, summarize the failure and cite the exact script that failed.
- Separate "report generated" from "report trustworthy".

## Recommended Hermes Behavior

When this skill is loaded and the user gives a BYDFI reporting task:

1. Decide which action maps to the user intent.
2. Run the wrapper script with the smallest action that satisfies the request.
3. Read the returned JSON summary.
4. Answer with:
   - what was run
   - whether it succeeded
   - where the output lives
   - what the next human action is, if any

## Guardrails

- Do not invent missing report paths.
- Do not claim delivery/webhook upload happened unless the returned JSON says so.
- Do not claim coverage is complete unless the evidence output explicitly says so.
