"""Clean version of macOS Calendar MCP Server implementation."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

logger = logging.getLogger(__name__)

try:
    import EventKit
    import Foundation

    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False


class CalendarMCPServer:
    """MCP Server for macOS Calendar integration."""

    def __init__(self):
        self.mcp = FastMCP("macOS Calendar MCP Server")
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

        @self.mcp.resource("calendar://events")
        async def list_events():
            """List available calendar events."""
            events = await self._get_events()
            return json.dumps(events, indent=2)

        @self.mcp.resource("calendar://calendars")
        async def list_calendars_resource():
            """List available calendars."""
            calendars = await self._get_calendars()
            return json.dumps(calendars, indent=2)

        @self.mcp.tool()
        async def get_events(
            start_date: str, end_date: str, calendar_name: str = None
        ) -> str:
            """Get calendar events for a date range."""
            events = await self._get_events(
                start_date=start_date,
                end_date=end_date,
                calendar_name=calendar_name,
            )
            return json.dumps(events, indent=2)

        @self.mcp.tool()
        async def create_event(
            title: str,
            start_date: str,
            end_date: str,
            calendar_name: str = None,
            notes: str = None,
        ) -> str:
            """Create a new calendar event."""
            result = await self._create_event(
                title=title,
                start_date=start_date,
                end_date=end_date,
                calendar_name=calendar_name,
                notes=notes,
            )
            return f"Event created successfully: {result}"

        @self.mcp.tool()
        async def list_calendars() -> str:
            """List all available calendars."""
            calendars = await self._get_calendars()
            return json.dumps(calendars, indent=2)

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
                        "allDay": bool(event.isAllDay()),
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
    import argparse

    parser = argparse.ArgumentParser(description="macOS Calendar MCP Server")
    parser.add_argument(
        "--transport",
        type=str,
        default="sse",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport protocol to use (default: sse)",
    )
    parser.add_argument(
        "--mount-path", type=str, default=None, help="Mount path for SSE transport"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info(
        f"🚀 Starting macOS Calendar MCP Server with {args.transport} transport"
    )
    logger.info("📡 Press Ctrl+C to exit")

    server_instance = CalendarMCPServer()

    # FastMCP provides multiple transport options
    # Use the async version to avoid event loop conflicts
    if args.transport == "sse":
        await server_instance.mcp.run_sse_async(mount_path=args.mount_path)
    elif args.transport == "stdio":
        await server_instance.mcp.run_stdio_async()
    elif args.transport == "streamable-http":
        await server_instance.mcp.run_streamable_http_async()
    else:
        # Fallback for unknown transports
        server_instance.mcp.run(transport=args.transport, mount_path=args.mount_path)
