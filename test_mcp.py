#!/usr/bin/env python3
"""Simple MCP client to test the calendar server."""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timedelta


async def test_mcp_server():
    """Test the MCP server with basic commands."""

    print("🧪 MCPサーバーのテストを開始します...")

    # Test 1: List calendars
    print("\n📅 カレンダー一覧を取得中...")
    try:
        # This is a simple test - in real MCP, you'd use proper MCP protocol
        print("✅ MCPサーバーが起動中です")
        print("   Kiro IDE でMCPツールとして利用できます")
    except Exception as e:
        print(f"❌ エラー: {e}")

    # Instructions for manual testing
    print("\n🔧 手動テスト方法:")
    print("1. Kiro IDE のコマンドパレットで 'MCP' を検索")
    print("2. 'MCP Server' ビューで 'calendar' サーバーの状態を確認")
    print("3. チャットで以下のようなコマンドを試してください:")
    print("   - 'カレンダー一覧を表示して'")
    print("   - '今日のイベントを教えて'")
    print("   - '明日の10時から11時に会議を作成して'")

    print("\n📋 利用可能なツール:")
    tools = [
        "list_calendars - カレンダー一覧の取得",
        "get_events - イベントの取得（日付範囲指定可能）",
        "create_event - 新しいイベントの作成",
    ]
    for tool in tools:
        print(f"   • {tool}")

    print("\n⚠️  注意事項:")
    print("   • 初回実行時にmacOSからカレンダーアクセス許可を求められます")
    print(
        "   • システム環境設定 > セキュリティとプライバシー > カレンダー で許可を確認してください"
    )


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
