from packages.agent.llm.contract import LLMRequest, LLMResponse


class MockLLMProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self._call_count: int = 0
        self._call_log: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self._call_log.append(request)
        if self._call_count >= len(self._responses):
            raise StopIteration("No more scripted responses available")
        response = self._responses[self._call_count]
        self._call_count += 1
        return response

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def call_log(self) -> list[LLMRequest]:
        return self._call_log

    def reset(self) -> None:
        self._call_count = 0
        self._call_log = []
