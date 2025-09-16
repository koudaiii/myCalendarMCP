"""Clean version of macOS Calendar MCP Server implementation."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

try:
    import EventKit
    import Foundation

    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False


class CalendarMCPServer:
    """MCP Server for macOS Calendar integration."""

    def __init__(self):
        self.server = Server("calendar-mcp")
        self.event_store = None

        # EventKit の初期化
        if EVENTKIT_AVAILABLE:
            try:
                self.event_store = EventKit.EKEventStore.alloc().init()
                # EventKit framework initialized successfully
            except Exception:
                # EventKit initialization error
                pass
        else:
            # EventKit framework not available
            pass

        self._setup_handlers()
        # MCP handlers have been set up

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available calendar resources."""
            return [
                Resource(
                    uri="calendar://events",
                    name="Calendar Events",
                    description="Access to calendar events",
                    mimeType="application/json",
                ),
                Resource(
                    uri="calendar://calendars",
                    name="Calendars",
                    description="List of available calendars",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read calendar resource."""
            if uri == "calendar://events":
                events = await self._get_events()
                return json.dumps(events, indent=2)
            elif uri == "calendar://calendars":
                calendars = await self._get_calendars()
                return json.dumps(calendars, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available calendar tools."""
            return [
                Tool(
                    name="get_events",
                    description="Get calendar events for a date range",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date (YYYY-MM-DD)",
                            },
                            "calendar_name": {
                                "type": "string",
                                "description": "Calendar name (optional)",
                            },
                        },
                        "required": ["start_date", "end_date"],
                    },
                ),
                Tool(
                    name="create_event",
                    description="Create a new calendar event",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Event title"},
                            "start_date": {
                                "type": "string",
                                "description": "Start date and time (YYYY-MM-DD HH:MM)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date and time (YYYY-MM-DD HH:MM)",
                            },
                            "calendar_name": {
                                "type": "string",
                                "description": "Calendar name (optional)",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Event notes (optional)",
                            },
                        },
                        "required": ["title", "start_date", "end_date"],
                    },
                ),
                Tool(
                    name="list_calendars",
                    description="List all available calendars",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_events":
                    events = await self._get_events(
                        start_date=arguments.get("start_date"),
                        end_date=arguments.get("end_date"),
                        calendar_name=arguments.get("calendar_name"),
                    )
                    return [TextContent(type="text", text=json.dumps(events, indent=2))]

                elif name == "create_event":
                    result = await self._create_event(
                        title=arguments["title"],
                        start_date=arguments["start_date"],
                        end_date=arguments["end_date"],
                        calendar_name=arguments.get("calendar_name"),
                        notes=arguments.get("notes"),
                    )
                    return [
                        TextContent(
                            type="text", text=f"Event created successfully: {result}"
                        )
                    ]

                elif name == "list_calendars":
                    calendars = await self._get_calendars()
                    return [
                        TextContent(type="text", text=json.dumps(calendars, indent=2))
                    ]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_calendars(self) -> List[Dict[str, Any]]:
        """Get list of calendars."""
        if not EVENTKIT_AVAILABLE or not self.event_store:
            return [{"error": "EventKit not available"}]

        try:
            calendars = self.event_store.calendarsForEntityType_(
                EventKit.EKEntityTypeEvent
            )
            result = []
            for calendar in calendars:
                result.append(
                    {
                        "title": str(calendar.title()),
                        "identifier": str(calendar.calendarIdentifier()),
                        "type": str(calendar.type()),
                        "allowsContentModifications": bool(
                            calendar.allowsContentModifications()
                        ),
                    }
                )
            return result
        except Exception as e:
            return [{"error": f"Failed to get calendars: {str(e)}"}]

    async def _get_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        calendar_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get calendar events."""
        if not EVENTKIT_AVAILABLE or not self.event_store:
            return [{"error": "EventKit not available"}]

        try:
            # Default to today and next 7 days
            if not start_date:
                start = Foundation.NSDate.date()
            else:
                start = Foundation.NSDate.dateWithTimeIntervalSince1970_(
                    datetime.strptime(start_date, "%Y-%m-%d").timestamp()
                )

            if not end_date:
                end = Foundation.NSDate.dateWithTimeIntervalSinceNow_(7 * 24 * 60 * 60)
            else:
                end = Foundation.NSDate.dateWithTimeIntervalSince1970_(
                    datetime.strptime(end_date, "%Y-%m-%d").timestamp()
                )

            calendars = self.event_store.calendarsForEntityType_(
                EventKit.EKEntityTypeEvent
            )
            predicate = (
                self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                    start, end, calendars
                )
            )

            events = self.event_store.eventsMatchingPredicate_(predicate)
            result = []

            for event in events:
                if calendar_name and str(event.calendar().title()) != calendar_name:
                    continue

                result.append(
                    {
                        "title": str(event.title()) if event.title() else "No Title",
                        "start": str(event.startDate()),
                        "end": str(event.endDate()),
                        "calendar": str(event.calendar().title()),
                        "notes": str(event.notes()) if event.notes() else "",
                        "allDay": bool(event.allDay()),
                    }
                )

            return result
        except Exception as e:
            return [{"error": f"Failed to get events: {str(e)}"}]

    async def _create_event(
        self,
        title: str,
        start_date: str,
        end_date: str,
        calendar_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Create a new event."""
        if not EVENTKIT_AVAILABLE or not self.event_store:
            return "EventKit not available"

        try:
            # Request access to calendar
            access_granted = self.event_store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeEvent, None
            )

            if not access_granted:
                return "Calendar access denied"

            event = EventKit.EKEvent.eventWithEventStore_(self.event_store)
            event.setTitle_(title)

            # Parse dates
            start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M")

            event.setStartDate_(
                Foundation.NSDate.dateWithTimeIntervalSince1970_(start_dt.timestamp())
            )
            event.setEndDate_(
                Foundation.NSDate.dateWithTimeIntervalSince1970_(end_dt.timestamp())
            )

            if notes:
                event.setNotes_(notes)

            # Find calendar
            calendars = self.event_store.calendarsForEntityType_(
                EventKit.EKEntityTypeEvent
            )
            target_calendar = None

            if calendar_name:
                for cal in calendars:
                    if str(cal.title()) == calendar_name:
                        target_calendar = cal
                        break

            if not target_calendar:
                target_calendar = self.event_store.defaultCalendarForNewEvents()

            event.setCalendar_(target_calendar)

            # Save event
            success = self.event_store.saveEvent_span_error_(
                event, EventKit.EKSpanThisEvent, None
            )

            if success:
                return f"Event '{title}' created successfully"
            else:
                return "Failed to save event"

        except Exception as e:
            return f"Failed to create event: {str(e)}"


async def main():
    """Main entry point for the MCP server."""
    # Starting macOS Calendar MCP Server
    # Waiting for MCP protocol communication
    # Press Ctrl+C to exit

    server_instance = CalendarMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            server_instance.server.create_initialization_options(),
        )
