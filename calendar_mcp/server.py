"""Clean version of macOS Calendar MCP Server implementation."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

logger = logging.getLogger(__name__)

# JSONデータのログ出力用ロガー
json_logger = logging.getLogger(f"{__name__}.json_data")
json_logger.setLevel(logging.INFO)


def log_json_data(data_type: str, data: Any, direction: str = ""):
    """JSON データをログ出力する"""
    try:
        if isinstance(data, (dict, list)):
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            json_str = str(data)

        prefix = f"[{direction}] " if direction else ""
        json_logger.info(f"{prefix}{data_type}:\n{json_str}")
    except Exception as e:
        json_logger.error(f"Failed to log {data_type}: {e}")


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
            logger.info("EventKit framework is available, initializing...")
            try:
                self.event_store = EventKit.EKEventStore.alloc().init()
                logger.info("EventKit framework initialized successfully")
                log_json_data(
                    "EVENTKIT INIT",
                    {"status": "success", "event_store": "initialized"},
                    "SYSTEM",
                )
            except Exception as e:
                logger.error(f"EventKit initialization failed: {e}")
                log_json_data(
                    "EVENTKIT INIT", {"status": "error", "error": str(e)}, "SYSTEM"
                )
        else:
            logger.warning("EventKit framework not available")
            log_json_data(
                "EVENTKIT INIT",
                {"status": "unavailable", "reason": "EventKit not installed"},
                "SYSTEM",
            )

        self._setup_handlers()
        logger.info("MCP handlers have been set up")

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.mcp.resource("calendar://events")
        async def list_events():
            """List available calendar events."""
            log_json_data("RESOURCE REQUEST", {"uri": "calendar://events"}, "INCOMING")
            events = await self._get_events()
            log_json_data("RESOURCE RESPONSE", events, "OUTGOING")
            return json.dumps(events, indent=2)

        @self.mcp.resource("calendar://calendars")
        async def list_calendars_resource():
            """List available calendars."""
            log_json_data(
                "RESOURCE REQUEST", {"uri": "calendar://calendars"}, "INCOMING"
            )
            calendars = await self._get_calendars()
            log_json_data("RESOURCE RESPONSE", calendars, "OUTGOING")
            return json.dumps(calendars, indent=2)

        @self.mcp.tool()
        async def get_events(
            start_date: str, end_date: str, calendar_name: str = None
        ) -> str:
            """Get calendar events for a date range."""
            args = {
                "start_date": start_date,
                "end_date": end_date,
                "calendar_name": calendar_name,
            }
            log_json_data(
                "TOOL REQUEST", {"name": "get_events", "arguments": args}, "INCOMING"
            )
            events = await self._get_events(
                start_date=start_date,
                end_date=end_date,
                calendar_name=calendar_name,
            )
            log_json_data("TOOL RESPONSE", events, "OUTGOING")
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
            args = {
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "calendar_name": calendar_name,
                "notes": notes,
            }
            log_json_data(
                "TOOL REQUEST", {"name": "create_event", "arguments": args}, "INCOMING"
            )
            result = await self._create_event(
                title=title,
                start_date=start_date,
                end_date=end_date,
                calendar_name=calendar_name,
                notes=notes,
            )
            response = f"Event created successfully: {result}"
            log_json_data("TOOL RESPONSE", {"result": response}, "OUTGOING")
            return response

        @self.mcp.tool()
        async def list_calendars() -> str:
            """List all available calendars."""
            log_json_data(
                "TOOL REQUEST", {"name": "list_calendars", "arguments": {}}, "INCOMING"
            )
            calendars = await self._get_calendars()
            log_json_data("TOOL RESPONSE", calendars, "OUTGOING")
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
            logger.info(f"Successfully retrieved {len(result)} calendars")
            return result
        except Exception as e:
            error_msg = f"Failed to get calendars: {str(e)}"
            logger.error(error_msg)
            log_json_data(
                "CALENDAR ERROR",
                {"operation": "get_calendars", "error": str(e)},
                "ERROR",
            )
            return [{"error": error_msg}]

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
            error_msg = f"Failed to get events: {str(e)}"
            logger.error(error_msg)
            log_json_data(
                "EVENT ERROR",
                {
                    "operation": "get_events",
                    "error": str(e),
                    "start_date": start_date,
                    "end_date": end_date,
                    "calendar_name": calendar_name,
                },
                "ERROR",
            )
            return [{"error": error_msg}]

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
            logger.info("Requesting calendar access permissions...")
            log_json_data(
                "CALENDAR ACCESS REQUEST",
                {"entity_type": "EKEntityTypeEvent", "operation": "create_event"},
                "SYSTEM",
            )

            access_granted = self.event_store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeEvent, None
            )

            if not access_granted:
                logger.warning("Calendar access denied by user")
                log_json_data(
                    "CALENDAR ACCESS DENIED",
                    {"reason": "user_denied_permission", "operation": "create_event"},
                    "WARNING",
                )
                return "Calendar access denied"
            else:
                logger.info("Calendar access granted")
                log_json_data(
                    "CALENDAR ACCESS GRANTED", {"operation": "create_event"}, "SYSTEM"
                )

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
                logger.info(f"Event '{title}' created successfully")
                log_json_data(
                    "EVENT CREATED",
                    {
                        "title": title,
                        "start_date": start_date,
                        "end_date": end_date,
                        "calendar": calendar_name or "default",
                        "status": "success",
                    },
                    "SYSTEM",
                )
                return f"Event '{title}' created successfully"
            else:
                logger.error("Failed to save event to calendar")
                log_json_data(
                    "EVENT SAVE FAILED",
                    {"title": title, "reason": "save_operation_failed"},
                    "ERROR",
                )
                return "Failed to save event"

        except Exception as e:
            error_msg = f"Failed to create event: {str(e)}"
            logger.error(error_msg)
            log_json_data(
                "CREATE EVENT ERROR",
                {
                    "operation": "create_event",
                    "error": str(e),
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "calendar_name": calendar_name,
                },
                "ERROR",
            )
            return error_msg


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

    # JSONロガーの設定
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(message)s"))
    json_logger.addHandler(json_handler)

    logger.info(
        f"🚀 Starting macOS Calendar MCP Server with {args.transport} transport"
    )
    logger.info("📡 Press Ctrl+C to exit")
    logger.info("📝 JSON request/response logging enabled")

    log_json_data(
        "SERVER STARTUP",
        {
            "transport": args.transport,
            "mount_path": args.mount_path,
            "timestamp": datetime.now().isoformat(),
        },
        "SYSTEM",
    )

    try:
        server_instance = CalendarMCPServer()

        # FastMCP provides multiple transport options
        # Use the async version to avoid event loop conflicts
        if args.transport == "sse":
            logger.info(f"Starting SSE server on mount path: {args.mount_path}")
            await server_instance.mcp.run_sse_async(mount_path=args.mount_path)
        elif args.transport == "stdio":
            logger.info("Starting STDIO server")
            await server_instance.mcp.run_stdio_async()
        elif args.transport == "streamable-http":
            logger.info("Starting Streamable HTTP server")
            await server_instance.mcp.run_streamable_http_async()
        else:
            logger.warning(f"Unknown transport: {args.transport}, using fallback")
            server_instance.mcp.run(
                transport=args.transport, mount_path=args.mount_path
            )
    except KeyboardInterrupt:
        logger.info("🚫 Server shutdown requested by user")
        log_json_data(
            "SERVER SHUTDOWN",
            {"reason": "user_interrupt", "timestamp": datetime.now().isoformat()},
            "SYSTEM",
        )
    except Exception as e:
        logger.error(f"Server error: {e}")
        log_json_data(
            "SERVER ERROR",
            {
                "error": str(e),
                "transport": args.transport,
                "timestamp": datetime.now().isoformat(),
            },
            "ERROR",
        )
        raise
    finally:
        logger.info("💯 Server stopped")
        log_json_data(
            "SERVER STOPPED", {"timestamp": datetime.now().isoformat()}, "SYSTEM"
        )
