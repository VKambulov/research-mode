from __future__ import annotations

import pytest

from research_mode_payloads import normalize_output_contract
from research_mode_utils import ValidationError

from .helpers import json_out, run


def test_output_contract_accepts_open_media_type() -> None:
    contract = normalize_output_contract(
        {
            "outputs": [
                {
                    "id": "report",
                    "role": "primary_deliverable",
                    "required": True,
                    "media_type": "application/x-vendor-custom-report",
                }
            ]
        }
    )

    assert contract["outputs"] == [
        {
            "id": "report",
            "role": "primary_deliverable",
            "required": True,
            "media_type": "application/x-vendor-custom-report",
        }
    ]


def test_output_contract_supports_multiple_required_outputs() -> None:
    contract = normalize_output_contract(
        {
            "outputs": [
                {
                    "id": "report",
                    "role": "primary_deliverable",
                    "media_type": "application/pdf",
                },
                {
                    "id": "sources",
                    "role": "supporting_deliverable",
                    "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                },
            ]
        }
    )

    assert [item["id"] for item in contract["outputs"]] == ["report", "sources"]
    assert all(item["required"] is True for item in contract["outputs"])


def test_output_contract_rejects_unsafe_output_id() -> None:
    with pytest.raises(ValidationError, match="output id"):
        normalize_output_contract(
            {
                "outputs": [
                    {"id": "../report", "role": "primary_deliverable"},
                ]
            }
        )


def test_output_contract_rejects_duplicate_output_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate output id"):
        normalize_output_contract(
            {
                "outputs": [
                    {"id": "report", "role": "primary_deliverable"},
                    {"id": "report", "role": "supporting_deliverable"},
                ]
            }
        )


def test_output_contract_parses_required_false() -> None:
    contract = normalize_output_contract(
        {
            "outputs": [
                {"id": "report", "role": "primary_deliverable"},
                {
                    "id": "appendix",
                    "role": "supporting_deliverable",
                    "required": False,
                },
            ]
        }
    )

    assert contract["outputs"][1]["required"] is False


def test_output_contract_rejects_multiple_primary_outputs() -> None:
    with pytest.raises(ValidationError, match="exactly one primary_deliverable"):
        normalize_output_contract(
            {
                "outputs": [
                    {"id": "report", "role": "primary_deliverable"},
                    {"id": "appendix", "role": "primary_deliverable"},
                ]
            }
        )


def test_output_contract_keeps_legacy_kind_but_prefers_outputs() -> None:
    contract = normalize_output_contract(
        {
            "kind": "pdf_report",
            "outputs": [
                {
                    "id": "report",
                    "role": "primary_deliverable",
                    "media_type": "application/pdf",
                }
            ],
        }
    )

    assert contract["kind"] == "pdf_report"
    assert contract["outputs"][0]["id"] == "report"


def test_create_accepts_repeatable_output_specs(root) -> None:
    created = json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            "multi-output-cli",
            "--goal",
            "Prepare report and source workbook",
            "--output",
            "id=report,role=primary_deliverable,media_type=application/pdf",
            "--output",
            "id=sources,role=supporting_deliverable,media_type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )

    outputs = created["working_memory"]["output_contract"]["outputs"]
    assert [item["id"] for item in outputs] == ["report", "sources"]


def test_set_deliverable_accepts_output_spec(root) -> None:
    run("create", "--root", str(root), "--id", "set-output-cli", "--goal", "Prepare report")

    updated = json_out(
        run(
            "set-deliverable",
            "--root",
            str(root),
            "--id",
            "set-output-cli",
            "--output",
            "id=report,role=primary_deliverable,media_type=application/pdf",
        )
    )

    assert updated["working_memory"]["output_contract"]["outputs"][0]["id"] == "report"
