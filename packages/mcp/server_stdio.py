from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from packages.mcp.server import NexusMCPServer


async def main() -> None:
    server = NexusMCPServer(name="nexus", version="0.1.0")
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(server_name="nexus", server_version="0.1.0"),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
