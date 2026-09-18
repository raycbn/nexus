# NEXUS Investigation Engine

## Overview

The Investigation Engine provides a structured framework for AI agents to investigate infrastructure problems. It orchestrates the existing AgentRuntime to collect observations, form hypotheses, validate them with additional evidence, and produce a structured conclusion — all while reusing the existing Agent → Tool → Policy → MCP → Connector → SSH flow.

The engine does **not** replace AgentRuntime; it consumes the structured execution results that AgentRuntime now records for every tool invocation.

## Architecture

```
InvestigationEngine
    ├── run_collection_phase()   → AgentRuntime with scripted LLM (infrastructure tools)
    ├── form_hypothesis()
    ├── run_validation_phase()   → AgentRuntime with scripted LLM (application tool)
    ├── validate_hypothesis()
    └── conclude()
```

The engine uses the same runtime, registry, policy, and MCP infrastructure as any other agent task. It simply structures the evidence produced by the runtime into an `Investigation` object.

### Flow Diagram

```
User Objective
      │
      ▼
InvestigationEngine
      │
      ├── run_collection_phase()
      │       │
      │       ▼
      │   AgentRuntime (MockLLM)
      │       │
      │       ├── get_system_info
      │       ├── get_cpu_usage
      │       ├── get_memory_usage
      │       ├── get_disk_usage
      │       ├── get_processes
      │       └── get_service_status
      │       │
      │       ▼
      │   Evidence[] (from tool_results)
      │
      ├── form_hypothesis("API slowness caused by /api/slow latency")
      │
      ├── run_validation_phase()
      │       │
      │       ▼
      │   AgentRuntime (MockLLM)
      │       │
      │       └── get_application_health
      │                │
      │                ▼
      │   Measures /api/slow latency via curl over SSH
      │
      ├── validate_hypothesis(passed=true)
      │
      └── conclude()
              │
              ▼
       Investigation object with:
       - objective
       - evidence[]
       - hypotheses[]
       - validations[]
       - conclusion (finding, confidence, uncertainty)
```

## Domain Models

### Investigation
Represents a complete investigation lifecycle.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `objective` | str | The investigation goal (e.g., "Investigate why the API is slow") |
| `status` | InvestigationStatus | `started` \| `collecting` \| `validating` \| `completed` \| `failed` |
| `started_at` | datetime | When the investigation began |
| `completed_at` | datetime \| None | When the investigation concluded |
| `evidence` | list[Evidence] | Collected observations |
| `hypotheses` | list[Hypothesis] | Proposed explanations |
| `validations` | list[Validation] | Hypothesis validation steps |
| `conclusion` | Conclusion \| None | Final finding |

### Evidence
A single piece of evidence from a tool execution.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `source_tool` | str | Tool identifier (e.g., `get_cpu_usage`) |
| `resource_id` | UUID \| None | Target resource |
| `observed_value` | dict \| str \| None | Structured tool output |
| `timestamp` | datetime | When the evidence was recorded |
| `mode` | str | `real` \| `simulation` \| `mcp` |
| `relevance` | float | 0.0–1.0, how relevant to the objective |

### Hypothesis
A proposed explanation for the observed problem.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `text` | str | Human-readable hypothesis |
| `supporting_evidence_ids` | list[UUID] | Evidence supporting the hypothesis |
| `contradicting_evidence_ids` | list[UUID] | Evidence contradicting the hypothesis |
| `status` | HypothesisStatus | `proposed` \| `supported` \| `contradicted` \| `validated` \| `unresolved` |

### Validation
A test of a hypothesis against new evidence.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `action_tool` | str | Tool used for validation |
| `expected_condition` | str | What we expected to observe |
| `actual_result` | dict \| str \| None | What we actually observed |
| `passed` | bool \| None | Whether the validation succeeded |

### Conclusion
The final finding of the investigation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `finding` | str | Human-readable conclusion |
| `confidence` | float | 0.0–1.0, confidence in the finding |
| `supporting_evidence_ids` | list[UUID] | Evidence backing the conclusion |
| `unresolved_uncertainty` | str \| None | Remaining unknowns |

## Structured Execution Results

AgentRuntime now captures a bounded, sanitized `ToolExecutionResult` for every successful tool execution:

```python
class ToolExecutionResult(BaseModel):
    structured_content: dict[str, Any] | None
    summary: str | None
```

- Extracted from the tool's return value (or MCP wrapper's `structured_content`)
- Keys/values containing sensitive terms (`password`, `secret`, `token`, etc.) are redacted
- Dictionary size and string lengths are bounded to prevent unbounded growth
- Failures are recorded with a sanitized error type (`tool execution failed: RuntimeError`) without exposing exception messages

The `ToolExecutedEvent` now includes:
- `result: ToolExecutionResult | None`
- `failure: str | None` (populated on failure)

## InvestigationEngine API

```python
engine = InvestigationEngine(
    runtime=runtime,  # AgentRuntime instance
    agent=agent,  # Agent configuration
    allowed_tool_identifiers=["get_system_info", ...],
)

# Phase 1: Collect infrastructure observations
state = await engine.run_collection_phase(
    objective="Investigate why the API is slow.",
    collection_responses=[...],  # scripted LLM responses
)

# Form a hypothesis
hypothesis = engine.form_hypothesis(
    text="The API slowness is caused by the /api/slow endpoint latency.",
    supporting_evidence_ids=[str(e.id) for e in engine.investigation.evidence],
)

# Phase 2: Validate with application health check
state = await engine.run_validation_phase(
    objective="Validate the hypothesis by checking application health.",
    validation_responses=[...],
)

# Validate hypothesis
engine.validate_hypothesis(
    hypothesis=hypothesis,
    action_tool="get_application_health",
    expected_condition="/api/slow latency >= ~2 seconds",
    actual_result=validation_result,
    passed=validation_result.get("slow_reproduced", False),
)

# Conclude
engine.conclude(
    finding="The API slowness is caused by the /api/slow endpoint...",
    confidence=0.95,
    supporting_evidence_ids=[...],
    unresolved_uncertainty="No other infrastructure bottlenecks detected.",
)
```

## Application Health Tool

The `GetApplicationHealthTool` is a read-only Linux tool that executes over SSH to check the lab application's HTTP endpoints:

| Endpoint | Check |
|----------|-------|
| `/health` | HTTP 200 |
| `/api/status` | HTTP 200 |
| `/api/db` | PostgreSQL connectivity |
| `/api/redis` | Redis connectivity |
| `/api/slow?seconds=N` | Latency measurement |

It never accepts arbitrary URLs from the LLM; all endpoints are hardcoded in the tool. Configuration is via environment:

```bash
LAB_APP_BASE_URL=http://localhost    # Base URL inside the lab container
LAB_APP_SLOW_SECONDS=2               # Delay to reproduce on /api/slow
```

Output schema:
```json
{
  "resource_id": "uuid",
  "mode": "real",
  "health": "healthy|unhealthy",
  "api_status": "healthy|unhealthy",
  "postgres": "healthy|unhealthy",
  "redis": "healthy|unhealthy",
  "slow_latency_seconds": 2.05,
  "slow_reproduced": true
}
```

## Deterministic Tests

Run the deterministic integration tests (no Docker, no Ollama):

```bash
pytest tests/integration/test_investigation.py -v
```

These tests use a fake SSH transport (`FakeSSHConnection`) that returns scripted responses for every command, including the `curl` commands used by the application health tool.

### Test Coverage
- `test_complete_investigation_flow`: Full end-to-end flow with 6 infrastructure tools + validation
- `test_unresolved_hypothesis`: Hypothesis contradicted by validation
- `test_evidence_creation_from_tool_results`: Evidence model construction
- `test_hypothesis_creation_and_status`: Hypothesis lifecycle
- `test_validation_passed`: Validation model
- `test_investigation_lifecycle`: Investigation object lifecycle

## Live Tests

Run the live tests against the Docker `linux-lab-01` target:

```bash
docker compose -f infrastructure/lab/compose.yml up -d
pytest tests/live/test_investigation_live.py -m live -v
```

### Live Test: `test_live_investigation_with_mock_llm`

1. Creates a real SSH connection to `linux-lab-01` via `LinuxConnector`
2. Registers all 7 Linux tools (6 infrastructure + 1 application health) via MCP
3. Runs the investigation engine with a scripted `MockLLMProvider`
4. Phase 1: Collects 6 infrastructure observations via real SSH
5. Phase 2: Executes `get_application_health` which runs real `curl` commands over SSH
6. Verifies:
   - All 6 infrastructure tools executed successfully
   - Application health tool returns `slow_reproduced=true`
   - Measured latency ≥ 1.5 seconds (threshold for ~2 second delay)
   - Hypothesis validated
   - Conclusion produced with confidence ≥ 0.9

### Optional Ollama Test

An optional live test using a real Ollama model is available but skipped by default. It exercises the same path with a real LLM:

```bash
pytest tests/live/test_investigation_live.py::TestInvestigationLive::test_live_investigation_ollama_e2e -m live -v
```

This test is marked `@pytest.mark.skipif` and only runs when Ollama is reachable with a compatible model.

## Running All Tests

```bash
# All non-live tests
pytest -m "not live"

# Core live tests (SSH, MCP, Linux tools)
pytest tests/live/test_linux_integration.py tests/live/test_linux_agent_live.py -m live

# Investigation live test
pytest tests/live/test_investigation_live.py -m live

# All live tests
pytest -m live
```

## Security

- No arbitrary shell commands: all commands are hardcoded in tools
- No arbitrary URLs: application health tool targets only configured endpoints
- No credentials in LLM context: SSH key path comes from config, never exposed to LLM
- No private keys in logs: execution results are sanitized
- Policy remains mandatory: every tool execution passes through `PolicyEvaluator`
- All tools are read-only (`is_read_only() == True`)

## Limitations

1. **Fake transport for deterministic tests**: The fake SSH transport matches commands by substring; it does not validate exact command structure.
2. **Latency threshold is approximate**: The test checks `latency >= 1.5s` for a 2-second configured delay; exact timing varies.
3. **Single hypothesis workflow**: The current engine supports a linear investigation (collect → hypothesize → validate → conclude). Complex multi-hypothesis workflows are not yet implemented.
4. **Ollama test is optional**: The real LLM test depends on model behavior and is skipped if Ollama is unavailable.
5. **Fake SSH connection uses `MagicMock`**: The mock returns `stdout`/`stderr`/`exit_status` attributes; it does not fully replicate `asyncssh.SSHCompletedProcess`.
6. **MCP client cleanup**: The live test fixture has a known issue with async cleanup in certain anyio versions; the test logic passes but fixture teardown may raise a benign `RuntimeError` (suppressed).