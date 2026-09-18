# Linux Connector

## Architecture

The Linux Connector provides read-only infrastructure observation for Linux resources via SSH.

### Flow

```
Agent -> ToolRegistry -> Tool -> LinuxConnector -> SSH -> Linux target
```

The AgentRuntime invokes tools via the existing AgentRuntime tool execution path.
Tools call `LinuxConnector.execute_read()` which dispatches commands over SSH.
PolicyEvaluator checks are performed before any tool execution (in AgentRuntime).
MCP integration exposes tools through the existing MCP adapter/server layer.

### Authentication Model

The connector uses private-key authentication via `asyncssh`.
The private key path is supplied via `auth_ref` configuration parameter.
The actual private key file is resolved outside the LLM layer and never exposed to it.
The key path is never logged, printed, or included in error messages.

### Resource Mapping

Resources of type `linux_server` map to SSH endpoints via the connector configuration:
- `host`: SSH hostname/IP
- `username`: SSH username
- `auth_ref`: Path to private SSH key file

### Supported Operations

| Tool | Description |
|------|-------------|
| `get_system_info` | hostname, kernel, OS, architecture, uptime |
| `get_cpu_usage` | CPU percent, load averages, CPU count |
| `get_memory_usage` | total/used/available memory, swap |
| `get_disk_usage` | filesystem usage per mount point |
| `get_processes` | pid, name, cpu%, memory% per process |
| `get_network_listeners` | listening TCP/UDP sockets with process info |
| `get_service_status` | sshd, nginx, python API status |

### Security Constraints

- All operations are read-only (v1)
- No remediation, write operations, or sudo execution
- No arbitrary shell execution
- Commands come from static allowlisted operation map
- Private keys are never logged or exposed
- Typed connector exceptions do not leak credential paths

### Development Setup

#### Prerequisites
- Python 3.12+
- Docker Compose (for linux-lab-01)

#### Starting the Lab
```bash
docker compose -f infrastructure/lab/compose.yml up -d
```

#### Running Normal Tests (no Docker required)
```bash
pytest -m "not live"
```

#### Running Live Tests (requires running lab)
```bash
pytest infrastructure/lab/tests/test_lab_live.py -m live -v
pytest tests/live/test_linux_connector.py -m live -v
```

### Connector Lifecycle

1. Instantiate `LinuxConnector` with resource, host, username, auth_ref
2. Call `connect(resource)` to establish SSH session
3. Call tools which use `execute_read()` for operations
4. Call `disconnect(resource)` to close SSH session cleanly

### Typed Exceptions

| Exception | Trigger |
|-----------|---------|
| `ConnectorConnectionError` | SSH connection failure |
| `ConnectorAuthenticationError` | Auth failure |
| `ConnectorTimeoutError` | Command or connect timeout |
| `ConnectorCommandError` | Remote command failure |
| `ConnectorInvalidResourceError` | Unsupported resource type |
| `ConnectorUnavailableError` | Not connected |

### SSH Key Setup

```bash
cp infrastructure/lab/ssh_key.pub infrastructure/lab/linux-lab/ssh/authorized_keys
```

The `authorized_keys` file is gitignored (local only).
