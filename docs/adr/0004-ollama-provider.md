# ADR 0004: Ollama LLM Provider

## Status

Accepted

## Context

NEXUS requires a real LLM provider for the Agent Runtime. Ollama was chosen for local LLM inference. The provider must:

- Integrate with the existing `LLMProvider` interface without modifying it
- Support tool calling (multi-turn agent-tool interaction)
- Be configurable via environment variables
- Fail clearly when Ollama or the model is unavailable
- Not leak Ollama SDK types outside the provider package
- Support thinking capability and configurable context size

## Decision

### Provider Architecture

The OllamaProvider implements `LLMProvider` and lives in `packages/agent/llm/ollama.py`. It uses the official `ollama` Python SDK internally but never exposes Ollama types outside its package.

The provider receives a `ToolRegistry` instance at construction time. This allows it to resolve tool identifiers from the request to Ollama tool schemas using the same registry that the AgentRuntime uses.

### Async Client

The provider uses `ollama.AsyncClient` (not the synchronous `Client`) because `AgentRuntime.run()` is async and runs within an asyncio event loop. Blocking the event loop with synchronous HTTP calls would degrade concurrency.

### Configuration

Six environment variables control the provider:

| Variable | Default | Purpose |
|----------|---------|---------|
| OLLAMA_HOST | 127.0.0.1 | Ollama server hostname |
| OLLAMA_PORT | 11434 | Ollama server port |
| OLLAMA_MODEL | None | Chat-capable model name (required) |
| OLLAMA_THINK | false | Thinking capability toggle |
| OLLAMA_NUM_CTX | 8192 | Context window size |
| OLLAMA_TIMEOUT | 120 | Request timeout (seconds) |

Configuration is loaded via Pydantic Settings in `packages/domain/config.py`. The OllamaProvider reads these at initialization and does not re-read them per request.

### OLLAMA_MODEL

No chat model is provided by default. The model must be configured via `OLLAMA_MODEL` environment variable. If not set, the provider raises `RuntimeError` at construction time with a clear message instructing the user to set the variable and load the model in Ollama.

### OLLAMA_THINK

Controls whether the model uses thinking/reasoning. Default is `false` for CPU-only local execution to maintain predictable agent latency. Can be set to `true` or thinking levels (`low`, `medium`, `high`) when resources allow. The value is passed as `think` parameter to Ollama's `chat()` method.

### OLLAMA_NUM_CTX

Maximum context tokens per request. Default is `8192` for local CPU inference. Passed as `options.num_ctx` in the Ollama chat request. Production deployments can increase this via environment variable.

### OLLAMA_TIMEOUT

Request timeout in seconds. Default is `120`. Set on `AsyncClient` at construction time. Prevents indefinite hangs when Ollama is unreachable or inference is slow on CPU.

### Dependency Constraint

The `ollama` SDK is constrained to `>=0.3.0,<1.0`:
- **Minimum 0.3.0**: First version where `AsyncClient.chat()` supports the `tools` parameter, required for tool calling.
- **Upper bound `<1.0`**: Follows semantic versioning; breaking changes may occur in the next major version.

### Tool Schema Adapter

`packages/agent/llm/adapter.py` converts `Tool` metadata into Ollama-compatible function schemas. This decouples tool implementations from Ollama. The adapter takes `Tool` instances (via the Tool contract) and produces dict schemas.

The provider resolves tools via the injected `ToolRegistry`, not via a local registry. This ensures the provider and runtime share the same tool set.

### Message Adapter

`packages/agent/llm/message_adapter.py` handles bidirectional conversion:
- NEXUS `LLMMessage` → Ollama message dicts (system, user, assistant, tool)
- Ollama response dict → NEXUS `LLMResponse` (including tool calls)

Tool results are sent back to Ollama as `tool` role messages with `tool_name` and `content` fields, per Ollama's tool-calling protocol. The assistant message containing tool calls is preserved in the conversation history between the tool request and tool result.

### Provider Lifecycle

The OllamaProvider lazily initializes the Ollama client on first `generate()` call. This avoids import-time failures when Ollama is not available (e.g., during unit tests). The client timeout is set at construction time.

## Consequences

### Positive
- AgentRuntime remains provider-neutral
- Easy to add mock providers for testing
- Configuration is environment-driven with clear error messages
- Tool resolution shared between runtime and provider via registry injection
- Thinking and context size configurable per deployment
- Timeout prevents indefinite hangs

### Negative
- Adds `ollama` SDK dependency (not needed for MockLLMProvider)
- Ollama-specific error codes are wrapped in RuntimeError
- Tool resolution requires a ToolRegistry lookup (shared with runtime)

### Risks
- Ollama SDK API may change in future versions
- Tool call argument serialization assumes JSON format

## Alternatives Considered

1. **Direct Ollama calls in AgentRuntime** - Rejected; violates provider abstraction
2. **OpenAI-compatible wrapper** - Not needed; Ollama SDK is sufficient
3. **Hardcoded model/host** - Rejected; configuration is required
4. **Provider creates own registry** - Rejected; would be empty and unable to resolve tools
