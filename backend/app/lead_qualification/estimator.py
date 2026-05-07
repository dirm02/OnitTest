"""Square-footage fallback usage estimator."""

from app.lead_qualification.state import LeadSlot, LeadState, SlotStatus

MWH_PER_SQUARE_FOOT_BY_SEGMENT = {
    # Simple deterministic PoC factors, not an engineering audit. They keep
    # the flow moving when a prospect knows site size but not annual MWh.
    "industrial": 0.025,
    "commercial": 0.012,
}
DEFAULT_MWH_PER_SQUARE_FOOT = 0.015


def estimate_usage_from_square_footage(state: LeadState) -> LeadState:
    """Infer annual usage from square footage when usage is unknown."""
    if state.annual_usage_mwh.is_known or not state.square_footage.is_known:
        return state

    segment = state.business_segment.value if state.business_segment.is_known else None
    factor = MWH_PER_SQUARE_FOOT_BY_SEGMENT.get(segment or "", DEFAULT_MWH_PER_SQUARE_FOOT)
    estimated_usage = round((state.square_footage.value or 0) * factor, 2)

    updated = state.model_copy(deep=True)
    updated.annual_usage_mwh = LeadSlot(value=estimated_usage, status=SlotStatus.INFERRED)
    return updated
