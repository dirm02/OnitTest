"""Lead qualification state primitives for ABC Energy Solutions."""

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


class SlotStatus(StrEnum):
    """Confidence/status for a collected lead qualification slot."""

    UNKNOWN = "unknown"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


T = TypeVar("T")


class LeadSlot(BaseModel, Generic[T]):
    """A value plus whether it is unknown, inferred, or confirmed."""

    value: T | None = None
    status: SlotStatus = SlotStatus.UNKNOWN

    @property
    def is_known(self) -> bool:
        """Return whether this slot carries a usable value."""
        return self.status != SlotStatus.UNKNOWN and self.value is not None


def unknown_slot() -> LeadSlot[object]:
    """Create a fresh unknown slot."""
    return LeadSlot()


class LeadState(BaseModel):
    """Conversation state for the ABC lead qualification PoC."""

    business_segment: LeadSlot[str] = Field(default_factory=LeadSlot[str])
    annual_usage_mwh: LeadSlot[float] = Field(default_factory=LeadSlot[float])
    square_footage: LeadSlot[int] = Field(default_factory=LeadSlot[int])
    contract_status: LeadSlot[str] = Field(default_factory=LeadSlot[str])
    expiry_months: LeadSlot[int] = Field(default_factory=LeadSlot[int])
    has_provider: LeadSlot[bool] = Field(default_factory=LeadSlot[bool])
    building_age_years: LeadSlot[int] = Field(default_factory=LeadSlot[int])
    final_tier: LeadSlot[str] = Field(default_factory=LeadSlot[str])
    reason: LeadSlot[str] = Field(default_factory=LeadSlot[str])

    def missing_fields(self) -> list[str]:
        """Return lead inputs that are still unknown."""
        fields = [
            "business_segment",
            "annual_usage_mwh",
            "square_footage",
            "contract_status",
            "expiry_months",
            "has_provider",
            "building_age_years",
        ]
        return [field for field in fields if not getattr(self, field).is_known]
