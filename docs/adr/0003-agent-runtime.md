# ADR 0003: Agent Runtime

## Status

Accepted

## Context

NEXUS v0.1 requires an agent runtime that can autonomously investigate operational incidents. The runtime must:

- Orchestrate a conversational loop between an LLM and tools
- Enforce security policies before tool execution
- Maintain structured state for observability and auditability
- Fail safely under all error conditions
- Be provider-neutral (not tied to Ollama or any specific LLM)

Key constraints:

- No database in v0.1 (state in memory only)
- No LangChain or LangGraph
- No autonomous remediation
- Read-only operations first
- All agent actions must be auditable

## Decision

### Core Components

The runtime consists of six core components:

1. **AgentRuntime** - Orchestration engine implementing the execution loop
2. **LLMProvider** - Abstract interface for LLM providers
3. **ToolRegistry** - Tool registration and lookup
4. **PolicyEvaluator** - Authorization and risk evaluation
5. **Tool** - Abstract tool interface with metadata and execution
6. **AgentState** - Runtime state container

### Execution Loop

The runtime implements a deterministic loop:

```
Initialize state → LLM decision → process response → repeat until final answer or max iterations
```

Each iteration:
1. Send current messages to LLM provider
2. Parse response (tool calls or final answer)
3. For each tool call: validate, evaluate policy, execute, record observation
4. Send observations back to LLM as tool messages
5. Repeat until LLM produces a final answer or max iterations reached

### LLM Provider Abstraction

The `LLMProvider` abstract class defines a single method:

```python
async def generate(self, request: LLMRequest) -> LLMResponse
```

`LLMRequest` contains messages and available tool identifiers. `LLMResponse` contains content and optional tool calls. This interface allows any LLM provider (Ollama, OpenAI, mock) to be used interchangeably.

### Mock LLM Provider

`MockLLMProvider` accepts a scripted sequence of `LLMResponse` objects. It returns them in order and raises `RuntimeError` when exhausted. It also tracks all requests for test verification.

### Tool Contract

The `Tool` abstract class provides:

- **Metadata methods**: `get_identifier()`, `get_name()`, `get_description()`, `get_input_schema()`, `get_output_schema()`, `get_risk_level()`, `is_read_only()`, `get_required_permissions()`
- **Execution method**: `async execute(parameters: dict) -> dict`

All tools are read-only by default. Non-read-only tools are rejected by the policy evaluator.

### Tool Registry

The `ToolRegistry` manages tool lifecycle:

- Register tools by their string identifier
- Retrieve tools by identifier
- List all registered tools
- Prevent duplicate registrations

### Policy Evaluator

The `PolicyEvaluator` takes a `Policy` model and evaluates whether a tool may be executed given the agent's allowed tool list. Checks are performed in order:

1. Agent has the tool in its allowed tools
2. Policy does not explicitly deny the tool
3. If policy has a non-empty allow list, tool is in it
4. Tool is read-only (v0.1 requirement)

### Agent State

`AgentState` tracks the full execution context:

- Objective, agent ID, organization ID, workspace ID
- Message history (user/assistant/tool messages)
- Tool calls requested by LLM
- Observations from tool executions
- Iteration count, final result, status

### Events

Runtime events provide observability without a database:

- `AgentStartedEvent` - Execution began
- `LLMResponseReceivedEvent` - LLM returned a response
- `ToolRequestedEvent` - LLM requested a tool call
- `ToolAllowedEvent` - Policy allowed execution
- `ToolDeniedEvent` - Policy denied execution
- `ToolExecutedEvent` - Tool executed (success/failure)
- `ObservationRecordedEvent` - Observation recorded
- `AgentCompletedEvent` - Final answer produced
- `AgentFailedEvent` - Execution failed

## Consequences

### Positive

- Provider-neutral LLM integration enables swapping providers without runtime changes
- Deterministic mock provider enables comprehensive testing
- Policy evaluation before every tool execution ensures security
- Structured state enables investigation reconstruction
- Runtime events enable observability without a database
- Explicit error handling ensures safe failure under all conditions

### Negative

- In-memory state is lost on restart (by design for v0.1)
- Policy evaluation is synchronous (async policy evaluation deferred)
- Tool execution is sequential (parallel tool calls deferred)
- Maximum iterations are global (per-agent limits deferred)

### Risks

- The execution loop may need refinement as tool complexity grows
- Policy evaluation may need to support async operations in future versions

## Alternatives Considered

1. **Using LangChain/LangGraph** - Rejected per project constraints
2. **Direct LLM calls in runtime** - Rejected in favor of provider abstraction
3. **Synchronous tool execution** - Rejected in favor of async for I/O operations
4. **Database-backed state** - Rejected for v0.1 simplicity
