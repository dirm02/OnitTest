"""Strategic Lead Matrix rules for ABC Energy Solutions."""

from pydantic import BaseModel

from app.lead_qualification.state import LeadSlot, LeadState, SlotStatus


class LeadClassification(BaseModel):
    """Result of applying the deterministic Strategic Lead Matrix."""

    tier: str
    ready: bool
    reason: str
    matched_rule: str | None = None


def classify_lead(state: LeadState) -> tuple[LeadState, LeadClassification]:
    """Classify the lead using the Strategic Lead Matrix."""
    segment = state.business_segment.value
    usage = state.annual_usage_mwh.value
    contract_status = state.contract_status.value
    expiry = state.expiry_months.value
    has_provider = state.has_provider.value
    building_age = state.building_age_years.value

    if state.has_provider.is_known and has_provider is False:
        return _with_classification(
            state,
            LeadClassification(
                tier="Tier 1",
                ready=True,
                reason="Prospect has no current provider.",
                matched_rule="any_no_current_provider",
            ),
        )

    if segment == "industrial" and usage is not None and expiry is not None:
        if usage > 500 and expiry < 6:
            return _with_classification(
                state,
                LeadClassification(
                    tier="Tier 1",
                    ready=True,
                    reason="Industrial usage is above 500 MWh and contract expires within 6 months.",
                    matched_rule="industrial_high_usage_expiring_soon",
                ),
            )
        if (
            usage >= 100
            and usage <= 500
            and expiry < 12
            and building_age is not None
            and building_age < 5
        ):
            return _with_classification(
                state,
                LeadClassification(
                    tier="Tier 2",
                    ready=True,
                    reason=(
                        "Industrial usage is 100-500 MWh, contract expires within 12 "
                        "months, and building age is under 5 years."
                    ),
                    matched_rule="industrial_mid_usage_new_building",
                ),
            )

    if segment == "commercial" and usage is not None:
        if usage > 50 and contract_status == "month_to_month":
            return _with_classification(
                state,
                LeadClassification(
                    tier="Tier 1",
                    ready=True,
                    reason="Commercial usage is above 50 MWh and contract is month-to-month.",
                    matched_rule="commercial_high_usage_month_to_month",
                ),
            )
        if (
            usage >= 20
            and usage <= 50
            and contract_status == "fixed_term"
            and building_age is not None
            and building_age < 2
        ):
            return _with_classification(
                state,
                LeadClassification(
                    tier="Tier 3",
                    ready=True,
                    reason=(
                        "Commercial usage is 20-50 MWh, contract is fixed term, "
                        "and building age is under 2 years."
                    ),
                    matched_rule="commercial_mid_usage_fixed_new_building",
                ),
            )

    missing = state.missing_fields()
    if missing:
        return _with_classification(
            state,
            LeadClassification(
                tier="Not Ready",
                ready=False,
                reason=f"Need more information: {', '.join(missing)}.",
            ),
        )

    return _with_classification(
        state,
        LeadClassification(
            tier="Manual Review",
            ready=True,
            reason="Lead is complete but does not match a Strategic Lead Matrix tier.",
        ),
    )


def _with_classification(
    state: LeadState,
    classification: LeadClassification,
) -> tuple[LeadState, LeadClassification]:
    updated = state.model_copy(deep=True)
    updated.final_tier = LeadSlot(value=classification.tier, status=SlotStatus.CONFIRMED)
    updated.reason = LeadSlot(value=classification.reason, status=SlotStatus.CONFIRMED)
    return updated, classification
