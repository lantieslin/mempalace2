"""Entry point for running MemPalace2 MCP server."""

from .mcp_server import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())