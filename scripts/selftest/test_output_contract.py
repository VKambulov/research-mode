from __future__ import annotations

import json
from pathlib import Path

from .helpers import assert_eq, assert_in, json_out, run


def test_deliverable_kind_cli_sets_output_contract(root: Path) -> None:
    created = json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "contract-kind-create",
            "--goal",
            "Prepare a report",
            "--deliverable",
            "自由文本，不用于判断格式",
            "--deliverable-kind",
            "pdf_report",
            "--skip-preflight",
        )
    )
    assert_eq(created["status"], "created", "create status")

    state = json.loads(
        (root / "contract-kind-create" / "state.json").read_text(encoding="utf-8")
    )
    working = state.get("working_memory") or {}
    contract = working.get("output_contract") or {}
    assert_eq(
        working.get("deliverable"),
        "自由文本，不用于判断格式",
        "deliverable remains display text",
    )
    assert_eq(contract.get("kind"), "pdf_report", "deliverable kind is structured")


def test_set_deliverable_kind_updates_contract_without_text(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "contract-kind-setter",
            "--goal",
            "Prepare a report",
            "--deliverable",
            "Keep this free-text hint",
            "--skip-preflight",
        )
    )

    updated = json_out(
        run(
            "set-deliverable",
            "--root",
            str(root),
            "--id",
            "contract-kind-setter",
            "--kind",
            "xlsx",
        )
    )
    assert_eq(updated["deliverable"], "Keep this free-text hint", "hint remains")
    assert_eq(
        updated["output_contract"]["kind"],
        "xlsx",
        "set-deliverable --kind should update output contract",
    )

    state = json.loads(
        (root / "contract-kind-setter" / "state.json").read_text(encoding="utf-8")
    )
    working = state.get("working_memory") or {}
    assert_eq(working.get("deliverable"), "Keep this free-text hint", "state hint remains")
    assert_eq(
        working.get("output_contract", {}).get("kind"),
        "xlsx",
        "state contract kind should be structured",
    )


def test_invalid_deliverable_kind_exits_nonzero(root: Path) -> None:
    result = run(
        "create",
        "--root",
        str(root),
        "--id",
        "invalid-contract-kind",
        "--goal",
        "Prepare a report",
        "--deliverable-kind",
        "spreadsheet",
        "--skip-preflight",
        check=False,
    )

    assert_eq(result.returncode, 2, "invalid deliverable kind should fail")
    assert_in("invalid choice", result.stderr, "argparse should explain invalid kind")
    assert_in("xlsx", result.stderr, "allowed enum values should be visible")


def test_free_text_remains_available_to_worker_and_surfaces(root: Path) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "free-text-preserved",
            "--goal",
            "请分析供应商风险，并保留这些原始说明给执行代理。",
            "--deliverable",
            "Свободное описание результата: сравнительная записка для чтения человеком.",
            "--constraint",
            "Не терять пользовательские формулировки.",
            "--instruction",
            "Сохрани контекст для worker-а.",
            "--skip-preflight",
        )
    )

    lease = json_out(run("begin", "--root", str(root), "--id", "free-text-preserved"))
    guidance_blob = "\n".join(lease.get("execution_guidance") or [])
    input_layer = lease.get("input_layer") or {}

    assert_eq(
        input_layer.get("deliverable"),
        "Свободное описание результата: сравнительная записка для чтения человеком.",
        "begin payload should still carry free-text deliverable",
    )
    assert_in(
        "requested deliverable",
        guidance_blob.lower(),
        "guidance should still mention requested deliverable",
    )

    summary_text = run(
        "summary",
        "--root",
        str(root),
        "--id",
        "free-text-preserved",
        "--format",
        "text",
    ).stdout
    assert_in(
        "Свободное описание результата",
        summary_text,
        "summary should still render free-text deliverable",
    )
