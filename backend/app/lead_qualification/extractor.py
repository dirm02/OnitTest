"""Deterministic lead data extraction.

This module is intentionally regex-based for Phase 1. The public hook returns
partial LeadState updates so an LLM extractor can be swapped in later without
changing the flow contract.
"""

import re

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

    if re.search(r"\b(industrial|manufactur(?:ing|er)|factory|plant|warehouse)\b", text):
        updates.business_segment = LeadSlot(value="industrial", status=SlotStatus.CONFIRMED)
    elif re.search(r"\b(commercial|office|retail|store|restaurant|clinic)\b", text):
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
        r"\b(no current provider|no provider|without (?:a )?provider|do(?:n't| not) have "
        r"(?:a )?(?:current )?provider)\b",
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
