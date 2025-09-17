import asyncio
from calendar_mcp.server import CalendarMCPServer

async def debug_tools():
    server = CalendarMCPServer()

    # Test list_resources
    resources = await server.mcp.list_resources()
    print(f"Resources type: {type(resources)}")
    print(f"Resources: {resources}")

    # Test read_resource
    result = await server.mcp.read_resource("calendar://events")
    print(f"Read resource type: {type(result)}")
    print(f"Read resource: {result}")

if __name__ == "__main__":
    asyncio.run(debug_tools())