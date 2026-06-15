from __future__ import annotations

import json
import os
import subprocess
import sys
import copy
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SCRIPTS_DIR / "research_mode.py"
FAKE_BIN_DIR = Path(__file__).resolve().parent / "fake_bin"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def run(
    *args: str, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    cmd = ["python3", str(SCRIPT), *args]
    env = os.environ.copy()
    env["PATH"] = f"{FAKE_BIN_DIR}{os.pathsep}{env.get('PATH', '')}"
    if "--root" in args:
        root_index = args.index("--root") + 1
        if root_index < len(args):
            env["RESEARCH_MODE_FAKE_OPENCLAW_STATE"] = str(
                Path(args[root_index]) / ".fake-openclaw-state.json"
            )
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        check=check,
        env=env,
    )


def json_out(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def assert_eq(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def assert_true(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def assert_in(needle, haystack, message: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"{message}: {needle!r} not found in {haystack!r}")


_DEFAULT_REPORT_MARKDOWN = (
    "# Final Report\n\n"
    "## Summary\n\n"
    "This is a comprehensive final report with substantial content for review. "
    "It provides key findings and details that meet quality requirements for "
    "human readability and completeness.\n\n"
    "Second paragraph adds more context, methodological detail, and supporting "
    "explanation so the artifact is ready for review.\n\n"
    "## Key Findings\n\n"
    "- Finding 1: Important discovery supported by evidence.\n"
    "- Finding 2: Another key insight from the research.\n\n"
    "## Conclusion\n\n"
    "The research is complete and ready for delivery with all key findings documented."
)

_DEFAULT_FINALIZATION = {
    "status": "passed",
    "inferred_user_need": "A readable final result for operator review.",
    "intended_recipient": "operator",
    "primary_deliverable_kind": "markdown_report",
    "internal_artifacts": [
        {"path": "iterations/001.md", "kind": "iteration_notes", "note": "Internal iteration record."}
    ],
    "candidate_artifacts": [
        {"path": "final-report.md", "kind": "markdown_report", "note": "Human-readable final report."}
    ],
    "blocking_defects": [],
    "nonblocking_defects": [],
    "revisions": [
        {"summary": "Prepared the accumulated findings as a reader-facing report."}
    ],
    "validation_evidence": [
        {"kind": "markdown_review", "summary": "Checked structure and readability."}
    ],
}


def human_ready_finalization(
    *,
    primary_deliverable_kind: str = "markdown_report",
    candidate_path: str = "final-report.md",
) -> dict:
    trace = copy.deepcopy(_DEFAULT_FINALIZATION)
    trace["primary_deliverable_kind"] = primary_deliverable_kind
    trace["candidate_artifacts"] = [
        {
            "path": candidate_path,
            "kind": primary_deliverable_kind,
            "note": "Human-readable final deliverable.",
        }
    ]
    return trace


def finish_to_awaiting_review(
    root: Path,
    task_id: str,
    lease: dict,
    *,
    markdown: str | None = None,
    sources: list | None = None,
    findings: list | None = None,
) -> dict:
    """Write a passing result file and finish iteration, expecting awaiting_review."""
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
                "sources": sources or [{"title": "src"}],
                "findings": findings or [{"kind": "fact", "text": "finding"}],
                "notify_recommendation": "final",
                "should_complete": True,
                "final_report_markdown": markdown or _DEFAULT_REPORT_MARKDOWN,
                "finalization": human_ready_finalization(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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
            lease["run_id"],
            "--result-file",
            str(result_file),
        )
    )
