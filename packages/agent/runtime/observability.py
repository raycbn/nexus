from typing import Any


class Observation:
    def __init__(self, tool_name: str, result: Any, success: bool) -> None:
        self.tool_name = tool_name
        self.result = result
        self.success = success

    def __str__(self) -> str:
        status = "success" if self.success else "failure"
        return f"[{self.tool_name}] {status}: {self.result}"


class InMemoryEventSink:
    def __init__(self) -> None:
        self._events: list[Any] = []

    def emit(self, event: Any) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[Any]:
        return self._events

    @property
    def count(self) -> int:
        return len(self._events)

    def get_by_type(self, event_type: type) -> list[Any]:
        return [e for e in self._events if isinstance(e, event_type)]

    def clear(self) -> None:
        self._events = []
