import re
from typing import Any
from uuid import UUID

from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.agent.runtime.runtime import AgentRuntime
from packages.agent.runtime.state import AgentState
from packages.domain.models.agent import Agent
from packages.domain.resource_graph import ResourceGraph
from packages.investigations.models import (
    Conclusion,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    Validation,
)
from packages.investigations.validation_executor import ValidationExecutionResult


class InvestigationEngine:
    def __init__(
        self,
        runtime: AgentRuntime,
        agent: Agent,
        allowed_tool_identifiers: list[str],
        organization_id: UUID,
        workspace_id: UUID | None = None,
        investigation: Investigation | None = None,
    ) -> None:
        self._runtime = runtime
        self._agent = agent
        self._allowed_tools = allowed_tool_identifiers
        self._investigation = investigation or Investigation(
            organization_id=organization_id,
            workspace_id=workspace_id,
            objective="",
        )

    @property
    def investigation(self) -> Investigation:
        return self._investigation

    def _extract_evidence_from_state(self, state: AgentState, phase: str) -> None:
        for i, tool_result in enumerate(state.tool_results):
            resource_id = tool_result.get("resource_id")
            try:
                parsed_resource_id = UUID(resource_id) if resource_id else None
            except (TypeError, ValueError):
                parsed_resource_id = None
            evidence = Evidence(
                source_tool=tool_result.get("tool_name", f"unknown_{i}"),
                resource_id=parsed_resource_id,
                observed_value=tool_result.get("structured_content"),
                mode="real",
                relevance=1.0,
            )
            self._investigation.add_evidence(evidence)

    async def run_collection_phase(
        self,
        objective: str,
        collection_responses: list[LLMResponse] | None = None,
        llm_objective: str | None = None,
    ) -> AgentState:
        self._investigation.objective = objective
        prompt = llm_objective or objective
        if collection_responses is None:
            state = await self._runtime.run(
                prompt,
                self._agent,
                allowed_tool_identifiers=self._allowed_tools,
            )
        else:
            llm = MockLLMProvider(collection_responses)
            with self._runtime.using_llm(llm):
                state = await self._runtime.run(
                    prompt,
                    self._agent,
                    allowed_tool_identifiers=self._allowed_tools,
                )

        self._extract_evidence_from_state(state, "collection")
        return state

    async def run_baseline_collection_phase(self, objective: str) -> AgentState:
        self._investigation.objective = objective
        state = await self._runtime.collect_read_only_tools(
            self._agent,
            allowed_tool_identifiers=self._allowed_tools,
        )
        self._extract_evidence_from_state(state, "baseline")
        return state

    async def run_validation_phase(
        self,
        objective: str,
        validation_responses: list[LLMResponse] | None = None,
    ) -> AgentState:
        if validation_responses is None:
            state = await self._runtime.run(
                objective,
                self._agent,
                allowed_tool_identifiers=self._allowed_tools,
            )
        else:
            llm = MockLLMProvider(validation_responses)
            with self._runtime.using_llm(llm):
                state = await self._runtime.run(
                    objective,
                    self._agent,
                    allowed_tool_identifiers=self._allowed_tools,
                )

        self._extract_evidence_from_state(state, "validation")
        return state

    def form_hypothesis(
        self,
        text: str,
        supporting_evidence_ids: list[UUID] | None = None,
        contradicting_evidence_ids: list[UUID] | None = None,
    ) -> Hypothesis | None:
        normalized = self._hypothesis_key(text)
        if any(
            self._hypotheses_are_semantically_duplicate(normalized, item.text)
            for item in self._investigation.hypotheses
        ):
            return None
        hypothesis = Hypothesis(
            text=text,
            supporting_evidence_ids=supporting_evidence_ids or [],
            contradicting_evidence_ids=contradicting_evidence_ids or [],
        )
        self._investigation.add_hypothesis(hypothesis)
        return hypothesis

    @staticmethod
    def _hypothesis_key(text: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold())
        stop_words = {"a", "an", "and", "because", "is", "of", "the", "to"}
        return " ".join(word for word in normalized.split() if word not in stop_words)

    @staticmethod
    def _hypotheses_are_semantically_duplicate(first: str, second: str) -> bool:
        first_tokens = set(first.split())
        second_tokens = set(InvestigationEngine._hypothesis_key(second).split())
        if not first_tokens or not second_tokens:
            return first_tokens == second_tokens
        overlap = len(first_tokens & second_tokens) / len(first_tokens | second_tokens)
        return overlap >= 0.8

    def validate_hypothesis(
        self,
        hypothesis: Hypothesis,
        action_tool: str,
        expected_condition: str,
        actual_result: dict[str, Any] | str | None,
        passed: bool | None = None,
    ) -> Validation:
        evidence = Evidence(
            source_tool=action_tool,
            observed_value=actual_result,
            mode="real",
            relevance=1.0,
        )
        evidence_id = self._investigation.add_evidence(evidence)
        validation = Validation(
            action_tool=action_tool,
            expected_condition=expected_condition,
            actual_result=actual_result,
            passed=passed,
            evidence_ids=[evidence_id],
        )
        self._investigation.add_validation(validation)
        if passed is True:
            hypothesis.supporting_evidence_ids.append(evidence_id)
        elif passed is False:
            hypothesis.contradicting_evidence_ids.append(evidence_id)

        if passed is True:
            hypothesis.status = HypothesisStatus.VALIDATED
        elif passed is False:
            hypothesis.status = HypothesisStatus.CONTRADICTED
        elif passed is None and actual_result is not None:
            hypothesis.status = HypothesisStatus.SUPPORTED

        return validation

    def apply_validation_results(
        self,
        results: list[ValidationExecutionResult],
    ) -> None:
        for result in results:
            hypothesis_index = result.action.hypothesis_index
            if hypothesis_index >= len(self._investigation.hypotheses):
                raise ValueError(
                    f"Validation references unknown hypothesis: {hypothesis_index}"
                )
            hypothesis = self._investigation.hypotheses[hypothesis_index]
            self.validate_hypothesis(
                hypothesis=hypothesis,
                action_tool=result.action.action_tool,
                expected_condition=result.action.expected_condition,
                actual_result=result.actual_result,
                passed=result.passed,
            )

    def evidence_resource_lineage(self, graph: ResourceGraph) -> dict[UUID, list[UUID]]:
        return {
            evidence.id: graph.lineage_ids(evidence.resource_id)
            for evidence in self._investigation.evidence
            if evidence.resource_id is not None
        }

    def calculate_confidence(self) -> float:
        hypotheses = self._investigation.hypotheses
        if not hypotheses:
            return 0.0
        validated = sum(item.status == HypothesisStatus.VALIDATED for item in hypotheses)
        contradicted = sum(item.status == HypothesisStatus.CONTRADICTED for item in hypotheses)
        unresolved = len(hypotheses) - validated - contradicted
        score = (validated + 0.5 * unresolved) / len(hypotheses)
        if validated and contradicted:
            score *= 0.75
        return round(max(0.0, min(1.0, score)), 2)

    def conclude(
        self,
        finding: str,
        confidence: float,
        supporting_evidence_ids: list[UUID] | None = None,
        unresolved_uncertainty: str | None = None,
    ) -> Conclusion:
        conclusion = Conclusion(
            finding=finding,
            confidence=confidence,
            supporting_evidence_ids=supporting_evidence_ids or [],
            unresolved_uncertainty=unresolved_uncertainty,
        )
        self._investigation.set_conclusion(conclusion)
        return conclusion
