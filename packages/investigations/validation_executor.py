from typing import Any

from packages.agent.runtime.execution import ToolExecutionResult
from packages.investigations.validation import ValidationAction, ValidationPlan
from packages.investigations.validation_judge import ValidationJudgments
from packages.policies.evaluator import PolicyEvaluator
from packages.tools.registry import ToolRegistry


class ValidationExecutionResult:
    def __init__(
        self,
        action: ValidationAction,
        actual_result: dict[str, Any] | None,
        success: bool,
    ) -> None:
        self.action = action
        self.actual_result = actual_result
        self.success = success
        self.passed: bool | None = None
        self.summary: str | None = None


class ValidationExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        policy: PolicyEvaluator,
        allowed_tool_identifiers: list[str],
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._allowed_tools = allowed_tool_identifiers

    async def execute(self, plan: ValidationPlan) -> list[ValidationExecutionResult]:
        results: list[ValidationExecutionResult] = []

        for action in plan.actions:
            tool = self._registry.get(action.action_tool)
            if tool is None:
                raise ValueError(f"Validation tool is not registered: {action.action_tool}")

            allowed, reason = self._policy.is_allowed(tool, self._allowed_tools)
            if not allowed:
                raise ValueError(
                    f"Validation tool denied: {reason or action.action_tool}"
                )

            raw_result = await tool.execute({})
            execution_result = ToolExecutionResult.from_result(raw_result)
            structured = (
                execution_result.structured_content
                if execution_result is not None
                else None
            )
            results.append(
                ValidationExecutionResult(
                    action=action,
                    actual_result=structured,
                    success=execution_result is not None,
                )
            )

        return results

    @staticmethod
    def apply_judgments(
        results: list[ValidationExecutionResult],
        judgments: ValidationJudgments,
    ) -> None:
        seen: set[int] = set()
        for judgment in judgments.judgments:
            if judgment.action_index in seen:
                raise ValueError(
                    f"Validation judge returned duplicate action index: "
                    f"{judgment.action_index}"
                )
            seen.add(judgment.action_index)
            result = results[judgment.action_index]
            result.passed = judgment.passed
            result.summary = judgment.summary

        missing = sorted(set(range(len(results))) - seen)
        if missing:
            raise ValueError(
                "Validation judge omitted action indexes: "
                + ", ".join(str(index) for index in missing)
            )
