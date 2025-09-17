"""Test cases for MCP tools in calendar_mcp.server."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from calendar_mcp.server import CalendarMCPServer

pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestCalendarMCPTools:
    """Test cases for MCP tools."""

    @pytest.fixture
    def server(self):
        """Create a CalendarMCPServer instance for testing."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', False):
            return CalendarMCPServer()

    @pytest.fixture
    def mock_event_store(self):
        """Create a mock EventKit event store."""
        mock_store = MagicMock()
        mock_store.calendarsForEntityType_.return_value = []
        mock_store.eventsMatchingPredicate_.return_value = []
        mock_store.defaultCalendarForNewEvents.return_value = MagicMock()
        mock_store.requestAccessToEntityType_completion_.return_value = True
        mock_store.saveEvent_span_error_.return_value = True
        return mock_store

    async def test_get_events_no_eventkit(self, server):
        """Test get_events when EventKit is not available."""
        result = await server._get_events()
        assert result == [{"error": "EventKit not available"}]

    async def test_get_calendars_no_eventkit(self, server):
        """Test get_calendars when EventKit is not available."""
        result = await server._get_calendars()
        assert result == [{"error": "EventKit not available"}]

    async def test_create_event_no_eventkit(self, server):
        """Test create_event when EventKit is not available."""
        result = await server._create_event(
            title="Test Event",
            start_date="2024-01-01 10:00",
            end_date="2024-01-01 11:00"
        )
        assert result == "EventKit not available"

    async def test_get_events_with_mock_eventkit(self, mock_event_store):
        """Test get_events with mocked EventKit."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', True):
            with patch('calendar_mcp.server.EventKit') as mock_eventkit:
                with patch('calendar_mcp.server.Foundation') as mock_foundation:
                    # Setup mocks
                    mock_foundation.NSDate.date.return_value = MagicMock()
                    mock_foundation.NSDate.dateWithTimeIntervalSinceNow_.return_value = MagicMock()
                    mock_foundation.NSDate.dateWithTimeIntervalSince1970_.return_value = MagicMock()

                    mock_event = MagicMock()
                    mock_event.title.return_value = "Test Event"
                    mock_event.startDate.return_value = "2024-01-01 10:00:00"
                    mock_event.endDate.return_value = "2024-01-01 11:00:00"
                    mock_event.calendar.return_value.title.return_value = "Calendar"
                    mock_event.notes.return_value = "Test notes"
                    mock_event.isAllDay.return_value = False

                    mock_event_store.eventsMatchingPredicate_.return_value = [mock_event]

                    server = CalendarMCPServer()
                    server.event_store = mock_event_store

                    result = await server._get_events()

                    assert len(result) == 1
                    assert result[0]["title"] == "Test Event"
                    assert result[0]["calendar"] == "Calendar"

    async def test_get_calendars_with_mock_eventkit(self, mock_event_store):
        """Test get_calendars with mocked EventKit."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', True):
            with patch('calendar_mcp.server.EventKit'):
                mock_calendar = MagicMock()
                mock_calendar.title.return_value = "Test Calendar"
                mock_calendar.calendarIdentifier.return_value = "test-id"
                mock_calendar.type.return_value = "Local"
                mock_calendar.allowsContentModifications.return_value = True

                mock_event_store.calendarsForEntityType_.return_value = [mock_calendar]

                server = CalendarMCPServer()
                server.event_store = mock_event_store

                result = await server._get_calendars()

                assert len(result) == 1
                assert result[0]["title"] == "Test Calendar"
                assert result[0]["identifier"] == "test-id"
                assert result[0]["allowsContentModifications"] is True

    async def test_create_event_with_mock_eventkit(self, mock_event_store):
        """Test create_event with mocked EventKit."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', True):
            with patch('calendar_mcp.server.EventKit') as mock_eventkit:
                with patch('calendar_mcp.server.Foundation') as mock_foundation:
                    # Setup mocks
                    mock_event = MagicMock()
                    mock_eventkit.EKEvent.eventWithEventStore_.return_value = mock_event
                    mock_foundation.NSDate.dateWithTimeIntervalSince1970_.return_value = MagicMock()

                    server = CalendarMCPServer()
                    server.event_store = mock_event_store

                    result = await server._create_event(
                        title="Test Event",
                        start_date="2024-01-01 10:00",
                        end_date="2024-01-01 11:00",
                        notes="Test notes"
                    )

                    assert "Test Event" in result
                    assert "created successfully" in result

                    # Verify event methods were called
                    mock_event.setTitle_.assert_called_once_with("Test Event")
                    mock_event.setNotes_.assert_called_once_with("Test notes")

    async def test_get_events_tool_call(self, server):
        """Test the get_events tool call through MCP handler."""
        # Get available tools
        tools = await server.mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "get_events" in tool_names

        # Call the tool through MCP
        result = await server.mcp.call_tool(
            "get_events",
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-02"
            }
        )

        # Should return tuple of (content_list, result_dict)
        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        parsed_result = json.loads(content_list[0].text)
        assert isinstance(parsed_result, list)

    async def test_create_event_tool_call(self, server):
        """Test the create_event tool call through MCP handler."""
        # Get available tools
        tools = await server.mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "create_event" in tool_names

        # Call the tool through MCP
        result = await server.mcp.call_tool(
            "create_event",
            {
                "title": "Test Event",
                "start_date": "2024-01-01 10:00",
                "end_date": "2024-01-01 11:00"
            }
        )

        # Should return tuple of (content_list, result_dict)
        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        assert "EventKit not available" in content_list[0].text

    async def test_list_calendars_tool_call(self, server):
        """Test the list_calendars tool call through MCP handler."""
        # Get available tools
        tools = await server.mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "list_calendars" in tool_names

        # Call the tool through MCP
        result = await server.mcp.call_tool("list_calendars", {})

        # Should return tuple of (content_list, result_dict)
        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        parsed_result = json.loads(content_list[0].text)
        assert isinstance(parsed_result, list)

    async def test_get_events_with_date_filters(self, mock_event_store):
        """Test get_events with specific date filters."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', True):
            with patch('calendar_mcp.server.EventKit'):
                with patch('calendar_mcp.server.Foundation') as mock_foundation:
                    mock_foundation.NSDate.dateWithTimeIntervalSince1970_.return_value = MagicMock()

                    server = CalendarMCPServer()
                    server.event_store = mock_event_store

                    result = await server._get_events(
                        start_date="2024-01-01",
                        end_date="2024-01-31",
                        calendar_name="Work"
                    )

                    # Should call the mock methods
                    mock_event_store.predicateForEventsWithStartDate_endDate_calendars_.assert_called_once()
                    mock_event_store.eventsMatchingPredicate_.assert_called_once()

    async def test_create_event_access_denied(self, mock_event_store):
        """Test create_event when calendar access is denied."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', True):
            with patch('calendar_mcp.server.EventKit'):
                mock_event_store.requestAccessToEntityType_completion_.return_value = False

                server = CalendarMCPServer()
                server.event_store = mock_event_store

                result = await server._create_event(
                    title="Test Event",
                    start_date="2024-01-01 10:00",
                    end_date="2024-01-01 11:00"
                )

                assert result == "Calendar access denied"

    async def test_create_event_save_failure(self, mock_event_store):
        """Test create_event when save operation fails."""
        with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', True):
            with patch('calendar_mcp.server.EventKit') as mock_eventkit:
                with patch('calendar_mcp.server.Foundation') as mock_foundation:
                    mock_event_store.saveEvent_span_error_.return_value = False
                    mock_eventkit.EKEvent.eventWithEventStore_.return_value = MagicMock()
                    mock_foundation.NSDate.dateWithTimeIntervalSince1970_.return_value = MagicMock()

                    server = CalendarMCPServer()
                    server.event_store = mock_event_store

                    result = await server._create_event(
                        title="Test Event",
                        start_date="2024-01-01 10:00",
                        end_date="2024-01-01 11:00"
                    )

                    assert result == "Failed to save event"

    async def test_tool_registration(self, server):
        """Test that MCP tools are properly registered."""
        tools = await server.mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        expected_tools = ["get_events", "create_event", "list_calendars"]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    async def test_get_events_tool_with_all_parameters(self, server):
        """Test get_events tool with all parameters."""
        result = await server.mcp.call_tool(
            "get_events",
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "calendar_name": "Work"
            }
        )

        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        parsed_result = json.loads(content_list[0].text)
        assert isinstance(parsed_result, list)

    async def test_create_event_tool_with_all_parameters(self, server):
        """Test create_event tool with all parameters."""
        result = await server.mcp.call_tool(
            "create_event",
            {
                "title": "Important Meeting",
                "start_date": "2024-02-15 14:00",
                "end_date": "2024-02-15 15:30",
                "calendar_name": "Work",
                "notes": "Quarterly review meeting"
            }
        )

        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        assert "EventKit not available" in content_list[0].text

    async def test_tool_error_handling(self, server):
        """Test error handling in tool calls."""
        # Test with invalid date format
        result = await server.mcp.call_tool(
            "get_events",
            {
                "start_date": "invalid-date",
                "end_date": "2024-01-01"
            }
        )

        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        parsed_result = json.loads(content_list[0].text)
        assert isinstance(parsed_result, list)

    async def test_resource_handlers(self, server):
        """Test MCP resource handlers."""
        resources = await server.mcp.list_resources()
        resource_uris = [str(resource.uri) for resource in resources]
        expected_resources = ["calendar://events", "calendar://calendars"]

        for resource_uri in expected_resources:
            assert resource_uri in resource_uris, f"Resource {resource_uri} not registered"

    async def test_list_events_resource(self, server):
        """Test calendar://events resource."""
        result = await server.mcp.read_resource("calendar://events")

        assert len(result) > 0
        assert result[0].mime_type == "text/plain"
        parsed_result = json.loads(result[0].content)
        assert isinstance(parsed_result, list)

    async def test_list_calendars_resource(self, server):
        """Test calendar://calendars resource."""
        result = await server.mcp.read_resource("calendar://calendars")

        assert len(result) > 0
        assert result[0].mime_type == "text/plain"
        parsed_result = json.loads(result[0].content)
        assert isinstance(parsed_result, list)

    async def test_mcp_server_initialization(self):
        """Test MCP server initialization."""
        server = CalendarMCPServer()
        assert server.mcp is not None
        assert hasattr(server, 'event_store')

    async def test_tool_response_format(self, server):
        """Test that tool responses are properly formatted."""
        # Test get_events response format
        result = await server.mcp.call_tool(
            "get_events",
            {"start_date": "2024-01-01", "end_date": "2024-01-02"}
        )

        # Should be valid JSON
        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        try:
            parsed = json.loads(content_list[0].text)
            assert isinstance(parsed, list)
        except json.JSONDecodeError:
            pytest.fail("get_events tool did not return valid JSON")

        # Test create_event response format
        result = await server.mcp.call_tool(
            "create_event",
            {
                "title": "Test",
                "start_date": "2024-01-01 10:00",
                "end_date": "2024-01-01 11:00"
            }
        )

        # Should be a string message
        content_list, result_dict = result
        assert len(content_list) > 0
        assert content_list[0].type == "text"
        assert isinstance(content_list[0].text, str)
        assert len(content_list[0].text) > 0