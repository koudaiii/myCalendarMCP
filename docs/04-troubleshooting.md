# トラブルシューティングガイド

## よくある問題と解決策

### 1. Asyncio Event Loop 競合エラー

#### 問題の症状
```
RuntimeError: Already running asyncio in this thread
```

#### 原因
`calendar_mcp/__main__.py` で `asyncio.run(main())` を実行し、その中で `server_instance.mcp.run()` を呼び出すことで、二重の event loop が作成される。

#### 解決策
FastMCP の各トランスポート専用の async メソッドを使用する：

```python
# ❌ 問題のあるコード
server_instance.mcp.run(transport=args.transport, mount_path=args.mount_path)

# ✅ 修正されたコード (calendar_mcp/server.py:272-280)
if args.transport == "sse":
    await server_instance.mcp.run_sse_async(mount_path=args.mount_path)
elif args.transport == "stdio":
    await server_instance.mcp.run_stdio_async()
elif args.transport == "streamable-http":
    await server_instance.mcp.run_streamable_http_async()
else:
    # Fallback for unknown transports
    server_instance.mcp.run(transport=args.transport, mount_path=args.mount_path)
```

#### 予防策
- FastMCP の `run()` メソッドは内部で `anyio.run()` を呼び出すため、既存の asyncio event loop 内では使用しない
- 新しいトランスポートを追加する際も async 版メソッドが存在するか確認する

### 2. EventKit アクセス権限エラー

#### 問題の症状
```
EventKit initialization failed: [Error details]
```

#### 考えられる原因
1. **システム権限の未許可**: macOS プライバシー設定でカレンダーアクセスが拒否されている
2. **EventKit フレームワークの利用不可**: 必要なフレームワークがインストールされていない
3. **サンドボックス制限**: アプリケーションがサンドボックス環境で実行されている

#### 解決手順

##### 1. システム権限の確認
```bash
# システム環境設定を開く
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Calendars"
```

**手動設定手順:**
1. システム環境設定 → プライバシーとセキュリティ
2. カレンダー を選択
3. アプリケーション（通常はターミナル）にチェックを入れる

##### 2. EventKit 利用可能性の確認
```python
# デバッグ用コード
try:
    import EventKit
    print("EventKit available")
    store = EventKit.EKEventStore.alloc().init()
    print("EventStore initialized successfully")
except ImportError:
    print("EventKit not available - install pyobjc-framework-EventKit")
except Exception as e:
    print(f"EventKit error: {e}")
```

##### 3. 依存関係の再インストール
```bash
# EventKit フレームワークの再インストール
uv pip install --force-reinstall pyobjc-framework-EventKit

# 全依存関係の更新
uv sync --force
```

#### フォールバック実装
```python
# calendar_mcp/server.py での対応例
if not EVENTKIT_AVAILABLE:
    return json.dumps([{
        "error": "EventKit framework not available",
        "status": "unavailable",
        "suggestion": "Install pyobjc-framework-EventKit and grant calendar permissions",
        "instructions": [
            "Run: uv pip install pyobjc-framework-EventKit",
            "Grant calendar access in System Preferences > Privacy & Security"
        ]
    }])
```

### 3. テスト実行エラー

#### 問題の症状
```
ValueError: Unable to find a suitable async backend
```

#### 原因
pytest の anyio バックエンド設定が適切でない。

#### 解決策

##### 1. conftest.py の設定確認
```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```

##### 2. pyproject.toml の設定確認
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
anyio_backends = ["asyncio"]
```

##### 3. テスト実行方法
```bash
# 推奨: プロジェクトのテストスクリプト使用
script/test

# 直接実行の場合
uv run pytest tests/ -v --tb=short

# 特定テストクラスのみ
uv run pytest tests/test_tools.py::TestCalendarMCPTools -v
```

### 4. JSON ログ出力の問題

#### 問題の症状
- ログが期待通りに出力されない
- JSON形式が崩れている
- 機密情報がログに含まれている

#### デバッグ手順

##### 1. ログ設定の確認
```python
# calendar_mcp/server.py:17-28
import logging
json_logger = logging.getLogger("calendar_mcp.server.json_data")
json_logger.setLevel(logging.INFO)

# ハンドラーが正しく設定されているか確認
if not json_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    json_logger.addHandler(handler)
```

##### 2. JSON出力の検証
```python
def log_json_data(logger, direction: str, data_type: str, data):
    try:
        # JSON変換可能性の事前チェック
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        logger.info(f"[{direction}] {data_type}:")
        logger.info(json_str)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization failed: {e}")
        logger.info(f"[{direction}] {data_type}: {str(data)}")
```

##### 3. 機密情報の除去
```python
def sanitize_log_data(data):
    """機密情報を除去"""
    sensitive_keys = ['password', 'token', 'secret', 'key', 'auth']

    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if any(sensitive in k.lower() for sensitive in sensitive_keys)
            else sanitize_log_data(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_log_data(item) for item in data]
    return data
```

### 5. パフォーマンス問題

#### 問題の症状
- レスポンス時間が5秒を超える
- メモリ使用量が急激に増加
- 大量のイベント取得時にタイムアウト

#### 診断方法

##### 1. パフォーマンス測定の追加
```python
import time
import tracemalloc

async def get_macos_calendar_events(...) -> str:
    # メモリトレース開始
    tracemalloc.start()
    start_time = time.time()

    try:
        result = await self._fetch_events(...)

        # パフォーマンス計測
        execution_time = time.time() - start_time
        current, peak = tracemalloc.get_traced_memory()

        logger.info(f"Execution time: {execution_time:.3f}s")
        logger.info(f"Memory usage: current={current/1024/1024:.2f}MB, peak={peak/1024/1024:.2f}MB")

        return result
    finally:
        tracemalloc.stop()
```

##### 2. 大量データの処理改善
```python
# ✅ ページネーション実装
async def get_events_paginated(start_date: str, end_date: str, page_size: int = 100):
    all_events = await self._fetch_all_events(start_date, end_date)

    # 大量データを分割
    for i in range(0, len(all_events), page_size):
        yield all_events[i:i + page_size]

# ✅ ストリーミング処理
async def process_events_stream(events):
    for event in events:
        processed = await self._process_single_event(event)
        yield processed

        # メモリ解放のため適度にyield
        if random.random() < 0.1:  # 10%の確率で
            await asyncio.sleep(0)  # イベントループに制御を戻す
```

### 6. MCPクライアント接続エラー

#### 問題の症状
- クライアントからの接続が確立されない
- ツール呼び出しでタイムアウト
- レスポンスが返ってこない

#### デバッグ手順

##### 1. トランスポートレベルの確認
```bash
# SSE (Server-Sent Events) の場合
curl -N -H "Accept: text/event-stream" http://localhost:3000/sse

# stdio の場合
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | script/server --transport stdio

# デバッグモードでの起動
DEBUG=1 script/server --transport sse
```

##### 2. ログレベルの調整
```python
# より詳細なログ出力
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("calendar_mcp")
logger.setLevel(logging.DEBUG)
```

##### 3. 接続テスト用ツール
```bash
# MCPクライアント接続テスト (Node.js環境)
npx @modelcontextprotocol/cli test-connection --transport stdio --command "script/server --transport stdio"
```

### 7. 日付フォーマットエラー

#### 問題の症状
```
Invalid date format received: '2024/09/18'
Expected format: YYYY-MM-DD
```

#### 解決策

##### 1. 柔軟な日付パースの実装
```python
from datetime import datetime
import re

def parse_flexible_date(date_str: str) -> str:
    """複数の日付フォーマットに対応"""
    formats = [
        "%Y-%m-%d",     # 2024-09-18
        "%Y/%m/%d",     # 2024/09/18
        "%m/%d/%Y",     # 09/18/2024
        "%d/%m/%Y",     # 18/09/2024
        "%Y%m%d",       # 20240918
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")  # 標準形式に正規化
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {date_str}")
```

##### 2. 入力検証の強化
```python
def validate_and_normalize_date(date_str: str) -> str:
    """日付の検証と正規化"""
    if not date_str:
        raise ValueError("Date string cannot be empty")

    try:
        normalized = parse_flexible_date(date_str)

        # 有効な日付範囲チェック
        date_obj = datetime.strptime(normalized, "%Y-%m-%d")
        min_date = datetime(2000, 1, 1)
        max_date = datetime(2100, 12, 31)

        if not (min_date <= date_obj <= max_date):
            raise ValueError(f"Date out of valid range: {normalized}")

        return normalized
    except Exception as e:
        raise ValueError(f"Invalid date '{date_str}': {e}")
```

## デバッグツール

### 1. 専用デバッグスクリプト

```python
# script/debug_tools.py
import asyncio
import json
from calendar_mcp.server import CalendarMCPServer

async def debug_tool_call(tool_name: str, **kwargs):
    """ツール呼び出しのデバッグ"""
    server = CalendarMCPServer()

    print(f"Testing tool: {tool_name}")
    print(f"Arguments: {json.dumps(kwargs, indent=2)}")

    try:
        result = await server.mcp.call_tool(tool_name, kwargs)
        print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 使用例
    asyncio.run(debug_tool_call(
        "get_macos_calendar_events",
        start_date="2024-09-18",
        end_date="2024-09-25"
    ))
```

### 2. システム情報確認スクリプト

```python
def check_system_requirements():
    """システム要件の確認"""
    checks = []

    # Python バージョン
    import sys
    checks.append(f"Python version: {sys.version}")

    # EventKit 利用可能性
    try:
        import EventKit
        checks.append("✅ EventKit: Available")
    except ImportError:
        checks.append("❌ EventKit: Not available")

    # macOS バージョン
    import platform
    if platform.system() == "Darwin":
        checks.append(f"✅ macOS: {platform.mac_ver()[0]}")
    else:
        checks.append(f"❌ Platform: {platform.system()} (macOS required)")

    # 依存関係
    try:
        import fastmcp
        checks.append(f"✅ FastMCP: {fastmcp.__version__}")
    except ImportError:
        checks.append("❌ FastMCP: Not installed")

    return "\\n".join(checks)
```

### 3. 継続的監視

```python
# 監視用メトリクス
class MCPMetrics:
    def __init__(self):
        self.tool_calls = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.start_time = time.time()

    def record_tool_call(self, execution_time: float, success: bool):
        self.tool_calls += 1
        self.total_execution_time += execution_time
        if not success:
            self.error_count += 1

    def get_statistics(self):
        uptime = time.time() - self.start_time
        avg_execution_time = self.total_execution_time / max(self.tool_calls, 1)
        error_rate = self.error_count / max(self.tool_calls, 1)

        return {
            "uptime_seconds": uptime,
            "total_tool_calls": self.tool_calls,
            "average_execution_time": avg_execution_time,
            "error_rate": error_rate,
            "calls_per_minute": self.tool_calls / (uptime / 60)
        }
```

## ヘルプとサポート

### 問題報告時に含めるべき情報

1. **環境情報**
   - macOS バージョン
   - Python バージョン
   - 依存関係のバージョン

2. **エラー情報**
   - 完全なエラーメッセージ
   - スタックトレース
   - 発生した操作の詳細

3. **再現手順**
   - 問題を再現するための具体的な手順
   - 期待される動作と実際の動作

4. **ログ**
   - 関連するログ出力
   - デバッグモードでの実行結果

### 追加リソース

- **プロジェクトリポジトリ**: 最新の問題と解決策
- **FastMCP ドキュメント**: フレームワーク固有の問題
- **Apple EventKit ドキュメント**: macOS 固有の問題
- **MCP 仕様書**: プロトコルレベルの詳細

このトラブルシューティングガイドにより、よくある問題を迅速に解決し、安定したMCPサーバー運用が可能になります。

---

各章で異なる観点からMCPについて包括的に説明したドキュメント一式が完成しました。