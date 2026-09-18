# ADR 005: MCP Integration

## Status

Accepted

## Context

NEXUS needs to expose its tools and capabilities to external MCP clients (Claude Desktop, Cursor, etc.). The Model Context Protocol provides a standardized interface for tool discovery and execution. We adopted MCP SDK v2.2.0 for this integration.

## Decision

1. **Use MCP SDK v2.2.0** for server and client implementations
2. **Two-registry pattern**: Server and agent runtime maintain separate `ToolRegistry` instances to prevent identifier collisions between original tools and MCP wrappers
3. **Snake_case field names**: Use `input_schema`, `output_schema`, `structured_content`, `is_error` per MCP SDK v2.2.0 type definitions
4. **Stdio transport** for standalone MCP server operation
5. **In-process transport** for testing via `mcp.client.Client(server)`

## Alternatives Considered

- **MCP SDK v1.x**: Not viable — v1 uses camelCase (`inputSchema`, `isError`) and has different transport APIs. All code in this repo targets v2.x.
- **HTTP/streamable transport**: Stdio was chosen for simplicity and compatibility with desktop MCP clients.
- **Shared registry**: Rejected — causes infinite recursion when the MCP wrapper's `execute()` calls back to the server which holds the wrapper.

## Consequences

- Server and runtime tools are in separate registries; tool registration must happen in both places
- Tests must use in-process transport or real stdio; network-based transport is not used in tests
- `MCPToolWrapper` implements the `Tool` ABC so it integrates seamlessly into the agent runtime's policy evaluation and execution flow
- The `structured_content` field in `CallToolResult` must be populated for tools with output schemas, or MCP clients raise `RuntimeError`
