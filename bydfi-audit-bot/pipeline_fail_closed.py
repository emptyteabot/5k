from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from evidence_guard_audit import build_report


ESSENTIAL_SOURCE_FILES = [
    "run_incremental_cycle.py",
    "run_history_backfill.py",
    "evidence_guard_audit.py",
]


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def write_blocked_report(repo_root: Path, entrypoint: str, args: list[str], report: dict[str, Any]) -> Path:
    reports_dir = repo_root / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"{entrypoint}_blocked_{now_stamp()}.json"
    missing_files = [name for name in ESSENTIAL_SOURCE_FILES if not (repo_root / name).exists()]
    autopilot_state = report.get("autopilot_state", {}) if isinstance(report, dict) else {}
    tail = "\n".join(
        [
            str(autopilot_state.get("last_incremental_retry_tail", "")),
            str(autopilot_state.get("last_backfill_tail", "")),
        ]
    ).lower()
    path_encoding_issue = "can't open file" in tail and ("����" in tail or "½»" in tail)
    payload = {
        "entrypoint": entrypoint,
        "invoked_args": args,
        "blocked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "reason": "fail_closed_guard",
        "overall_status": report.get("overall_status"),
        "missing_source_files": missing_files,
        "path_encoding_issue": path_encoding_issue,
        "evidence_guard_report": report,
        "operator_message": (
            "The current snapshot is not a healthy runnable reporting pipeline. "
            "Python cannot open run_incremental_cycle.py / run_history_backfill.py due to path encoding issues."
            if path_encoding_issue
            else "The current snapshot is not a healthy runnable reporting pipeline. "
            "Management report generation is blocked until source files and evidence lineage are restored."
        ),
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main(entrypoint: str) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--help", action="store_true")
    _, unknown = parser.parse_known_args()

    repo_root = Path(__file__).resolve().parent
    report, _ = build_report(repo_root)
    blocked_path = write_blocked_report(repo_root, entrypoint, sys.argv[1:], report)

    missing_files = [name for name in ESSENTIAL_SOURCE_FILES if not (repo_root / name).exists()]
    autopilot_state = report.get("autopilot_state", {}) if isinstance(report, dict) else {}
    tail = "\n".join(
        [
            str(autopilot_state.get("last_incremental_retry_tail", "")),
            str(autopilot_state.get("last_backfill_tail", "")),
        ]
    ).lower()
    path_encoding_issue = "can't open file" in tail and ("����" in tail or "½»" in tail)

    print(f"[fail-closed] entrypoint={entrypoint}")
    print(f"[fail-closed] evidence_guard_status={report.get('overall_status')}")
    print(f"[fail-closed] blocked_report={blocked_path}")
    if missing_files:
        print(f"[fail-closed] missing_source_files={', '.join(missing_files)}")
    if path_encoding_issue:
        print("[fail-closed] path_encoding_issue=true (python can't open script path)")
    latest_ts = report.get("latest_any_message_timestamp")
    if latest_ts:
        print(f"[fail-closed] latest_any_message_timestamp={latest_ts}")
    print(
        "[fail-closed] report generation blocked because this snapshot lacks "
        "a healthy, auditable, reproducible source pipeline."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(Path(__file__).stem))
