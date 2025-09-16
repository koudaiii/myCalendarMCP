"""Entry point for the Calendar MCP server."""

import asyncio
import signal
import sys

from .server import main

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        print("\n🛑 終了中...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    setup_signal_handlers()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 終了中...")
    except SystemExit:
        pass
