import json

from pydantic import BaseModel

from packages.agent.llm.contract import LLMMessage, LLMProvider, LLMRequest, LLMResponse

CONCLUSION_SYSTEM_PROMPT = """You are the NEXUS conclusion synthesizer.
No tools are available. Use only the supplied hypotheses and validation results.
Validation results are authoritative observations; do not contradict passed/failed values.
Do not invent measurements or claim checks that were not performed.
Return ONLY JSON:
{"finding":"string","confidence":0.0,"uncertainty":"string or null"}
Confidence must be between 0 and 1."""


class ConclusionResult(BaseModel):
    finding: str
    confidence: float = 0.0
    uncertainty: str | None = None


class ConclusionSynthesizer:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def synthesize(self, payload: dict[str, object]) -> ConclusionResult:
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=CONCLUSION_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            ],
            response_format="json",
        )
        response = await self._llm.generate(request)
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: LLMResponse) -> ConclusionResult:
        try:
            return ConclusionResult.model_validate(json.loads(response.content.strip()))
        except Exception as exc:
            raise ValueError("Conclusion synthesizer returned invalid JSON") from exc
