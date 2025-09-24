# MCPライブラリリファレンス

このドキュメントでは、myCalendarMCPプロジェクトで使用している主要なライブラリとその詳細な使用方法について解説します。

## 目次
- [利用しているパッケージ](#利用しているパッケージ)
- [MCPライブラリ](#mcpライブラリ)
- [EventKitライブラリ](#eventkitライブラリ)
- [その他の依存関係](#その他の依存関係)
- [開発依存関係](#開発依存関係)
- [テスト方法とコード確認手順](#テスト方法とコード確認手順)

## 利用しているパッケージ

### 主要依存関係 (pyproject.toml)

```toml
dependencies = [
    "mcp",                           # Model Context Protocol コアライブラリ
    "pyobjc-framework-EventKit",     # macOS EventKit フレームワークへのPythonバインディング
    "pyobjc-framework-Cocoa",        # macOS Cocoa フレームワークへのPythonバインディング
    "python-dateutil",               # 日付時刻処理拡張ライブラリ
]
```

### 開発依存関係

```toml
[project.optional-dependencies]
dev = [
    "pytest",                        # テストフレームワーク
    "black",                         # コードフォーマッター
    "ruff",                          # リンター・フォーマッター
]
```

## MCPライブラリ

### パッケージ情報
- **バージョン**: `mcp v1.14.0`
- **公式リポジトリ**: https://github.com/modelcontextprotocol/python-sdk
- **ドキュメント**: https://docs.anthropic.com/en/docs/mcp/

### 主要コンポーネント

#### FastMCP
MCPサーバーを簡単に構築するためのフレームワーク

```python
from mcp.server import FastMCP
from mcp.types import ToolAnnotations

# FastMCPインスタンスの作成
server = FastMCP("calendar-mcp")

# ツールの定義例
@server.tool(
    name="get_macos_calendar_events",
    description="macOSカレンダーからイベントを取得",
    annotations=ToolAnnotations(
        readOnlyHint=True,      # 読み取り専用操作
        idempotentHint=True,    # 冪等性がある
        openWorldHint=False     # 閉じた世界の仮定
    ),
)
async def get_calendar_events(start_date: str, end_date: str) -> str:
    # 実装
    pass

# リソースの定義例
@server.resource("calendar://events")
async def read_events() -> str:
    # 実装
    pass
```

#### 利用可能なトランスポート
```python
# SSE (Server-Sent Events) - 推奨
await server.run_sse_async(mount_path="/calendar")

# STDIO (標準入出力)
await server.run_stdio_async()

# Streamable HTTP
await server.run_streamable_http_async()
```

#### ToolAnnotationsの使い分け
```python
from mcp.types import ToolAnnotations

# 読み取り専用ツール
annotations=ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    openWorldHint=False
)

# データ変更ツール
annotations=ToolAnnotations(
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False
)
```

### 内部依存関係

FastMCPは以下のライブラリに依存：
- `anyio v4.10.0`: 非同期I/Oライブラリ
- `httpx v0.28.1`: HTTP クライアントライブラリ
- `pydantic v2.11.9`: データバリデーション
- `starlette v0.48.0`: ASGI Webフレームワーク
- `uvicorn v0.35.0`: ASGI サーバー

### テスト用MCPクライアント実装

```python
import json
import subprocess
import asyncio

class MCPClient:
    def __init__(self, process):
        self.process = process
        self.request_id = 0

    def send_request(self, method, params=None):
        """JSON-RPC リクエストを送信"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id,
            "params": params or {}
        }

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        self.process.stdin.flush()

        # レスポンス読み取り
        response_line = self.process.stdout.readline().decode()
        return json.loads(response_line)

    def initialize_mcp(self):
        """MCPプロトコル初期化"""
        # 初期化リクエスト
        init_response = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-client-test",
                "version": "1.0.0"
            }
        })

        # 初期化完了通知
        self.send_notification("notifications/initialized")

        return init_response

    def send_notification(self, method, params=None):
        """通知（レスポンス不要）を送信"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json.encode())
        self.process.stdin.flush()

# 使用例
async def test_mcp_client():
    # MCPサーバー起動
    process = subprocess.Popen(
        ["script/server", "--transport", "stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )

    client = MCPClient(process)

    # プロトコル初期化
    client.initialize_mcp()

    # ツール呼び出し
    response = client.send_request("tools/call", {
        "name": "list_macos_calendars",
        "arguments": {}
    })

    print(f"Response: {response}")

    process.terminate()
```

## EventKitライブラリ

### パッケージ情報
- **バージョン**: `pyobjc-framework-eventkit v11.1`
- **コア**: `pyobjc-core v11.1`
- **依存**: `pyobjc-framework-cocoa v11.1`

### 基本的な使用方法

#### EventStore初期化
```python
try:
    import EventKit
    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False
    EventKit = None

if EVENTKIT_AVAILABLE:
    # EventStoreインスタンス作成
    event_store = EventKit.EKEventStore.alloc().init()

    # カレンダーアクセス許可確認
    access_granted = event_store.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeEvent
    ) == EventKit.EKAuthorizationStatusAuthorized
```

#### カレンダー一覧取得
```python
def get_calendars():
    """利用可能なカレンダー一覧を取得"""
    if not EVENTKIT_AVAILABLE:
        return []

    calendars = event_store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
    calendar_list = []

    for calendar in calendars:
        calendar_info = {
            "title": str(calendar.title()),
            "type": str(calendar.type()),
            "allowsContentModifications": bool(calendar.allowsContentModifications()),
            "color": calendar.color().description() if calendar.color() else None,
            "source": str(calendar.source().title()) if calendar.source() else None
        }
        calendar_list.append(calendar_info)

    return calendar_list
```

#### イベント取得
```python
from datetime import datetime, timedelta
import EventKit

def get_events(start_date: datetime, end_date: datetime, calendar_name: str = None):
    """指定期間のイベントを取得"""
    if not EVENTKIT_AVAILABLE:
        return []

    # NSDateに変換
    from Foundation import NSDate
    start_ns_date = NSDate.dateWithTimeIntervalSince1970_(start_date.timestamp())
    end_ns_date = NSDate.dateWithTimeIntervalSince1970_(end_date.timestamp())

    # 述語作成
    predicate = event_store.predicateForEventsWithStartDate_endDate_calendars_(
        start_ns_date, end_ns_date, None
    )

    # イベント取得
    events = event_store.eventsMatchingPredicate_(predicate)

    event_list = []
    for event in events:
        # カレンダー名フィルタリング
        if calendar_name and str(event.calendar().title()) != calendar_name:
            continue

        event_info = {
            "title": str(event.title()) if event.title() else "",
            "start_date": event.startDate().description(),
            "end_date": event.endDate().description(),
            "calendar": str(event.calendar().title()),
            "notes": str(event.notes()) if event.notes() else "",
            "location": str(event.location()) if event.location() else "",
            "allDay": bool(event.isAllDay()),
            "url": str(event.URL()) if event.URL() else ""
        }
        event_list.append(event_info)

    return event_list
```

#### イベント作成
```python
def create_event(title: str, start_date: datetime, end_date: datetime,
                calendar_name: str = None, notes: str = "", location: str = ""):
    """新しいイベントを作成"""
    if not EVENTKIT_AVAILABLE:
        return {"success": False, "error": "EventKit not available"}

    # カレンダー取得
    calendars = event_store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
    target_calendar = None

    for calendar in calendars:
        if calendar_name is None or str(calendar.title()) == calendar_name:
            if calendar.allowsContentModifications():
                target_calendar = calendar
                break

    if not target_calendar:
        return {"success": False, "error": "No writable calendar found"}

    # イベント作成
    new_event = EventKit.EKEvent.eventWithEventStore_(event_store)
    new_event.setTitle_(title)

    # 時刻設定
    from Foundation import NSDate
    start_ns_date = NSDate.dateWithTimeIntervalSince1970_(start_date.timestamp())
    end_ns_date = NSDate.dateWithTimeIntervalSince1970_(end_date.timestamp())

    new_event.setStartDate_(start_ns_date)
    new_event.setEndDate_(end_ns_date)
    new_event.setCalendar_(target_calendar)

    if notes:
        new_event.setNotes_(notes)
    if location:
        new_event.setLocation_(location)

    # イベント保存
    error = event_store.saveEvent_span_error_(
        new_event, EventKit.EKSpanThisEvent, None
    )

    if error[1]:  # エラーが発生した場合
        return {"success": False, "error": str(error[1])}

    return {
        "success": True,
        "event_id": str(new_event.eventIdentifier()),
        "calendar": str(target_calendar.title())
    }
```

### EventKit エラーハンドリング

```python
def check_calendar_access():
    """カレンダーアクセス権限チェック"""
    if not EVENTKIT_AVAILABLE:
        return False, "EventKit framework not available"

    status = event_store.authorizationStatusForEntityType_(EventKit.EKEntityTypeEvent)

    if status == EventKit.EKAuthorizationStatusNotDetermined:
        return False, "Calendar access not determined"
    elif status == EventKit.EKAuthorizationStatusRestricted:
        return False, "Calendar access restricted"
    elif status == EventKit.EKAuthorizationStatusDenied:
        return False, "Calendar access denied"
    elif status == EventKit.EKAuthorizationStatusAuthorized:
        return True, "Calendar access authorized"
    else:
        return False, f"Unknown authorization status: {status}"
```

## その他の依存関係

### python-dateutil
- **バージョン**: `v2.9.0.post0`
- **用途**: 柔軟な日付時刻パースとタイムゾーン処理

```python
from dateutil.parser import parse as parse_date
from dateutil.tz import gettz

# 柔軟な日付パース
date_str = "2024-12-25 10:30:00"
parsed_date = parse_date(date_str)

# タイムゾーン処理
tokyo_tz = gettz("Asia/Tokyo")
localized_date = parsed_date.replace(tzinfo=tokyo_tz)
```

## 開発依存関係

### pytest
- **バージョン**: `v8.4.2`
- **設定**: `pyproject.toml`の`[tool.pytest.ini_options]`

```bash
# 基本的なテスト実行
uv run pytest tests/ -v

# 特定のテストクラス実行
uv run pytest tests/test_tools.py::TestCalendarMCPTools -v

# カバレッジ付きテスト実行
uv run pytest tests/ --cov=calendar_mcp --cov-report=html
```

### black / ruff
- **Black バージョン**: `v25.1.0`
- **Ruff バージョン**: `v0.13.0`
- **設定**: 行長88文字、Python 3.8+ 対応

```bash
# コードフォーマット
uv run black calendar_mcp/ tests/

# リント実行
uv run ruff check calendar_mcp/ tests/

# 自動修正付きリント
uv run ruff check --fix calendar_mcp/ tests/
```

## テスト方法とコード確認手順

### 1. 環境セットアップ

```bash
# 依存関係インストール
uv install

# 開発用依存関係も含めてインストール
uv install --dev
```

### 2. 依存関係確認

```bash
# 依存関係ツリー表示
uv tree

# 特定パッケージの詳細確認
uv show mcp
uv show pyobjc-framework-eventkit
```

### 3. コード品質チェック

```bash
# 統合スクリプトでテスト実行
script/test

# 手動での段階的実行
uv run ruff check calendar_mcp/ tests/      # リント
uv run black --check calendar_mcp/ tests/   # フォーマット確認
uv run pytest tests/ -v                    # テスト実行
```

### 4. MCPサーバー動作確認

```bash
# 基本動作確認
script/server

# MCPクライアント経由の統合テスト
script/mcp_client_test

# 特定のトランスポートでテスト
script/server --transport stdio
script/server --transport sse
```

### 5. EventKit機能確認

```python
# EventKit利用可能性チェック
python3 -c "
try:
    import EventKit
    store = EventKit.EKEventStore.alloc().init()
    print('EventKit: Available')

    status = store.authorizationStatusForEntityType_(EventKit.EKEntityTypeEvent)
    print(f'Authorization Status: {status}')
    print(f'Authorized: {status == EventKit.EKAuthorizationStatusAuthorized}')
except Exception as e:
    print(f'EventKit: Not Available - {e}')
"
```

### 6. パフォーマンステスト

```bash
# メモリ使用量監視
script/server &
PID=$!
while kill -0 $PID 2>/dev/null; do
    ps -p $PID -o pid,vsz,rss,pcpu,time
    sleep 1
done
```

### 7. ログレベル調整

```python
import logging

# デバッグレベルでの詳細ログ
logging.getLogger('calendar_mcp').setLevel(logging.DEBUG)
logging.getLogger('calendar_mcp.server.json_data').setLevel(logging.INFO)

# 基本的な設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 8. トラブルシューティング

#### よくある問題と解決策

**EventKitアクセス拒否:**
```bash
# システム設定でカレンダーアクセスを確認
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Calendars"
```

**依存関係の競合:**
```bash
# 仮想環境の再作成
uv venv --python 3.10
source .venv/bin/activate
uv install
```

**MCPプロトコルエラー:**
```bash
# デバッグモードでサーバー起動
PYTHONPATH=. python -m calendar_mcp --transport stdio --debug
```

**テスト失敗時の詳細確認:**
```bash
# 詳細出力とログ付きテスト
uv run pytest tests/ -v -s --tb=long --log-cli-level=DEBUG
```

## まとめ

このプロジェクトでは、以下の主要技術スタックを使用してMCPサーバーを実装しています：

1. **MCP (Model Context Protocol)**: AI エージェントとの標準プロトコル
2. **EventKit**: macOSネイティブカレンダーアクセス
3. **FastMCP**: 高レベルMCPサーバーフレームワーク
4. **pyobjc**: Objective-C ブリッジによるmacOS API アクセス

各ライブラリの適切な使用により、堅牢で拡張性のあるMCPサーバーを実現しています。