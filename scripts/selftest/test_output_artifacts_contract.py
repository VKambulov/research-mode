from __future__ import annotations

import pytest

from research_mode_payloads import normalize_output_contract
from research_mode_utils import ValidationError


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
