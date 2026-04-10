from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

RISK_TRANSLATIONS = {
    "Autopilot health is degraded": {
        "title": "自动链路健康度下降",
        "impact": "所谓“最新日报”很可能其实是陈旧、残缺或失败产物。",
        "action": "正式生成日报前，必须先校验链路健康和任务成功状态。",
    },
    "No durable audit run lineage exists": {
        "title": "审计 run 链路缺失",
        "impact": "当前结论无法追溯到 prompt、模型、源数据和执行 run。",
        "action": "给每次日报补齐 run_id、prompt hash、model id、source ids 和产物落盘。",
    },
    "AI-generated analysis is mixed into the evidence store": {
        "title": "AI 二次分析混入原始证据库",
        "impact": "后续日报可能在总结上一轮 AI 输出，而不是一手业务证据。",
        "action": "把分析产物和原始证据分层存放，默认检索时排除二次分析。",
    },
    "Department history contains empty or near-empty records": {
        "title": "部门历史记录存在空内容",
        "impact": "趋势判断会被占位记录和空记录污染。",
        "action": "低内容记录先剔除，再做部门进展判断。",
    },
    "Noise and system chatter are mixed into business evidence": {
        "title": "业务证据混入系统噪音",
        "impact": "模型会把群操作、系统提示和 UI 噪音误判成业务进展。",
        "action": "在摘要前先做系统噪音识别和剥离。",
    },
    "Encoding pollution exists in source metadata": {
        "title": "源数据存在编码污染",
        "impact": "去重、归因和聚类都会失真。",
        "action": "编码修复前，这类记录不应直接进入管理层日报。",
    },
    "Secondary AI meeting summaries exist in source documents": {
        "title": "源文档中存在 AI 二次会议总结",
        "impact": "这类内容只能作为辅助材料，不能直接当成一手证据。",
        "action": "把它们标成二级证据，并要求一手材料交叉确认。",
    },
}

SOURCE_TYPE_LABELS = {
    "external_document_message": "外部文档消息",
    "document_message": "文档消息",
    "group_message": "群消息",
    "meeting_note": "会议纪要",
}

MOJIBAKE_MARKERS = (
    "鑷",
    "鍙",
    "銆",
    "锛",
    "鈥",
    "鏈€",
    "璇",
    "鍔",
    "闃",
    "绔",
    "鎶",
)


def pick_latest(paths: list[Path]) -> Path | None:
    return max(paths, key=lambda item: item.stat().st_mtime, default=None)


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def severity_rank(value: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(str(value).lower(), 0)


def parse_time(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def format_cn_time(value: str | None) -> str:
    parsed = parse_time(value)
    if parsed is None:
        return "暂无"
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M")


def format_cn_day(value: str | None) -> str:
    parsed = parse_time(value)
    if parsed is None:
        return datetime.now().astimezone().strftime("%Y-%m-%d")
    return parsed.astimezone().strftime("%Y-%m-%d")


def relative_age_text(value: str | None, *, anchor: str | None = None) -> str:
    target = parse_time(value)
    base = parse_time(anchor) or datetime.now().astimezone()
    if target is None:
        return "暂无"
    hours = max(0.0, (base - target).total_seconds() / 3600)
    if hours < 1:
        return "不到 1 小时"
    if hours < 24:
        return f"{round(hours)} 小时"
    return f"{hours / 24:.1f} 天"


def clean_text(value: Any, *, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def looks_garbled(value: Any) -> bool:
    text = str(value or "")
    if not text:
        return False
    marker_hits = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
    return marker_hits >= 3


def normalize_text(value: Any, *, fallback: str, limit: int = 140) -> str:
    text = clean_text(value, limit=limit)
    if not text:
        return fallback
    if looks_garbled(text):
        return fallback
    return text


def source_type_label(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "未知来源"
    return SOURCE_TYPE_LABELS.get(raw, raw)


def build_latest_anchor(report: dict[str, Any]) -> dict[str, str]:
    latest_record = report.get("latest_substantive_record", {})
    return {
        "reporter_name": clean_text(latest_record.get("reporter_name"), limit=48) or "未知上报人",
        "source_type_label": source_type_label(latest_record.get("source_type")),
        "source_title": normalize_text(
            latest_record.get("source_title"),
            fallback="原始标题存在编码污染，暂不直接引用。",
            limit=96,
        ),
        "preview": normalize_text(
            latest_record.get("preview"),
            fallback="原始预览存在编码污染，已隐藏。",
            limit=420,
        ),
        "message_timestamp": format_cn_time(latest_record.get("message_timestamp")),
    }


def translate_risk(risk: dict[str, Any]) -> dict[str, Any]:
    raw_title = str(risk.get("title") or "未命名风险")
    translated = RISK_TRANSLATIONS.get(raw_title)
    evidence = [
        normalize_text(item, fallback="证据项存在编码污染，已折叠。", limit=120)
        for item in risk.get("evidence", [])
    ]
    return {
        "severity": str(risk.get("severity") or "low").lower(),
        "title": translated["title"] if translated else raw_title,
        "impact": translated["impact"]
        if translated
        else normalize_text(risk.get("impact"), fallback="影响待确认。", limit=140),
        "action": translated["action"]
        if translated
        else normalize_text(risk.get("action"), fallback="动作待补充。", limit=140),
        "evidence": evidence,
    }


def has_path_encoding_issue(report: dict[str, Any]) -> bool:
    autopilot_state = report.get("autopilot_state", {}) if isinstance(report, dict) else {}
    tails = [
        str(autopilot_state.get("last_incremental_retry_tail", "")),
        str(autopilot_state.get("last_backfill_tail", "")),
    ]
    merged = "\n".join(tails).lower()
    return "can't open file" in merged and ("����" in merged or "½»" in merged)


def build_operator_message(missing_files: list[str], path_encoding_issue: bool) -> str:
    if path_encoding_issue:
        return "当前自动日报链路未恢复健康，核心阻塞是运行环境路径编码异常：Python 无法打开 run_incremental_cycle.py / run_history_backfill.py。今天的输出只能给出已核实事实、阻塞点和修复动作。"
    if missing_files:
        missing = "、".join(missing_files)
        return f"当前自动日报链路未恢复健康，关键入口文件缺失：{missing}。今天的输出只能给出已核实事实、阻塞点和修复动作。"
    return "当前自动日报链路未通过健康校验。今天的输出只保留已核实事实和明确动作，不伪装成正常业务进展。"


def build_cards(
    report: dict[str, Any],
    missing_files: list[str],
    path_encoding_issue: bool,
    generated_at: str,
    risk_counts: dict[str, int],
) -> list[dict[str, str]]:
    metrics = report.get("metrics", {})
    return [
        {
            "label": "日报状态",
            "value": str(report.get("overall_status", "unknown")).upper(),
            "detail": "链路异常时只输出核实事实和修复动作，不拼装假进展。",
            "tone": "rose" if report.get("overall_status") == "fail" else "accent",
        },
        {
            "label": "最新证据时差",
            "value": relative_age_text(report.get("latest_any_message_timestamp"), anchor=generated_at),
            "detail": f"最新一手证据时间：{format_cn_time(report.get('latest_any_message_timestamp'))}",
            "tone": "cyan",
        },
        {
            "label": "高压风险数",
            "value": str(risk_counts.get("critical", 0) + risk_counts.get("high", 0)),
            "detail": f"{risk_counts.get('critical', 0)} 个 critical，{risk_counts.get('high', 0)} 个 high",
            "tone": "amber",
        },
        {
            "label": "缺失入口",
            "value": "0" if path_encoding_issue else str(len(missing_files)),
            "detail": "当前未发现入口文件缺失，主要阻塞是运行环境路径编码异常。"
            if path_encoding_issue
            else "入口文件缺失意味着链路还没恢复，日报必须如实暴露阻塞。",
            "tone": "rose" if (missing_files or path_encoding_issue) else "accent",
        },
        {
            "label": "证据文档",
            "value": str(metrics.get("source_documents_count", 0)),
            "detail": f"噪音文档 {metrics.get('noisy_doc_count', 0)}，系统噪音记录 {metrics.get('system_noise_record_count', 0)}",
            "tone": "accent",
        },
        {
            "label": "审计链路",
            "value": str(metrics.get("audit_runs_count", 0)),
            "detail": f"无 lineage 输出 {metrics.get('replied_without_runs', 0)} 条",
            "tone": "amber",
        },
    ]


def build_sections(
    report: dict[str, Any],
    latest_anchor: dict[str, str],
    missing_files: list[str],
    path_encoding_issue: bool,
    generated_at: str,
    risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    metrics = report.get("metrics", {})
    verified_facts = [
        f"最新一手业务证据时间：{format_cn_time(report.get('latest_any_message_timestamp'))}，距当前已滞后 {relative_age_text(report.get('latest_any_message_timestamp'), anchor=generated_at)}。",
        f"最新一手证据上报人：{latest_anchor['reporter_name']}；来源类型：{latest_anchor['source_type_label']}。",
        f"最新一手证据标题：{latest_anchor['source_title']}",
        f"当前证据库文档数：{metrics.get('source_documents_count', 0)}；其中噪音文档 {metrics.get('noisy_doc_count', 0)} 条，系统噪音记录 {metrics.get('system_noise_record_count', 0)} 条。",
        f"审计运行链路记录数：{metrics.get('audit_runs_count', 0)}；但系统内已有无 run lineage 的回复 {metrics.get('replied_without_runs', 0)} 条。",
    ]

    risk_bullets = [
        f"[{str(item.get('severity', '')).upper()}] {item.get('title')}：{item.get('impact')} 动作：{item.get('action')}"
        for item in risks[:3]
    ]

    action_bullets = [
        "先补齐缺失入口文件，恢复最基本的数据采集入口。",
        "修复 run_incremental_cycle / run_history_backfill 的真实执行路径，再谈业务日报自动化。",
        "给每次日报输出补齐 run_id、prompt hash、source ids，避免出现“有结论、无链路”。",
    ]
    if path_encoding_issue:
        action_bullets[0] = "先修复运行环境路径编码问题，恢复 run_incremental_cycle / run_history_backfill 可执行。"
    elif missing_files:
        action_bullets[0] = f"先补齐缺失入口文件：{'、'.join(missing_files)}。"
    else:
        action_bullets[0] = "当前未发现缺失入口文件，下一步应集中修复增量采集和回填任务的执行失败。"

    cannot_conclude = [
        "不能据此输出真实业务进展日报，因为当前链路处于 fail-closed 状态，数据不是新鲜的。",
        "不能据此输出部门执行质量结论，因为存在短记录、AI 二次总结和系统噪音混入。",
        "不能据此输出确定性的延期、交付和方向一致性判断，因为 owner、ETA、acceptance lineage 仍不完整。",
    ]

    return [
        {
            "title": "今日结论",
            "intro": "这不是展示型看板，而是今天可以直接往上发的日报骨架。",
            "bullets": [
                "当前自动日报链路仍处于 fail-closed 状态，今天只能输出已核实事实、核心阻塞和修复动作，不能伪装成正常业务进展日报。",
                f"最新业务证据仍停留在 {format_cn_time(report.get('latest_any_message_timestamp'))}，说明当前日报自动化已经脱离实时状态。",
            ],
        },
        {
            "title": "已确认事实",
            "bullets": verified_facts,
        },
        {
            "title": "核心阻塞",
            "bullets": risk_bullets or ["今天没有提取到高置信阻塞项。"],
        },
        {
            "title": "下一步动作",
            "bullets": action_bullets,
        },
        {
            "title": "当前不能下的结论",
            "bullets": cannot_conclude,
        },
    ]


def build_sendable_report(
    report: dict[str, Any],
    latest_anchor: dict[str, str],
    missing_files: list[str],
    path_encoding_issue: bool,
    generated_at: str,
    risks: list[dict[str, Any]],
) -> tuple[str, str]:
    day_label = format_cn_day(generated_at)
    metrics = report.get("metrics", {})

    lines = [
        f"【{day_label} 自动日报】",
        "",
        "一、今日结论",
        "- 当前自动日报链路仍处于 fail-closed 状态，今天不输出伪装成业务进展的结论，只输出已核实事实、核心阻塞和修复动作。",
        f"- 最新一手业务证据停留在 {format_cn_time(report.get('latest_any_message_timestamp'))}，距今 {relative_age_text(report.get('latest_any_message_timestamp'), anchor=generated_at)}，说明当前增量采集已经失去时效性。",
        "",
        "二、已确认事实",
        f"- 最新一手业务证据上报人：{latest_anchor['reporter_name']}；来源类型：{latest_anchor['source_type_label']}；标题：{latest_anchor['source_title']}",
        f"- 当前证据库文档数：{metrics.get('source_documents_count', 0)}；噪音文档 {metrics.get('noisy_doc_count', 0)} 条；系统噪音记录 {metrics.get('system_noise_record_count', 0)} 条。",
        f"- 审计链路 run 数量：{metrics.get('audit_runs_count', 0)}；无 lineage 回复 {metrics.get('replied_without_runs', 0)} 条。",
    ]

    if path_encoding_issue:
        lines.append("- 当前运行阻塞并非入口文件缺失，而是运行环境路径编码异常（日志显示 Python 无法打开 `run_incremental_cycle.py` / `run_history_backfill.py`）。")
    elif missing_files:
        lines.append(f"- 缺失关键入口文件：{'、'.join(missing_files)}。")

    lines.extend(["", "三、核心阻塞"])
    if risks:
        for item in risks[:3]:
            lines.append(f"- [{str(item.get('severity', '')).upper()}] {item.get('title')}；影响：{item.get('impact')}；动作：{item.get('action')}")
    else:
        lines.append("- 今日未提取到高置信阻塞项。")

    lines.extend(
        [
            "",
            "四、下一步动作",
            "- 先修复运行环境路径编码异常并恢复 run_incremental_cycle / run_history_backfill 可执行。"
            if path_encoding_issue
            else (
                f"- 先补齐缺失入口文件并恢复 run_incremental_cycle / run_history_backfill 可执行。"
                if missing_files
                else "- 集中修复增量采集与回填任务的执行失败。"
            ),
            "- 恢复 incremental / backfill 成功退出后，再重启正式业务日报自动化。",
            "- 给每次日报输出补齐 run_id、prompt hash、source ids，避免“有结论、无链路”。",
            "",
            "五、当前不能下的结论",
            "- 不能据此输出真实业务进展判断。",
            "- 不能据此输出部门执行质量判断。",
            "- 不能据此输出确定性的延期、交付和方向一致性判断。",
        ]
    )

    markdown = "\n".join(lines)
    return markdown, markdown


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    reports_dir = repo_root / "data" / "reports"
    dashboard_json_path = repo_root / "vercel-dashboard" / "public" / "latest-dashboard.json"

    latest_evidence_path = pick_latest(list(reports_dir.glob("evidence_guard_*.json")))
    latest_blocked_path = pick_latest(list(reports_dir.glob("run_*_blocked_*.json")))

    latest_evidence = load_json(latest_evidence_path)
    latest_blocked = load_json(latest_blocked_path)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    risk_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    translated_risks = []
    for risk in latest_evidence.get("risks", []):
        severity = str(risk.get("severity", "")).lower()
        if severity in risk_counts:
            risk_counts[severity] += 1
        translated_risks.append(translate_risk(risk))

    translated_risks.sort(key=lambda item: severity_rank(str(item.get("severity", ""))), reverse=True)
    latest_anchor = build_latest_anchor(latest_evidence)
    missing_files = [str(item) for item in latest_blocked.get("missing_source_files", [])]
    path_encoding_issue = has_path_encoding_issue(latest_evidence)
    direct_markdown, direct_plain = build_sendable_report(
        latest_evidence,
        latest_anchor,
        missing_files,
        path_encoding_issue,
        generated_at,
        translated_risks,
    )

    payload = {
        "generated_at": generated_at,
        "report_date": format_cn_day(generated_at),
        "title": "BYDFi 自动日报站",
        "subtitle": "每天自动刷新，打开就是可直接复制发送的日报页面，不是展示型看板。",
        "overall_status": latest_evidence.get("overall_status", "unknown"),
        "latest_evidence_file": latest_evidence_path.name if latest_evidence_path else None,
        "latest_blocked_file": latest_blocked_path.name if latest_blocked_path else None,
        "latest_any_message_timestamp": latest_evidence.get("latest_any_message_timestamp"),
        "latest_substantive_record": latest_evidence.get("latest_substantive_record", {}),
        "latest_anchor": latest_anchor,
        "metrics": latest_evidence.get("metrics", {}),
        "risk_counts": risk_counts,
        "risks": translated_risks,
        "operator_message": build_operator_message(missing_files, path_encoding_issue),
        "raw_operator_message": latest_blocked.get("operator_message"),
        "missing_source_files": missing_files,
        "evidence_guard_generated_at": latest_evidence.get("generated_at"),
        "cards": build_cards(latest_evidence, missing_files, path_encoding_issue, generated_at, risk_counts),
        "sections": build_sections(latest_evidence, latest_anchor, missing_files, path_encoding_issue, generated_at, translated_risks),
        "direct_report_markdown": direct_markdown,
        "direct_report_plain": direct_plain,
    }

    dashboard_json_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote={dashboard_json_path}")


if __name__ == "__main__":
    main()
