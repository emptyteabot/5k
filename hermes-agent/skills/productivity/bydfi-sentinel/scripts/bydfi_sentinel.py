from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def find_audit_bot_root() -> Path:
    env_root = os.environ.get("BYDFI_AUDIT_BOT_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    current = Path(__file__).resolve()
    hermes_root = current.parents[4]
    candidates = [
        (hermes_root.parent / "bydfi-audit-bot").resolve(),
        (hermes_root.parent / "5k" / "bydfi-audit-bot").resolve(),
        (hermes_root / ".." / "bydfi-audit-bot").resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run BYDFI local reporting workflows from Hermes.")
    parser.add_argument(
        "action",
        choices=["daily", "weekly", "mckinsey", "evidence-guard"],
        help="Workflow to run.",
    )
    parser.add_argument("--period", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--render-ceo", action="store_true")
    parser.add_argument("--render-digest-pdf", action="store_true")
    parser.add_argument("--render-final-pdf", action="store_true")
    parser.add_argument("--deliver", action="store_true")
    parser.add_argument("--skip-discover", action="store_true")
    parser.add_argument("--skip-auto-collect", action="store_true")
    parser.add_argument("--stale-hours", type=int, default=48)
    return parser


def resolve_command(args: argparse.Namespace, audit_bot_root: Path) -> list[str]:
    python_bin = os.environ.get("BYDFI_AUDIT_BOT_PYTHON", "").strip() or sys.executable

    if args.action == "daily":
      command = [python_bin, "-X", "utf8", str(audit_bot_root / "run_daily_ops_cycle.py")]
      if args.skip_discover:
          command.append("--skip-discover")
      if args.skip_auto_collect:
          command.append("--skip-auto-collect")
      if args.render_ceo:
          command.append("--render-ceo")
      if args.render_digest_pdf:
          command.append("--render-digest-pdf")
      if args.deliver:
          command.append("--deliver")
      command.extend(["--stale-hours", str(args.stale_hours)])
      return command

    if args.action == "weekly":
        command = [python_bin, "-X", "utf8", str(audit_bot_root / "run_weekly_ops_cycle.py")]
        if args.skip_discover:
            command.append("--skip-discover")
        if args.skip_auto_collect:
            command.append("--skip-auto-collect")
        if args.render_ceo:
            command.append("--render-ceo")
        if args.render_digest_pdf:
            command.append("--render-digest-pdf")
        if args.deliver:
            command.append("--deliver")
        command.extend(["--stale-hours", str(args.stale_hours)])
        return command

    if args.action == "mckinsey":
        command = [
            python_bin,
            "-X",
            "utf8",
            str(audit_bot_root / "run_mckinsey_ceo_cycle.py"),
            "--period",
            args.period,
        ]
        if args.skip_discover:
            command.append("--skip-discover")
        if args.skip_auto_collect:
            command.append("--skip-auto-collect")
        if args.deliver:
            command.append("--deliver")
        if args.render_final_pdf:
            command.append("--render-final-pdf")
        command.extend(["--stale-hours", str(args.stale_hours)])
        return command

    return [
        python_bin,
        "-X",
        "utf8",
        str(audit_bot_root / "evidence_guard_audit.py"),
        "--repo-root",
        str(audit_bot_root),
    ]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    audit_bot_root = find_audit_bot_root()
    if not audit_bot_root.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "audit_bot_root_missing",
                    "audit_bot_root": str(audit_bot_root),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    command = resolve_command(args, audit_bot_root)
    proc = subprocess.run(
        command,
        cwd=str(audit_bot_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = {
        "ok": proc.returncode == 0,
        "action": args.action,
        "audit_bot_root": str(audit_bot_root),
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
