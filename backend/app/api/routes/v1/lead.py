"""Public ABC Energy Solutions lead qualification endpoint."""

from fastapi import APIRouter

from app.lead_qualification import LeadQualificationFlow
from app.schemas.lead import LeadTurnRequest, LeadTurnResponse, new_lead_session_id

router = APIRouter()
flow = LeadQualificationFlow()


@router.post("/turn", response_model=LeadTurnResponse)
async def qualify_lead_turn(payload: LeadTurnRequest) -> LeadTurnResponse:
    """Run one deterministic lead qualification turn without authentication."""
    result = flow.run_turn(payload.message, payload.state)
    return LeadTurnResponse(
        session_id=payload.session_id or new_lead_session_id(),
        response=result.response,
        state=result.state,
        missing_fields=result.missing_fields,
        classification=result.classification,
        trace=result.trace,
    )
