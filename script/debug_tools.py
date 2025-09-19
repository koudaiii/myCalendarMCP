import asyncio

from calendar_mcp.server import CalendarMCPServer


async def debug_tools():
    server = CalendarMCPServer()

    # Test list_resources
    await server.mcp.list_resources()

    # Test read_resource
    await server.mcp.read_resource("calendar://events")


if __name__ == "__main__":
    asyncio.run(debug_tools())
