"""Entry point for the Calendar MCP server."""

import asyncio
import logging
import signal
import sys

from .server import main

logger = logging.getLogger(__name__)


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info("🛑 Shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_signal_handlers()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down gracefully...")
        sys.exit(0)
    except SystemExit:
        pass
