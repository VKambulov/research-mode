from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from research_mode_registry import resolve_task_from_args
from research_mode_surfaces import build_summary_payload
from research_mode_utils import json_dump


def _pending_result_file(task_dir: Path, state: dict[str, Any]) -> Path | None:
    lock = state.get("lock") or {}
    run_id = lock.get("run_id")
    if not run_id:
        return None
    candidate = task_dir / ".tmp" / f"result-{run_id}.json"
    return candidate if candidate.exists() else None


def build_health_payload(task, state: dict[str, Any]) -> dict[str, Any]:
    summary = build_summary_payload(task, state, findings_limit=0, sources_limit=0)
    findings: list[dict[str, Any]] = []
    recommended_actions: list[dict[str, Any]] = []

    consistency = summary.get("consistency") or {}
    for warning in consistency.get("warnings") or []:
        findings.append(
            {
                "code": warning.get("code") or "consistency_warning",
                "severity": "warning",
                "status": "manual_review_needed",
                "message": warning.get("message") or "State consistency warning",
                "details": warning.get("details") or {},
            }
        )
    for guidance in consistency.get("operator_guidance") or []:
        recommended_actions.append(
            {
                "kind": "manual_review",
                "warning_code": guidance.get("warning_code"),
                "note": guidance.get("note") or "",
                "checklist": guidance.get("checklist") or [],
            }
        )

    pending_result = _pending_result_file(task.task_dir, state)
    if pending_result is not None:
        findings.append(
            {
                "code": "pending_result_available",
                "severity": "warning",
                "status": "repair_needed",
                "message": "A pending worker result exists and can be recovered explicitly.",
                "details": {"result_file": str(pending_result)},
            }
        )
        recommended_actions.append(
            {
                "kind": "repair",
                "command": "recover --apply-pending-result",
                "note": "Run recover only after confirming the pending result belongs to the active run.",
            }
        )

    statuses = {str(finding.get("status") or "") for finding in findings}
    if "manual_review_needed" in statuses:
        status = "manual_review_needed"
    elif "repair_needed" in statuses:
        status = "repair_needed"
    else:
        status = "ok"

    return {
        "status": status,
        "task_id": state.get("id"),
        "task_status": state.get("status"),
        "phase": state.get("phase"),
        "findings": findings,
        "recommended_actions": recommended_actions,
        "read_only": True,
        "task_dir": str(task.task_dir),
    }


def render_health_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Health: {payload.get('status')}",
        f"Task: {payload.get('task_id')} ({payload.get('task_status')}, phase={payload.get('phase')})",
    ]
    findings = payload.get("findings") or []
    if findings:
        lines.append("Findings:")
        for finding in findings:
            lines.append(f"- {finding.get('code')}: {finding.get('message')}")
    actions = payload.get("recommended_actions") or []
    if actions:
        lines.append("Recommended actions:")
        for action in actions:
            label = action.get("command") or action.get("warning_code") or action.get("kind")
            note = action.get("note") or ""
            lines.append(f"- {label}: {note}" if note else f"- {label}")
    lines.append("Read-only: true")
    return "\n".join(lines) + "\n"


def health_command(args: argparse.Namespace) -> int:
    task = resolve_task_from_args(
        Path(args.root).expanduser().resolve(), research_id=args.id, path=args.path
    )
    state = task.read_state()
    payload = build_health_payload(task, state)
    if args.format == "text":
        sys.stdout.write(render_health_text(payload))
        return 0
    json_dump(payload)
    return 0
