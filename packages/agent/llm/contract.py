from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    tools: list[str] = Field(default_factory=list)
    response_format: str | dict[str, Any] | None = None


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    thinking: str = ""

    @property
    def is_final_answer(self) -> bool:
        return len(self.tool_calls) == 0 and bool(self.content)

    @property
    def wants_tool_execution(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProviderError(RuntimeError):
    """Base error for provider-level failures."""


class LLMRateLimitError(LLMProviderError):
    """Provider rejected the request because a rate limit was reached."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
