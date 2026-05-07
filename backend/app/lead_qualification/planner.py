"""Question planning and response generation for one lead turn."""

from app.lead_qualification.rules import LeadClassification
from app.lead_qualification.state import LeadState

QUESTION_BY_FIELD = {
    "has_provider": "Do you currently have an electricity provider?",
    "business_segment": "Is your site industrial or commercial?",
    "annual_usage_mwh": "What is your annual electricity usage in MWh? Square footage works too if you do not know it.",
    "square_footage": "What is the approximate square footage of the site?",
    "contract_status": "Is your current contract month-to-month or fixed term?",
    "expiry_months": "How many months are left before the current contract expires?",
    "building_age_years": "How old is the building in years?",
}

QUESTION_ORDER = [
    "has_provider",
    "business_segment",
    "annual_usage_mwh",
    "square_footage",
    "contract_status",
    "expiry_months",
    "building_age_years",
]


def plan_next_question(state: LeadState) -> str | None:
    """Pick the next missing lead field to ask for."""
    if state.final_tier.is_known and state.final_tier.value != "Not Ready":
        return None

    missing = set(state.missing_fields())
    for field in QUESTION_ORDER:
        if field in missing:
            return QUESTION_BY_FIELD[field]
    return None


def build_response(classification: LeadClassification, next_question: str | None) -> str:
    """Create the assistant response for a lead turn."""
    if classification.tier.startswith("Tier"):
        return (
            f"{classification.tier}: {classification.reason} "
            "ABC Energy Solutions should prioritize this lead for follow-up."
        )
    if next_question:
        return f"Thanks, I have updated the lead profile. {next_question}"
    return f"{classification.tier}: {classification.reason}"
