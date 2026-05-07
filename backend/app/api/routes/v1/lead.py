"""Public ABC Energy Solutions lead qualification endpoints."""

import logging

from fastapi import APIRouter

from app.api.deps import DBSession
from app.lead_qualification import LeadQualificationFlow
from app.repositories.lead import append_turn, list_sessions
from app.schemas.lead import (
    LeadSessionsResponse,
    LeadSessionSummary,
    LeadTurnRequest,
    LeadTurnResponse,
    new_lead_session_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()
flow = LeadQualificationFlow()


@router.post("/turn", response_model=LeadTurnResponse)
async def qualify_lead_turn(payload: LeadTurnRequest, db: DBSession) -> LeadTurnResponse:
    """Run one lead qualification turn and persist it when storage is available."""
    session_id = payload.session_id or new_lead_session_id()
    result = flow.run_turn(payload.message, payload.state)

    response = LeadTurnResponse(
        session_id=session_id,
        response=result.response,
        state=result.state,
        missing_fields=result.missing_fields,
        classification=result.classification,
        trace=result.trace,
    )

    try:
        await append_turn(
            db,
            session_id=session_id,
            user_message=payload.message,
            assistant_response=result.response,
            state=result.state.model_dump(mode="json"),
            classification=result.classification.model_dump(mode="json"),
            trace=result.trace,
            source=_session_source(result.trace),
        )
    except Exception:
        logger.exception("Failed to persist lead qualification turn")

    return response


@router.get("/sessions", response_model=LeadSessionsResponse)
async def get_lead_sessions(db: DBSession, limit: int = 20, skip: int = 0) -> LeadSessionsResponse:
    """Return recent saved lead qualification sessions."""
    try:
        sessions = await list_sessions(db, skip=skip, limit=min(limit, 100))
    except Exception:
        logger.exception("Failed to list lead qualification sessions")
        return LeadSessionsResponse(items=[])

    return LeadSessionsResponse(
        items=[
            LeadSessionSummary(
                session_id=session.session_id,
                latest_state=session.latest_state,
                final_tier=session.final_tier,
                matched_rule=session.matched_rule,
                reason=session.reason,
                source=session.source,
                created_at=session.created_at.isoformat() if session.created_at else None,
                updated_at=(
                    session.updated_at.isoformat()
                    if session.updated_at
                    else session.created_at.isoformat()
                    if session.created_at
                    else None
                ),
            )
            for session in sessions
        ]
    )


def _session_source(trace: dict) -> str:
    extraction = trace.get("extraction") if isinstance(trace, dict) else None
    if isinstance(extraction, dict) and extraction.get("llm_enabled"):
        return "gemini+pocketflow"
    return "pocketflow"
