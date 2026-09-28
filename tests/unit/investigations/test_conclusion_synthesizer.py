import asyncio

import pytest
from packages.agent.llm.contract import LLMResponse
from packages.agent.llm.mock import MockLLMProvider
from packages.investigations.conclusion_synthesizer import ConclusionSynthesizer


def test_synthesizer_uses_validation_results():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content='{"finding":"Postgres is unhealthy",'
                '"confidence":0.9,"uncertainty":null}'
            )
        ]
    )
    result = asyncio.run(
        ConclusionSynthesizer(llm).synthesize(
            {
                "hypotheses": [{"text": "Postgres is unhealthy", "status": "validated"}],
                "validations": [{"passed": True, "actual_result": {"status": "unhealthy"}}],
            }
        )
    )
    assert result.finding == "Postgres is unhealthy"
    assert result.confidence == 0.9


def test_synthesizer_rejects_invalid_json():
    llm = MockLLMProvider([LLMResponse(content="not json")])
    with pytest.raises(ValueError, match="invalid JSON"):
        asyncio.run(ConclusionSynthesizer(llm).synthesize({"hypotheses": []}))


def test_synthesizer_requests_json():
    class CapturingLLM:
        def __init__(self):
            self.request = None

        async def generate(self, request):
            self.request = request
            return LLMResponse(content='{"finding":"ok","confidence":0.5}')

    llm = CapturingLLM()
    asyncio.run(ConclusionSynthesizer(llm).synthesize({"hypotheses": []}))
    assert llm.request.response_format == "json"
    assert llm.request.tools == []
