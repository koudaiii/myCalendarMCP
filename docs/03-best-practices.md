# MCPサーバー開発ベストプラクティス

## ツールスペース干渉の回避

### 1. 固有性を持つツール名の採用

**❌ 避けるべき命名例:**
```python
@tool(name="get_events")           # 汎用的すぎる
@tool(name="create_event")         # 他システムと衝突リスク
@tool(name="list_calendars")       # 複数のカレンダーサービスで重複
```

**✅ 推奨される命名例:**
```python
@tool(name="get_macos_calendar_events")     # プラットフォーム固有で明確
@tool(name="create_macos_calendar_event")   # サービス特定性を保持
@tool(name="list_macos_calendars")          # 衝突回避と明確性
```

**命名規則のガイドライン:**
- プラットフォーム名の明示: `macos_`, `google_`, `outlook_`
- サービス名の含有: `calendar_`, `email_`, `file_`
- 動詞 + 対象 + 具体的範囲: `get_macos_calendar_events`

### 2. 適切なツール数の維持

**研究データ:**
- OpenAI推奨: 20個未満のツールで高精度を維持
- 大規模ツールスペース: 最大85%の性能低下

**実装指針:**
```python
# ✅ コアツールのみに絞る（3-5個程度）
CORE_TOOLS = [
    "get_macos_calendar_events",    # データ取得
    "create_macos_calendar_event",  # データ作成
    "list_macos_calendars"          # メタデータ取得
]

# ❌ 過度に細分化されたツール
AVOID_TOOLS = [
    "get_event_title", "get_event_date", "get_event_location",  # 機能分散
    "create_morning_event", "create_afternoon_event"            # 過度な特化
]
```

## FastMCP ツール定義のベストプラクティス

### 1. 包括的なツール説明

```python
@self.mcp.tool(
    name="get_macos_calendar_events",
    description=(
        "指定された期間のmacOSカレンダーイベントを取得します。\\n\\n"
        "Parameters:\\n"
        "- start_date (str): 開始日 (YYYY-MM-DD形式、例: '2024-09-18')\\n"
        "- end_date (str): 終了日 (YYYY-MM-DD形式、例: '2024-09-25')\\n"
        "- calendar_name (str, optional): 特定のカレンダー名での絞り込み\\n\\n"
        "Examples:\\n"
        "- 今週のイベント: start_date='2024-09-18', end_date='2024-09-25'\\n"
        "- 特定カレンダー: calendar_name='仕事'\\n\\n"
        "Returns: イベントのJSON配列（タイトル、開始/終了時刻、カレンダー名等）"
    ),
    annotations=ToolAnnotations(
        title="macOSカレンダーイベント取得",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False
    ),
)
```

**説明文の構成要素:**
1. **概要**: ツールの主要機能（1-2行）
2. **Parameters**: 各パラメータの詳細（型、制約、例）
3. **Examples**: 具体的な使用例
4. **Returns**: 戻り値の形式と内容

### 2. 適切なアノテーション設定

#### 読み取り専用ツール
```python
annotations=ToolAnnotations(
    title="人間が読みやすいタイトル",
    readOnlyHint=True,      # システム状態を変更しない
    idempotentHint=True,    # 同じ入力で同じ結果
    openWorldHint=False     # 定義された範囲内で動作
)
```

#### 書き込みツール
```python
annotations=ToolAnnotations(
    title="データ作成・変更ツール",
    destructiveHint=True,   # システム状態を変更
    idempotentHint=False,   # 実行毎に異なる結果の可能性
    openWorldHint=False     # 定義された範囲内で動作
)
```

### 3. 型安全性の確保

```python
# ✅ 明確な型ヒント
async def get_macos_calendar_events(
    start_date: str,           # ISO 8601 形式を期待
    end_date: str,             # ISO 8601 形式を期待
    calendar_name: str = None  # オプショナル
) -> str:                      # JSON文字列を返却

# ✅ 入力検証の実装
def validate_date_format(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
```

## パフォーマンス最適化

### 1. レスポンスサイズの管理

```python
# ✅ 適切な制限設定
MAX_EVENTS_PER_RESPONSE = 1000  # 推奨上限
MAX_RESPONSE_SIZE_MB = 10       # メモリ制限考慮

# ✅ ページネーション実装例
async def get_events_with_pagination(
    start_date: str,
    end_date: str,
    page_size: int = 100,
    page_offset: int = 0
) -> str:
    # 大量データの分割取得
```

### 2. 非同期処理の活用

```python
# ✅ EventKit操作の非同期化
async def get_macos_calendar_events(...) -> str:
    log_json_data(json_logger, "INCOMING", "TOOL REQUEST", {
        "name": "get_macos_calendar_events",
        "arguments": {...}
    })

    # 非同期でEventKit操作
    result = await self._fetch_events_async(...)

    log_json_data(json_logger, "OUTGOING", "TOOL RESPONSE", result)
    return json.dumps(result, ensure_ascii=False)

# ✅ タイムアウト設定
async def _fetch_events_async(...) -> List[Dict]:
    try:
        return await asyncio.wait_for(
            self._eventkit_operation(),
            timeout=5.0  # 5秒タイムアウト
        )
    except asyncio.TimeoutError:
        return [{"error": "Operation timed out"}]
```

### 3. メモリ効率の最適化

```python
# ✅ EventStore インスタンス再利用
class CalendarMCPServer:
    def __init__(self):
        self.event_store = None  # 再利用のため保持

    def _ensure_event_store(self):
        if self.event_store is None:
            self.event_store = EventKit.EKEventStore.alloc().init()

# ✅ 大量データの適切な処理
def process_large_dataset(events):
    for event in events:
        yield self._convert_event(event)  # Generator使用
        # メモリ使用量を抑制
```

## エラーハンドリングベストプラクティス

### 1. 段階的エラーハンドリング

```python
async def get_macos_calendar_events(...) -> str:
    # レベル1: EventKit利用可能性チェック
    if not EVENTKIT_AVAILABLE:
        return json.dumps([{
            "error": "EventKit framework not available",
            "status": "unavailable",
            "suggestion": "This tool requires macOS EventKit framework"
        }])

    # レベル2: 権限チェック
    try:
        self._ensure_event_store()
    except Exception as e:
        return json.dumps([{
            "error": "Calendar access permission denied",
            "status": "permission_denied",
            "details": str(e)
        }])

    # レベル3: 入力検証
    if not self._validate_date_format(start_date):
        return json.dumps([{
            "error": "Invalid date format",
            "expected": "YYYY-MM-DD",
            "received": start_date
        }])
```

### 2. 建設的エラーメッセージ

```python
# ❌ 低品質エラーメッセージ
return [{"error": "job failed"}]

# ✅ 建設的エラーメッセージ
return [{
    "error": "Calendar access denied",
    "error_code": "CALENDAR_PERMISSION_DENIED",
    "message": "Please grant calendar access in System Preferences > Privacy & Security > Calendars",
    "suggestion": "Add this application to allowed calendar apps",
    "documentation": "https://support.apple.com/guide/mac-help/..."
}]
```

### 3. フォールバック機能

```python
async def get_macos_calendar_events(...) -> str:
    try:
        # 主要機能の実行
        return await self._get_events_from_eventkit(...)
    except EventKitUnavailableError:
        # フォールバック: 限定機能での対応
        return json.dumps([{
            "notice": "EventKit unavailable, showing cached events",
            "events": await self._get_cached_events(...)
        }])
    except Exception as e:
        # 最終フォールバック
        return json.dumps([{
            "error": "Unexpected error occurred",
            "status": "internal_error",
            "timestamp": datetime.now().isoformat()
        }])
```

## ログ・監視のベストプラクティス

### 1. 構造化ログの実装

```python
def log_json_data(logger, direction: str, data_type: str, data):
    """構造化JSON ログの出力"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "direction": direction,
        "data_type": data_type,
        "data": data
    }
    logger.info(f"[{direction}] {data_type}:")
    logger.info(json.dumps(log_entry, indent=2, ensure_ascii=False))
```

### 2. パフォーマンス測定

```python
import time

async def get_macos_calendar_events(...) -> str:
    start_time = time.time()

    try:
        result = await self._fetch_events(...)

        # パフォーマンスログ
        execution_time = time.time() - start_time
        performance_logger.info(f"Tool execution time: {execution_time:.3f}s")

        return result
    except Exception as e:
        execution_time = time.time() - start_time
        error_logger.error(f"Tool failed after {execution_time:.3f}s: {e}")
        raise
```

### 3. セキュリティ配慮

```python
def sanitize_log_data(data):
    """ログ出力時の機密情報除去"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in ['password', 'token', 'secret', 'key']:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_log_data(value)
        return sanitized
    return data
```

## テスト設計

### 1. 包括的テストスイート

```python
# tests/test_tools.py の設計パターン
class TestCalendarMCPTools:
    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_events_success(self):
        """正常ケースのテスト"""

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_get_events_invalid_date(self):
        """エラーケースのテスト"""

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_eventkit_unavailable(self):
        """フォールバックのテスト"""
```

### 2. モックとスタブの活用

```python
@pytest.fixture
def mock_eventkit_unavailable():
    """EventKit利用不可のモック"""
    with patch('calendar_mcp.server.EVENTKIT_AVAILABLE', False):
        yield

async def test_eventkit_unavailable_fallback(self, mock_eventkit_unavailable):
    """EventKit利用不可時のフォールバック動作検証"""
```

## デプロイメントとメンテナンス

### 1. 設定管理

```python
# 環境依存設定の外部化
CONFIG = {
    "max_events": int(os.getenv("MCP_MAX_EVENTS", "1000")),
    "timeout_seconds": int(os.getenv("MCP_TIMEOUT", "5")),
    "log_level": os.getenv("MCP_LOG_LEVEL", "INFO"),
}
```

### 2. バージョン管理

```python
# calendar_mcp/__init__.py
__version__ = "1.0.0"

# APIバージョニング対応
@tool(name="get_macos_calendar_events_v2")
async def get_events_v2(...):
    """新しいAPIバージョン"""
```

### 3. 互換性の維持

```python
# 後方互換性の保持
@tool(name="get_events")  # 旧API名
async def get_events_legacy(...):
    """旧APIとの互換性維持"""
    warnings.warn("Use get_macos_calendar_events instead", DeprecationWarning)
    return await self.get_macos_calendar_events(...)
```

これらのベストプラクティスにより、高品質で保守可能なMCPサーバーを構築できます。

---

次の章では、開発・運用時によく遭遇する問題とその解決方法について説明します。