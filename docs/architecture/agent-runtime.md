# Agent Runtime

This document describes the NEXUS Agent Runtime - the orchestration engine that drives autonomous AI agents to investigate operational incidents.

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ objective
       ▼
┌──────────────┐
│ AgentRuntime │◄── orchestrates the loop
└──────┬───────┘
       │ asks for decisions
       ▼
┌──────────────┐
│  LLMProvider │◄── LLM provider (Ollama, etc.)
└──────┬───────┘
       │ decision (tool call or final answer)
       ▼
┌──────────────┐
│  ToolRegistry │◄── registered tools
└──────┬───────┘
       │ validate tool
       ▼
┌──────────────┐
│  Policy      │◄── authorization/risk decisions
└──────┬───────┘
       │ allowed/denied
       ▼
┌──────────────┐
│  Tool        │◄── concrete tool implementation
└──────┬───────┘
       │ execution result
       ▼
┌──────────────┐
│ Observation  │◄── recorded for LLM context
└──────────────┘
       │ observation
       ▼
┌──────────────┐
│  LLMProvider │◄── sends observation back
└──────┬───────┘
       │ final answer
       ▼
┌──────────────┐
│  FinalResult │
└──────────────┘
```

## Execution Loop

```
1. Receive objective and agent configuration
2. Prepare available tools (from registry, filtered by agent config)
3. Send objective as user message to LLM
4. Loop:
   a. LLM returns response (tool calls or final answer)
   b. Emit llm_response_received event
   c. If tool calls:
      i. For each tool call:
         - Emit tool_requested event
         - Look up tool in registry
         - If not found: emit tool_denied (unknown tool)
         - If found: evaluate policy
           - If denied: emit tool_denied
           - If allowed: emit tool_allowed
           - Execute tool
           - If success: emit tool_executed, record observation
           - If failure: emit tool_executed (failure), record error
      ii. Send observations back to LLM as tool messages
   d. If final answer:
      - Store result
      - Emit agent_completed
      - Break loop
5. Enforce max_iterations limit
6. Return structured AgentState
```

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `AgentRuntime` | Orchestrates the execution loop, enforces limits, records state |
| `LLMProvider` | Abstract interface for LLM providers (Ollama, Mock, etc.) |
| `MockLLMProvider` | Deterministic scripted provider for testing |
| `ToolRegistry` | Registers, retrieves, and lists tools; prevents duplicates |
| `PolicyEvaluator` | Evaluates whether a tool may be executed given policy and agent config |
| `Tool` | Abstract interface for tools (metadata + execution) |
| `AgentState` | Runtime state container (objective, messages, observations, result) |

## Security Model

- All tools are read-only by default in v0.1
- Non-read-only tools are always denied
- Unknown tools are denied
- Policy evaluator runs before every tool execution
- Every significant action produces a runtime event for observability

## Error Handling

The runtime handles these error conditions explicitly:

| Condition | Behavior |
|-----------|----------|
| Unknown tool | Record observation, continue loop |
| Policy violation | Record denied observation, continue loop |
| Maximum iterations exceeded | Set status to max_iterations |
| Malformed LLM response | Runtime handles via LLMResponse schema validation |
| Tool execution failure | Record error observation, continue loop |
| LLM provider failure | Set status to failed, break loop |

## State Lifecycle

```
PENDING → RUNNING → COMPLETED
                     ↘ FAILED
                     ↘ MAX_ITERATIONS
```
