from __future__ import annotations

import re
import posixpath
import xml.etree.ElementTree as ET  # nosec B405
import zipfile
from pathlib import Path
from typing import Any

from research_mode_utils import ValidationError, is_relative_to, resolve_under_task


FINALIZATION_REQUIRED_TRACE_FIELDS = [
    "status",
    "inferred_user_need",
    "intended_recipient",
    "primary_deliverable_kind",
    "internal_artifacts",
    "candidate_artifacts",
    "blocking_defects",
    "revisions",
    "validation_evidence",
]

RAW_FINAL_ARTIFACT_SIGNALS = [
    "raw",
    "draft",
    "internal",
    "working",
    "iterations/",
    ".tmp/",
    "evidence_urls",
    "confidence",
    "active/unknown",
]

PACKAGE_KINDS = {"package", "final_package"}
PACKAGE_ENTRYPOINTS = ("README.md", "index.md", "final-report.md")
EXPECTED_FORMATS_BY_PRIMARY_KIND = {
    "markdown": {"markdown"},
    "markdown_report": {"markdown"},
    "md_report": {"markdown"},
    "pdf": {"pdf"},
    "pdf_report": {"pdf"},
    "docx": {"docx"},
    "docx_report": {"docx"},
    "html": {"html", "htm"},
    "html_report": {"html", "htm"},
    "spreadsheet": {"xlsx"},
    "xlsx": {"xlsx"},
    "xlsx_report": {"xlsx"},
    "csv": {"csv"},
    "csv_export": {"csv"},
    "package": {"package"},
}

FORMAT_ALIASES = {
    "markdown_report": (
        "markdown",
        "md",
        "markdown report",
        "md report",
        "маркдаун",
        "markdown-отчет",
        "markdown-отчёт",
        "md-отчет",
        "md-отчёт",
    ),
    "pdf_report": (
        "pdf",
        "pdf report",
        "pdf-отчет",
        "pdf-отчёт",
        "пдф",
    ),
    "docx_report": (
        "docx",
        "word",
        "docx report",
        "word document",
        "документ word",
        "ворд",
    ),
    "xlsx": (
        "xlsx",
        "spreadsheet",
        "excel",
        "workbook",
        "таблица",
        "таблицу",
        "табличный",
        "эксель",
    ),
    "csv": (
        "csv",
        "csv export",
    ),
    "html_report": (
        "html",
        "interactive",
        "web page",
        "интерактив",
        "веб-страница",
    ),
    "package": (
        "package",
        "zip",
        "bundle",
        "пакет",
        "архив",
    ),
}

PRIMARY_KIND_NORMALIZATION = {
    "markdown": "markdown_report",
    "md_report": "markdown_report",
    "pdf": "pdf_report",
    "docx": "docx_report",
    "html": "html_report",
    "spreadsheet": "xlsx",
    "xlsx_report": "xlsx",
    "csv_export": "csv",
}


def _expected_formats_for_primary_kind(primary_kind: str) -> set[str]:
    return EXPECTED_FORMATS_BY_PRIMARY_KIND.get(
        str(primary_kind or "").strip().lower(),
        set(),
    )


def _format_mismatch_reasons(
    primary_kind: str,
    actual_format: str | None,
) -> list[str]:
    expected = _expected_formats_for_primary_kind(primary_kind)
    if not expected:
        return []
    actual = str(actual_format or "").strip().lower()
    if actual in expected:
        return []
    return ["primary_deliverable_format_mismatch"]


def _normalize_deliverable_kind(kind: str | None) -> str | None:
    cleaned = str(kind or "").strip().lower()
    if not cleaned:
        return None
    return PRIMARY_KIND_NORMALIZATION.get(cleaned, cleaned)


def _explicit_user_format_kind(deliverable_desc: str) -> str | None:
    text = f" {str(deliverable_desc or '').lower()} "
    matches: list[tuple[int, int, str]] = []
    for kind, aliases in FORMAT_ALIASES.items():
        for alias in aliases:
            padded_alias = f" {alias} "
            index = text.find(padded_alias)
            if index < 0:
                index = text.find(alias)
            if index >= 0:
                matches.append((index, len(alias), kind))
                break
    if not matches:
        return None
    _index, _length, kind = min(matches, key=lambda item: (item[0], -item[1]))
    return kind


def _format_to_deliverable_kind(artifact_format: str) -> str | None:
    if artifact_format == "package":
        return "package"
    if artifact_format in {"markdown", "md"}:
        return "markdown_report"
    if artifact_format in {"pdf", "docx"}:
        return f"{artifact_format}_report"
    if artifact_format in {"html", "htm"}:
        return "html_report"
    if artifact_format in {"xlsx", "csv"}:
        return artifact_format
    return None


def _artifact_format_kind(
    artifact_check: dict[str, Any] | None,
    *,
    preferred_primary_kind: str | None = None,
) -> str | None:
    artifacts = (artifact_check or {}).get("artifacts") or []
    expected_formats = _expected_formats_for_primary_kind(str(preferred_primary_kind or ""))
    if expected_formats:
        for artifact in artifacts:
            artifact_format = str(artifact.get("format") or "").strip().lower()
            if artifact_format in expected_formats:
                return _format_to_deliverable_kind(artifact_format)
    for artifact in (artifact_check or {}).get("artifacts") or []:
        artifact_format = str(artifact.get("format") or "").strip().lower()
        deliverable_kind = _format_to_deliverable_kind(artifact_format)
        if deliverable_kind:
            return deliverable_kind
    return None


def build_deliverable_format_decision(
    *,
    state: dict[str, Any],
    finalization: dict[str, Any] | None,
    report_markdown: str,
    artifact_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = finalization or {}
    working_memory = state.get("working_memory") or {}
    deliverable_desc = str(working_memory.get("deliverable") or "")
    explicit_kind = _explicit_user_format_kind(deliverable_desc)
    primary_kind = _normalize_deliverable_kind(trace.get("primary_deliverable_kind"))
    feasible_kind = _artifact_format_kind(
        artifact_check,
        preferred_primary_kind=primary_kind,
    )
    if not feasible_kind and str(report_markdown or "").strip():
        feasible_kind = "markdown_report"

    context_blob = "\n".join(
        str(item or "")
        for item in (
            deliverable_desc,
            trace.get("inferred_user_need"),
            trace.get("intended_recipient"),
            state.get("goal"),
            state.get("title"),
        )
    ).lower()
    source = "explicit" if explicit_kind else "declared" if primary_kind else "inferred"
    selected_kind = explicit_kind or primary_kind or feasible_kind
    if explicit_kind:
        reason = "User explicitly requested this deliverable format."
    elif primary_kind:
        reason = "Worker declared this primary deliverable kind."
    else:
        reason = "Worker-provided artifact format is already suitable."
    alternatives: list[str] = []

    if not explicit_kind:
        chat_thread = any(
            marker in context_blob
            for marker in (
                "chat",
                "thread",
                "mattermost",
                "telegram",
                "topic",
                "чат",
                "тред",
                "топик",
                "канал",
            )
        )
        narrative_report = any(
            marker in context_blob
            for marker in (
                "long narrative",
                "long report",
                "narrative report",
                "report",
                "отчет",
                "отчёт",
                "исследование",
            )
        )
        tabular = any(
            marker in context_blob
            for marker in (
                "tabular",
                "dataset",
                "spreadsheet",
                "xlsx",
                "csv",
                "таблица",
                "таблич",
                "датасет",
            )
        )
        interactive = any(
            marker in context_blob
            for marker in ("interactive", "dashboard", "html", "интерактив", "дашборд")
        )
        bundle = any(
            marker in context_blob
            for marker in ("package", "bundle", "zip", "пакет", "архив")
        )

        if bundle:
            source = "inferred"
            selected_kind = "package"
            reason = "Multi-file or bundled output is easier to review as a package."
            alternatives = ["markdown_report", "zip"]
        elif interactive:
            source = "inferred"
            selected_kind = "html_report"
            reason = "Interactive or visual output is easier to review as HTML."
            alternatives = ["pdf_report", "markdown_report"]
        elif tabular and feasible_kind == "markdown_report":
            source = "inferred"
            selected_kind = "xlsx"
            reason = "Tabular data is easier to inspect as a spreadsheet or CSV."
            alternatives = ["csv", "markdown_report"]
        elif chat_thread and narrative_report and feasible_kind == "markdown_report":
            source = "inferred"
            selected_kind = "pdf_report"
            reason = "Long narrative report delivered in a chat/thread is easier to review as PDF."
            alternatives = ["markdown_report", "docx_report"]

    if selected_kind is None:
        selected_kind = feasible_kind or "markdown_report"
    if feasible_kind is None:
        feasible_kind = selected_kind

    return {
        "selected_kind": selected_kind,
        "desired_kind": selected_kind,
        "feasible_kind": feasible_kind,
        "reason": reason,
        "source": source,
        "alternatives_considered": alternatives,
    }


def check_deliverable_format_decision(
    *,
    state: dict[str, Any],
    finalization: dict[str, Any] | None,
    report_markdown: str,
    artifact_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = build_deliverable_format_decision(
        state=state,
        finalization=finalization,
        report_markdown=report_markdown,
        artifact_check=artifact_check,
    )
    desired_kind = decision.get("desired_kind")
    feasible_kind = decision.get("feasible_kind")
    reasons: list[str] = []
    if desired_kind != feasible_kind:
        if decision.get("source") == "explicit":
            reasons.append("explicit_deliverable_format_mismatch")
        elif decision.get("source") == "declared":
            reasons.append("primary_deliverable_format_mismatch")
        else:
            reasons.append("default_deliverable_format_mismatch")
    return {
        "check": "deliverable_format_decision",
        "passed": not reasons,
        "reasons": reasons,
        **decision,
    }


def build_finalization_contract(state: dict[str, Any]) -> dict[str, Any]:
    working_memory = state.get("working_memory") or {}
    finalization = state.get("finalization") or {}
    return {
        "required_status": "passed",
        "required_trace_fields": FINALIZATION_REQUIRED_TRACE_FIELDS,
        "validation_requirements": [
            "blocking_defects must be empty",
            "validation_evidence must describe what was checked",
            "candidate_artifacts must be user-facing or the report text must be self-contained",
            "raw/internal workspace artifacts must not be exposed as the final result",
        ],
        "raw_artifact_signals": RAW_FINAL_ARTIFACT_SIGNALS,
        "requested_deliverable": working_memory.get("deliverable"),
        "current_status": finalization.get("status") or "not_started",
        "attempt_count": int(finalization.get("attempt_count") or 0),
        "max_attempts": int(finalization.get("max_attempts") or 3),
    }


def build_finalization_surface(state: dict[str, Any]) -> dict[str, Any]:
    finalization = state.get("finalization") or {}
    internal_artifacts = finalization.get("internal_artifacts") or []
    candidate_artifacts = finalization.get("candidate_artifacts") or []
    blocking_defects = finalization.get("blocking_defects") or []
    nonblocking_defects = finalization.get("nonblocking_defects") or []
    revisions = finalization.get("revisions") or []
    validation_evidence = finalization.get("validation_evidence") or []
    validation_findings = finalization.get("last_validation_findings") or []

    surface = {
        "status": finalization.get("status"),
        "attempt_count": int(finalization.get("attempt_count") or 0),
        "last_validated_at": finalization.get("last_validated_at"),
        "max_attempts": int(finalization.get("max_attempts") or 3),
        "inferred_user_need": finalization.get("inferred_user_need"),
        "intended_recipient": finalization.get("intended_recipient"),
        "primary_deliverable_kind": finalization.get("primary_deliverable_kind"),
        "deliverable_decision": finalization.get("deliverable_decision"),
        "internal_artifacts": internal_artifacts,
        "candidate_artifacts": candidate_artifacts,
        "blocking_defects": blocking_defects,
        "nonblocking_defects": nonblocking_defects,
        "revisions": revisions,
        "validation_evidence": validation_evidence,
        "last_validation_findings": validation_findings,
        "internal_artifacts_count": len(internal_artifacts),
        "candidate_artifacts_count": len(candidate_artifacts),
        "blocking_defects_count": len(blocking_defects),
        "nonblocking_defects_count": len(nonblocking_defects),
        "revisions_count": len(revisions),
        "validation_evidence_count": len(validation_evidence),
    }
    surface["operator_next_action"] = _build_operator_next_action(
        state=state,
        finalization_surface=surface,
    )
    return surface


def _build_operator_next_action(
    *,
    state: dict[str, Any],
    finalization_surface: dict[str, Any],
) -> dict[str, Any]:
    task_status = str(state.get("status") or "")
    finalization_status = str(finalization_surface.get("status") or "")
    findings = finalization_surface.get("last_validation_findings") or []
    blocking_defects = finalization_surface.get("blocking_defects") or []
    reasons = _collect_failed_finalization_reasons(findings, blocking_defects)
    attempt_count = int(finalization_surface.get("attempt_count") or 0)
    max_attempts = int(finalization_surface.get("max_attempts") or 3)

    if finalization_status == "needs_intervention":
        return {
            "kind": "operator_intervention",
            "label": "Inspect failed finalization and decide repair path",
            "rationale": "Finalization exhausted automatic attempts or marked itself as requiring human intervention.",
            "reasons": reasons,
            "commands": [
                "summary --format text",
                "request-changes --feedback '<required fixes>'",
                "stop",
            ],
        }

    if task_status == "awaiting_review" and finalization_status == "passed":
        return {
            "kind": "review_candidate",
            "label": "Review candidate deliverable",
            "rationale": "The worker supplied passing finalization evidence and the task is gated for human review.",
            "reasons": [],
            "commands": [
                "summary --format text",
                "draft-report --format markdown",
                "approve",
                "request-changes --feedback '<required fixes>'",
            ],
        }

    if (
        task_status == "finalize"
        or finalization_status in {"rework", "failed"}
        or reasons
    ):
        if max_attempts > 0 and attempt_count >= max_attempts:
            return {
                "kind": "operator_intervention",
                "label": "Inspect repeated finalization failures",
                "rationale": "Finalization has reached the configured attempt limit.",
                "reasons": reasons,
                "commands": [
                    "summary --format text",
                    "request-changes --feedback '<required fixes>'",
                    "stop",
                ],
            }
        return {
            "kind": "worker_rework",
            "label": "Let the worker repair finalization defects",
            "rationale": "Finalization validation did not pass; the next worker turn should fix failed checks before review.",
            "reasons": reasons,
            "commands": [
                "begin",
                "finish after rework",
                "summary --format text",
            ],
        }

    if finalization_status == "passed":
        return {
            "kind": "verify_review_state",
            "label": "Verify review gate state",
            "rationale": "Finalization passed, but the task is not currently awaiting review.",
            "reasons": [],
            "commands": ["summary --format text"],
        }

    return {
        "kind": "continue_research",
        "label": "Continue research until finalization evidence exists",
        "rationale": "No passing finalization evidence is available yet.",
        "reasons": reasons,
        "commands": ["begin", "summary --format text"],
    }


def _collect_failed_finalization_reasons(
    findings: list[dict[str, Any]],
    blocking_defects: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    for finding in findings:
        if finding.get("passed"):
            continue
        finding_reasons = finding.get("reasons") or []
        if finding_reasons:
            reasons.extend(str(item) for item in finding_reasons)
        elif finding.get("check"):
            reasons.append(str(finding.get("check")))
    for defect in blocking_defects:
        text = defect.get("summary") or defect.get("text") or defect.get("reason")
        if text:
            reasons.append(str(text))
    return list(dict.fromkeys(reasons))


def inspect_candidate_artifacts(
    *,
    task_dir: Path,
    final_report_path: Path,
    finalization: dict[str, Any] | None,
    report_markdown: str,
) -> dict[str, Any]:
    trace = finalization or {}
    candidate_artifacts = trace.get("candidate_artifacts") or []
    report_text = str(report_markdown or "").strip()
    primary_kind = str(trace.get("primary_deliverable_kind") or "").strip().lower()

    if not candidate_artifacts:
        reasons = [] if report_text else ["primary_deliverable_missing"]
        if report_text:
            reasons.extend(_format_mismatch_reasons(primary_kind, "markdown"))
        return {
            "check": "candidate_artifact_inspection",
            "passed": bool(report_text) and not reasons,
            "reasons": reasons,
            "artifacts": [],
            "mode": "self_contained_report" if report_text else "missing",
        }

    checked: list[dict[str, Any]] = []
    reasons: list[str] = []
    expected_formats = _expected_formats_for_primary_kind(primary_kind)

    for artifact in candidate_artifacts:
        artifact_path = str(artifact.get("path") or "").strip()
        artifact_kind = str(artifact.get("kind") or "artifact").strip() or "artifact"
        if not artifact_path:
            reasons.append("candidate_artifact_missing")
            checked.append({"path": artifact_path, "kind": artifact_kind, "exists": False})
            continue

        final_report_names = {
            str(final_report_path),
            final_report_path.name,
            "final-report.md",
        }
        if artifact_path in final_report_names and report_text:
            markdown_result = _inspect_markdown_text(report_text)
            checked.append(
                {
                    "path": artifact_path,
                    "kind": artifact_kind,
                    "exists": True,
                    "source": "final_report_markdown",
                    **markdown_result,
                }
            )
            reasons.extend(markdown_result.get("reasons") or [])
            continue

        try:
            resolved = resolve_under_task(
                task_dir, artifact_path, label="candidate artifact"
            )
        except ValidationError:
            reasons.append("candidate_artifact_outside_task")
            checked.append(
                {
                    "path": artifact_path,
                    "kind": artifact_kind,
                    "exists": False,
                    "inside_task": False,
                }
            )
            continue

        if not resolved.exists():
            reasons.append("candidate_artifact_missing")
            checked.append(
                {
                    "path": artifact_path,
                    "kind": artifact_kind,
                    "exists": False,
                    "inside_task": True,
                }
            )
            continue
        if not resolved.is_file():
            package_result = _inspect_package_candidate(
                task_dir=task_dir,
                resolved=resolved,
                artifact=artifact,
                artifact_path=artifact_path,
                artifact_kind=artifact_kind,
                primary_kind=primary_kind,
            )
            checked.append(package_result)
            reasons.extend(package_result.get("reasons") or [])
            continue

        file_result = _inspect_existing_file(resolved)
        checked.append(
            {
                "path": artifact_path,
                "kind": artifact_kind,
                "exists": True,
                "inside_task": True,
                "is_file": True,
                **file_result,
            }
        )
        reasons.extend(file_result.get("reasons") or [])

    if expected_formats:
        has_matching_primary = any(
            str(item.get("format") or "").strip().lower() in expected_formats
            for item in checked
        )
        if not has_matching_primary:
            reasons.append("primary_deliverable_format_mismatch")
            for item in checked:
                artifact_format = str(item.get("format") or "").strip().lower()
                if artifact_format and artifact_format not in expected_formats:
                    item["reasons"] = list(
                        dict.fromkeys(
                            [
                                *(item.get("reasons") or []),
                                "primary_deliverable_format_mismatch",
                            ]
                        )
                    )

    deduped_reasons = list(dict.fromkeys(reasons))
    return {
        "check": "candidate_artifact_inspection",
        "passed": not deduped_reasons,
        "reasons": deduped_reasons,
        "artifacts": checked,
        "mode": "candidate_artifacts",
    }


def _inspect_package_candidate(
    *,
    task_dir: Path,
    resolved: Path,
    artifact: dict[str, Any],
    artifact_path: str,
    artifact_kind: str,
    primary_kind: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    outputs_dir = task_dir / "workspace" / "outputs"
    if primary_kind != "package" or artifact_kind not in PACKAGE_KINDS:
        reasons.append("candidate_artifact_not_file")
    if not resolved.is_dir():
        reasons.append("candidate_package_not_directory")
    if not is_relative_to(resolved, outputs_dir):
        reasons.append("candidate_package_not_under_outputs")

    entrypoint_name = str(artifact.get("entrypoint") or "").strip()
    entrypoint: Path | None = None
    if entrypoint_name:
        candidate = (resolved / entrypoint_name).resolve()
        if is_relative_to(candidate, resolved) and candidate.is_file():
            entrypoint = candidate
        else:
            reasons.append("candidate_package_entrypoint_missing")
    else:
        for name in PACKAGE_ENTRYPOINTS:
            candidate = resolved / name
            if candidate.is_file():
                entrypoint = candidate.resolve()
                break
        if entrypoint is None:
            reasons.append("candidate_package_entrypoint_missing")

    attachments: list[str] = []
    inspectable_files = 0
    try:
        package_items = list(resolved.rglob("*"))
    except OSError:
        package_items = []
        reasons.append("candidate_package_unreadable")

    for item in package_items:
        try:
            item_resolved = item.resolve()
        except OSError:
            reasons.append("candidate_package_unreadable")
            continue
        if not is_relative_to(item_resolved, task_dir):
            reasons.append("candidate_package_symlink_escape")
            continue
        if item.is_file():
            inspectable_files += 1
            attachments.append(str(item_resolved))

    if inspectable_files == 0:
        reasons.append("candidate_package_empty")

    return {
        "path": artifact_path,
        "kind": artifact_kind,
        "exists": True,
        "inside_task": True,
        "is_file": False,
        "is_directory": resolved.is_dir(),
        "package_path": str(resolved),
        "entrypoint_path": str(entrypoint) if entrypoint else None,
        "attachments": attachments,
        "file_count": inspectable_files,
        "format": "package",
        "reasons": list(dict.fromkeys(reasons)),
    }


def _inspect_existing_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return _inspect_markdown_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".xlsx":
        return _inspect_xlsx_file(path)
    try:
        with path.open("rb") as handle:
            sample = handle.read(1)
    except OSError:
        return {"format": suffix.lstrip(".") or "file", "reasons": ["candidate_artifact_unreadable"]}
    return {
        "format": suffix.lstrip(".") or "file",
        "reasons": [] if sample or path.stat().st_size == 0 else ["candidate_artifact_unreadable"],
        "size_bytes": path.stat().st_size,
    }


def _inspect_markdown_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    reasons: list[str] = []
    heading_count = len(re.findall(r"^#{1,6}\s+\S", stripped, flags=re.MULTILINE))
    if not stripped:
        reasons.append("markdown_candidate_empty")
    if heading_count < 1:
        reasons.append("markdown_candidate_missing_heading")
    if len(stripped.split()) < 20:
        reasons.append("markdown_candidate_too_short")
    return {
        "format": "markdown",
        "heading_count": heading_count,
        "word_count": len(stripped.split()),
        "reasons": reasons,
    }


def _inspect_xlsx_file(path: Path) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        return {"format": "xlsx", "reasons": ["xlsx_candidate_not_openable"]}
    try:
        with zipfile.ZipFile(path) as workbook:
            names = set(workbook.namelist())
            has_workbook = "xl/workbook.xml" in names
            sheet_files = [name for name in names if name.startswith("xl/worksheets/")]
            sheet_names = (
                _read_xlsx_sheet_names(workbook.read("xl/workbook.xml"))
                if has_workbook
                else []
            )
            strict_reasons = _inspect_xlsx_strict_ooxml(workbook, sheet_files, names)
    except zipfile.BadZipFile:
        return {"format": "xlsx", "reasons": ["xlsx_candidate_not_openable"]}
    except (KeyError, ET.ParseError):
        return {"format": "xlsx", "reasons": ["xlsx_candidate_invalid_workbook_xml"]}
    reasons = []
    if not has_workbook:
        reasons.append("xlsx_candidate_missing_workbook")
    if not sheet_files:
        reasons.append("xlsx_candidate_missing_sheets")
    if has_workbook and not sheet_names:
        reasons.append("xlsx_candidate_missing_sheet_names")
    reasons.extend(strict_reasons)
    return {
        "format": "xlsx",
        "sheet_count": len(sheet_files),
        "sheet_names": sheet_names,
        "strict_checks": {
            "engine": "ooxml",
            "libreoffice_roundtrip": "not_available",
        },
        "reasons": reasons,
    }


def _inspect_xlsx_strict_ooxml(
    workbook: zipfile.ZipFile, sheet_files: list[str], names: set[str]
) -> list[str]:
    reasons: list[str] = []
    rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    main_ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    office_rel_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

    for sheet_file in sheet_files:
        try:
            sheet_root = ET.fromstring(workbook.read(sheet_file))  # nosec B314
        except (KeyError, ET.ParseError):
            reasons.append("xlsx_candidate_invalid_worksheet_xml")
            continue

        worksheet_filters = {
            str(elem.attrib.get("ref") or "").upper()
            for elem in sheet_root.iter(f"{main_ns}autoFilter")
            if elem.attrib.get("ref")
        }
        table_part_ids = [
            str(elem.attrib.get(office_rel_key) or "").strip()
            for elem in sheet_root.iter(f"{main_ns}tablePart")
            if elem.attrib.get(office_rel_key)
        ]
        if not table_part_ids:
            continue

        rels_path = _worksheet_rels_path(sheet_file)
        relationships: dict[str, str] = {}
        if rels_path not in names:
            reasons.append("xlsx_table_relationships_missing")
        else:
            try:
                rels_root = ET.fromstring(workbook.read(rels_path))  # nosec B314
            except ET.ParseError:
                reasons.append("xlsx_table_relationships_invalid")
            else:
                for rel in rels_root.iter(f"{rel_ns}Relationship"):
                    rel_id = str(rel.attrib.get("Id") or "")
                    target = str(rel.attrib.get("Target") or "")
                    if rel_id and target:
                        relationships[rel_id] = target

        for rel_id in table_part_ids:
            target = relationships.get(rel_id)
            if not target:
                reasons.append("xlsx_table_relationship_missing")
                continue
            table_path = _resolve_ooxml_target(sheet_file, target)
            if table_path not in names:
                reasons.append("xlsx_table_part_missing")
                continue
            try:
                table_root = ET.fromstring(workbook.read(table_path))  # nosec B314
            except ET.ParseError:
                reasons.append("xlsx_table_part_invalid")
                continue
            table_ref = str(table_root.attrib.get("ref") or "").upper()
            table_filter_refs = {
                str(elem.attrib.get("ref") or "").upper()
                for elem in table_root.iter(f"{main_ns}autoFilter")
                if elem.attrib.get("ref")
            }
            if not table_ref:
                reasons.append("xlsx_table_ref_missing")
            conflict_refs = {table_ref, *table_filter_refs} & worksheet_filters
            if conflict_refs:
                reasons.append("xlsx_conflicting_table_autofilter")

    return list(dict.fromkeys(reasons))


def _worksheet_rels_path(sheet_file: str) -> str:
    directory, filename = sheet_file.rsplit("/", 1)
    return f"{directory}/_rels/{filename}.rels"


def _resolve_ooxml_target(source_file: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    source_dir = source_file.rsplit("/", 1)[0]
    return posixpath.normpath(posixpath.join(source_dir, target))


def _read_xlsx_sheet_names(workbook_xml: bytes) -> list[str]:
    # XLSX workbook XML is read for metadata only.
    root = ET.fromstring(  # nosec B314
        workbook_xml
    )
    names: list[str] = []
    for elem in root.iter():
        if elem.tag.rsplit("}", 1)[-1] != "sheet":
            continue
        name = str(elem.attrib.get("name") or "").strip()
        if name:
            names.append(name)
    return names
