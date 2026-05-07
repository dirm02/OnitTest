"""Small PocketFlow-compatible turn orchestration for lead qualification."""

from typing import Any

from pocketflow import Flow, Node
from pydantic import BaseModel

from app.lead_qualification.estimator import estimate_usage_from_square_footage
from app.lead_qualification.extractor import extract_lead_updates_with_trace, merge_state
from app.lead_qualification.planner import build_response, plan_next_question
from app.lead_qualification.rules import LeadClassification, classify_lead
from app.lead_qualification.state import LeadState


class LeadTurnResult(BaseModel):
    """Result of running one lead qualification turn."""

    response: str
    state: LeadState
    missing_fields: list[str]
    classification: LeadClassification
    trace: dict[str, Any]


class LeadQualificationFlow:
    """Deterministic PocketFlow graph for one lead qualification turn."""

    def __init__(self) -> None:
        extract = ExtractLeadFactsNode()
        merge = MergeLeadStateNode()
        estimate = EstimateUsageNode()
        classify = ClassifyLeadNode()
        respond = PlanAndRespondNode()

        extract >> merge >> estimate >> classify >> respond
        self._flow = Flow(start=extract)

    def run_turn(self, message: str, state: LeadState | None = None) -> LeadTurnResult:
        """Extract, merge, estimate, classify, plan, and respond for one user turn."""
        shared: dict[str, Any] = {
            "message": message,
            "starting_state": state or LeadState(),
        }
        self._flow.run(shared)

        classified_state = shared["state"]
        classification = shared["classification"]
        next_question = shared["next_question"]
        response = shared["response"]
        missing_fields = classified_state.missing_fields()

        trace: dict[str, Any] = {
            "nodes": [
                "extract",
                "merge",
                "estimate_usage",
                "classify",
                "plan_next_question",
                "respond",
            ],
            "source": "pocketflow",
            "extracted": shared["extracted"].model_dump(mode="json"),
            "extraction": shared["extraction_trace"],
            "estimated_usage_applied": shared["estimated_usage_applied"],
            "matched_rule": classification.matched_rule,
            "next_question": next_question,
        }

        return LeadTurnResult(
            response=response,
            state=classified_state,
            missing_fields=missing_fields,
            classification=classification,
            trace=trace,
        )


class ExtractLeadFactsNode(Node):
    """Extract deterministic field updates from the latest user message."""

    def prep(self, shared: dict[str, Any]) -> str:
        return str(shared["message"])

    def exec(self, message: str) -> tuple[LeadState, dict[str, Any]]:
        return extract_lead_updates_with_trace(message)

    def post(
        self,
        shared: dict[str, Any],
        prep_res: str,
        exec_res: tuple[LeadState, dict[str, Any]],
    ) -> None:
        extracted, extraction_trace = exec_res
        shared["extracted"] = extracted
        shared["extraction_trace"] = extraction_trace


class MergeLeadStateNode(Node):
    """Merge extracted facts into the current lead state."""

    def prep(self, shared: dict[str, Any]) -> tuple[LeadState, LeadState]:
        return shared["starting_state"], shared["extracted"]

    def exec(self, prep_res: tuple[LeadState, LeadState]) -> LeadState:
        starting_state, extracted = prep_res
        return merge_state(starting_state, extracted)

    def post(
        self, shared: dict[str, Any], prep_res: tuple[LeadState, LeadState], exec_res: LeadState
    ) -> None:
        shared["state_before_estimate"] = exec_res
        shared["state"] = exec_res


class EstimateUsageNode(Node):
    """Apply square-footage fallback when annual usage is unknown."""

    def prep(self, shared: dict[str, Any]) -> LeadState:
        return shared["state"]

    def exec(self, state: LeadState) -> LeadState:
        return estimate_usage_from_square_footage(state)

    def post(self, shared: dict[str, Any], prep_res: LeadState, exec_res: LeadState) -> None:
        shared["estimated_usage_applied"] = (
            not prep_res.annual_usage_mwh.is_known
            and exec_res.annual_usage_mwh.is_known
            and exec_res.annual_usage_mwh.status == "inferred"
        )
        shared["state"] = exec_res


class ClassifyLeadNode(Node):
    """Apply the deterministic Strategic Lead Matrix."""

    def prep(self, shared: dict[str, Any]) -> LeadState:
        return shared["state"]

    def exec(self, state: LeadState) -> tuple[LeadState, LeadClassification]:
        return classify_lead(state)

    def post(
        self,
        shared: dict[str, Any],
        prep_res: LeadState,
        exec_res: tuple[LeadState, LeadClassification],
    ) -> None:
        state, classification = exec_res
        shared["state"] = state
        shared["classification"] = classification


class PlanAndRespondNode(Node):
    """Plan the next question and generate the response text."""

    def prep(self, shared: dict[str, Any]) -> tuple[LeadState, LeadClassification]:
        return shared["state"], shared["classification"]

    def exec(self, prep_res: tuple[LeadState, LeadClassification]) -> tuple[str | None, str]:
        state, classification = prep_res
        next_question = plan_next_question(state)
        return next_question, build_response(classification, next_question)

    def post(
        self,
        shared: dict[str, Any],
        prep_res: tuple[LeadState, LeadClassification],
        exec_res: tuple[str | None, str],
    ) -> None:
        next_question, response = exec_res
        shared["next_question"] = next_question
        shared["response"] = response
