from typing import Any
from uuid import uuid4

from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentState
from packages.domain.models.agent import Agent
from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    Validation,
)


class InvestigationEngine:
    def __init__(
        self,
        runtime: AgentRuntime,
        agent: Agent,
        allowed_tool_identifiers: list[str],
    ) -> None:
        self._runtime = runtime
        self._agent = agent
        self._allowed_tools = allowed_tool_identifiers
        self._investigation = Investigation(
            objective=runtime._events._events[0].objective if runtime._events._events else ""
        )

    @property
    def investigation(self) -> Investigation:
        return self._investigation

    def _extract_evidence_from_state(self, state: AgentState, phase: str) -> None:
        for i, tool_result in enumerate(state.tool_results):
            evidence = Evidence(
                source_tool=tool_result.get("tool_name", f"unknown_{i}"),
                resource_id=None,
                observed_value=tool_result.get("structured_content"),
                mode="real",
                relevance=1.0,
            )
            self._investigation.add_evidence(evidence)

    async def run_collection_phase(
        self,
        objective: str,
        collection_responses: list[LLMResponse],
    ) -> AgentState:
        self._investigation.objective = objective
        llm = MockLLMProvider(collection_responses)
        old_llm = self._runtime._llm
        self._runtime._llm = llm

        state = await self._runtime.run(
            objective,
            self._agent,
            allowed_tool_identifiers=self._allowed_tools,
        )

        self._runtime._llm = old_llm
        self._extract_evidence_from_state(state, "collection")
        return state

    async def run_validation_phase(
        self,
        objective: str,
        validation_responses: list[LLMResponse],
    ) -> AgentState:
        llm = MockLLMProvider(validation_responses)
        old_llm = self._runtime._llm
        self._runtime._llm = llm

        state = await self._runtime.run(
            objective,
            self._agent,
            allowed_tool_identifiers=self._allowed_tools,
        )

        self._runtime._llm = old_llm
        self._extract_evidence_from_state(state, "validation")
        return state

    def form_hypothesis(
        self,
        text: str,
        supporting_evidence_ids: list[str] | None = None,
        contradicting_evidence_ids: list[str] | None = None,
    ) -> Hypothesis:
        hypothesis = Hypothesis(
            text=text,
            supporting_evidence_ids=[uuid4() for _ in (supporting_evidence_ids or [])],
            contradicting_evidence_ids=[uuid4() for _ in (contradicting_evidence_ids or [])],
        )
        self._investigation.add_hypothesis(hypothesis)
        return hypothesis

    def validate_hypothesis(
        self,
        hypothesis: Hypothesis,
        action_tool: str,
        expected_condition: str,
        actual_result: dict[str, Any] | str | None,
        passed: bool | None = None,
    ) -> Validation:
        validation = Validation(
            action_tool=action_tool,
            expected_condition=expected_condition,
            actual_result=actual_result,
            passed=passed,
        )
        self._investigation.add_validation(validation)

        if passed is True:
            hypothesis.status = HypothesisStatus.VALIDATED
        elif passed is False:
            hypothesis.status = HypothesisStatus.CONTRADICTED
        elif passed is None and actual_result is not None:
            hypothesis.status = HypothesisStatus.SUPPORTED

        return validation

    def conclude(
        self,
        finding: str,
        confidence: float,
        supporting_evidence_ids: list[str] | None = None,
        unresolved_uncertainty: str | None = None,
    ) -> Conclusion:
        conclusion = Conclusion(
            finding=finding,
            confidence=confidence,
            supporting_evidence_ids=[uuid4() for _ in (supporting_evidence_ids or [])],
            unresolved_uncertainty=unresolved_uncertainty,
        )
        self._investigation.set_conclusion(conclusion)
        return conclusion
