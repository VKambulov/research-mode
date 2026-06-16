"""Delivery manifest: population, mark-delivered, primary file validation."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .helpers import (
    assert_eq,
    assert_in,
    assert_true,
    finish_to_awaiting_review,
    human_ready_adequacy,
    json_out,
    run,
)


_HUMAN_READY_FINALIZATION = {
    "status": "passed",
    "inferred_user_need": "A readable result that can be reviewed without reconstructing it from internal artifacts.",
    "intended_recipient": "operator",
    "primary_deliverable_kind": "markdown_report",
    "internal_artifacts": [
        {"path": "iterations/001.md", "kind": "iteration_notes", "note": "Internal iteration notes."}
    ],
    "candidate_artifacts": [
        {"path": "final-report.md", "kind": "markdown_report", "note": "Human-readable final report."}
    ],
    "blocking_defects": [],
    "nonblocking_defects": [],
    "revisions": [
        {"summary": "Converted synthesis notes into a reader-facing final report."}
    ],
    "validation_evidence": [
        {"kind": "markdown_review", "summary": "Checked headings, summary, findings, and conclusion."}
    ],
}


def _finish_with_payload(root: Path, task_id: str, lease: dict, payload: dict) -> dict:
    result_file = Path(lease["paths"]["result_file"])
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    finished = json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            task_id,
            "--run-id",
            lease["run_id"],
            "--result-file",
            str(result_file),
        )
    )
    if finished.get("status") != "idle":
        return finished

    verify_lease = json_out(run("begin", "--root", str(root), "--id", task_id))
    if verify_lease.get("phase") != "verify":
        return finished
    verify_result = Path(verify_lease["paths"]["result_file"])
    verify_result.write_text(
        json.dumps(
            {
                "summary": "Research adequacy passed.",
                "next_angle": "Prepare the final deliverable.",
                "meaningful_progress": True,
                "phase": "verify",
                "open_questions": [],
                "sources": [],
                "findings": [],
                "notify_recommendation": "silent",
                "should_complete": False,
                "final_report_markdown": None,
                "adequacy": human_ready_adequacy(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    routed = json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            task_id,
            "--run-id",
            verify_lease["run_id"],
            "--result-file",
            str(verify_result),
        )
    )
    if routed.get("status") != "idle":
        return routed

    finalize_lease = json_out(run("begin", "--root", str(root), "--id", task_id))
    final_payload = dict(payload)
    final_payload["phase"] = "finalize"
    finalize_result = Path(finalize_lease["paths"]["result_file"])
    finalize_result.write_text(
        json.dumps(final_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            task_id,
            "--run-id",
            finalize_lease["run_id"],
            "--result-file",
            str(finalize_result),
        )
    )


def _final_payload(finalization: dict | None = None) -> dict:
    payload = {
        "summary": "Research completed.",
        "next_angle": "",
        "meaningful_progress": True,
        "phase": "synthesize",
        "open_questions": [],
        "sources": [{"title": "src"}],
        "findings": [{"kind": "fact", "text": "finding"}],
        "notify_recommendation": "final",
        "should_complete": True,
        "final_report_markdown": (
            "# Final Report\n\n"
            "## Summary\n\n"
            "This is a comprehensive final report prepared as a readable deliverable. "
            "It summarizes the result, explains the evidence, and avoids exposing raw internal fields.\n\n"
            "## Key Findings\n\n"
            "- Finding 1: Important discovery supported by evidence.\n"
            "- Finding 2: Another key insight from the research.\n\n"
            "## Conclusion\n\n"
            "The result is ready for operator review."
        ),
    }
    if finalization is not None:
        payload["finalization"] = finalization
    return payload


def _write_minimal_xlsx(path: Path, *, sheet_name: str = "Сводка") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
""",
        )
        workbook.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        )
        workbook.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{sheet_name}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>Итог</t></is></c></row>
  </sheetData>
</worksheet>
""",
        )


def test_initial_state_has_explicit_finalization_defaults(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "finalization-defaults",
            "--goal",
            "Finalization defaults test",
        )
    )
    state = json.loads((root / "finalization-defaults" / "state.json").read_text(encoding="utf-8"))
    finalization = state.get("finalization") or {}
    assert_eq(
        finalization.get("status"),
        "not_started",
        "new tasks should start with explicit finalization.not_started",
    )
    assert_eq(
        finalization.get("max_attempts"),
        3,
        "new tasks should preserve the bounded finalization loop default",
    )
    assert_true(
        isinstance(finalization.get("validation_evidence"), list),
        "new tasks should expose validation_evidence as a list",
    )


def test_worker_final_without_finalization_trace_enters_finalize(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "finalization-missing-trace",
            "--goal",
            "Missing finalization trace test",
        )
    )
    lease = json_out(run("begin", "--root", str(root), "--id", "finalization-missing-trace"))
    finished = _finish_with_payload(root, "finalization-missing-trace", lease, _final_payload())

    assert_eq(
        finished.get("status"),
        "finalize",
        "worker final without finalization trace should enter finalize rather than awaiting_review",
    )
    reasons = finished.get("finalization_validation", {}).get("reasons") or []
    assert_in(
        "finalization_not_started",
        reasons,
        "validation should explain that finalization trace was missing",
    )


def test_worker_final_rejects_raw_artifact_exposed_as_final(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "raw-artifact-final",
            "--goal",
            "Check client base and prepare the final spreadsheet",
            "--deliverable",
            "usable spreadsheet for a manager",
        )
    )
    lease = json_out(run("begin", "--root", str(root), "--id", "raw-artifact-final"))
    raw_finalization = {
        **_HUMAN_READY_FINALIZATION,
        "primary_deliverable_kind": "spreadsheet",
        "candidate_artifacts": [
            {
                "path": "workspace/outputs/client_check_raw.xlsx",
                "kind": "raw_workbook",
                "note": "Contains active/unknown/confidence/evidence_urls working fields.",
            }
        ],
        "validation_evidence": [
            {"kind": "manifest_review", "summary": "Only confirmed that the raw workbook exists."}
        ],
    }
    finished = _finish_with_payload(
        root,
        "raw-artifact-final",
        lease,
        _final_payload(raw_finalization),
    )

    assert_eq(
        finished.get("status"),
        "finalize",
        "raw working artifact should not pass as a review-ready deliverable",
    )
    reasons = finished.get("finalization_validation", {}).get("reasons") or []
    assert_in(
        "raw_artifact_exposed_as_final",
        reasons,
        "validation should identify raw artifact exposure",
    )


def test_worker_final_with_human_ready_finalization_trace_reaches_review(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "human-ready-trace",
            "--goal",
            "Human-ready finalization trace test",
        )
    )
    lease = json_out(run("begin", "--root", str(root), "--id", "human-ready-trace"))
    finished = _finish_with_payload(
        root,
        "human-ready-trace",
        lease,
        _final_payload(_HUMAN_READY_FINALIZATION),
    )
    assert_eq(
        finished.get("status"),
        "awaiting_review",
        "human-ready finalization trace should allow awaiting_review",
    )
    state = json.loads((root / "human-ready-trace" / "state.json").read_text(encoding="utf-8"))
    assert_eq(
        (state.get("finalization") or {}).get("status"),
        "passed",
        "state should persist passed finalization trace",
    )
    summary = json_out(
        run(
            "summary",
            "--root",
            str(root),
            "--id",
            "human-ready-trace",
            "--format",
            "json",
        )
    )
    fin = summary.get("finalization") or {}
    assert_eq(
        fin.get("inferred_user_need"),
        _HUMAN_READY_FINALIZATION["inferred_user_need"],
        "summary should expose inferred user need",
    )
    assert_eq(
        fin.get("primary_deliverable_kind"),
        "markdown_report",
        "summary should expose primary deliverable kind",
    )
    assert_eq(
        fin.get("candidate_artifacts_count"),
        1,
        "summary should count candidate artifacts",
    )
    assert_eq(
        fin.get("validation_evidence_count"),
        1,
        "summary should count validation evidence",
    )
    summary_text = run(
        "summary",
        "--root",
        str(root),
        "--id",
        "human-ready-trace",
        "--format",
        "text",
    ).stdout
    assert_in(
        "Finalization need:",
        summary_text,
        "summary text should expose finalization need",
    )
    assert_in(
        "Primary deliverable: markdown_report",
        summary_text,
        "summary text should expose primary deliverable kind",
    )
    playbook = (root / "human-ready-trace" / "task-playbook.md").read_text(encoding="utf-8")
    assert_in(
        "Inferred user need",
        playbook,
        "playbook should expose inferred user need",
    )
    assert_in(
        "Validation evidence",
        playbook,
        "playbook should expose validation evidence",
    )


def test_worker_final_rejects_missing_candidate_artifact(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "missing-candidate-artifact",
            "--goal",
            "Missing candidate artifact test",
        )
    )
    lease = json_out(run("begin", "--root", str(root), "--id", "missing-candidate-artifact"))
    finalization = {
        **_HUMAN_READY_FINALIZATION,
        "primary_deliverable_kind": "markdown_report",
        "candidate_artifacts": [
            {
                "path": "reports/missing-final.md",
                "kind": "markdown_report",
                "note": "Expected review-ready report.",
            }
        ],
    }
    finished = _finish_with_payload(
        root,
        "missing-candidate-artifact",
        lease,
        _final_payload(finalization),
    )
    assert_eq(
        finished.get("status"),
        "finalize",
        "missing candidate artifact should route to finalize",
    )
    reasons = finished.get("finalization_validation", {}).get("reasons") or []
    assert_in(
        "candidate_artifact_missing",
        reasons,
        "missing candidate artifact should be explicit",
    )


def test_worker_final_inspects_existing_markdown_candidate_artifact(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "markdown-candidate-artifact",
            "--goal",
            "Markdown candidate artifact test",
        )
    )
    task_dir = root / "markdown-candidate-artifact"
    reports_dir = task_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "final.md").write_text(
        "# Final Report\n\n"
        "## Summary\n\n"
        "This markdown report is a human-facing deliverable with enough content to be inspected. "
        "It is not an internal iteration log and it gives the reviewer a clear summary.\n",
        encoding="utf-8",
    )
    lease = json_out(run("begin", "--root", str(root), "--id", "markdown-candidate-artifact"))
    finalization = {
        **_HUMAN_READY_FINALIZATION,
        "primary_deliverable_kind": "markdown_report",
        "candidate_artifacts": [
            {
                "path": "reports/final.md",
                "kind": "markdown_report",
                "note": "Review-ready Markdown report.",
            }
        ],
    }
    finished = _finish_with_payload(
        root,
        "markdown-candidate-artifact",
        lease,
        _final_payload(finalization),
    )
    assert_eq(
        finished.get("status"),
        "awaiting_review",
        "existing markdown candidate artifact should pass inspection",
    )
    findings = finished.get("finalization_validation", {}).get("findings") or []
    artifact_finding = next(
        (item for item in findings if item.get("check") == "candidate_artifact_inspection"),
        {},
    )
    assert_true(
        artifact_finding.get("passed"),
        "candidate artifact inspection should pass for readable markdown",
    )
    inspected = artifact_finding.get("artifacts") or []
    assert_true(
        any(item.get("path") == "reports/final.md" for item in inspected),
        "inspection finding should list the checked markdown artifact",
    )


def test_worker_final_inspects_xlsx_candidate_sheet_names(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "xlsx-candidate-artifact",
            "--goal",
            "XLSX candidate artifact test",
            "--deliverable",
            "review-ready spreadsheet",
        )
    )
    task_dir = root / "xlsx-candidate-artifact"
    _write_minimal_xlsx(task_dir / "reports" / "final.xlsx", sheet_name="Сводка")
    lease = json_out(run("begin", "--root", str(root), "--id", "xlsx-candidate-artifact"))
    finalization = {
        **_HUMAN_READY_FINALIZATION,
        "primary_deliverable_kind": "spreadsheet",
        "candidate_artifacts": [
            {
                "path": "reports/final.xlsx",
                "kind": "spreadsheet",
                "note": "Review-ready workbook.",
            }
        ],
    }
    finished = _finish_with_payload(
        root,
        "xlsx-candidate-artifact",
        lease,
        _final_payload(finalization),
    )
    assert_eq(
        finished.get("status"),
        "awaiting_review",
        "valid XLSX candidate artifact should pass inspection",
    )
    findings = finished.get("finalization_validation", {}).get("findings") or []
    artifact_finding = next(
        (item for item in findings if item.get("check") == "candidate_artifact_inspection"),
        {},
    )
    inspected = artifact_finding.get("artifacts") or []
    xlsx_artifact = next(
        (item for item in inspected if item.get("path") == "reports/final.xlsx"),
        {},
    )
    assert_eq(xlsx_artifact.get("format"), "xlsx", "XLSX inspection should expose format")
    assert_eq(xlsx_artifact.get("sheet_count"), 1, "XLSX inspection should count sheets")
    assert_eq(
        xlsx_artifact.get("sheet_names"),
        ["Сводка"],
        "XLSX inspection should expose sheet names",
    )


def test_delivery_manifest_populated_on_completion(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-test",
            "--goal",
            "Delivery manifest test",
        )
    )
    task_dir = root / "delivery-test"
    state_path = task_dir / "state.json"

    lease = json_out(run("begin", "--root", str(root), "--id", "delivery-test"))
    finished = finish_to_awaiting_review(root, "delivery-test", lease)
    assert_eq(
        finished.get("status"),
        "awaiting_review",
        "worker-initiated final should go to awaiting_review",
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    delivery = state.get("delivery") or {}
    assert_true(
        bool(delivery.get("primary_file")),
        "delivery.primary_file should be set after awaiting_review",
    )
    assert_true(
        delivery.get("review_ready"),
        "delivery.review_ready should be True after awaiting_review",
    )
    assert_true(
        not delivery.get("ready"),
        "delivery.ready should remain False until explicit delivery approval",
    )


def test_mark_delivered_command(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "mark-delivered-test",
            "--goal",
            "Mark delivered test",
        )
    )
    task_dir = root / "mark-delivered-test"
    reports_dir = task_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "final.pdf").write_text("dummy pdf", encoding="utf-8")
    (reports_dir / "leads.xlsx").write_text("dummy xlsx", encoding="utf-8")

    result = json_out(
        run(
            "mark-delivered",
            "--root",
            str(root),
            "--id",
            "mark-delivered-test",
            "--primary-file",
            "reports/final.pdf",
            "--summary-text",
            "Analysis complete. PDF attached.",
            "--channel-strategy",
            "attach",
            "--attachment",
            "reports/leads.xlsx",
            "--ready",
        )
    )
    assert_true(
        result.get("delivery_ready"),
        "mark-delivered should set delivery_ready=True",
    )
    assert_true(
        result.get("primary_file"),
        "primary_file should be set (resolved to absolute path)",
    )
    assert_eq(
        result.get("summary_text"),
        "Analysis complete. PDF attached.",
        "summary_text should be set",
    )
    assert_eq(
        result.get("channel_strategy"),
        "attach",
        "channel_strategy should be set",
    )
    attachments = result.get("attachments") or []
    assert_true(
        any("leads.xlsx" in att for att in attachments),
        "attachment should be in attachments list",
    )


def test_mark_delivered_succeeds_with_valid_relative_primary_file(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-relative-success",
            "--goal",
            "Test mark-delivered with relative path",
        )
    )
    task_dir = root / "delivery-relative-success"
    reports_dir = task_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    final_pdf = reports_dir / "final.pdf"
    final_pdf.write_text("dummy pdf content", encoding="utf-8")

    result = json_out(
        run(
            "mark-delivered",
            "--root",
            str(root),
            "--id",
            "delivery-relative-success",
            "--primary-file",
            "reports/final.pdf",
            "--ready",
        )
    )
    assert_true(
        result.get("delivery_ready"),
        "mark-delivered should set delivery_ready=True with valid relative path",
    )
    assert_true(
        result.get("primary_file"),
        "primary_file should be set with resolved absolute path",
    )


def test_mark_delivered_fails_with_missing_primary_file_when_ready(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-missing-file",
            "--goal",
            "Test mark-delivered with missing file",
        )
    )
    fail_result = run(
        "mark-delivered",
        "--root",
        str(root),
        "--id",
        "delivery-missing-file",
        "--primary-file",
        "reports/nonexistent.pdf",
        "--ready",
        check=False,
    )
    assert_true(
        fail_result.returncode != 0,
        "mark-delivered should fail with missing primary_file and --ready",
    )
    assert_in(
        "does not exist", fail_result.stderr.lower(),
        "error message should indicate file does not exist",
    )


def test_mark_delivered_rejects_external_primary_file(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-external-file",
            "--goal",
            "Test mark-delivered rejects external file",
        )
    )
    outside_file = root.parent / "outside-delivery.txt"
    outside_file.write_text("outside\n", encoding="utf-8")

    fail_result = run(
        "mark-delivered",
        "--root",
        str(root),
        "--id",
        "delivery-external-file",
        "--primary-file",
        str(outside_file),
        "--ready",
        check=False,
    )

    assert_true(
        fail_result.returncode != 0,
        "mark-delivered should reject primary_file outside the task directory",
    )
    assert_in(
        "outside task directory",
        fail_result.stderr.lower(),
        "error should mention task directory containment",
    )


def test_mark_delivered_fails_when_primary_file_points_to_directory(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-directory-test",
            "--goal",
            "Test mark-delivered with directory path",
        )
    )
    task_dir = root / "delivery-directory-test"
    reports_dir = task_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    fail_result = run(
        "mark-delivered",
        "--root",
        str(root),
        "--id",
        "delivery-directory-test",
        "--primary-file",
        "reports",
        "--ready",
        check=False,
    )
    assert_true(
        fail_result.returncode != 0,
        "mark-delivered should fail when primary_file is a directory",
    )
    assert_in(
        "not a file", fail_result.stderr.lower(),
        "error message should indicate path is not a file",
    )


def test_mark_delivered_fails_ready_without_primary_file(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-no-primary",
            "--goal",
            "Test mark-delivered --ready without primary_file",
        )
    )
    fail_result = run(
        "mark-delivered",
        "--root",
        str(root),
        "--id",
        "delivery-no-primary",
        "--ready",
        check=False,
    )
    assert_true(
        fail_result.returncode != 0,
        "mark-delivered should fail when --ready without primary_file",
    )
    assert_in(
        "primary_file", fail_result.stderr.lower(),
        "error message should mention primary_file requirement",
    )


def test_mark_delivered_validates_existing_primary_on_ready(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "delivery-existing-invalid",
            "--goal",
            "Test mark-delivered validates existing primary_file",
        )
    )
    task_dir = root / "delivery-existing-invalid"
    state_path = task_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["delivery"] = {"primary_file": "reports/missing.pdf"}
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fail_result = run(
        "mark-delivered",
        "--root",
        str(root),
        "--id",
        "delivery-existing-invalid",
        "--ready",
        check=False,
    )
    assert_true(
        fail_result.returncode != 0,
        "mark-delivered should fail when existing primary_file is invalid",
    )
    assert_in(
        "does not exist", fail_result.stderr.lower(),
        "error message should indicate file does not exist",
    )
