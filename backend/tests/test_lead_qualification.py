"""Focused tests for ABC Energy Solutions lead qualification."""

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.lead_qualification import LeadQualificationFlow, LeadState
from app.lead_qualification.estimator import estimate_usage_from_square_footage
from app.lead_qualification.rules import classify_lead
from app.lead_qualification.state import LeadSlot, SlotStatus


def test_industrial_high_usage_expiring_soon_is_tier_1():
    state = LeadState(
        business_segment=LeadSlot(value="industrial", status=SlotStatus.CONFIRMED),
        annual_usage_mwh=LeadSlot(value=650, status=SlotStatus.CONFIRMED),
        expiry_months=LeadSlot(value=5, status=SlotStatus.CONFIRMED),
        has_provider=LeadSlot(value=True, status=SlotStatus.CONFIRMED),
    )

    _, classification = classify_lead(state)

    assert classification.tier == "Tier 1"
    assert classification.matched_rule == "industrial_high_usage_expiring_soon"


def test_industrial_mid_usage_new_building_is_tier_2():
    state = LeadState(
        business_segment=LeadSlot(value="industrial", status=SlotStatus.CONFIRMED),
        annual_usage_mwh=LeadSlot(value=250, status=SlotStatus.CONFIRMED),
        expiry_months=LeadSlot(value=11, status=SlotStatus.CONFIRMED),
        building_age_years=LeadSlot(value=4, status=SlotStatus.CONFIRMED),
        has_provider=LeadSlot(value=True, status=SlotStatus.CONFIRMED),
    )

    _, classification = classify_lead(state)

    assert classification.tier == "Tier 2"
    assert classification.matched_rule == "industrial_mid_usage_new_building"


def test_commercial_high_usage_month_to_month_is_tier_1():
    state = LeadState(
        business_segment=LeadSlot(value="commercial", status=SlotStatus.CONFIRMED),
        annual_usage_mwh=LeadSlot(value=70, status=SlotStatus.CONFIRMED),
        contract_status=LeadSlot(value="month_to_month", status=SlotStatus.CONFIRMED),
        has_provider=LeadSlot(value=True, status=SlotStatus.CONFIRMED),
    )

    _, classification = classify_lead(state)

    assert classification.tier == "Tier 1"
    assert classification.matched_rule == "commercial_high_usage_month_to_month"


def test_commercial_mid_usage_fixed_new_building_is_tier_3():
    state = LeadState(
        business_segment=LeadSlot(value="commercial", status=SlotStatus.CONFIRMED),
        annual_usage_mwh=LeadSlot(value=35, status=SlotStatus.CONFIRMED),
        contract_status=LeadSlot(value="fixed_term", status=SlotStatus.CONFIRMED),
        building_age_years=LeadSlot(value=1, status=SlotStatus.CONFIRMED),
        has_provider=LeadSlot(value=True, status=SlotStatus.CONFIRMED),
    )

    _, classification = classify_lead(state)

    assert classification.tier == "Tier 3"
    assert classification.matched_rule == "commercial_mid_usage_fixed_new_building"


def test_no_current_provider_is_tier_1():
    state = LeadState(has_provider=LeadSlot(value=False, status=SlotStatus.CONFIRMED))

    _, classification = classify_lead(state)

    assert classification.tier == "Tier 1"
    assert classification.matched_rule == "any_no_current_provider"


def test_no_current_electricity_provider_phrase_is_tier_1():
    result = LeadQualificationFlow().run_turn(
        "Prospect has no current electricity provider. Commercial warehouse, "
        "around 40 MWh annually, fixed term details unknown."
    )

    assert result.state.has_provider.value is False
    assert result.classification.tier == "Tier 1"
    assert result.classification.matched_rule == "any_no_current_provider"
    assert result.trace["next_question"] is None


def test_square_footage_fallback_estimates_usage_when_unknown():
    state = LeadState(
        business_segment=LeadSlot(value="commercial", status=SlotStatus.CONFIRMED),
        square_footage=LeadSlot(value=5000, status=SlotStatus.CONFIRMED),
    )

    estimated = estimate_usage_from_square_footage(state)

    assert estimated.annual_usage_mwh.value == 60
    assert estimated.annual_usage_mwh.status == SlotStatus.INFERRED


def test_missing_field_planning_asks_for_provider_first():
    result = LeadQualificationFlow().run_turn("Hi, I want to see if ABC can help.")

    assert result.classification.tier == "Not Ready"
    assert result.missing_fields[0] == "business_segment"
    assert result.trace["next_question"] == "Do you currently have an electricity provider?"


def test_simple_multi_turn_flow_reuses_state_and_classifies():
    flow = LeadQualificationFlow()
    first = flow.run_turn("We are a commercial office, 6,000 square feet.")

    second = flow.run_turn(
        "We have a provider and are month-to-month. The building is 3 years old.",
        first.state,
    )

    assert second.state.annual_usage_mwh.value == 72
    assert second.state.annual_usage_mwh.status == SlotStatus.INFERRED
    assert second.classification.tier == "Tier 1"
    assert second.classification.matched_rule == "commercial_high_usage_month_to_month"


@pytest.mark.anyio
async def test_public_lead_turn_endpoint(client: AsyncClient):
    response = await client.post(
        f"{settings.API_V1_STR}/lead/turn",
        json={
            "message": (
                "Industrial plant, 650 MWh annually, provider in place, "
                "contract expires in 5 months."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"]
    assert data["classification"]["tier"] == "Tier 1"
    assert data["state"]["has_provider"]["value"] is True
    assert data["state"]["final_tier"]["value"] == "Tier 1"
    assert data["trace"]["next_question"] is None
