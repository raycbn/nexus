# ADR 0004: Ollama LLM Provider

## Status

Accepted

## Context

NEXUS v0.2 requires a real LLM provider for the Agent Runtime. Ollama was chosen for local LLM inference. The provider must:

- Integrate with the existing `LLMProvider` interface without modifying it
- Support tool calling (multi-turn agent-tool interaction)
- Be configurable via environment variables
- Fail clearly when Ollama or the model is unavailable
- Not leak Ollama SDK types outside the provider package

## Decision

### Provider Architecture

The OllamaProvider implements `LLMProvider` and lives in `packages/agent/llm/ollama.py`. It uses the official `ollama` Python SDK internally but never exposes Ollama types outside its package.

### Async Client

The provider uses `ollama.AsyncClient` (not the synchronous `Client`) because `AgentRuntime.run()` is async and runs within an asyncio event loop. Blocking the event loop with synchronous HTTP calls would degrade concurrency.

### Configuration

Three environment variables control the provider:
- `OLLAMA_HOST` - hostname (default: localhost)
- `OLLAMA_PORT` - port (default: 11434)
- `OLLAMA_MODEL` - model name (default: nomic-embed-text)

Configuration is loaded via Pydantic Settings in `packages/domain/config.py`. The OllamaProvider reads these at initialization and does not re-read them per request.

### Dependency Constraint

The `ollama` SDK is constrained to `>=0.3.0,<1.0`:
- **Minimum 0.3.0**: First version where `AsyncClient.chat()` supports the `tools` parameter, required for tool calling.
- **Upper bound `<1.0`**: Follows semantic versioning; breaking changes may occur in the next major version.

### Tool Schema Adapter

`packages/agent/llm/adapter.py` converts `Tool` metadata into Ollama-compatible function schemas. This decouples tool implementations from Ollama. The adapter takes `Tool` instances (via the Tool contract) and produces dict schemas.

### Message Adapter

`packages/agent/llm/message_adapter.py` handles bidirectional conversion:
- NEXUS `LLMMessage` → Ollama message dicts (system, user, assistant, tool)
- Ollama response dict → NEXUS `LLMResponse` (including tool calls)

Tool results are sent back to Ollama as `tool` role messages with `tool_name` and `content` fields, per Ollama's tool-calling protocol. The assistant message containing tool calls is preserved in the conversation history between the tool request and tool result.

### Provider Lifecycle

The OllamaProvider lazily initializes the Ollama client on first `generate()` call. This avoids import-time failures when Ollama is not available (e.g., during unit tests).

## Consequences

### Positive
- AgentRuntime remains provider-neutral
- Easy to add mock providers for testing
- Configuration is environment-driven
- Clear error messages when Ollama is unavailable
- Tool and message adapters are independently testable

### Negative
- Adds `ollama` SDK dependency (not needed for MockLLMProvider)
- Ollama-specific error codes are wrapped in RuntimeError
- Tool resolution requires a ToolRegistry lookup (simplified in v0.2)

### Risks
- Ollama SDK API may change in future versions
- Tool call argument serialization assumes JSON format

## Alternatives Considered

1. **Direct Ollama calls in AgentRuntime** - Rejected; violates provider abstraction
2. **OpenAI-compatible wrapper** - Not needed; Ollama SDK is sufficient
3. **Hardcoded model/host** - Rejected; configuration is required
