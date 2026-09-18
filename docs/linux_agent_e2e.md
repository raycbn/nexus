# Linux Agent End-to-End Integration

This document describes how a NEXUS agent inspects a real Linux resource through
the full stack:

```
AgentRuntime -> ToolRegistry -> PolicyEvaluator -> MCP -> Linux Tool -> LinuxConnector -> SSH -> linux-lab-01
          -> Observation -> AgentRuntime -> final response
```

## Architecture

The end-to-end path reuses the existing v0.1 building blocks without redesign:

- **AgentRuntime** (`packages/agent/runtime/runtime.py`) owns the agent loop. It
  receives an objective, an `Agent` config, and a list of allowed tool
  identifiers. Each iteration it asks the configured `LLMProvider` for a decision.
- **ToolRegistry** (`packages/tools/registry.py`) holds every available tool. The
  runtime resolves each tool request by identifier.
- **PolicyEvaluator** (`packages/policies/evaluator.py`) runs **before every**
  tool execution. A tool is allowed only when it is in the agent's
  `allowed_tool_identifiers`, not in the policy `denied_tool_ids`, and
  `is_read_only()` returns `True`. Denied and unknown tools never reach execution.
- **MCP** (`packages/mcp/server.py`, `packages/mcp/client.py`) exposes the real
  Linux tools to the runtime as `MCPToolWrapper` instances. The MCP server
  attaches each tool's `resource_mode` and `resource_id` to the tool `meta` so
  observability survives the protocol boundary.
- **Linux tools** (`packages/tools/providers/linux_tools.py`) are read-only,
  static/allowlisted commands. Each is constructed with a configured
  `LinuxConnector` and declares `get_resource_mode() == "real"`.
- **LinuxConnector** (`packages/connectors/providers/linux.py`) opens an SSH
  session via `asyncssh` and runs the single allowlisted command per tool call.
  It receives the `Resource` plus externally-resolved connection parameters
  (host, port, username, key path) — never credentials from the LLM.

### Flow diagram

```
                 +------------------+
   objective ---> | AgentRuntime     |
                 +--------+---------+
                          |  LLM decision (tool_calls)
                 +--------v---------+        +------------------+
                 | ToolRegistry     | -----> | PolicyEvaluator  |
                 +--------+---------+   deny  +------------------+
                          | allow
                 +--------v---------+        +------------------+
                 |    MCP (server<-> | -----> | MCPToolWrapper    |
                 |    client, in-proc)|        +------------------+
                          | execute
                 +--------v---------+
                 | Linux Tool        |  (resource_mode="real", read-only)
                 +--------+---------+
                          | execute_read(command)
                 +--------v---------+
                 | LinuxConnector    |  (SSH via asyncssh)
                 +--------+---------+
                          | SSH channel
                 +--------v---------+
                 | linux-lab-01      |  (real Docker target, port 2222)
                 +-------------------+
                          | observation
                          v
                 +--------+---------+
                 | AgentRuntime      |  (records events, loops)
                 +-------------------+
```

## Configuring the linux-lab-01 resource

The development resource is described by the generic `Resource` domain model
(`packages/domain/models/resource.py`) with `resource_type="linux_server"`.
Connection details are **configuration-driven**, never hardcoded in source:

| Setting              | Env var          | Default                          |
|----------------------|------------------|----------------------------------|
| SSH host             | `LAB_SSH_HOST`   | `localhost`                      |
| SSH port             | `LAB_SSH_PORT`   | `2222`                           |
| SSH username         | `LAB_SSH_USERNAME` | `nexus`                        |
| SSH private key path | `LAB_SSH_KEY_PATH` | `infrastructure/lab/ssh_key`  |

The private key **path** is configured; the key contents are never stored in
source (the file is gitignored under `infrastructure/lab/.gitignore`). The
`LinuxConnector` is built from this configuration via the factory:

```python
from packages.connectors.factory import create_connector
from packages.domain.models.resource import Resource

resource = Resource(
    organization_id=org.id,
    workspace_id=workspace.id,
    name="linux-lab-01",
    resource_type="linux_server",
)
connector = create_connector(resource)
await connector.connect(resource)
```

`create_connector` dispatches on `resource_type` and reads `NexusSettings`
(`packages/domain/config.py`) so the connector is never constructed implicitly
from tool input.

## Registering real Linux tools

`register_linux_tools(connector, registry)` builds the read-only Linux tools
wired to a configured connector and registers them in a `ToolRegistry`. These
tools are then exposed through the existing `NexusMCPServer`:

```python
from packages.connectors.factory import register_linux_tools
from packages.mcp.server import NexusMCPServer
from packages.mcp.client import MCPToolClient
from packages.tools.registry import ToolRegistry

server_registry = ToolRegistry()
register_linux_tools(connector, server_registry)

mcp_server = NexusMCPServer(name="nexus-linux", registry=server_registry)
mcp_client = MCPToolClient(server_name="nexus-linux")
await mcp_client.connect(mcp_server.server)

runtime_registry = ToolRegistry()
for tool_def in await mcp_client.list_tools():
    runtime_registry.register(mcp_client.create_tool_wrapper(tool_def))
```

Each Linux tool is associated with its `resource`, its `connector`,
`RiskLevel.LOW`, `read_only=True`, and `resource_mode="real"`.

## Observability

Every real execution is recorded via `ToolExecutedEvent`
(`packages/agent/runtime/events.py`) and includes:

- `tool_name`
- `resource_id` (the Resource UUID)
- `resource_mode` (`"real"` for Linux tools, `"simulation"` for mock tools,
  `"mcp"`/`"real"` for MCP-wrapped tools propagated via `meta`)
- `duration`
- `success` / `failure`

The `MCPToolWrapper` forwards `resource_mode` and `resource_id` from the
underlying tool through the MCP `meta` field, so observability is preserved
across the MCP boundary.

## Running the deterministic integration tests

These run without Docker or Ollama; SSH is replaced by a fake transport:

```bash
pytest tests/integration/test_linux_agent_e2e.py -v
```

They prove the complete deterministic path with a `MockLLMProvider`:

```python
AgentRuntime -> PolicyEvaluator -> Tool -> MCP -> LinuxConnector
   -> fake SSH transport -> observation -> final result
```

## Running the live Docker tests

Requires the local lab to be running (`linux-lab-01` on port 2222):

```bash
docker compose -f infrastructure/lab/compose.yml up -d
pytest tests/live/test_linux_agent_live.py -m live -v
```

These connect a real `LinuxConnector` over SSH to the Docker `linux-lab-01`
target. `test_runtime_executes_linux_tools_over_real_ssh` uses a scripted
`MockLLMProvider` plus the real SSH transport. The optional
`test_linux_agent_ollama_e2e` test additionally exercises the end-to-end path
through a real Ollama model; it is skipped automatically when Ollama is not
reachable.

Live tests are marked `@pytest.mark.live` and are excluded from the normal suite
via the default `addopts = "-m 'not live'"` in `pyproject.toml`.

## Security

- Private key paths are configuration-driven; key contents are never in source.
- The LLM never receives credentials or resource connection details.
- Linux tools execute only static, allowlisted commands — no arbitrary command
  arguments are accepted from the LLM.
- `PolicyEvaluator` runs before every tool; denied/unknown tools never reach the
  connector or generate any SSH command.
- `LinuxConnector` has no access to the Docker API.
- All tools are read-only (`is_read_only() == True`); no write/remediation
  tools are provided.
