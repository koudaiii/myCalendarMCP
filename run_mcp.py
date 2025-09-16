#!/usr/bin/env python3
"""Simple wrapper to run MCP server with proper error handling."""

import sys
import subprocess
import signal
import os

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🛑 シャットダウンシグナル ({signum}) を受信しました")
    print("📝 MCPサーバーを終了中...")
    sys.exit(0)

def main():
    """Run the MCP server with proper error handling."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🚀 macOS Calendar MCP Server を起動中...")
        
        # Run the MCP server
        result = subprocess.run([
            sys.executable, "-m", "calendar_mcp"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\n🛑 キーボード割り込みを受信しました")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()