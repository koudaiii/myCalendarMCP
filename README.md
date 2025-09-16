# macOS Calendar MCP Server

An MCP (Model Context Protocol) server for accessing macOS Calendar app (EventKit).

## Features

- Get calendar events
- Create new events
- Update and delete events
- Get calendar list

## Requirements

- macOS (Apple Silicon supported)
- Python 3.8+
- EventKit framework access permission

### macOS Privacy Settings

To access the calendar, you need to grant permission in macOS privacy settings:

1. **System Settings** > **Privacy & Security** > **Calendar**
2. Turn **ON** the following applications:
   - Terminal/iTerm2 (when using CLI)

**Note**: Please restart the application after changing settings.

## Setup

```bash
# Environment setup (using uv)
./script/setup
```

## Starting MCP Server

```bash
# Start MCP server (SSE transport - HTTP mode)
./script/server

# Customize transport method
./script/server --transport sse        # SSE (HTTP) - default
./script/server --transport stdio      # Standard input/output
./script/server --transport streamable-http  # Streamable HTTP

# Run tests
./script/test
```

**HTTP Endpoints**:
- SSE: Accessible at `http://127.0.0.1:8000/sse`
- Streamable HTTP: Accessible at `http://127.0.0.1:8000` (for MCP clients)

### HTTP Transport Features and Limitations

**SSE Transport Connection:**
- Endpoint: `http://127.0.0.1:8000/sse`
- Protocol: Server-Sent Events (SSE)
- Message sending: POST `http://127.0.0.1:8000/messages`

**Streamable HTTP Transport Connection:**
- Endpoint: `http://127.0.0.1:8000/`
- Protocol: HTTP/1.1 streaming
- Bidirectional communication support


### VS Code (Claude Code) Configuration

- `$ script/server --transport sse`

**SSE Transport Configuration (settings.json or .vscode/settings.json):**
```json
{
  "claude.mcpServers": {
    "calendar-mcp": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

**Streamable HTTP Transport Configuration (settings.json or .vscode/settings.json):**

- `$ script/server --transport streamable-http`

```json
{
  "claude.mcpServers": {
    "calendar-mcp": {
      "url": "http://127.0.0.1:8000/"
    }
  }
}
```

## Direct CLI Usage

```bash
# Get events for the next 7 days
./script/query "Show me recent events"

# Get events for 3 days
./script/query -d 3 "Events for the next 3 days"

# Get events from specific calendar
./script/query -c "Work" "Work calendar events"

# Show available calendar list
./script/query -l "Show calendar list"

# Show help
./script/query -h
```

## Troubleshooting

### ❌ Cannot access calendar

**Issue**: "EventKit not available" or empty event list

**Solution**:
1. **Check privacy settings**
   ```
   System Settings > Privacy & Security > Calendar
   ```
   Turn on the Terminal you're using

2. **Restart the application**
   Always restart the application after changing settings


### ❌ uv command not found

**Issue**: "command not found: uv"

**Solution**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```