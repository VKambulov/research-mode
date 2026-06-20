"""Reliability diagnostics: counters, attention merge, read-only surfaces."""
from __future__ import annotations

import json
from pathlib import Path

from .helpers import assert_eq, assert_in, assert_true, json_out, run

from research_mode_reliability import (
    build_reliability_attention,
    build_reliability_health_findings,
    clear_failure_counter,
    record_failure_event,
)


def _completion_rejection_event(*, run_id: str, reason: str) -> dict:
    return {
        "code": "completion_validation_retry_loop",
        "severity": "warning",
        "phase": "finalize",
        "run_id": run_id,
        "reasons": [reason],
    }


def test_reliability_counter_records_repeated_fingerprint() -> None:
    state: dict = {}
    event = _completion_rejection_event(
        run_id="run-1",
        reason="deliverable_comparative_shape_weak",
    )

    updated = record_failure_event(state, event, at="2026-06-19T00:00:00Z")
    updated = record_failure_event(
        updated,
        {**event, "run_id": "run-2"},
        at="2026-06-19T00:05:00Z",
    )

    counter = updated["reliability"]["failure_counters"][
        "completion_validation_retry_loop"
    ]
    fingerprint = (
        "completion_validation_retry_loop:finalize:"
        "deliverable_comparative_shape_weak"
    )
    assert_eq(counter["count"], 2, "code-level counter should count all code events")
    assert_eq(counter["fingerprint"], fingerprint, "counter should expose latest fingerprint")
    assert_eq(
        counter["fingerprints"][fingerprint]["count"],
        2,
        "exact fingerprint counter should count repeated same reason",
    )
    assert_true("reliability" not in state, "record_failure_event should not mutate input state")


def test_reliability_counter_keeps_fingerprints_separate() -> None:
    state: dict = {}
    first = _completion_rejection_event(
        run_id="run-1",
        reason="deliverable_comparative_shape_weak",
    )
    second = _completion_rejection_event(
        run_id="run-2",
        reason="candidate_artifact_missing",
    )

    updated = record_failure_event(state, first, at="2026-06-19T00:00:00Z")
    updated = record_failure_event(updated, second, at="2026-06-19T00:05:00Z")

    counter = updated["reliability"]["failure_counters"][
        "completion_validation_retry_loop"
    ]
    fingerprints = counter["fingerprints"]
    assert_eq(counter["count"], 2, "code counter should include both failures")
    assert_eq(
        fingerprints[
            "completion_validation_retry_loop:finalize:"
            "deliverable_comparative_shape_weak"
        ]["count"],
        1,
        "first exact fingerprint should not inherit second reason",
    )
    assert_eq(
        fingerprints["completion_validation_retry_loop:finalize:candidate_artifact_missing"][
            "count"
        ],
        1,
        "second exact fingerprint should have its own counter",
    )


def test_reliability_events_are_bounded_and_clearable() -> None:
    state: dict = {}
    for idx in range(25):
        state = record_failure_event(
            state,
            _completion_rejection_event(
                run_id=f"run-{idx}",
                reason="deliverable_comparative_shape_weak",
            ),
            at=f"2026-06-19T00:{idx:02d}:00Z",
        )

    events = state["reliability"]["last_events"]
    assert_eq(len(events), 20, "last_events should keep a bounded recent window")
    assert_eq(events[0]["run_id"], "run-5", "oldest overflow events should be dropped")

    cleared = clear_failure_counter(state, "completion_validation_retry_loop")
    counter = cleared["reliability"]["failure_counters"][
        "completion_validation_retry_loop"
    ]
    assert_eq(counter["status"], "cleared", "clear should mark counter cleared")
    assert_true("cleared_at" in counter, "clear should record timestamp")
    assert_eq(
        state["reliability"]["failure_counters"]["completion_validation_retry_loop"][
            "status"
        ],
        "active",
        "clear_failure_counter should not mutate input state",
    )


def test_reliability_attention_and_health_findings_from_existing_state() -> None:
    state: dict = {}
    state = record_failure_event(
        state,
        _completion_rejection_event(
            run_id="run-1",
            reason="deliverable_comparative_shape_weak",
        ),
        at="2026-06-19T00:00:00Z",
    )
    state = record_failure_event(
        state,
        _completion_rejection_event(
            run_id="run-2",
            reason="deliverable_comparative_shape_weak",
        ),
        at="2026-06-19T00:05:00Z",
    )

    attention = build_reliability_attention(state)
    assert_eq(
        attention["status"],
        "manual_review_needed",
        "repeated completion rejection should request manual review",
    )
    assert_eq(
        attention["conditions"][0]["code"],
        "completion_validation_retry_loop",
        "attention should expose stable failure code",
    )

    health_findings = build_reliability_health_findings(state)
    assert_eq(
        health_findings[0]["code"],
        "completion_validation_retry_loop",
        "health should expose reliability finding",
    )
    assert_eq(
        health_findings[0]["status"],
        "manual_review_needed",
        "health finding should carry operator status",
    )


def test_reliability_surfaces_are_read_only(root: Path) -> None:
    task_id = "reliability-read-only"
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            task_id,
            "--goal",
            "Expose reliability diagnostics without mutating state.",
            "--skip-preflight",
        )
    )
    state_path = root / task_id / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state = record_failure_event(
        state,
        _completion_rejection_event(
            run_id="run-1",
            reason="deliverable_comparative_shape_weak",
        ),
        at="2026-06-19T00:00:00Z",
    )
    state = record_failure_event(
        state,
        _completion_rejection_event(
            run_id="run-2",
            reason="deliverable_comparative_shape_weak",
        ),
        at="2026-06-19T00:05:00Z",
    )
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_text(encoding="utf-8")

    summary = json_out(
        run("summary", "--root", str(root), "--id", task_id, "--format", "json")
    )
    attention = summary.get("operator_attention") or {}
    assert_eq(
        attention.get("status"),
        "manual_review_needed",
        "summary should merge reliability attention",
    )
    assert_true(
        any(
            item.get("code") == "completion_validation_retry_loop"
            for item in attention.get("conditions") or []
        ),
        "summary should expose reliability condition",
    )
    assert_in(
        "completion_validation_retry_loop",
        run("summary", "--root", str(root), "--id", task_id, "--format", "text").stdout,
        "summary text should include reliability condition",
    )

    health = json_out(
        run("health", "--root", str(root), "--id", task_id, "--format", "json")
    )
    assert_true(
        any(
            item.get("code") == "completion_validation_retry_loop"
            for item in health.get("findings") or []
        ),
        "health should include reliability findings",
    )

    run("status", "--root", str(root), "--id", task_id, "--format", "json")
    run("queue-status", "--root", str(root), "--format", "json")
    after = state_path.read_text(encoding="utf-8")
    assert_eq(after, before, "read-only operator commands must not rewrite state")
