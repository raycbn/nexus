# NEXUS Fault Injection Framework

## Overview

The Fault Injection Framework provides a controlled, deterministic, and reversible mechanism for injecting infrastructure faults into the NEXUS lab environment. It enables testing of investigation workflows under adverse conditions without affecting production systems.

## Architecture

```
FaultInjection Framework
    │
    ├── FaultScenarioRegistry (singleton)
    │       │
    │       ├── api_latency      → Uses /api/slow?seconds=N endpoint
    │       ├── api_failure      → Uses /api/error endpoint (HTTP 500)
    │       ├── redis_unavailable  → Pauses lab-redis container
    │       └── postgres_unavailable → Pauses lab-postgres container
    │
    ├── DockerClient (low-level Docker operations)
    │       ├── pause_container() / unpause_container()
    │       ├── start_container() / stop_container()
    │       └── get_container_status()
    │
    ├── Scenarios (implement FaultScenarioBase)
    │       ├── activate() → ScenarioResult
    │       └── deactivate() → ScenarioResult
    │
    └── FaultScenario (domain model)
            ├── id: FaultScenarioId
            ├── state: ScenarioState
            ├── config: dict
            └── error: str | None
```

## Scenarios

### 1. api_latency
- **Mechanism**: Sets `LAB_APP_SLOW_SECONDS` environment variable, which the `GetApplicationHealthTool` reads to call `/api/slow?seconds=N`
- **Effect**: Increases API latency for the `/api/slow` endpoint
- **Config**: `latency_seconds` (1-30, default: 3)
- **Reversibility**: Removes environment variable on deactivation

### 2. api_failure
- **Mechanism**: Uses existing `/api/error` endpoint which always returns HTTP 500
- **Effect**: Simulates API failure condition
- **Config**: None required (endpoint always exists)
- **Reversibility**: No cleanup needed (endpoint always available)

### 3. redis_unavailable
- **Mechanism**: Pauses the `lab-redis` Docker container using `docker pause`
- **Effect**: Makes Redis unavailable to the application; `/api/redis` returns 503/timeout
- **Config**: None
- **Reversibility**: `docker unpause lab-redis`

### 4. postgres_unavailable
- **Mechanism**: Pauses the `lab-postgres` Docker container using `docker pause`
- **Effect**: Makes PostgreSQL unavailable; `/api/db` returns 503/timeout
- **Config**: None
- **Reversibility**: `docker unpause lab-postgres`

## Safety & Isolation

- **No LLM Access**: Fault injection is never exposed as agent tools
- **No Arbitrary Docker Commands**: Only predefined container operations
- **No Arbitrary Container Targeting**: Only predefined lab containers
- **Explicit Activation**: Requires explicit `registry.activate()` call
- **Reversible**: All scenarios implement `deactivate()` for cleanup
- **Lab-Scoped**: Only affects NEXUS lab containers (`lab-redis`, `lab-postgres`, `linux-lab-01`)
- **Test Fixture Cleanup**: Pytest fixtures ensure cleanup even on test failure

## Usage

### Registry Access
```python
from packages.fault_injection import get_registry, FaultScenarioId

registry = get_registry()
```

### Activate Scenario
```python
result = registry.activate("api_latency")
assert result.success
```

### Deactivate Scenario
```python
result = registry.deactivate("api_latency")
assert result.success
```

### Check Status
```python
scenario = registry.get("api_latency")
print(scenario.is_active())  # True/False
print(scenario.state)  # "inactive" | "activating" | "active" | "deactivating" | "failed"
```

## Running Tests

### Deterministic Unit Tests
```bash
pytest tests/unit/fault_injection/ -v
```
Tests scenario lifecycle, registry, docker client mocks - no Docker required.

### Live Tests (Requires Docker Lab)
```bash
# Start lab
docker compose -f infrastructure/lab/compose.yml up -d

# Run all live tests
pytest tests/live/test_fault_injection_live.py -m live -v

# Run investigation integration test
pytest tests/live/test_investigation_fault_integration.py -m live -v

# Run all live tests
pytest tests/live/ -m live -v
```

## Investigation Engine Integration

The Fault Injection Framework integrates with the Investigation Engine for end-to-end testing:

```python
from packages.fault_injection import get_registry, FaultScenarioId
from packages.investigations.engine import InvestigationEngine

# 1. Activate fault
fault_registry = get_registry()
fault_registry.activate(FaultScenarioId.API_LATENCY)

# 2. Run investigation
engine = InvestigationEngine(runtime=runtime, agent=agent, allowed_tool_identifiers=...)
state1 = await engine.run_collection_phase(...)

# 3. Form hypothesis
hypothesis = engine.form_hypothesis(text="API slowness caused by /api/slow latency")

# 4. Validate with application health tool
state2 = await engine.run_validation_phase(...)

# 5. Validate hypothesis
engine.validate_hypothesis(
    hypothesis, "get_application_health", "...", validation_result, passed=True
)

# 6. Conclude
engine.conclude(finding="...", confidence=0.95)

# 6. Clean up
fault_registry.deactivate("api_latency")
```

## Configuration

Environment variables (in `.env` or `infrastructure/lab/.env`):
- `LAB_APP_SLOW_SECONDS`: Default latency for `/api/slow` endpoint (default: 2)
- `LAB_APP_BASE_URL`: Base URL for application health checks (default: `http://localhost:8080`)

Docker Compose: `infrastructure/lab/compose.yml` defines the lab infrastructure.

## Limitations

1. **Container Pause Semantics**: `docker pause` uses cgroups freezer - processes are frozen but memory preserved. Not equivalent to network partition or crash.

2. **Recovery Time**: Services need 2-5 seconds to recover after unpause. Tests include `time.sleep()` for recovery.

3. **Container State**: If a test fails mid-run, containers may remain paused. Pytest fixtures handle cleanup, but manual intervention may be needed if pytest crashes.

4. **No Network Partition**: Cannot simulate network partitions between containers - only full service unavailability.

5. **No Resource Exhaustion**: Cannot simulate CPU/memory/disk exhaustion (would require cgroups manipulation beyond pause).

6. **Single Lab Instance**: Framework assumes single lab instance. Multiple concurrent fault injections on same service not supported.

7. **Environment Variable Scope**: `LAB_APP_SLOW_SECONDS` affects all tools in process. Not thread-safe for concurrent scenarios.

## Security Considerations

- **No Credentials in Code**: Docker client uses host Docker daemon socket
- **No Arbitrary Commands**: Only `docker pause/unpause/start/stop/inspect` on predefined containers
- **No Secret Leakage**: Scenario configs don't contain secrets
- **Audit Trail**: All activations/deactivations logged via `ScenarioResult`

## Troubleshooting

### Container Already Paused
```bash
docker unpause lab-redis
docker unpause lab-postgres
```

### Services Not Recovering
```bash
docker compose -f infrastructure/lab/compose.yml restart redis postgres
```

### Lab Not Running
```bash
cd infrastructure/lab && docker compose -f compose.yml up -d
```

### Verify Lab Health
```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/status
curl http://localhost:8080/api/redis
curl http://localhost:8080/api/db
```