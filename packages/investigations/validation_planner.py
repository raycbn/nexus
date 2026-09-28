import json

from packages.agent.llm.contract import LLMMessage, LLMProvider, LLMRequest, LLMResponse
from packages.investigations.models import Hypothesis
from packages.investigations.validation import ValidationPlan

MAX_VALIDATION_ACTIONS = 8


VALIDATION_PLANNER_SYSTEM_PROMPT = """You are the NEXUS validation planning agent.
No tools are executed in this phase.
For each hypothesis, propose only read-only checks that can confirm or contradict it.
Use only the available tool identifiers provided by NEXUS.
Return ONLY valid JSON with exactly this shape:
{
  "actions": [
    {
      "hypothesis_index": 0,
      "action_tool": "tool_id",
      "expected_condition": "string"
    }
  ]
}
Do not invent tools. Do not include write, mutate, restart, delete, or remediation actions.
Keep the plan compact."""


class ValidationPlanner:
    def __init__(
        self,
        llm: LLMProvider,
        available_tool_identifiers: list[str],
    ) -> None:
        self._llm = llm
        self._available_tools = available_tool_identifiers

    async def plan(self, hypotheses: list[Hypothesis]) -> ValidationPlan:
        request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=VALIDATION_PLANNER_SYSTEM_PROMPT,
                ),
                LLMMessage(
                    role="user",
                    content=self._build_prompt(hypotheses),
                ),
            ],
            response_format="json",
        )
        response = await self._llm.generate(request)
        plan = self._parse_response(response)
        self._validate_tools(plan)
        self._validate_hypothesis_indexes(plan, len(hypotheses))
        self._validate_action_count(plan)
        return plan

    def _build_prompt(self, hypotheses: list[Hypothesis]) -> str:
        hypothesis_lines = [
            f"{index}: {hypothesis.text}"
            for index, hypothesis in enumerate(hypotheses)
        ]
        tools = ", ".join(self._available_tools)
        return (
            "Available read-only tools: "
            f"{tools}\n\n"
            "Hypotheses to validate:\n"
            + "\n".join(hypothesis_lines)
        )

    @staticmethod
    def _parse_response(response: LLMResponse) -> ValidationPlan:
        content = response.content.strip()
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Validation planner returned invalid JSON") from exc

        return ValidationPlan.model_validate(payload)

    def _validate_tools(self, plan: ValidationPlan) -> None:
        allowed = set(self._available_tools)
        invalid = [
            action.action_tool
            for action in plan.actions
            if action.action_tool not in allowed
        ]
        if invalid:
            raise ValueError(
                "Validation planner proposed unavailable tools: "
                + ", ".join(sorted(set(invalid)))
            )

    @staticmethod
    def _validate_hypothesis_indexes(
        plan: ValidationPlan,
        hypothesis_count: int,
    ) -> None:
        invalid = [
            action.hypothesis_index
            for action in plan.actions
            if action.hypothesis_index < 0
            or action.hypothesis_index >= hypothesis_count
        ]
        if invalid:
            raise ValueError(
                "Validation planner proposed invalid hypothesis indexes: "
                + ", ".join(str(index) for index in sorted(set(invalid)))
            )

    @staticmethod
    def _validate_action_count(plan: ValidationPlan) -> None:
        if len(plan.actions) > MAX_VALIDATION_ACTIONS:
            raise ValueError(
                "Validation planner proposed too many actions: "
                f"{len(plan.actions)} > {MAX_VALIDATION_ACTIONS}"
            )
