"""Focused tests for ABC Energy lead persistence primitives."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.lead import LeadSession, LeadTurn


def test_lead_model_tables_and_columns() -> None:
    """Lead models expose the intended table and storage columns."""
    assert LeadSession.__tablename__ == "lead_sessions"
    assert LeadTurn.__tablename__ == "lead_turns"

    session_columns = LeadSession.__table__.columns
    turn_columns = LeadTurn.__table__.columns

    assert "session_id" in session_columns
    assert "latest_state" in session_columns
    assert "final_tier" in session_columns
    assert "matched_rule" in session_columns
    assert "reason" in session_columns
    assert "source" in session_columns
    assert "created_at" in session_columns
    assert "updated_at" in session_columns

    assert "lead_session_id" in turn_columns
    assert "user_message" in turn_columns
    assert "assistant_response" in turn_columns
    assert "state" in turn_columns
    assert "classification" in turn_columns
    assert "trace" in turn_columns


@pytest.mark.anyio
async def test_upsert_session_creates_new_session() -> None:
    """Upsert creates a session when one does not already exist."""
    from app.repositories import lead as lead_repo

    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_or_none_result(None))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    session = await lead_repo.upsert_session(
        db,
        session_id="lead-123",
        latest_state={"business_segment": {"value": "industrial"}},
        final_tier="Tier 1",
        matched_rule="industrial_high_usage_expiring_soon",
        reason="Qualified",
    )

    assert isinstance(session, LeadSession)
    assert session.session_id == "lead-123"
    assert session.latest_state == {"business_segment": {"value": "industrial"}}
    assert session.final_tier == "Tier 1"
    assert session.matched_rule == "industrial_high_usage_expiring_soon"
    assert session.reason == "Qualified"
    assert session.source == "abc_energy"
    db.add.assert_called_once_with(session)
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(session)


@pytest.mark.anyio
async def test_append_turn_updates_session_summary_and_adds_turn() -> None:
    """Appending a turn stores snapshots and mirrors classification on the session."""
    from app.repositories import lead as lead_repo

    existing_session = LeadSession(
        id=uuid4(),
        session_id="lead-123",
        latest_state={},
        source="abc_energy",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_or_none_result(existing_session))
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    state = {"final_tier": {"value": "Tier 2"}}
    classification = {
        "tier": "Tier 2",
        "matched_rule": "industrial_mid_usage_new_building",
        "reason": "Qualified",
    }
    trace = {"steps": ["extract", "classify"]}

    turn = await lead_repo.append_turn(
        db,
        session_id="lead-123",
        user_message="We use 200 MWh.",
        assistant_response="Thanks, this looks like Tier 2.",
        state=state,
        classification=classification,
        trace=trace,
    )

    assert isinstance(turn, LeadTurn)
    assert turn.lead_session_id == existing_session.id
    assert turn.user_message == "We use 200 MWh."
    assert turn.assistant_response == "Thanks, this looks like Tier 2."
    assert turn.state == state
    assert turn.classification == classification
    assert turn.trace == trace
    assert existing_session.latest_state == state
    assert existing_session.final_tier == "Tier 2"
    assert existing_session.matched_rule == "industrial_mid_usage_new_building"
    assert existing_session.reason == "Qualified"
    assert db.add.call_count == 2
    db.flush.assert_awaited()
    db.refresh.assert_awaited()


def _scalar_one_or_none_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result
