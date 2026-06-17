"""Read-only health diagnostics."""
from __future__ import annotations

import json
from pathlib import Path

from .helpers import assert_eq, assert_in, assert_true, json_out, run


def test_health_ok_json_is_read_only(root: Path) -> None:
    created = json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "health-ok",
            "--goal",
            "Test healthy task diagnostics",
        )
    )
    assert_eq(created["status"], "created", "create status")

    state_path = root / "health-ok" / "state.json"
    before = state_path.read_text(encoding="utf-8")
    health = json_out(
        run(
            "health",
            "--root",
            str(root),
            "--id",
            "health-ok",
            "--format",
            "json",
        )
    )
    after = state_path.read_text(encoding="utf-8")

    assert_eq(after, before, "health must not mutate state")
    assert_eq(health["status"], "ok", "healthy task status")
    assert_eq(health["findings"], [], "healthy task should have no findings")
    assert_eq(health["recommended_actions"], [], "healthy task should need no action")
    assert_eq(health["task_id"], "health-ok", "health should identify the task")


def test_health_reports_missing_review_artifact(root: Path) -> None:
    created = json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "health-missing-artifact",
            "--goal",
            "Test missing review artifact health",
        )
    )
    assert_eq(created["status"], "created", "create status")

    state_path = root / "health-missing-artifact" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "awaiting_review"
    state["review"] = {"status": "pending", "revision_count": 0}
    state["artifacts"] = {"final_report_path": None}
    state["delivery"] = {"primary_file": None}
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    before = state_path.read_text(encoding="utf-8")

    health = json_out(
        run(
            "health",
            "--root",
            str(root),
            "--id",
            "health-missing-artifact",
            "--format",
            "json",
        )
    )
    after = state_path.read_text(encoding="utf-8")

    assert_eq(after, before, "health must not mutate inconsistent state")
    assert_eq(health["status"], "manual_review_needed", "missing artifact status")
    findings = health["findings"]
    assert_true(
        any(finding.get("code") == "missing_reviewable_artifact" for finding in findings),
        "health should expose missing_reviewable_artifact",
    )
    actions = health["recommended_actions"]
    assert_true(actions, "health should include recommended actions")

    text = run(
        "health",
        "--root",
        str(root),
        "--id",
        "health-missing-artifact",
        "--format",
        "text",
    ).stdout
    assert_in(
        "Health: manual_review_needed",
        text,
        "health text should show overall status",
    )
    assert_in(
        "missing_reviewable_artifact",
        text,
        "health text should show finding code",
    )
