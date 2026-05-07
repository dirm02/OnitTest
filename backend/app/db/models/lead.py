"""ABC Energy lead qualification persistence models."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class LeadSession(Base, TimestampMixin):
    """Lead qualification session state for a client-managed session id."""

    __tablename__ = "lead_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    latest_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    final_tier: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    matched_rule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="abc_energy")

    turns: Mapped[list["LeadTurn"]] = relationship(
        "LeadTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LeadTurn.created_at",
    )

    def __repr__(self) -> str:
        return f"<LeadSession(id={self.id}, session_id={self.session_id})>"


class LeadTurn(Base, TimestampMixin):
    """One user/assistant turn in an ABC Energy lead qualification session."""

    __tablename__ = "lead_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lead_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    classification: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    trace: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    session: Mapped[LeadSession] = relationship("LeadSession", back_populates="turns")

    def __repr__(self) -> str:
        return f"<LeadTurn(id={self.id}, lead_session_id={self.lead_session_id})>"
