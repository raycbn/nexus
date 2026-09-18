from typing import Any

from pydantic import BaseModel

MAX_STRUCTURED_RESULT_KEYS = 100
MAX_STRUCTURED_VALUE_LENGTH = 4096
SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "key",
    "authorization",
    "credential",
    "private",
    "auth",
)


def _sanitize_key(key: str) -> bool:
    kl = key.lower()
    return not any(part in kl for part in SENSITIVE_KEY_PARTS)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value[:MAX_STRUCTURED_VALUE_LENGTH]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value[:MAX_STRUCTURED_RESULT_KEYS]]
    if isinstance(value, dict):
        return _sanitize_dict(value)
    return str(value)[:MAX_STRUCTURED_VALUE_LENGTH]


def _sanitize_dict(d: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for i, (k, v) in enumerate(d.items()):
        if i >= MAX_STRUCTURED_RESULT_KEYS:
            break
        if _sanitize_key(k):
            result[k] = _sanitize_value(v)
    return result


def extract_structured_result(result: Any) -> dict[str, Any] | None:
    """Extract and sanitize structured content from a tool execution result.

    Handles:
    - Direct dict results (Linux tools)
    - MCP wrapper results with 'structured_content' key
    """
    if not isinstance(result, dict):
        return None

    # MCP wrapper returns {content, structured_content, is_error}
    if "structured_content" in result and isinstance(result["structured_content"], dict):
        return _sanitize_dict(result["structured_content"])

    # Direct dict result (Linux tools return dict with resource_id, mode, data)
    return _sanitize_dict(result)


class ToolExecutionResult(BaseModel):
    """Bounded structured result from a successful tool execution."""

    structured_content: dict[str, Any] | None = None
    summary: str | None = None

    @classmethod
    def from_result(cls, result: Any) -> "ToolExecutionResult | None":
        structured = extract_structured_result(result)
        if structured is None:
            return None
        return cls(structured_content=structured)


def sanitize_failure(exc: BaseException) -> str:
    """Return a safe failure summary without sensitive exception contents."""
    return f"tool execution failed: {type(exc).__name__}"


def sanitize_observation_failure(exc: BaseException) -> str:
    return "Tool execution failed"
