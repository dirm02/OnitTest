"""Public schemas for lead qualification endpoints."""

from typing import Any
from uuid import uuid4

from pydantic import Field

from app.lead_qualification.rules import LeadClassification
from app.lead_qualification.state import LeadState
from app.schemas.base import BaseSchema


class LeadTurnRequest(BaseSchema):
    """Request payload for one lead qualification turn."""

    session_id: str | None = None
    message: str = Field(min_length=1)
    state: LeadState | None = None


class LeadTurnResponse(BaseSchema):
    """Response payload for one lead qualification turn."""

    session_id: str
    response: str
    state: LeadState
    missing_fields: list[str]
    classification: LeadClassification
    trace: dict[str, Any]


class LeadSessionSummary(BaseSchema):
    """Saved lead qualification session summary."""

    session_id: str
    latest_state: LeadState
    final_tier: str | None = None
    matched_rule: str | None = None
    reason: str | None = None
    source: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class LeadSessionsResponse(BaseSchema):
    """Response payload for saved lead sessions."""

    items: list[LeadSessionSummary]


def new_lead_session_id() -> str:
    """Create a lightweight client-managed lead session id."""
    return str(uuid4())
