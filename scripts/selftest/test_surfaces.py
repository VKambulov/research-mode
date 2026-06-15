"""Operator surfaces: revision diffs, evidence gaps, provenance, audit trail."""
from __future__ import annotations

import json
from pathlib import Path

from .helpers import (
    assert_eq,
    assert_in,
    assert_true,
    finish_to_awaiting_review,
    human_ready_finalization,
    json_out,
    run,
)

# Importable after helpers.py configures sys.path
from research_mode_reasons import record_manual_override


def test_revision_diff_on_awaiting_review(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "revision-diff-test",
            "--goal",
            "Revision diff test",
        )
    )
    task_dir = root / "revision-diff-test"
    state_path = task_dir / "state.json"

    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["revision_snapshot"] = {
        "final_report_path": "old-report.md",
        "revision_count": 0,
    }
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lease = json_out(run("begin", "--root", str(root), "--id", "revision-diff-test"))
    result_file = Path(lease["paths"]["result_file"])
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "summary": "First draft.",
                "next_angle": "done",
                "meaningful_progress": True,
                "phase": "synthesize",
                "open_questions": [],
                "sources": [{"title": "s"}],
                "findings": [{"kind": "fact", "text": "f."}],
                "notify_recommendation": "final",
                "should_complete": True,
                "final_report_markdown": "# Report\n\n## Summary\n\nThis is a comprehensive report with sufficient content to pass all validation checks. It provides detailed findings and context for the human reviewer.\n\nParagraph two adds more detailed information about the research findings. This paragraph exists to ensure the word count exceeds the minimum threshold.\n\n## Details\n\nThe analysis covers key aspects with adequate evidence. More details are included here for completeness. Additional sentences ensure the report is substantial enough for validation.",
                "finalization": human_ready_finalization(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    finished = json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            "revision-diff-test",
            "--run-id",
            lease["run_id"],
            "--result-file",
            str(result_file),
        )
    )
    assert_eq(finished["status"], "awaiting_review", "should land in awaiting_review")

    summary_json = json_out(
        run(
            "summary",
            "--root",
            str(root),
            "--id",
            "revision-diff-test",
            "--format",
            "json",
        )
    )
    rev_diff = summary_json.get("revision_diff") or {}
    assert_true(
        bool(rev_diff.get("final_report_updated")),
        "revision_diff should show final_report_updated",
    )
    changes = rev_diff.get("changes") or []
    assert_true(
        len(changes) > 0,
        f"revision_diff should have at least one change, got {changes}",
    )


def test_evidence_gaps_in_surfaces(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "evidence-gaps-test",
            "--goal",
            "Evidence gaps test",
        )
    )
    task_dir = root / "evidence-gaps-test"
    state_path = task_dir / "state.json"

    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.setdefault("working_memory", {})["open_questions"] = [
        "What about the secondary market?"
    ]
    state.setdefault("saturation", {})["consecutive_low_yield"] = 2
    state.setdefault("saturation", {})["low_yield_threshold"] = 2
    state.setdefault("saturation", {})["topic_saturated"] = True
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    draft_md = run(
        "draft-report",
        "--root",
        str(root),
        "--id",
        "evidence-gaps-test",
        "--format",
        "markdown",
    ).stdout
    assert_in(
        "Evidence gaps", draft_md,
        "draft report should include evidence gaps section",
    )
    assert_in(
        "open_question", draft_md,
        "evidence gaps should include open question",
    )
    assert_true(
        "high_risk" in draft_md.lower() or "recommended" in draft_md.lower(),
        "evidence gaps should include risk/recommendation info",
    )


def test_provenance_confidence_in_final_report(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "provenance-test",
            "--goal",
            "Provenance test",
        )
    )
    lease = json_out(run("begin", "--root", str(root), "--id", "provenance-test"))
    result_file = Path(lease["paths"]["result_file"])
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "summary": "Research complete.",
                "next_angle": "",
                "meaningful_progress": True,
                "phase": "synthesize",
                "open_questions": [],
                "sources": [
                    {
                        "title": "Official Government Source",
                        "url": "https://gov.example.com/data",
                    },
                    {
                        "title": "Wikipedia article",
                        "url": "https://en.wikipedia.org/wiki/Test",
                    },
                ],
                "findings": [
                    {
                        "kind": "fact",
                        "text": "Confirmed by multiple sources.",
                        "source_urls": [
                            "https://gov.example.com/data",
                            "https://en.wikipedia.org/wiki/Test",
                        ],
                    },
                    {
                        "kind": "hypothesis",
                        "text": "Single-source estimate.",
                        "source_urls": ["https://en.wikipedia.org/wiki/Test"],
                    },
                    {
                        "kind": "note",
                        "text": "No source attached.",
                    },
                ],
                "notify_recommendation": "final",
                "should_complete": True,
                "final_report_markdown": "# Research Report\n\n## Summary\n\nThis research project produced comprehensive findings with sufficient evidence from multiple independent sources. The analysis covered key aspects of the topic and provided actionable insights supported by authoritative data. The methodology was sound and the conclusions are well-grounded in the available evidence.\n## Key Findings\n\nThe primary findings include multiple data points corroborated by government sources and independent research. The evidence base consists of official publications and secondary analyses that together provide a coherent picture of the research landscape.\n## Methodology\n\nData was collected through systematic web searches and cross-referenced against authoritative sources. All findings were validated against primary sources where available.\n## Conclusions\n\nThe research demonstrates clear patterns supported by the evidence and provides a foundation for informed decision-making based on the available data.",
                "finalization": human_ready_finalization(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    finished = json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            "provenance-test",
            "--run-id",
            lease["run_id"],
            "--result-file",
            str(result_file),
        )
    )
    assert_eq(
        finished["status"],
        "awaiting_review",
        "should land in awaiting_review",
    )
    draft_md = run(
        "draft-report",
        "--root",
        str(root),
        "--id",
        "provenance-test",
        "--format",
        "markdown",
    ).stdout
    assert_true(
        "[" in draft_md and "]" in draft_md,
        "draft report should contain confidence badges",
    )
    findings_start = draft_md.find("## Key findings")
    findings_section = draft_md[findings_start:] if findings_start >= 0 else draft_md
    assert_true(
        "●●" in findings_section
        or "●○" in findings_section
        or "[???" in findings_section,
        "key findings should show provenance confidence badges",
    )
    evidence_start = draft_md.find("## Evidence base")
    evidence_section = draft_md[evidence_start:] if evidence_start >= 0 else draft_md
    assert_true(
        "●●" in evidence_section
        or "●○" in evidence_section
        or "○○" in evidence_section,
        "evidence base should show quality tier badges for sources",
    )


def test_manual_override_audit_trail(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "audit-trail-test",
            "--goal",
            "Audit trail test",
        )
    )
    task_dir = root / "audit-trail-test"
    state_path = task_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))

    record_manual_override(
        state,
        reason="user_requested_hotfix",
        description="User asked to fix typo in final report outside research flow.",
        changed_artifacts=["final-report.md"],
    )

    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary_json = json_out(
        run(
            "summary",
            "--root",
            str(root),
            "--id",
            "audit-trail-test",
            "--format",
            "json",
        )
    )
    last_marker = (summary_json.get("history") or {}).get("last_audit_marker")
    assert_eq(
        last_marker,
        "manual_override",
        "history should have last_audit_marker=manual_override",
    )

    audit_trail = (summary_json.get("history") or {}).get("audit_trail") or []
    assert_true(
        len(audit_trail) > 0,
        "history should have audit_trail entries",
    )
    last_entry = audit_trail[-1]
    assert_eq(
        last_entry.get("audit_marker"),
        "manual_override",
        "last audit trail entry should have audit_marker=manual_override",
    )
    assert_eq(
        last_entry.get("override_reason"),
        "user_requested_hotfix",
        "audit trail should record override reason",
    )
    assert_in(
        "final-report.md", last_entry.get("changed_artifacts") or [],
        "audit trail should record changed artifacts",
    )


def test_finalization_operator_next_action_for_review_ready_task(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "finalization-action-review",
            "--goal",
            "Operator action review test",
        )
    )
    lease = json_out(
        run("begin", "--root", str(root), "--id", "finalization-action-review")
    )
    finished = finish_to_awaiting_review(root, "finalization-action-review", lease)
    assert_eq(
        finished.get("status"),
        "awaiting_review",
        "fixture should land in awaiting_review",
    )

    summary_json = json_out(
        run(
            "summary",
            "--root",
            str(root),
            "--id",
            "finalization-action-review",
            "--format",
            "json",
        )
    )
    next_action = (summary_json.get("finalization") or {}).get("operator_next_action")
    assert_eq(
        (next_action or {}).get("kind"),
        "review_candidate",
        "review-ready finalization should tell operator to review candidate artifact",
    )
    assert_in(
        "approve",
        " ".join((next_action or {}).get("commands") or []),
        "review candidate action should mention approve command",
    )

    summary_text = run(
        "summary",
        "--root",
        str(root),
        "--id",
        "finalization-action-review",
        "--format",
        "text",
    ).stdout
    assert_in(
        "Operator next action: review_candidate",
        summary_text,
        "summary text should expose operator next action",
    )


def test_finalization_operator_next_action_for_rework_task(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "finalization-action-rework",
            "--goal",
            "Operator action rework test",
        )
    )
    lease = json_out(
        run("begin", "--root", str(root), "--id", "finalization-action-rework")
    )
    result_file = Path(lease["paths"]["result_file"])
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "summary": "Research completed.",
                "next_angle": "",
                "meaningful_progress": True,
                "phase": "synthesize",
                "open_questions": [],
                "sources": [{"title": "src"}],
                "findings": [{"kind": "fact", "text": "finding"}],
                "notify_recommendation": "final",
                "should_complete": True,
                "final_report_markdown": "# Final Report\n\n## Summary\n\nThis report has enough readable content to pass markdown structure checks while the candidate artifact path deliberately points to a missing file so finalization must return to rework.\n\n## Findings\n\nThe finding text is long enough to keep this report above the minimum word count for markdown inspection.",
                "finalization": human_ready_finalization(
                    candidate_path="workspace/outputs/missing-report.md"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    finished = json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            "finalization-action-rework",
            "--run-id",
            lease["run_id"],
            "--result-file",
            str(result_file),
        )
    )
    assert_eq(
        finished.get("status"),
        "finalize",
        "missing candidate artifact should return task to finalize",
    )

    summary_json = json_out(
        run(
            "summary",
            "--root",
            str(root),
            "--id",
            "finalization-action-rework",
            "--format",
            "json",
        )
    )
    next_action = (summary_json.get("finalization") or {}).get("operator_next_action")
    assert_eq(
        (next_action or {}).get("kind"),
        "worker_rework",
        "failed finalization should tell operator to let worker rework",
    )
    assert_in(
        "candidate_artifact_missing",
        " ".join((next_action or {}).get("reasons") or []),
        "worker rework action should carry failed validation reasons",
    )

    summary_text = run(
        "summary",
        "--root",
        str(root),
        "--id",
        "finalization-action-rework",
        "--format",
        "text",
    ).stdout
    assert_in(
        "Operator next action: worker_rework",
        summary_text,
        "summary text should expose rework next action",
    )
