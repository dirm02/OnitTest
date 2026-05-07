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


def new_lead_session_id() -> str:
    """Create a lightweight client-managed lead session id."""
    return str(uuid4())
