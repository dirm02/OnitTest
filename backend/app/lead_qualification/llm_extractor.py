"""Optional Gemini structured extraction for lead qualification.

The Strategic Lead Matrix remains deterministic. This module only extracts
conversation facts into the same partial LeadState shape used by the regex
extractor.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.lead_qualification.state import LeadSlot, LeadState, SlotStatus


class LLMExtractionUnavailableError(RuntimeError):
    """Raised when the optional LLM extractor is not configured or importable."""


class LeadExtractionPayload(BaseModel):
    """Structured facts the LLM is allowed to extract from one user message."""

    business_segment: Literal["commercial", "industrial"] | None = None
    annual_usage_mwh: float | None = Field(default=None, ge=0)
    square_footage: int | None = Field(default=None, ge=0)
    contract_status: Literal["month_to_month", "fixed_term"] | None = None
    expiry_months: int | None = Field(default=None, ge=0)
    has_provider: bool | None = None
    building_age_years: int | None = Field(default=None, ge=0)

    @field_validator("business_segment", "contract_status", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        """Treat empty LLM strings as missing values."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


class LLMExtractionResult(BaseModel):
    """LeadState update plus source metadata for tracing."""

    updates: LeadState
    source: Literal["gemini"]
    model: str
    fields: list[str]


SYSTEM_PROMPT = """You extract ABC Energy Solutions lead qualification facts.
Return only fields explicitly stated in the user's latest message. Do not infer
Strategic Lead Matrix tier, readiness, final_tier, or reason.

Allowed values:
- business_segment: "commercial" or "industrial". If the user explicitly says
  commercial warehouse, use "commercial".
- contract_status: "month_to_month" or "fixed_term".
- annual_usage_mwh: numeric annual electricity usage in MWh.
- square_footage: numeric building size in square feet.
- expiry_months: numeric months until contract expiry or renewal.
- has_provider: false only when the user says they have no provider; true only
  when they say they have a current provider.
- building_age_years: numeric age of the building or facility in years.
Leave unknown fields null."""


def _payload_to_state(payload: LeadExtractionPayload) -> tuple[LeadState, list[str]]:
    updates = LeadState()
    fields: list[str] = []

    for field in LeadExtractionPayload.model_fields:
        value = getattr(payload, field)
        if value is None:
            continue
        setattr(updates, field, LeadSlot(value=value, status=SlotStatus.CONFIRMED))
        fields.append(field)

    return updates, fields


def _build_agent(model_name: str):
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider
        from pydantic_ai.settings import ModelSettings
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise LLMExtractionUnavailableError("pydantic_ai Google support is unavailable") from exc

    model = GoogleModel(
        model_name,
        provider=GoogleProvider(api_key=settings.GOOGLE_API_KEY),
    )
    return Agent[None, LeadExtractionPayload](
        model=model,
        output_type=LeadExtractionPayload,
        system_prompt=SYSTEM_PROMPT,
        model_settings=ModelSettings(temperature=0),
        retries=1,
    )


def _configured_model(model_name: str | None = None) -> str:
    if not settings.GOOGLE_API_KEY:
        raise LLMExtractionUnavailableError("GOOGLE_API_KEY is not configured")
    return model_name or settings.AI_MODEL


async def extract_lead_updates_llm(
    message: str,
    *,
    model_name: str | None = None,
) -> LLMExtractionResult:
    """Extract lead facts with Gemini and return a partial LeadState update."""
    configured_model = _configured_model(model_name)
    agent = _build_agent(configured_model)
    result = await agent.run(message)
    updates, fields = _payload_to_state(result.output)
    return LLMExtractionResult(
        updates=updates,
        source="gemini",
        model=configured_model,
        fields=fields,
    )


def extract_lead_updates_llm_sync(
    message: str,
    *,
    model_name: str | None = None,
) -> LLMExtractionResult:
    """Sync wrapper for flows that are not async yet."""
    if _inside_running_event_loop():
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                lambda: asyncio.run(extract_lead_updates_llm(message, model_name=model_name))
            )
            return future.result()

    configured_model = _configured_model(model_name)
    agent = _build_agent(configured_model)
    result = agent.run_sync(message)
    updates, fields = _payload_to_state(result.output)
    return LLMExtractionResult(
        updates=updates,
        source="gemini",
        model=configured_model,
        fields=fields,
    )


def _inside_running_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True
