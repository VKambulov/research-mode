from __future__ import annotations

from research_mode_lifecycle_helpers import compute_source_quality_score


def test_source_quality_does_not_use_title_or_note_keywords() -> None:
    source = {
        "url": "https://example.com/post",
        "title": "official government report",
        "note": "verified primary source",
    }

    result = compute_source_quality_score(source)

    assert "official_domain" not in result["factors"]
    assert "authoritative_tag" not in result["factors"]


def test_source_quality_uses_structured_tags_and_domain() -> None:
    source = {
        "url": "https://agency.gov/report",
        "tags": ["official_source", "primary_source"],
    }

    result = compute_source_quality_score(source)

    assert "official_domain" in result["factors"]
    assert "authoritative_tag" in result["factors"]


def test_source_quality_ignores_uncontrolled_tag_text() -> None:
    source = {
        "url": "https://example.com/report",
        "tags": ["this says verified but is not a controlled tag"],
    }

    result = compute_source_quality_score(source)

    assert "authoritative_tag" not in result["factors"]
