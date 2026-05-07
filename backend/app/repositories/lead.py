"""Repository helpers for ABC Energy lead qualification persistence."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.lead import LeadSession, LeadTurn


async def get_session(
    db: AsyncSession,
    session_id: str,
    *,
    include_turns: bool = False,
) -> LeadSession | None:
    """Get a lead session by its public session id."""
    query = select(LeadSession).where(LeadSession.session_id == session_id)
    if include_turns:
        query = query.options(selectinload(LeadSession.turns))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_sessions(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    source: str | None = None,
    final_tier: str | None = None,
) -> list[LeadSession]:
    """List lead sessions newest first."""
    query = select(LeadSession)
    if source is not None:
        query = query.where(LeadSession.source == source)
    if final_tier is not None:
        query = query.where(LeadSession.final_tier == final_tier)

    query = (
        query.order_by(func.coalesce(LeadSession.updated_at, LeadSession.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def upsert_session(
    db: AsyncSession,
    *,
    session_id: str,
    latest_state: dict[str, Any] | None = None,
    final_tier: str | None = None,
    matched_rule: str | None = None,
    reason: str | None = None,
    source: str = "abc_energy",
) -> LeadSession:
    """Create or update a lead session."""
    db_session = await get_session(db, session_id)
    if db_session is None:
        db_session = LeadSession(
            session_id=session_id,
            latest_state=latest_state or {},
            final_tier=final_tier,
            matched_rule=matched_rule,
            reason=reason,
            source=source,
        )
    else:
        if latest_state is not None:
            db_session.latest_state = latest_state
        if final_tier is not None:
            db_session.final_tier = final_tier
        if matched_rule is not None:
            db_session.matched_rule = matched_rule
        if reason is not None:
            db_session.reason = reason
        db_session.source = source

    db.add(db_session)
    await db.flush()
    await db.refresh(db_session)
    return db_session


async def update_latest_state(
    db: AsyncSession,
    *,
    db_session: LeadSession,
    latest_state: dict[str, Any],
    final_tier: str | None = None,
    matched_rule: str | None = None,
    reason: str | None = None,
) -> LeadSession:
    """Replace the latest state snapshot and optional classification summary."""
    db_session.latest_state = latest_state
    if final_tier is not None:
        db_session.final_tier = final_tier
    if matched_rule is not None:
        db_session.matched_rule = matched_rule
    if reason is not None:
        db_session.reason = reason

    db.add(db_session)
    await db.flush()
    await db.refresh(db_session)
    return db_session


async def append_turn(
    db: AsyncSession,
    *,
    session_id: str,
    user_message: str,
    assistant_response: str,
    state: dict[str, Any],
    classification: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
    source: str = "abc_energy",
) -> LeadTurn:
    """Append one lead turn and update the owning session's latest state."""
    classification_data = classification or {}
    db_session = await upsert_session(
        db,
        session_id=session_id,
        latest_state=state,
        final_tier=_string_or_none(classification_data.get("tier")),
        matched_rule=_string_or_none(classification_data.get("matched_rule")),
        reason=_string_or_none(classification_data.get("reason")),
        source=source,
    )
    turn = LeadTurn(
        lead_session_id=db_session.id,
        user_message=user_message,
        assistant_response=assistant_response,
        state=state,
        classification=classification_data,
        trace=trace or {},
    )

    db.add(turn)
    await db.flush()
    await db.refresh(turn)
    return turn


def _string_or_none(value: object) -> str | None:
    """Return strings as-is and coerce other present values for summary columns."""
    if value is None:
        return None
    return str(value)
