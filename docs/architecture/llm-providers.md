# LLM Providers

NEXUS uses a provider abstraction for LLM inference. The AgentRuntime depends on the `LLMProvider` interface, never on a specific provider implementation.

## Provider Abstraction

```
┌──────────────┐
│ LLMProvider  │  (abstract interface in packages/agent/llm/contract.py)
└──────┬───────┘
       │ implements
       ▼
┌──────────────┐
│ OllamaProvider│  (packages/agent/llm/ollama.py)
└──────────────┘
┌──────────────┐
│ MockLLMProvider│ (packages/agent/llm/mock.py)
└──────────────┘
```

The `LLMProvider` interface defines a single method:

```python
async def generate(self, request: LLMRequest) -> LLMResponse
```

This keeps the AgentRuntime provider-neutral.

## Configuration

LLM provider configuration is managed through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| OLLAMA_HOST | Ollama server hostname | localhost |
| OLLAMA_PORT | Ollama server port | 11434 |
| OLLAMA_MODEL | Model name to use | nomic-embed-text |

Configuration is loaded via Pydantic Settings in `packages/domain/config.py`.

## Dependency

The `ollama` Python SDK is pinned to `>=0.3.0,<1.0` in `pyproject.toml`. Version 0.3.0 is the minimum that supports `AsyncClient.chat()` with the `tools` parameter. The upper bound `<1.0` follows semantic versioning to prevent breaking changes in a future major release.

## Async Decision

The OllamaProvider uses `ollama.AsyncClient` (not the synchronous `Client`) because `AgentRuntime.run()` is an async method that runs in an asyncio event loop. Using the synchronous client would block the event loop during HTTP requests, degrading concurrency. The `AsyncClient.chat()` method returns an awaitable and integrates naturally with the provider's async `generate()` interface.

## Message Conversion

NEXUS messages are converted to provider-specific formats in `packages/agent/llm/message_adapter.py`:

| NEXUS Role | Ollama Role | Notes |
|------------|-------------|-------|
| system | system | Direct mapping |
| user | user | Direct mapping |
| assistant | assistant | Content + tool_calls |
| tool | tool | tool_name + content |

Tool results are sent to Ollama as `tool` role messages with `tool_name` and `content` fields, per Ollama's tool-calling protocol.

Tool call arguments are JSON-serialized when sending to Ollama and parsed when receiving.

## Tool Schema Conversion

NEXUS Tool metadata is converted to Ollama tool schema via `packages/agent/llm/adapter.py`:

```
NEXUS Tool → {type: "function", function: {name, description, parameters}}
```

The adapter takes a `Tool` instance and produces Ollama-compatible schema dictionaries. Tool implementations are never coupled to Ollama types.

## Tool Calling Flow

```
1. AgentRuntime sends LLMRequest with tool identifiers
2. OllamaProvider converts identifiers → Tool schemas via ToolSchemaAdapter
3. OllamaProvider sends chat request with messages + tools
4. Ollama returns response with optional tool_calls
5. OllamaMessageAdapter converts response → LLMResponse
6. AgentRuntime processes tool calls or final answer
```

## Failure Behavior

- If Ollama is unreachable: `RuntimeError` with clear message
- If model is missing: Ollama returns error, wrapped in `RuntimeError`
- If response is malformed: `JSONDecodeError` caught, raw string preserved
- AgentRuntime handles all provider failures gracefully
