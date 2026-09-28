import json

from pydantic import BaseModel, Field

from packages.agent.llm.contract import LLMMessage, LLMProvider, LLMRequest, LLMResponse

VALIDATION_JUDGE_SYSTEM_PROMPT = """You are the NEXUS validation judge.
No tools are available in this phase.
For each validation result, compare the observed result with the expected condition.
Return ONLY valid JSON with exactly this shape:
{
  "judgments": [
    {
      "action_index": 0,
      "passed": true,
      "summary": "short evidence-based explanation"
    }
  ]
}
Use only the supplied observations.
Do not invent missing values.
Set passed to null when the observation is insufficient to decide.
Keep summaries compact."""


class ValidationJudgment(BaseModel):
    action_index: int
    passed: bool | None = None
    summary: str | None = None


class ValidationJudgments(BaseModel):
    judgments: list[ValidationJudgment] = Field(default_factory=list)


class ValidationJudge:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def judge(self, results: list[dict[str, object]]) -> ValidationJudgments:
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=VALIDATION_JUDGE_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=self._build_prompt(results),
                ),
            ],
            response_format="json",
        )
        response = await self._llm.generate(request)
        judgments = self._parse_response(response)
        self._validate_indexes(judgments, len(results))
        return judgments

    @staticmethod
    def _build_prompt(results: list[dict[str, object]]) -> str:
        blocks = []
        for index, result in enumerate(results):
            observed = json.dumps(
                result.get("actual_result"),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            blocks.append(
                f"{index}: tool={result['action_tool']}; "
                f"expected={result['expected_condition']}; "
                f"observed={observed}"
            )
        return "Validation results to judge:\n" + "\n".join(blocks)

    @staticmethod
    def _parse_response(response: LLMResponse) -> ValidationJudgments:
        content = response.content.strip()
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Validation judge returned invalid JSON") from exc
        return ValidationJudgments.model_validate(payload)

    @staticmethod
    def _validate_indexes(
        judgments: ValidationJudgments,
        result_count: int,
    ) -> None:
        invalid = [
            judgment.action_index
            for judgment in judgments.judgments
            if judgment.action_index < 0 or judgment.action_index >= result_count
        ]
        if invalid:
            raise ValueError(
                "Validation judge proposed invalid action indexes: "
                + ", ".join(str(index) for index in sorted(set(invalid)))
            )
