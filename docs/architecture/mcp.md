# MCP Integration

NEXUS integrates with the Model Context Protocol (MCP) v2.2.0 to expose tools and resources to MCP clients (e.g., Claude Desktop, Cursor, or other MCP-compatible applications).

## Architecture

The MCP integration consists of four components:

| Component | File | Role |
|-----------|------|------|
| `NexusMCPServer` | `packages/mcp/server.py` | Wraps `mcp.server.Server`, registers tools from a `ToolRegistry` |
| `MCPToolClient` | `packages/mcp/client.py` | Connects to an MCP server, lists/calls tools, wraps results |
| `MCPAdapter` | `packages/mcp/adapter.py` | Converts between NEXUS `Tool` objects and MCP `Tool` definitions |
| Events | `packages/mcp/events.py` | Pydantic models for MCP connection and tool-call events |
| Stdio entry point | `packages/mcp/server_stdio.py` | Launches the server over stdio for standalone use |

## Tool Flow

```
ToolRegistry (server side)
    → NexusMCPServer._on_list_tools() → MCP Tool definitions
    → MCPToolClient.list_tools() → discovered MCP tools
    → MCPToolWrapper (registered in runtime registry)
    → AgentRuntime calls wrapper.execute() → MCPToolClient.call_tool()
    → NexusMCPServer._on_call_tool() → original Tool.execute()
```

## Running the MCP Server

```bash
python -m packages.mcp.server_stdio
```

This starts a Nexus MCP server over stdio. Configure it in Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "nexus": {
      "command": "python",
      "args": ["-m", "packages.mcp.server_stdio"]
    }
  }
}
```

## Key Design Decisions

- **Two registries**: The server uses its own `ToolRegistry` (with original tools) while the agent runtime uses a separate `ToolRegistry` (with `MCPToolWrapper` instances). This prevents identifier collisions and avoids infinite recursion.
- **Snake_case MCP types**: MCP SDK v2.2.0 uses `input_schema`, `output_schema`, `structured_content`, and `is_error` (not camelCase).
- **Structured content**: `NexusMCPServer._on_call_tool()` populates `structured_content` from tool results when the result is a dict, ensuring MCP clients can validate outputs.
- **In-process transport**: Tests use `mcp.client.Client(server)` for direct in-process connections without network overhead.

## Event Types

MCP-specific events are defined in `packages/mcp/events.py`:

- `MCPConnectedEvent` — client connected to an MCP server
- `MCPDisconnectedEvent` — client disconnected from an MCP server
- `MCPToolDiscoveredEvent` — tool discovered via MCP listing
- `MCPToolCallStartedEvent` — initiated a tool call through MCP
- `MCPToolCallCompletedEvent` — completed a tool call through MCP
- `MCPToolCallFailedEvent` — failed a tool call through MCP
