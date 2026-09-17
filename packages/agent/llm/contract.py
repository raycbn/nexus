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


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    tools: list[str] = Field(default_factory=list)


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)

    @property
    def is_final_answer(self) -> bool:
        return len(self.tool_calls) == 0 and bool(self.content)

    @property
    def wants_tool_execution(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
