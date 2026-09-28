import contextlib
import json
from typing import Any
from uuid import UUID

from packages.agent.llm.contract import LLMProvider
from packages.agent.llm.ollama import OllamaProvider
from packages.agent.runtime.events import (
    LLMResponseReceivedEvent,
    ToolAllowedEvent,
    ToolDeniedEvent,
    ToolExecutedEvent,
    ToolRequestedEvent,
)
from packages.agent.runtime.runtime import AgentRuntime
from packages.auth import get_settings
from packages.connectors.factory import create_connector, register_linux_tools
from packages.connectors.providers.linux import LinuxConnector
from packages.domain.models.agent import Agent
from packages.domain.models.context import TenantContext
from packages.domain.models.policy import Policy as PolicyModel
from packages.domain.models.resource import Resource
from packages.investigations.conclusion_synthesizer import ConclusionResult, ConclusionSynthesizer
from packages.investigations.engine import InvestigationEngine
from packages.investigations.models import (
    Hypothesis,
    Investigation,
    InvestigationEvent,
    InvestigationStatus,
)
from packages.investigations.validation import ValidationPlan
from packages.investigations.validation_executor import (
    ValidationExecutionResult,
    ValidationExecutor,
)
from packages.investigations.validation_judge import ValidationJudge, ValidationJudgments
from packages.investigations.validation_planner import ValidationPlanner
from packages.mcp.client import MCPToolClient
from packages.mcp.server import NexusMCPServer
from packages.persistence.repositories.core import CoreRepository
from packages.persistence.repositories.investigation import InvestigationPostgresRepository
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.registry import ToolRegistry
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

INFRASTRUCTURE_TOOL_IDS = [
    "get_system_info",
    "get_cpu_usage",
    "get_memory_usage",
    "get_disk_usage",
    "get_processes",
    "get_network_listeners",
    "get_service_status",
    "get_application_health",
]
ALL_TOOL_IDS = list(INFRASTRUCTURE_TOOL_IDS)
MAX_HYPOTHESES = 5

INVESTIGATION_SYSTEM_PROMPT = """You are the NEXUS operational investigation agent.
Your job is to investigate infrastructure incidents using only the provided read-only tools.
Use tools deliberately: collect enough evidence to answer the objective, compare signals, and
validate important hypotheses when a read-only check can confirm or contradict them.
Never invent measurements, services, endpoints, causes, or remediation results.
Clearly distinguish observed facts from inference. Prefer concrete evidence from tools
over assumptions.
When evidence is insufficient, say so and record the uncertainty.

When you finish, return ONLY valid JSON with this shape:
{
  "hypotheses": [
    {
      "text": "string",
      "supporting_tools": ["tool_id"],
      "contradicting_tools": ["tool_id"]
    }
  ],
  "validations": [
    {
      "action_tool": "tool_id",
      "expected_condition": "string",
      "passed": true,
      "summary": "string"
    }
  ],
  "finding": "string",
  "confidence": 0.0,
  "supporting_tools": ["tool_id"],
  "uncertainty": "string or null"
}
Confidence must be between 0 and 1. Use null uncertainty only when the evidence is sufficient."""


ANALYSIS_SYSTEM_PROMPT = """You are the NEXUS investigation analysis agent.
No tools are available in this phase. Analyze only the baseline evidence provided by NEXUS.
Do not request tools, invent missing measurements, or claim that a hypothesis was validated.
Return ONLY valid JSON with exactly this shape:
{
  "hypotheses": [
    {
      "text": "string",
      "supporting_tools": ["tool_id"],
      "contradicting_tools": ["tool_id"]
    }
  ],
  "validations": [],
  "finding": "string",
  "confidence": 0.0,
  "supporting_tools": ["tool_id"],
  "uncertainty": "string or null"
}
Keep the output compact. Do not echo the evidence. Do not add other top-level fields.
Keep validations as an empty array until a later validation phase.
"""


class LLMHypothesisResult(BaseModel):
    text: str
    supporting_tools: list[str] = Field(default_factory=list)
    contradicting_tools: list[str] = Field(default_factory=list)


class LLMValidationResult(BaseModel):
    action_tool: str
    expected_condition: str
    hypothesis_index: int | None = None
    passed: bool | None = None
    summary: str | None = None


class LLMInvestigationResult(BaseModel):
    hypotheses: list[LLMHypothesisResult] = Field(default_factory=list)
    validations: list[LLMValidationResult] = Field(default_factory=list)
    finding: str
    confidence: float = 0.0
    supporting_tools: list[str] = Field(default_factory=list)
    uncertainty: str | None = None


class InvestigationApplicationService:
    def __init__(self, tenant_context: TenantContext, session: AsyncSession | None = None) -> None:
        self._tenant = tenant_context
        self._session = session
        self._core_repository = CoreRepository(session) if session is not None else None
        self._investigation_repository = (
            InvestigationPostgresRepository(session) if session is not None else None
        )

    @property
    def tenant(self) -> TenantContext:
        return self._tenant

    async def run_investigation(
        self, objective: str, investigation: Investigation | None = None
    ) -> Investigation:
        """Run an autonomous read-only investigation with real Ollama inference."""
        if self._core_repository is None or self._investigation_repository is None:
            raise RuntimeError("A database session is required to run an investigation")
        objective = objective.strip()
        if not objective:
            raise ValueError("Investigation objective cannot be empty")
        if investigation is not None:
            investigation.objective = objective

        resource = await self._get_or_create_resource()
        agent = await self._get_or_create_agent()
        agent.system_instructions = (
            f"{agent.system_instructions.strip()}\n\n{INVESTIGATION_SYSTEM_PROMPT}".strip()
        )
        policy = self._get_or_create_policy()

        connector = create_connector(resource)
        if not isinstance(connector, LinuxConnector):
            raise TypeError("The Linux investigation service requires a LinuxConnector")
        await connector.connect(resource)

        try:
            server_registry = ToolRegistry()
            register_linux_tools(connector, server_registry)

            mcp_server = NexusMCPServer(name="nexus-linux-live", registry=server_registry)
            mcp_client = MCPToolClient(server_name="nexus-linux-live")
            await mcp_client.connect(mcp_server.server)

            try:
                discovered = await mcp_client.list_tools()
                runtime_registry = ToolRegistry()
                for tool_def in discovered:
                    runtime_registry.register(mcp_client.create_tool_wrapper(tool_def))

                evaluator = PolicyEvaluator(policy)
                llm = self._create_llm(runtime_registry)
                runtime = AgentRuntime(
                    llm=llm,
                    registry=runtime_registry,
                    policy=evaluator,
                    max_iterations=10,
                )
                engine = InvestigationEngine(
                    runtime=runtime,
                    agent=agent,
                    allowed_tool_identifiers=ALL_TOOL_IDS,
                    organization_id=self._tenant.organization_id,
                    workspace_id=self._tenant.workspace_id,
                    investigation=investigation,
                )

                baseline_state = await engine.run_baseline_collection_phase(objective)
                await self._persist_runtime_events(engine.investigation, runtime)
                engine.investigation.status = InvestigationStatus.VALIDATING
                engine.investigation.phase = "hypothesis"
                if investigation is not None:
                    await self._checkpoint_investigation(engine.investigation, "baseline.collected")

                analysis_registry = ToolRegistry()
                analysis_llm = self._create_llm(analysis_registry, num_predict=384)
                analysis_runtime = AgentRuntime(
                    llm=analysis_llm,
                    registry=analysis_registry,
                    policy=evaluator,
                    max_iterations=1,
                )
                analysis_agent = agent.model_copy(
                    update={"system_instructions": ANALYSIS_SYSTEM_PROMPT}
                )
                analysis_state = await analysis_runtime.run(
                    self._build_analysis_prompt(objective, baseline_state.tool_results),
                    analysis_agent,
                    allowed_tool_identifiers=[],
                    response_format="json",
                )
                result = self._parse_llm_result(analysis_state.final_result)
                await self._persist_runtime_events(engine.investigation, analysis_runtime)

                if result is not None:
                    evidence_by_tool = self._evidence_ids_by_tool(engine.investigation)
                    for hypothesis_result in result.hypotheses:
                        supporting_ids = self._ids_for_tools(
                            hypothesis_result.supporting_tools, evidence_by_tool
                        )
                        contradicting_ids = self._ids_for_tools(
                            hypothesis_result.contradicting_tools, evidence_by_tool
                        )
                        if not self._hypothesis_has_evidence(hypothesis_result, evidence_by_tool):
                            continue
                        engine.form_hypothesis(
                            text=hypothesis_result.text,
                            supporting_evidence_ids=supporting_ids,
                            contradicting_evidence_ids=contradicting_ids,
                        )

                    engine.investigation.phase = "validation"
                    if investigation is not None:
                        await self._checkpoint_investigation(
                            engine.investigation, "hypotheses.formed"
                        )
                    validation_plan = await self._plan_validations(
                        analysis_llm,
                        engine.investigation.hypotheses,
                    )
                    validation_executor = ValidationExecutor(
                        registry=runtime_registry,
                        policy=evaluator,
                        allowed_tool_identifiers=ALL_TOOL_IDS,
                    )
                    validation_results = await validation_executor.execute(validation_plan)
                    judgment_llm = self._create_llm(analysis_registry, num_predict=384)
                    validation_judgments = await self._judge_validations(
                        judgment_llm,
                        validation_results,
                    )
                    validation_executor.apply_judgments(
                        validation_results,
                        validation_judgments,
                    )
                    engine.apply_validation_results(validation_results)
                    engine.investigation.phase = "conclusion"
                    if investigation is not None:
                        await self._checkpoint_investigation(
                            engine.investigation, "validation.completed"
                        )
                    conclusion = await self._synthesize_conclusion(
                        judgment_llm,
                        engine.investigation,
                    )
                    conclusion_ids = self._ids_for_tools(result.supporting_tools, evidence_by_tool)
                    conclusion_ids.extend(
                        evidence_id
                        for validation in engine.investigation.validations
                        for evidence_id in validation.evidence_ids
                    )
                    conclusion_ids = list(dict.fromkeys(conclusion_ids))
                    engine.conclude(
                        finding=conclusion.finding,
                        confidence=engine.calculate_confidence(),
                        supporting_evidence_ids=conclusion_ids,
                        unresolved_uncertainty=conclusion.uncertainty,
                    )
                    engine.investigation.status = InvestigationStatus.COMPLETED
                    engine.investigation.phase = "completed"
                else:
                    fallback = analysis_state.final_result or (
                        "The investigation did not produce a final answer."
                    )
                    engine.conclude(
                        finding=fallback,
                        confidence=0.0,
                        supporting_evidence_ids=[e.id for e in engine.investigation.evidence],
                        unresolved_uncertainty=(
                            "The model response was not valid structured investigation JSON; "
                            "the raw finding was preserved without adding unsupported claims."
                        ),
                    )

                if (
                    analysis_state.status.value != "completed"
                    and engine.investigation.conclusion is not None
                ):
                    engine.investigation.conclusion.confidence = 0.0
                    engine.investigation.conclusion.unresolved_uncertainty = (
                        f"{engine.investigation.conclusion.unresolved_uncertainty or ''} "
                        "The agent runtime did not complete normally."
                    ).strip()

                saved = (
                    await self._investigation_repository.update(
                        engine.investigation,
                        self._tenant.organization_id,
                        self._tenant.workspace_id,
                    )
                    if investigation is not None
                    else await self._investigation_repository.create(engine.investigation)
                )
                await self._record_investigation_events(saved)
                return saved
            finally:
                with contextlib.suppress(Exception):
                    await mcp_client.disconnect()
        finally:
            await connector.disconnect(resource)

    async def _persist_runtime_events(
        self, investigation: Investigation, runtime: AgentRuntime
    ) -> None:
        if self._investigation_repository is None or self._session is None:
            return
        for event in runtime.events.events:
            metadata: dict[str, Any] = {}
            if isinstance(event, ToolRequestedEvent):
                event_type = "tool.requested"
                metadata = {"tool_name": event.tool_name}
            elif isinstance(event, ToolAllowedEvent):
                event_type = "policy.allowed"
                metadata = {"tool_name": event.tool_name}
            elif isinstance(event, ToolDeniedEvent):
                event_type = "policy.denied"
                metadata = {"tool_name": event.tool_name, "reason": event.reason}
            elif isinstance(event, ToolExecutedEvent):
                event_type = "tool.executed"
                metadata = {
                    "tool_name": event.tool_name,
                    "success": event.success,
                    "duration_ms": round(event.duration * 1000, 2),
                    "resource_mode": event.resource_mode,
                    "resource_id": event.resource_id,
                    "failure": event.failure,
                }
            elif isinstance(event, LLMResponseReceivedEvent):
                event_type = "llm.response"
                metadata = {
                    "iteration": event.iteration,
                    "has_tool_calls": event.has_tool_calls,
                    "tool_call_count": event.tool_call_count,
                    "duration_ms": round(event.duration * 1000, 2),
                }
            else:
                continue
            await self._investigation_repository.add_event(
                InvestigationEvent(
                    investigation_id=investigation.id,
                    event_type=event_type,
                    phase=investigation.phase,
                    metadata=metadata,
                )
            )
        await self._session.commit()

    async def _checkpoint_investigation(
        self, investigation: Investigation, event_type: str
    ) -> Investigation:
        if self._investigation_repository is None or self._session is None:
            return investigation
        saved = await self._investigation_repository.update(
            investigation, self._tenant.organization_id, self._tenant.workspace_id
        )
        await self._investigation_repository.add_event(
            InvestigationEvent(
                investigation_id=saved.id,
                event_type=event_type,
                phase=saved.phase,
                metadata={
                    "evidence_count": len(saved.evidence),
                    "hypothesis_count": len(saved.hypotheses),
                    "validation_count": len(saved.validations),
                    "has_conclusion": saved.conclusion is not None,
                },
            )
        )
        await self._session.commit()
        return saved

    async def _record_investigation_events(self, investigation: Investigation) -> None:
        if self._investigation_repository is None:
            return
        phases = [("investigation.started", "collection")]
        if investigation.evidence:
            phases.append(("baseline.collected", "collection"))
        if investigation.hypotheses:
            phases.append(("hypotheses.formed", "hypothesis"))
        if investigation.validations:
            phases.append(("validation.completed", "validation"))
        if investigation.conclusion:
            phases.append(("conclusion.completed", "completed"))
        for event_type, phase in phases:
            await self._investigation_repository.add_event(
                InvestigationEvent(
                    investigation_id=investigation.id,
                    event_type=event_type,
                    phase=phase,
                    metadata={
                        "evidence_count": len(investigation.evidence),
                        "hypothesis_count": len(investigation.hypotheses),
                        "validation_count": len(investigation.validations),
                        "has_conclusion": investigation.conclusion is not None,
                    },
                )
            )

    async def _get_or_create_resource(self) -> Resource:
        return await self._core_repository.ensure_dev_resource(
            self._tenant.organization_id,
            self._tenant.workspace_id,
        )

    async def _get_or_create_agent(self) -> Agent:
        return await self._core_repository.ensure_dev_agent(
            self._tenant.organization_id,
            self._tenant.workspace_id,
        )

    def _get_or_create_policy(self) -> PolicyModel:
        return PolicyModel(
            organization_id=self._tenant.organization_id,
            name="linux-investigation-policy",
            allowed_tool_ids=ALL_TOOL_IDS,
        )

    @staticmethod
    async def _plan_validations(
        llm: LLMProvider,
        hypotheses: list[Hypothesis],
    ) -> ValidationPlan:
        planner = ValidationPlanner(
            llm=llm,
            available_tool_identifiers=ALL_TOOL_IDS,
        )
        return await planner.plan(hypotheses)

    @staticmethod
    async def _synthesize_conclusion(
        llm: LLMProvider,
        investigation: Investigation,
    ) -> ConclusionResult:
        payload = {
            "objective": investigation.objective,
            "hypotheses": [
                {"text": item.text, "status": item.status.value}
                for item in investigation.hypotheses
            ],
            "validations": [
                {
                    "action_tool": item.action_tool,
                    "expected_condition": item.expected_condition,
                    "actual_result": item.actual_result,
                    "passed": item.passed,
                }
                for item in investigation.validations
            ],
        }
        return await ConclusionSynthesizer(llm).synthesize(payload)

    @staticmethod
    async def _judge_validations(
        llm: LLMProvider,
        results: list[ValidationExecutionResult],
    ) -> ValidationJudgments:
        judge = ValidationJudge(llm)
        payload = [
            {
                "action_tool": result.action.action_tool,
                "expected_condition": result.action.expected_condition,
                "actual_result": result.actual_result,
            }
            for result in results
        ]
        return await judge.judge(payload)

    @staticmethod
    def _create_llm(
        runtime_registry: ToolRegistry,
        num_predict: int | None = None,
    ) -> OllamaProvider:
        settings = get_settings()
        return OllamaProvider(
            host=settings.ollama_host,
            model=settings.ollama_model,
            registry=runtime_registry,
            timeout=settings.ollama_timeout,
            num_predict=num_predict,
        )

    @staticmethod
    def _build_analysis_prompt(
        objective: str,
        tool_results: list[dict[str, Any]],
    ) -> str:
        evidence_blocks: list[str] = []
        total_chars = 0
        for item in tool_results:
            tool_name = item.get("tool_name", "unknown_tool")
            content = json.dumps(
                item.get("structured_content"),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if len(content) > 2200:
                content = content[:2200] + "...[truncated]"
            block = f"{tool_name}: {content}"
            if total_chars + len(block) > 14000:
                evidence_blocks.append("Additional baseline evidence omitted for context size.")
                break
            evidence_blocks.append(block)
            total_chars += len(block)

        return (
            f"Investigation objective: {objective}\n\n"
            "Baseline read-only evidence collected by NEXUS:\n"
            + "\n".join(evidence_blocks)
            + "\n\nAnalyze these observations only. "
            "Form hypotheses only when supported by the evidence. "
            "Do not claim validation because no validation tools were run."
        )

    @staticmethod
    def _parse_llm_result(content: str | None) -> LLMInvestigationResult | None:
        if not content:
            return None
        candidate = content.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            candidate = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            ).strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start < 0 or end <= start:
                return None
            try:
                payload = json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                return None
        try:
            parsed = LLMInvestigationResult.model_validate(payload)
            parsed.hypotheses = parsed.hypotheses[:MAX_HYPOTHESES]
            return parsed
        except Exception:
            pass

        hypothesis_payload = payload.get("hypotheses")
        if not isinstance(hypothesis_payload, list):
            return None

        hypotheses: list[LLMHypothesisResult] = []
        for item in hypothesis_payload:
            if isinstance(item, str):
                if item.strip():
                    hypotheses.append(LLMHypothesisResult(text=item.strip()))
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("description") or item.get("hypothesis")
            if not isinstance(text, str) or not text.strip():
                continue
            hypotheses.append(
                LLMHypothesisResult(
                    text=text.strip(),
                    supporting_tools=item.get("supporting_tools", []),
                    contradicting_tools=item.get("contradicting_tools", []),
                )
            )

        if not hypotheses:
            return None

        return LLMInvestigationResult(
            hypotheses=hypotheses[:MAX_HYPOTHESES],
            validations=[],
            finding=payload.get(
                "finding",
                payload.get(
                    "investigation",
                    "Baseline analysis produced hypotheses; validation is pending.",
                ),
            ),
            confidence=payload.get("confidence", 0.0),
            supporting_tools=payload.get("supporting_tools", []),
            uncertainty=payload.get(
                "uncertainty",
                "The model returned a simplified hypothesis JSON shape; validation is pending.",
            ),
        )

    @staticmethod
    def _hypothesis_has_evidence(
        hypothesis_result: LLMHypothesisResult,
        evidence_by_tool: dict[str, list[UUID]],
    ) -> bool:
        return bool(
            InvestigationApplicationService._ids_for_tools(
                hypothesis_result.supporting_tools, evidence_by_tool
            )
            or InvestigationApplicationService._ids_for_tools(
                hypothesis_result.contradicting_tools, evidence_by_tool
            )
        )

    @staticmethod
    def _evidence_ids_by_tool(investigation: Investigation) -> dict[str, list[UUID]]:
        evidence_by_tool: dict[str, list[UUID]] = {}
        for evidence in investigation.evidence:
            evidence_by_tool.setdefault(evidence.source_tool, []).append(evidence.id)
        return evidence_by_tool

    @staticmethod
    def _ids_for_tools(tools: list[str], evidence_by_tool: dict[str, list[UUID]]) -> list[UUID]:
        ids: list[UUID] = []
        for tool in tools:
            ids.extend(evidence_by_tool.get(tool, []))
        return list(dict.fromkeys(ids))

    @staticmethod
    def _results_by_tool(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for item in tool_results:
            tool_name = item.get("tool_name")
            if tool_name:
                results[tool_name] = item.get("structured_content")
        return results
