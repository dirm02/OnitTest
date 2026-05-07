"""Eval fixtures for lead extraction and deterministic qualification rules."""

import json
from pathlib import Path

import pytest

from app.lead_qualification import LeadQualificationFlow
from app.lead_qualification.extractor import extract_lead_updates_with_trace
from app.lead_qualification.state import LeadSlot, LeadState, SlotStatus

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lead_eval_cases.json"


@pytest.fixture(autouse=True)
def disable_live_llm(monkeypatch):
    """Keep eval tests offline even when a developer has GOOGLE_API_KEY set."""
    monkeypatch.setattr("app.core.config.settings.GOOGLE_API_KEY", "")


def _load_cases() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["id"])
def test_eval_cases_use_deterministic_fallback_and_matrix(case: dict):
    result = LeadQualificationFlow().run_turn(case["message"])

    for field, expected_value in case["expected_state"].items():
        assert getattr(result.state, field).value == expected_value

    assert result.classification.tier == case["expected_tier"]
    assert result.classification.matched_rule == case["expected_rule"]
    assert result.trace["extraction"]["source"] == "deterministic_regex"
    assert result.trace["extraction"]["llm_enabled"] is False


def test_optional_llm_path_fills_unknown_fields_without_overriding_deterministic_fields(
    monkeypatch,
):
    def fake_llm_extract(message: str):
        del message
        llm_state = LeadState(
            business_segment=LeadSlot(value="industrial", status=SlotStatus.CONFIRMED),
            building_age_years=LeadSlot(value=1, status=SlotStatus.CONFIRMED),
        )

        class FakeResult:
            updates = llm_state
            model = "gemini-test"
            fields = ["business_segment", "building_age_years"]

        return FakeResult()

    monkeypatch.setattr(
        "app.lead_qualification.llm_extractor.extract_lead_updates_llm_sync",
        fake_llm_extract,
    )

    updates, trace = extract_lead_updates_with_trace(
        "Commercial warehouse, 40 MWh annually, provider in place, fixed term.",
    )

    assert updates.business_segment.value == "commercial"
    assert updates.building_age_years.value == 1
    assert trace["source"] == "deterministic_regex+gemini"
    assert trace["llm_enabled"] is True
    assert trace["llm_fields"] == ["business_segment", "building_age_years"]
