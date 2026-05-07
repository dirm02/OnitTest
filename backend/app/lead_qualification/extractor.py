"""Deterministic lead data extraction.

This module is intentionally regex-based for Phase 1. The public hook returns
partial LeadState updates so an LLM extractor can be swapped in later without
changing the flow contract.
"""

import re
from typing import Any

from app.lead_qualification.state import LeadSlot, LeadState, SlotStatus

NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"


def _to_float(value: str) -> float:
    return float(value.replace(",", ""))


def _to_int(value: str) -> int:
    return round(_to_float(value))


def extract_lead_updates(message: str) -> LeadState:
    """Extract confirmed lead fields from one user message."""
    text = message.lower()
    updates = LeadState()

    if re.search(r"\bcommercial\b", text):
        updates.business_segment = LeadSlot(value="commercial", status=SlotStatus.CONFIRMED)
    elif re.search(r"\b(industrial|manufactur(?:ing|er)|factory|plant|warehouse)\b", text):
        updates.business_segment = LeadSlot(value="industrial", status=SlotStatus.CONFIRMED)
    elif re.search(r"\b(office|retail|store|restaurant|clinic)\b", text):
        updates.business_segment = LeadSlot(value="commercial", status=SlotStatus.CONFIRMED)

    usage = re.search(rf"({NUMBER})\s*(?:mwh|megawatt[- ]?hours?)\b", text) or re.search(
        rf"(?:usage|use|consume|consumption)[^\d]{{0,20}}({NUMBER})",
        text,
    )
    if usage:
        updates.annual_usage_mwh = LeadSlot(
            value=_to_float(usage.group(1)),
            status=SlotStatus.CONFIRMED,
        )

    square_feet = re.search(
        rf"({NUMBER})\s*(?:sq\.?\s*ft|sqft|square\s*feet|square\s*foot)\b",
        text,
    )
    if square_feet:
        updates.square_footage = LeadSlot(
            value=_to_int(square_feet.group(1)),
            status=SlotStatus.CONFIRMED,
        )

    if re.search(r"\b(month[- ]?to[- ]?month|monthly)\b", text):
        updates.contract_status = LeadSlot(value="month_to_month", status=SlotStatus.CONFIRMED)
    elif re.search(r"\b(fixed[- ]?term|fixed contract|term contract|under contract)\b", text):
        updates.contract_status = LeadSlot(value="fixed_term", status=SlotStatus.CONFIRMED)

    expiry = re.search(
        rf"(?:expir(?:es|ing|y)|ends?|renews?|left|remaining)[^\d]{{0,20}}({NUMBER})\s*months?",
        text,
    ) or re.search(rf"({NUMBER})\s*months?\s*(?:left|remaining|until expiry|to expiry)", text)
    if expiry:
        updates.expiry_months = LeadSlot(
            value=_to_int(expiry.group(1)),
            status=SlotStatus.CONFIRMED,
        )

    if re.search(
        r"\b(no (?:current )?(?:electricity |energy |utility )?provider|"
        r"without (?:a )?(?:current )?(?:electricity |energy |utility )?provider|"
        r"do(?:n't| not) have (?:a )?(?:current )?"
        r"(?:electricity |energy |utility )?provider)\b",
        text,
    ):
        updates.has_provider = LeadSlot(value=False, status=SlotStatus.CONFIRMED)
    elif re.search(
        r"\b(current provider|provider in place|have (?:a )?provider|with (?:a )?provider)\b",
        text,
    ):
        updates.has_provider = LeadSlot(value=True, status=SlotStatus.CONFIRMED)

    age = re.search(
        rf"(?:building age|building is|built|facility is)[^\d]{{0,20}}({NUMBER})\s*years?",
        text,
    ) or re.search(rf"({NUMBER})\s*[- ]?year[- ]?old\s*(?:building|facility|site)", text)
    if age:
        updates.building_age_years = LeadSlot(
            value=_to_int(age.group(1)),
            status=SlotStatus.CONFIRMED,
        )

    return updates


def extract_lead_updates_with_trace(
    message: str,
    *,
    prefer_llm: bool = True,
) -> tuple[LeadState, dict[str, Any]]:
    """Extract lead updates with optional LLM enrichment and deterministic fallback."""
    deterministic_updates = extract_lead_updates(message)
    deterministic_fields = _known_fields(deterministic_updates)

    trace: dict[str, Any] = {
        "source": "deterministic_regex",
        "deterministic_fields": deterministic_fields,
        "llm_enabled": False,
        "llm_fields": [],
        "llm_error": None,
    }

    if not prefer_llm:
        return deterministic_updates, trace

    try:
        from app.lead_qualification.llm_extractor import (
            LLMExtractionUnavailableError,
            extract_lead_updates_llm_sync,
        )

        llm_result = extract_lead_updates_llm_sync(message)
    except LLMExtractionUnavailableError as exc:
        trace["llm_error"] = str(exc)
        return deterministic_updates, trace
    except Exception as exc:  # pragma: no cover - exercised only with live provider failures
        trace["llm_error"] = f"{type(exc).__name__}: {exc}"
        return deterministic_updates, trace

    trace.update(
        {
            "source": "deterministic_regex+gemini",
            "llm_enabled": True,
            "llm_model": llm_result.model,
            "llm_fields": llm_result.fields,
        }
    )

    return merge_state(llm_result.updates, deterministic_updates), trace


def merge_state(existing: LeadState, updates: LeadState) -> LeadState:
    """Merge new confirmed/inferred slot updates into existing state."""
    merged = existing.model_copy(deep=True)
    for field in LeadState.model_fields:
        update_slot = getattr(updates, field)
        current_slot = getattr(merged, field)
        if update_slot.status == SlotStatus.UNKNOWN or update_slot.value is None:
            continue
        if (
            current_slot.status == SlotStatus.CONFIRMED
            and update_slot.status != SlotStatus.CONFIRMED
        ):
            continue
        setattr(merged, field, update_slot)
    return merged


def _known_fields(state: LeadState) -> list[str]:
    return [
        field
        for field in LeadState.model_fields
        if getattr(state, field).status != SlotStatus.UNKNOWN
        and getattr(state, field).value is not None
    ]
