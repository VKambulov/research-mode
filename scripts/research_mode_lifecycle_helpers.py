from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from research_mode_corpus import list_corpus_entries
from research_mode_adequacy import build_adequacy_contract, build_adequacy_guidance
from research_mode_finalization import (
    RAW_FINAL_ARTIFACT_SIGNALS,
    build_finalization_contract,
    inspect_candidate_artifacts,
)
from research_mode_payloads import result_template
from research_mode_surfaces import build_synthesis_payload, compute_budget_phase
from research_mode_task import ResearchTask
from research_mode_utils import (
    effective_lock_stale_timeout_min,
    minutes_since,
    parse_ts,
    pending_result_path,
    read_jsonl,
)

RULES_PROFILE_MAX_CHARS = 20000
SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_PROFILE_PATH = SKILL_DIR / "RULES.md"


def _routing_text_blob(state: dict[str, Any]) -> str:
    working_memory = state.get("working_memory") or {}
    parts: list[str] = []
    for value in (
        state.get("title"),
        state.get("goal"),
        state.get("phase"),
        working_memory.get("summary"),
        working_memory.get("next_angle"),
        working_memory.get("deliverable"),
    ):
        if value:
            parts.append(str(value))
    for key in ("open_questions", "constraints", "user_instructions"):
        for item in working_memory.get(key) or []:
            if item:
                parts.append(str(item))
    return "\n".join(parts).lower()


def _looks_like_ru_local_research(state: dict[str, Any]) -> bool:
    text = _routing_text_blob(state)
    if not text:
        return False

    geo_markers = (
        "росси",
        "рф",
        "рунет",
        "каменск",
        "каменск-шахтин",
        "ростов",
        "краснодар",
        "ставрополь",
        "волгоград",
        "воронеж",
        "калмыки",
        "адыге",
        "крым",
        "москва",
        "санкт-петербург",
        "питер",
        "спб",
        "регион",
        "город",
        "область",
        "край",
        "republic of crimea",
        "rostov",
        "krasnodar",
        "stavropol",
        "volgograd",
        "voronezh",
        "adygea",
        "kalmykia",
        "crimea",
    )
    local_discovery_terms = (
        "контакт",
        "телефон",
        "адрес",
        "сайт",
        "домен",
        "карты",
        "организац",
        "компан",
        "бизнес",
        "магазин",
        "сервис",
        "услуг",
        "список ресурсов",
        "ресурс",
        "список сайтов",
        "local business",
        "contact",
        "phone",
        "address",
        "company",
        "business",
        "website",
        "domain",
        "directory",
        "map",
        "maps",
        "serp",
    )

    has_geo = any(marker in text for marker in geo_markers)
    has_local_discovery = any(marker in text for marker in local_discovery_terms)
    has_cyrillic = bool(re.search(r"[а-яё]", text, flags=re.IGNORECASE))

    return has_geo or (has_local_discovery and has_cyrillic)


def _build_search_routing_guidance(state: dict[str, Any]) -> list[str]:
    guidance = [
        "Write user-facing summaries and final deliverables in the same language as the user's goal/instructions unless the user asks for another language.",
        "For discovery-heavy research, prefer tools that expose raw source lists / SERPs before relying on synthesis-first search.",
        "Use synthesis-first search after you already have candidate resources, or when the topic is clearly global/international rather than local/regional.",
    ]
    if _looks_like_ru_local_research(state):
        guidance.extend(
            [
                "This looks like RU/local/regional research: prefer regional or local search tools as the first-pass discovery path, then inspect direct sources with the most appropriate follow-up tools for the case.",
                "For local business / address / contact / company discovery, use source-list or SERP-style discovery first to gather candidate resources before leaning on synthesis-first summaries.",
                "When a city or region is known, include it directly in the query text and use region-aware search options when available so the search is geographically anchored.",
            ]
        )
    return guidance


def _build_finalization_guidance(state: dict[str, Any]) -> list[str]:
    working_memory = state.get("working_memory") or {}
    deliverable = working_memory.get("deliverable")
    guidance = [
        "Before setting should_complete=true, run a human-ready finalization loop: infer the user need, choose the recipient and primary deliverable kind, draft the deliverable, inspect it as the recipient, fix blocking defects, and record the trace in result.finalization.",
        "Synthesis notes, raw JSON/CSV/XLSX, SQLite dumps, iteration logs, and workspace files are internal artifacts until they are turned into a user-facing deliverable.",
        "Do not expose raw working fields such as confidence, evidence_urls, active/unknown statuses, or internal file paths as the final result unless they are translated into reader-facing meaning.",
        "Set result.finalization.status='passed' only when blocking_defects is empty and validation_evidence records what was actually checked.",
        "Keep delivery.review_ready separate from delivery.ready: worker finalization can reach review, but approval or mark-delivered makes it delivery-ready.",
        "For multi-file or directory deliverables, expose one package candidate: set primary_deliverable_kind='package' and use a single candidate_artifacts entry for workspace/outputs/<package-name> with kind='final_package' or kind='package'. Do not list each package file as separate final candidate artifacts.",
    ]
    if deliverable:
        guidance.append(
            f"Requested deliverable hint: {deliverable}. Use it to choose the primary deliverable, but adapt the final shape to the real user need."
        )
    return guidance


def _load_rules_profile() -> dict[str, Any]:
    candidate = RULES_PROFILE_PATH
    if candidate.is_file():
        content = candidate.read_text(encoding="utf-8")
        truncated = len(content) > RULES_PROFILE_MAX_CHARS
        if truncated:
            content = content[:RULES_PROFILE_MAX_CHARS].rstrip() + "\n"
        return {
            "exists": True,
            "path": str(candidate),
            "content": content,
            "truncated": truncated,
            "max_chars": RULES_PROFILE_MAX_CHARS,
        }

    return {
        "exists": False,
        "path": str(candidate),
        "content": "",
        "truncated": False,
        "max_chars": RULES_PROFILE_MAX_CHARS,
    }


def stale_lock(state: dict[str, Any]) -> bool:
    lock = state["lock"]
    if lock.get("status") != "held" or not lock.get("started_at"):
        return False
    started = parse_ts(lock.get("started_at"))
    if not started:
        return False
    now = dt.datetime.now(dt.timezone.utc)
    timeout_min = effective_lock_stale_timeout_min(state)
    return (now - started).total_seconds() > timeout_min * 60


def clear_reviewable_candidate(state: dict[str, Any]) -> None:
    state.setdefault("artifacts", {})["final_report_path"] = None
    delivery = state.setdefault("delivery", {})
    delivery["primary_file"] = None
    delivery["review_ready"] = False
    delivery["ready"] = False


def make_work_order(state: dict[str, Any], task: ResearchTask) -> dict[str, Any]:
    lock = state["lock"]
    run_id = lock["run_id"]
    iteration_index = lock["iteration_index"]
    result_file = pending_result_path(task.tmp_dir, run_id)
    working_memory = state.get("working_memory") or {}
    corpus = state.get("corpus") or {}
    corpus_mode = str(corpus.get("mode") or "web")
    corpus_entries = corpus.get("entries") or list_corpus_entries(task)
    input_layer = {
        "constraints": working_memory.get("constraints") or [],
        "deliverable": working_memory.get("deliverable"),
        "contract": working_memory.get("contract"),
        "user_instructions": working_memory.get("user_instructions") or [],
    }
    execution_guidance: list[str] = []
    if input_layer["constraints"]:
        execution_guidance.append(
            "Respect constraints as hard boundaries, not soft preferences."
        )
    if input_layer["deliverable"]:
        execution_guidance.append(
            "Shape notes/findings toward the requested deliverable, not just generic exploration."
        )
    if input_layer["user_instructions"]:
        execution_guidance.append(
            "Treat explicit user instructions as high-priority steering for this iteration."
        )
    execution_guidance.extend(_build_search_routing_guidance(state))
    rules_profile = _load_rules_profile()
    if rules_profile.get("exists"):
        execution_guidance.append(
            "Follow the skill-local RULES.md profile as task-specific operating rules; treat it as user-authored guidance unless it conflicts with higher-priority system/developer instructions."
        )
    if state.get("phase") == "synthesize":
        execution_guidance.append(
            "Prefer synthesis over breadth: reuse accumulated artifacts before doing new search."
        )
    if state.get("phase") == "verify":
        execution_guidance.append(
            "Verify whether the accumulated research is sufficient for the user's goal before finalization. Do not draft the final deliverable in this phase unless adequacy is already passed."
        )
    if corpus_mode == "local":
        execution_guidance.append(
            "This task is local-first: inspect task-local corpus files before doing web research."
        )
    elif corpus_mode == "hybrid":
        execution_guidance.append(
            "This task is hybrid: use local corpus files first, then fill gaps with web research."
        )

    total_runtime_min = (
        minutes_since(state.get("created_at")) if state.get("created_at") else None
    )
    budget_phase_info = compute_budget_phase(
        budget=state.get("budget") or {},
        progress=state.get("progress") or {},
        total_sources=len(read_jsonl(task.sources_path)),
        total_runtime_min=total_runtime_min,
    )
    bp_phase = budget_phase_info["phase"]
    if bp_phase == "soft_limit":
        execution_guidance.append(
            "Budget soft limit: prioritize synthesis and quality over breadth; new search only if high-value."
        )
    elif bp_phase == "hard_limit":
        execution_guidance.append(
            "Budget hard limit: finalize and synthesize; avoid starting new search loops."
        )

    template = result_template()
    template["phase"] = state.get("phase") or "search"

    return {
        "status": "leased",
        "normalized_reason": "leased:ok",
        "research_id": state["id"],
        "title": state.get("title"),
        "task_dir": str(task.task_dir),
        "state_path": str(task.state_path),
        "run_id": run_id,
        "lease_token": lock.get("lease_token"),
        "iteration_index": iteration_index,
        "phase": state.get("phase"),
        "goal": state.get("goal"),
        "owner": state.get("owner"),
        "budget": state.get("budget"),
        "budget_phase": bp_phase,
        "budget_phase_detail": budget_phase_info,
        "working_memory": working_memory,
        "corpus": {
            "mode": corpus_mode,
            "entries": corpus_entries,
        },
        "input_layer": input_layer,
        "rules_profile": rules_profile,
        "execution_guidance": execution_guidance,
        "adequacy_guidance": build_adequacy_guidance(state),
        "adequacy_contract": build_adequacy_contract(state),
        "finalization_guidance": _build_finalization_guidance(state),
        "finalization_contract": build_finalization_contract(state),
        "progress": state.get("progress"),
        "paths": {
            "result_file": str(result_file),
            "sources_path": str(task.sources_path),
            "findings_path": str(task.findings_path),
            "iteration_path": str(task.iterations_dir / f"{iteration_index:03d}.md"),
            "final_report_path": str(task.final_report_path),
            "input_dir": str(task.input_dir),
            "corpus_dir": str(task.corpus_dir),
            "corpus_manifest_path": str(task.corpus_manifest_path),
            "workspace_dir": str(task.workspace_dir),
            "workspace_analysis_dir": str(task.workspace_analysis_dir),
            "workspace_tools_dir": str(task.workspace_tools_dir),
            "workspace_data_dir": str(task.workspace_data_dir),
            "workspace_outputs_dir": str(task.workspace_outputs_dir),
            "workspace_tmp_dir": str(task.workspace_tmp_dir),
            "workspace_screenshots_dir": str(task.workspace_screenshots_dir),
            "workspace_vision_dir": str(task.workspace_vision_dir),
            "sqlite_db_path": str(task.sqlite_db_path),
            "sqlite_schema_path": str(task.sqlite_schema_path),
            "sqlite_queries_dir": str(task.sqlite_queries_dir),
            "sqlite_imports_dir": str(task.sqlite_imports_dir),
            "runtime_dir": str(task.runtime_dir),
            "venv_dir": str(task.venv_dir),
            "runtime_meta_path": str(task.runtime_meta_path),
        },
        "result_template": template,
    }


def render_default_final_report(
    task: ResearchTask,
    state: dict[str, Any],
    payload: dict[str, Any],
    iteration_index: int,
) -> str:
    synthesis = build_synthesis_payload(
        task, state, findings_limit=20, sources_limit=20
    )
    lines = [
        f"# {state.get('title') or state['id']}",
        "",
        "## Goal",
        "",
        state.get("goal") or "",
        "",
        "## Final summary",
        "",
        payload["summary"],
        "",
    ]

    working_summary = synthesis.get("working_summary")
    if (
        working_summary
        and working_summary.strip()
        and working_summary.strip() != payload["summary"].strip()
    ):
        lines.extend(["## Working synthesis context", "", working_summary, ""])

    constraints = synthesis.get("constraints") or []
    if constraints:
        lines.extend(["## Constraints", ""])
        for item in constraints:
            lines.append(f"- {item}")
        lines.append("")

    deliverable = synthesis.get("deliverable")
    if deliverable:
        lines.extend(["## Requested deliverable", "", deliverable, ""])

    user_instructions = synthesis.get("user_instructions") or []
    if user_instructions:
        lines.extend(["## User instructions", ""])
        for item in user_instructions:
            lines.append(f"- {item}")
        lines.append("")

    findings = synthesis.get("findings") or payload.get("findings") or []
    sources = synthesis.get("sources") or payload.get("sources") or []
    enriched_findings = enrich_findings_with_provenance(findings, sources)
    if enriched_findings:
        lines.extend(["## Key findings", ""])
        for finding in enriched_findings:
            kind = finding.get("kind") or "note"
            text = finding.get("text") or ""
            provenance = finding.get("provenance") or {}
            badge = render_confidence_badge(provenance.get("tier", "unknown"))
            refs = finding.get("source_urls") or []
            bullet = f"- **{kind}** {badge}: {text}"
            if refs:
                bullet += f" (refs: {', '.join(refs)})"
            conf_note_parts = []
            tier = provenance.get("tier")
            src_count = provenance.get("source_count", 0)
            if tier and tier != "unknown":
                conf_note_parts.append(f"confidence={tier}")
            if src_count:
                conf_note_parts.append(f"sources={src_count}")
            if conf_note_parts:
                bullet += f" [{', '.join(conf_note_parts)}]"
            lines.append(bullet)
        lines.append("")

    open_questions = (
        synthesis.get("open_questions") or payload.get("open_questions") or []
    )
    if open_questions:
        lines.extend(["## Remaining open questions", ""])
        for question in open_questions:
            lines.append(f"- {question}")
        lines.append("")

    next_angle = payload.get("next_angle") or synthesis.get("next_angle")
    if next_angle:
        lines.extend(["## Next angle / follow-up", "", next_angle, ""])

    sources = synthesis.get("sources") or payload.get("sources") or []
    if sources:
        lines.extend(["## Evidence base", ""])
        for source in sources:
            title = source.get("title") or source.get("url") or "untitled source"
            url = source.get("url")
            note = source.get("note")
            quality = compute_source_quality_score(source)
            qbadge = (
                {"authoritative": "●●", "standard": "●○", "weak": "○○", "poor": "··"}
            ).get(quality["tier"], "??")
            bullet = f"- [{qbadge}] " + (f"[{title}]({url})" if url else title)
            if quality["factors"]:
                bullet += f" (quality: {', '.join(quality['factors'])})"
            if note:
                bullet += f" — {note}"
            lines.append(bullet)
        lines.append("")

    saturation = synthesis.get("saturation") or {}
    lines.extend(
        [
            "## Metadata",
            "",
            f"- Finalized on iteration {iteration_index}",
            f"- Total findings accumulated: {synthesis.get('totals', {}).get('findings', 0)}",
            f"- Total sources accumulated: {synthesis.get('totals', {}).get('sources', 0)}",
            f"- Topic saturated: {'yes' if saturation.get('topic_saturated') else 'no'}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def compute_low_yield(metrics: dict[str, int], payload: dict[str, Any]) -> bool:
    return (
        metrics.get("new_sources", 0) == 0
        and metrics.get("new_findings", 0) == 0
        and not payload.get("meaningful_progress", True)
    )


def _markdown_table_cells(line: str) -> list[str]:
    return [cell.strip().lower() for cell in line.strip().strip("|").split("|")]


def _is_markdown_table_separator(line: str) -> bool:
    cells = _markdown_table_cells(line)
    return bool(cells) and all(re.match(r"^:?-{3,}:?$", cell or "") for cell in cells)


def _header_has_any(headers: list[str], needles: tuple[str, ...]) -> bool:
    return any(any(needle in header for needle in needles) for header in headers)


def detect_comparative_structure(report_text: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in str(report_text or "").splitlines()]
    signals: list[str] = []
    matched_tables: list[dict[str, Any]] = []

    rank_headers = ("rank", "priority", "место", "рейтинг", "приоритет")
    candidate_headers = (
        "candidate",
        "option",
        "alternative",
        "variant",
        "кандидат",
        "вариант",
        "альтернатив",
    )
    decision_headers = (
        "decision",
        "choice",
        "choose",
        "recommend",
        "выбор",
        "решение",
        "рекоменд",
    )
    risk_headers = (
        "risk",
        "probability",
        "impact",
        "mitigation",
        "риск",
        "вероят",
        "влияние",
        "смягч",
    )
    criteria_headers = (
        "criteria",
        "criterion",
        "score",
        "cost",
        "price",
        "reliability",
        "критер",
        "оцен",
        "стоим",
        "цена",
        "надёж",
        "надеж",
    )

    table_count = 0
    for index, line in enumerate(lines[:-1]):
        if "|" not in line or not _is_markdown_table_separator(lines[index + 1]):
            continue

        headers = _markdown_table_cells(line)
        data_rows = 0
        for data_line in lines[index + 2 :]:
            if "|" not in data_line or _is_markdown_table_separator(data_line):
                break
            cells = _markdown_table_cells(data_line)
            if any(cell for cell in cells):
                data_rows += 1

        table_count += 1
        has_rank = _header_has_any(headers, rank_headers)
        has_candidate = _header_has_any(headers, candidate_headers)
        has_decision = _header_has_any(headers, decision_headers)
        has_risk = _header_has_any(headers, risk_headers)
        has_criteria = _header_has_any(headers, criteria_headers)

        table_signals: list[str] = []
        if data_rows >= 2 and has_candidate:
            if has_rank and (has_decision or has_risk or has_criteria):
                table_signals.append("ranked_table")
            if has_risk:
                table_signals.append("risk_matrix")
            if sum([has_decision, has_risk, has_criteria, has_rank]) >= 2:
                table_signals.append("decision_table")

        if table_signals:
            signals.extend(signal for signal in table_signals if signal not in signals)
            matched_tables.append(
                {
                    "headers": headers,
                    "data_rows": data_rows,
                    "signals": table_signals,
                }
            )

    return {
        "passed": bool(signals),
        "signals": signals,
        "table_count": table_count,
        "matched_tables": matched_tables,
    }


def inspect_deliverable_requirements(
    deliverable: str,
    report_markdown: str,
    *,
    payload: dict[str, Any],
    total_sources: int,
    total_findings: int,
) -> dict[str, Any]:
    text = str(deliverable or "").strip()
    lowered = text.lower()
    report = str(report_markdown or "")
    lines = [line.rstrip() for line in report.splitlines()]
    bullet_count = sum(
        1 for line in lines if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line)
    )
    pre_metadata_lines: list[str] = []
    for line in lines:
        if line.strip() == "## Metadata":
            break
        pre_metadata_lines.append(line)
    pre_metadata_bullet_count = sum(
        1
        for line in pre_metadata_lines
        if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line)
    )
    heading_count = sum(1 for line in lines if re.match(r"^#{1,6}\s+", line))
    comparison_signal_count = sum(
        1
        for needle in (
            " vs ",
            " compared ",
            " comparison",
            " compare",
            " contrast",
            " отличие",
            " отличия",
            " разница",
            " сравнение",
            " сравнить",
            " преимущества",
            " недостатки",
        )
        if needle in report.lower()
    )

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []

    if any(token in lowered for token in ("bullet", "спис", "list")):
        passed = pre_metadata_bullet_count >= 2
        checks.append(
            {
                "kind": "bullet_list",
                "passed": passed,
                "bullet_count": bullet_count,
                "pre_metadata_bullet_count": pre_metadata_bullet_count,
                "minimum_bullets": 2,
            }
        )
        if not passed:
            reasons.append("deliverable_bullet_list_unstructured")

    if any(token in lowered for token in ("overview", "обзор", "summary", "сводк")):
        passed = heading_count >= 1 or bullet_count >= 2
        checks.append(
            {
                "kind": "overview",
                "passed": passed,
                "heading_count": heading_count,
                "bullet_count": bullet_count,
            }
        )
        if not passed:
            reasons.append("deliverable_overview_outline_empty")

    if any(token in lowered for token in ("compar", "сравн", "сопостав")):
        evidence_units = max(int(total_sources or 0), int(total_findings or 0))
        comparative_structure = detect_comparative_structure(report)
        passed = evidence_units >= 2 and (
            comparison_signal_count >= 1 or bool(comparative_structure.get("passed"))
        )
        checks.append(
            {
                "kind": "comparative",
                "passed": passed,
                "comparison_signal_count": comparison_signal_count,
                "structure_signals": comparative_structure.get("signals") or [],
                "structure_table_count": comparative_structure.get("table_count") or 0,
                "matched_structures": comparative_structure.get("matched_tables") or [],
                "evidence_units": evidence_units,
                "minimum_evidence_units": 2,
            }
        )
        if not passed:
            reasons.append("deliverable_comparative_shape_weak")

    return {
        "checks": checks,
        "reasons": reasons,
        "report_metrics": {
            "bullet_count": bullet_count,
            "pre_metadata_bullet_count": pre_metadata_bullet_count,
            "heading_count": heading_count,
            "comparison_signal_count": comparison_signal_count,
        },
    }


def inspect_deliverable_contract(
    report_markdown: str,
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    if not contract:
        return {
            "check": "deliverable_contract",
            "passed": True,
            "reasons": [],
            "skipped": True,
        }

    reasons: list[str] = []
    required_sections: list[str] = contract.get("required_sections") or []
    required_sheets: list[str] = contract.get("required_sheets") or []

    lines = report_markdown.splitlines()
    heading_lines = {}
    for line in lines:
        m = re.match(r"^#+\s+(.+?)\s*$", line)
        if m:
            heading_lines[m.group(1).strip().lower()] = m.group(1).strip()

    missing_sections: list[str] = []
    for section in required_sections:
        section_lower = str(section).strip().lower()
        if section_lower not in heading_lines:
            missing_sections.append(str(section).strip())
            reasons.append(f"required_section_missing:{section_lower}")

    sheet_missing: list[str] = []
    for sheet in required_sheets:
        sheet_lower = str(sheet).strip().lower()
        if sheet_lower not in {s.lower() for s in heading_lines.values()}:
            sheet_missing.append(str(sheet).strip())
            reasons.append(f"required_sheet_missing:{sheet_lower}")

    passed = not missing_sections and not sheet_missing

    return {
        "check": "deliverable_contract",
        "passed": passed,
        "reasons": reasons,
        "skipped": False,
        "required_sections": required_sections,
        "present_sections": list(heading_lines.keys()),
        "missing_sections": missing_sections,
        "required_sheets": required_sheets,
        "sheet_missing": sheet_missing,
    }


def validate_completion(
    task: ResearchTask,
    state: dict[str, Any],
    payload: dict[str, Any],
    *,
    phase: str,
    report_markdown: str,
    triggered_by: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    report_text = str(report_markdown or "").strip()
    working_memory = state.get("working_memory") or {}
    deliverable = str(working_memory.get("deliverable") or "").strip()
    total_sources = len(read_jsonl(task.sources_path))
    total_findings = len(read_jsonl(task.findings_path))

    if not report_text:
        reasons.append("final_report_empty")
    if working_memory.get("deliverable") is not None and not deliverable:
        reasons.append("deliverable_lost")
    if (
        total_sources <= 0
        and total_findings <= 0
        and triggered_by not in {"topic_saturated", "budget"}
    ):
        reasons.append("evidence_base_empty")
    budget_triggered = triggered_by == "budget"
    if (
        phase != "synthesize"
        and not bool(payload.get("should_complete"))
        and not budget_triggered
    ):
        reasons.append("phase_not_ready_for_completion")

    deliverable_validation = inspect_deliverable_requirements(
        deliverable,
        report_text,
        payload=payload,
        total_sources=total_sources,
        total_findings=total_findings,
    )
    reasons.extend(
        item
        for item in deliverable_validation.get("reasons", [])
        if item not in reasons
    )

    return {
        "passed": not reasons,
        "reasons": reasons,
        "triggered_by": triggered_by,
        "phase": phase,
        "report_bytes": len(report_text.encode("utf-8")) if report_text else 0,
        "deliverable_present": bool(deliverable),
        "deliverable_validation": deliverable_validation,
        "total_sources": total_sources,
        "total_findings": total_findings,
    }


def compose_finish_update_text(
    state: dict[str, Any],
    payload: dict[str, Any],
    next_status: str,
    *,
    iteration_count: int,
    final_report_path: str | None,
) -> str | None:
    title = state.get("title") or state.get("id") or "исследование"
    summary = payload.get("summary") or ""
    next_angle = payload.get("next_angle") or ""
    open_questions = payload.get("open_questions") or []
    findings = payload.get("findings") or []
    findings_block: list[str] = []
    for finding in findings[:3]:
        text = (finding.get("text") or "").strip()
        if text:
            findings_block.append(f"- {text}")

    if next_status == "complete":
        lines = [
            f"Исследование «{title}» завершено.",
            f"Итог: {summary}",
        ]
        if findings_block:
            lines.append("Ключевое:")
            lines.extend(findings_block)
        if final_report_path:
            lines.append("Финальный отчёт готов.")
        return "\n".join(lines)

    if next_status == "awaiting_review":
        lines = [
            f"Исследование «{title}» готово к ревью.",
            f"Итог: {summary}",
        ]
        if findings_block:
            lines.append("Ключевое:")
            lines.extend(findings_block)
        if final_report_path:
            lines.append("Финальный отчёт подготовлен и ждёт проверки.")
        return "\n".join(lines)

    notify = payload.get("notify_recommendation")
    if notify == "blocker":
        lines = [
            f"По исследованию «{title}» нужен твой ввод.",
            f"Сейчас: {summary}",
        ]
        if open_questions:
            lines.append("Что нужно уточнить:")
            lines.extend(f"- {question}" for question in open_questions[:3])
        elif next_angle:
            lines.append(f"Подвисший следующий шаг: {next_angle}")
        return "\n".join(lines)

    if notify in {"milestone", "auto"}:
        lines = [
            f"Апдейт по исследованию «{title}».",
            f"Прогресс: {summary}",
            f"Итераций: {iteration_count}",
        ]
        if findings_block:
            lines.append("Что уже нашлось:")
            lines.extend(findings_block)
        if next_angle:
            lines.append(f"Дальше копаю: {next_angle}")
        return "\n".join(lines)

    return None


def compose_failure_update_text(
    state: dict[str, Any], error_message: str, next_status: str
) -> str | None:
    title = state.get("title") or state.get("id") or "исследование"
    if next_status == "cancelled":
        return (
            f"Исследование «{title}» остановлено. Последний контекст: {error_message}"
        )
    if next_status == "failed":
        return f"Исследование «{title}» упёрлось в блокер и остановилось. Ошибка: {error_message}"
    return None


def should_notify(
    state: dict[str, Any], payload: dict[str, Any], next_status: str
) -> bool:
    policy = payload["notify_recommendation"]
    if policy == "silent":
        return False
    if policy in {"blocker", "final", "milestone"}:
        return True
    if next_status in {"complete", "failed", "cancelled"}:
        return True
    if not payload["meaningful_progress"]:
        return False
    meaningful_iterations = int(state["progress"].get("meaningful_iterations") or 0)
    milestone_every = int(state["delivery"].get("milestone_every_iterations") or 2)
    if milestone_every <= 0:
        milestone_every = 2
    return meaningful_iterations > 0 and meaningful_iterations % milestone_every == 0


def validate_candidate_final(
    task: ResearchTask,
    state: dict[str, Any],
    payload: dict[str, Any],
    *,
    report_markdown: str | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    all_passed = True
    if report_markdown is None:
        report_markdown = str(payload.get("final_report_markdown") or "")
    working_memory = state.get("working_memory") or {}
    deliverable_desc = str(working_memory.get("deliverable") or "").lower()

    finalization_check = _check_finalization_trace(
        payload.get("finalization"), report_markdown
    )
    findings.append(finalization_check)
    if not finalization_check["passed"]:
        all_passed = False

    artifact_check = inspect_candidate_artifacts(
        task_dir=task.task_dir,
        final_report_path=task.final_report_path,
        finalization=payload.get("finalization"),
        report_markdown=report_markdown,
    )
    findings.append(artifact_check)
    if not artifact_check["passed"]:
        all_passed = False

    primary_kind = str(
        (payload.get("finalization") or {}).get("primary_deliverable_kind") or ""
    ).strip().lower()
    package_final = (
        primary_kind == "package"
        and artifact_check["passed"]
        and any(
            item.get("format") == "package"
            for item in artifact_check.get("artifacts") or []
        )
    )

    if package_final:
        findings.append(
            {
                "check": "package_deliverable_quality",
                "passed": True,
                "reasons": [],
            }
        )
    else:
        deliverable_check = _check_deliverable_quality(report_markdown, deliverable_desc)
        findings.append(deliverable_check)
        if not deliverable_check["passed"]:
            all_passed = False

    draft_check = _check_no_draft_artifacts(task, report_markdown)
    findings.append(draft_check)
    if not draft_check["passed"]:
        all_passed = False

    human_readiness_check = _check_human_readiness(report_markdown)
    findings.append(human_readiness_check)
    if not human_readiness_check["passed"]:
        all_passed = False

    naming_check = _check_naming_hygiene(report_markdown)
    findings.append(naming_check)

    manifest_check = _check_delivery_manifest(state)
    findings.append(manifest_check)
    if not manifest_check["passed"]:
        all_passed = False

    contract_check = inspect_deliverable_contract(
        report_markdown, working_memory.get("contract")
    )
    findings.append(contract_check)
    if not contract_check["passed"]:
        all_passed = False

    reasons: list[str] = []
    for finding in findings:
        for reason in finding.get("reasons") or []:
            if reason not in reasons:
                reasons.append(reason)

    return {
        "passed": all_passed,
        "findings": findings,
        "reasons": reasons,
        "status": "passed" if all_passed else "rejected",
    }


def _check_finalization_trace(
    finalization: dict[str, Any] | None,
    report_markdown: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    trace = finalization or {}
    status = trace.get("status")
    if status in (None, "", "not_started"):
        reasons.append("finalization_not_started")
    elif status != "passed":
        reasons.append("finalization_not_passed")

    blocking_defects = trace.get("blocking_defects") or []
    if blocking_defects:
        reasons.append("finalization_blocking_defects")

    validation_evidence = trace.get("validation_evidence") or []
    if status == "passed" and not validation_evidence:
        reasons.append("primary_deliverable_unvalidated")

    candidate_artifacts = trace.get("candidate_artifacts") or []
    primary_kind = str(trace.get("primary_deliverable_kind") or "").strip().lower()
    report_text = str(report_markdown or "").strip()
    if status == "passed" and not candidate_artifacts and not report_text:
        reasons.append("primary_deliverable_missing")

    raw_blob_parts: list[str] = [primary_kind]
    for artifact in candidate_artifacts:
        artifact_path = str(artifact.get("path") or "")
        artifact_kind = str(artifact.get("kind") or "").strip().lower()
        package_candidate = (
            primary_kind == "package"
            and artifact_kind in {"package", "final_package"}
            and artifact_path.startswith("workspace/outputs/")
        )
        if not package_candidate:
            raw_blob_parts.extend(
                [
                    artifact_path,
                    artifact_kind,
                    str(artifact.get("note") or ""),
                ]
            )
    raw_blob = "\n".join(raw_blob_parts).lower()
    raw_signals = RAW_FINAL_ARTIFACT_SIGNALS
    if status == "passed" and any(signal in raw_blob for signal in raw_signals):
        reasons.append("raw_artifact_exposed_as_final")

    if status == "passed":
        if not str(trace.get("inferred_user_need") or "").strip():
            reasons.append("user_facing_quality_weak")
        if not primary_kind:
            reasons.append("primary_deliverable_missing")

    return {
        "check": "finalization_trace",
        "passed": not reasons,
        "reasons": reasons,
        "status": status,
        "primary_deliverable_kind": primary_kind or None,
        "candidate_artifacts_count": len(candidate_artifacts),
        "validation_evidence_count": len(validation_evidence),
        "blocking_defects_count": len(blocking_defects),
    }


def _check_delivery_manifest(state: dict[str, Any]) -> dict[str, Any]:
    from pathlib import Path

    delivery = state.get("delivery") or {}
    primary_file = delivery.get("primary_file")
    if not primary_file:
        return {
            "check": "delivery_manifest",
            "passed": True,
            "reasons": [],
        }

    path = Path(primary_file)
    if not path.is_absolute():
        task_dir = Path(state.get("artifacts", {}).get("task_dir", "."))
        path = task_dir / path

    passed = path.exists()
    reasons = [] if passed else ["primary_file_not_found"]

    return {
        "check": "delivery_manifest",
        "passed": passed,
        "reasons": reasons,
        "primary_file": primary_file,
    }


def _check_deliverable_quality(
    report_markdown: str,
    deliverable_desc: str,
) -> dict[str, Any]:
    report_lines = [
        line.strip() for line in report_markdown.splitlines() if line.strip()
    ]

    passed = True
    reasons: list[str] = []

    if not report_markdown.strip():
        passed = False
        reasons.append("final_report_empty")
    else:
        meaningful_lines = [
            line
            for line in report_lines
            if not line.startswith("#") and not line.startswith("```")
        ]
        if len(meaningful_lines) < 3:
            passed = False
            reasons.append("final_report_too_short")
        if len(report_markdown) < 200:
            passed = False
            reasons.append("final_report_truncated")

    if deliverable_desc and any(
        t in deliverable_desc for t in ("bullet", "список", "list")
    ):
        bullet_count = sum(
            1
            for line in report_lines
            if line.startswith("- ") or line.startswith("* ")
        )
        if bullet_count < 2:
            passed = False
            reasons.append("deliverable_bullet_list_missing")

    return {
        "check": "deliverable_quality",
        "passed": passed,
        "reasons": reasons,
    }


def _check_no_draft_artifacts(
    task: ResearchTask,
    report_markdown: str,
) -> dict[str, Any]:
    passed = True
    reasons: list[str] = []
    report_lower = report_markdown.lower()

    draft_signals = [
        ("use this draft", "contains_scaffolding_draft_instruction"),
        ("notes for finalization", "contains_finalization_notes"),
        ("not final", "contains_not_final_disclaimer"),
        ("use as draft", "contains_draft_usage_hint"),
        ("placeholder", "contains_placeholder"),
        ("todo:", "contains_todo_marker"),
        ("файл лежит", "user_must_find_file"),
        ("найди файл", "user_must_find_file"),
    ]

    for signal, reason in draft_signals:
        if signal in report_lower:
            passed = False
            reasons.append(reason)

    if not passed:
        return {
            "check": "draft_artifacts",
            "passed": False,
            "reasons": reasons,
        }

    return {
        "check": "draft_artifacts",
        "passed": True,
        "reasons": [],
    }


def _check_human_readiness(report_markdown: str) -> dict[str, Any]:
    passed = True
    reasons: list[str] = []

    if len(report_markdown) < 200:
        passed = False
        reasons.append("report_too_short_for_human")
    else:
        words = report_markdown.split()
        if len(words) < 30:
            passed = False
            reasons.append("report_insufficient_content")

    return {
        "check": "human_readiness",
        "passed": passed,
        "reasons": reasons,
    }


def _check_naming_hygiene(report_markdown: str) -> dict[str, Any]:
    passed = True
    reasons: list[str] = []
    report_lower = report_markdown.lower()

    if "-draft." in report_lower or "_draft." in report_lower:
        passed = False
        reasons.append("report_named_as_draft")

    return {
        "check": "naming_hygiene",
        "passed": passed,
        "reasons": reasons,
    }


CONFIDENCE_TIERS = {"high", "medium", "low", "reserve"}


def compute_confidence_score(
    finding: dict[str, Any],
    all_sources: list[dict[str, Any]],
    source_scores: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_urls = finding.get("source_urls") or []
    source_count = len(source_urls)
    kind = str(finding.get("kind") or "note").lower()

    if source_scores is None:
        source_scores = {}

    contributing_sources: list[dict[str, Any]] = []
    total_source_quality = 0.0
    for url in source_urls:
        src = next((s for s in all_sources if s.get("url") == url), None)
        if src:
            contributing_sources.append(src)
            score = source_scores.get(url, {})
            total_source_quality += float(score.get("quality_score", 0.5))

    if not contributing_sources:
        tier = "reserve"
        confidence = 0.0
        reason = "no_verifiable_source"
    elif source_count >= 3:
        avg_quality = total_source_quality / len(contributing_sources)
        tier = "high" if avg_quality >= 0.7 else "medium"
        confidence = min(0.95, 0.5 + avg_quality * 0.45)
        reason = "multi_source_corroborated"
    elif source_count == 2:
        avg_quality = total_source_quality / len(contributing_sources)
        tier = "high" if avg_quality >= 0.8 else "medium"
        confidence = min(0.85, 0.45 + avg_quality * 0.40)
        reason = "dual_source"
    else:
        single_score = total_source_quality if contributing_sources else 0.5
        tier = "medium" if single_score >= 0.6 else "low"
        confidence = min(0.7, 0.3 + single_score * 0.4)
        reason = "single_source"

    if kind in ("estimate", "hypothesis", "note"):
        if tier == "high":
            tier = "medium"
            confidence = round(confidence * 0.8, 3)
            reason = f"{reason};softened_by_kind"
        elif tier == "medium":
            tier = "low"
            confidence = round(confidence * 0.7, 3)
            reason = f"{reason};softened_by_kind"

    if finding.get("downgraded_to_reserve"):
        tier = "reserve"
        confidence = 0.1
        reason = "downgraded_to_reserve"

    return {
        "tier": tier,
        "confidence": round(confidence, 3),
        "source_count": source_count,
        "reason": reason,
        "provenance_refs": [
            {
                "url": src.get("url"),
                "title": src.get("title"),
            }
            for src in contributing_sources
        ],
    }


def compute_source_quality_score(source: dict[str, Any]) -> dict[str, Any]:
    url = str(source.get("url") or "")
    title = str(source.get("title") or "").lower()
    note = str(source.get("note") or "").lower()
    tags = [str(t).lower() for t in (source.get("tags") or [])]
    fetched_at = source.get("fetched_at") or source.get("recorded_at")
    all_tags = tags + [note]
    score = 0.5
    factors: list[str] = []

    official_signals = [
        "official",
        "government",
        "edu",
        "gov",
        "org.",
        "autoridade",
        "ministerio",
        "government",
        ".gov.",
        ".edu",
    ]
    if any(s in url.lower() or s in title for s in official_signals):
        score += 0.25
        factors.append("official_domain")

    user_gen_signals = [
        "forum",
        "reddit",
        "quora",
        ".stackex",
        "blogspot",
        "medium.com",
    ]
    if any(s in url.lower() for s in user_gen_signals):
        score -= 0.1
        factors.append("user_generated_platform")

    if any(s in all_tags for s in ("primary", "verified", "authoritative")):
        score += 0.15
        factors.append("authoritative_tag")

    if any(s in all_tags for s in ("stale", "outdated", "unverified")):
        score -= 0.2
        factors.append("stale_tag")

    if fetched_at:
        try:
            fetched_ts = parse_ts(fetched_at)
            if fetched_ts:
                age_days = (dt.datetime.now(dt.timezone.utc) - fetched_ts).days
                if age_days <= 30:
                    score += 0.1
                    factors.append("fresh_30d")
                elif age_days <= 90:
                    score += 0.05
                    factors.append("fresh_90d")
                elif age_days >= 365:
                    score -= 0.1
                    factors.append("stale_over_1yr")
        except (TypeError, ValueError, OverflowError):
            fetched_ts = None

    quality_score = max(0.0, min(1.0, score))

    tier: str
    if quality_score >= 0.75:
        tier = "authoritative"
    elif quality_score >= 0.55:
        tier = "standard"
    elif quality_score >= 0.35:
        tier = "weak"
    else:
        tier = "poor"

    return {
        "quality_score": round(quality_score, 3),
        "tier": tier,
        "factors": factors,
        "url": url,
        "title": source.get("title"),
    }


def enrich_findings_with_provenance(
    findings: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_scores: dict[str, dict[str, Any]] = {}
    for src in sources:
        url = src.get("url")
        if url:
            source_scores[str(url)] = compute_source_quality_score(src)

    enriched: list[dict[str, Any]] = []
    for finding in findings:
        confidence_info = compute_confidence_score(finding, sources, source_scores)
        enriched_finding = {**finding, "provenance": confidence_info}
        enriched.append(enriched_finding)
    return enriched


def render_confidence_badge(tier: str) -> str:
    symbols = {
        "high": "[●●●]",
        "medium": "[●●○]",
        "low": "[●○○]",
        "reserve": "[○○○]",
    }
    return symbols.get(tier, "[???]")


def build_revision_diff(
    old_state: dict[str, Any] | None,
    new_state: dict[str, Any],
) -> dict[str, Any]:
    old_review = (old_state or {}).get("review") or {}
    new_review = new_state.get("review") or {}
    old_revision = int(old_review.get("revision_count") or 0)
    new_revision = int(new_review.get("revision_count") or 0)

    old_final_path = (old_state or {}).get("artifacts", {}).get("final_report_path")
    new_final_path = new_state.get("artifacts", {}).get("final_report_path")
    final_report_changed = (
        old_final_path != new_final_path and new_final_path is not None
    )

    changes: list[str] = []
    if new_revision > old_revision:
        changes.append(f"revision_count:{old_revision}->{new_revision}")
    if final_report_changed:
        changes.append("final_report_updated")
    if new_review.get("status") != old_review.get("status") and new_review.get(
        "status"
    ):
        changes.append(
            f"review_status:{old_review.get('status')}->{new_review.get('status')}"
        )

    return {
        "revision_from": old_revision,
        "revision_to": new_revision,
        "changes": changes,
        "final_report_updated": final_report_changed,
    }


def build_evidence_gaps(state: dict[str, Any]) -> dict[str, Any]:
    working_memory = state.get("working_memory") or {}
    open_questions = working_memory.get("open_questions") or []
    finalization = state.get("finalization") or {}
    validation_findings = finalization.get("last_validation_findings") or []
    failed_checks = [f.get("check") for f in validation_findings if not f.get("passed")]
    saturation = state.get("saturation") or {}
    low_yield_streak = int(saturation.get("consecutive_low_yield") or 0)
    budget = state.get("budget") or {}
    max_iter = int(budget.get("max_iterations") or 0)
    progress = state.get("progress") or {}
    iter_count = int(progress.get("iteration_count") or 0)
    budget_headroom = max(0, max_iter - iter_count) if max_iter > 0 else None

    evidence_gaps: list[str] = []
    for q in open_questions:
        evidence_gaps.append(f"open_question:{q}")
    for check in failed_checks:
        evidence_gaps.append(f"failed_validation:{check}")
    if low_yield_streak >= 1:
        evidence_gaps.append(f"low_yield_streak:{low_yield_streak}")
    if budget_headroom is not None and budget_headroom <= 1:
        evidence_gaps.append("budget_almost_exhausted")

    high_risk_assumptions: list[str] = []
    if low_yield_streak >= 2:
        high_risk_assumptions.append("topic_saturation_heuristic_may_be_wrong")
    if failed_checks:
        high_risk_assumptions.append(
            f"deliverable_validation_has_failures:{','.join(failed_checks)}"
        )
    if budget_headroom == 0 and iter_count > 0:
        high_risk_assumptions.append("hard_budget_limit_reached_mid_research")

    recommended_next_checks: list[str] = []
    if failed_checks:
        recommended_next_checks.append(
            f"address_failed_validations:{','.join(failed_checks)}"
        )
    if open_questions:
        recommended_next_checks.append("resolve_open_questions_before_finalizing")
    if evidence_gaps:
        recommended_next_checks.append("review_evidence_gaps_before_presenting_to_user")

    return {
        "evidence_gaps": evidence_gaps,
        "high_risk_assumptions": high_risk_assumptions,
        "recommended_next_checks": recommended_next_checks,
        "has_open_gaps": len(evidence_gaps) > 0,
    }
