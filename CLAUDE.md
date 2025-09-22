# Claude Code メモリ

- [問題と解決策の記録](#問題と解決策の記録)
  - [1. Asyncio Event Loop 競合エラー](#1-asyncio-event-loop-競合エラー)
  - [2. プロジェクト構造](#2-プロジェクト構造)
  - [3. 動作確認コマンド](#3-動作確認コマンド)
  - [4. 注意事項](#4-注意事項)
  - [5. テスト環境とMCPツール検証](#5-テスト環境とmcpツール検証)
  - [6. JSONログ出力機能](#6-jsonログ出力機能)
  - [7. MCPエコシステムにおける設計原則とベストプラクティス](#7-mcpエコシステムにおける設計原則とベストプラクティス)
  - [8. パフォーマンス設計指針とEventKit技術仕様](#8-パフォーマンス設計指針とeventkit技術仕様)
  - [9. FastMCPツールの適切な定義とベストプラクティス](#9-fastmcpツールの適切な定義とベストプラクティス)
  - [10. MCPクライアントテストスクリプト（script/mcp_client_test）](#10-mcpクライアントテストスクリプトscriptmcp_client_test)

## 問題と解決策の記録

### 1. Asyncio Event Loop 競合エラー

**問題:**
- `script/server` 実行時に `RuntimeError: Already running asyncio in this thread` エラーが発生
- `calendar_mcp/__main__.py` で `asyncio.run(main())` を実行し、その中で `server_instance.mcp.run()` を呼び出すことで、二重の event loop が作成されることが原因

**解決策:**
- `calendar_mcp/server.py:271-280` で、各トランスポートタイプに対応する async 版のメソッドを使用するように修正
  - `sse`: `run_sse_async(mount_path=args.mount_path)`
  - `stdio`: `run_stdio_async()`
  - `streamable-http`: `run_streamable_http_async()`

**修正箇所:**
```python
# Before (server.py:271)
server_instance.mcp.run(transport=args.transport, mount_path=args.mount_path)

# After (server.py:272-280)
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

### 2. プロジェクト構造

**ファイル構成:**
- `calendar_mcp/__main__.py`: エントリーポイント、シグナルハンドラー設定
- `calendar_mcp/server.py`: メインサーバー実装、FastMCP 使用
- `script/server`: サーバー起動スクリプト

**利用可能なトランスポート:**
- `stdio` (標準入出力)
- `sse` (Server-Sent Events) - デフォルト
- `streamable-http` (HTTP ストリーミング)

### 3. 動作確認コマンド

```bash
# デフォルト (SSE)
script/server

# 特定のトランスポート指定
script/server --transport sse
script/server --transport stdio
script/server --transport streamable-http

# MCPクライアント経由のテスト
script/mcp_client_test
```

### 4. 注意事項

- FastMCP の `run()` メソッドは内部で `anyio.run()` を呼び出すため、既存の asyncio event loop 内では使用不可
- 各トランスポートには対応する async 版メソッドが存在するため、それらを使用する必要がある
- 将来的に新しいトランスポートが追加された場合、同様の対応が必要

### 5. テスト環境とMCPツール検証

**テストファイル構成:**
- `tests/conftest.py`: pytest設定、asyncioバックエンド指定
- `tests/test_tools.py`: MCPツールの包括的テストスイート

**テスト対象:**
- MCPツール呼び出し (`get_events`, `create_event`, `list_calendars`)
- MCPリソース読み込み (`calendar://events`, `calendar://calendars`)
- EventKit利用可能/不可能時の動作
- エラーハンドリング（不正な日付形式等）
- レスポンス形式の妥当性

**テスト実行方法:**
```bash
# 全体テスト実行（推奨）
script/test

# 単体テストのみ実行
uv run pytest tests/ -v

# 特定のテストクラス実行
uv run pytest tests/test_tools.py::TestCalendarMCPTools -v
```

**テスト設定のポイント:**
- anyio backends を asyncio のみに制限（pytest.ini_options で `anyio_backends = ["asyncio"]` 設定）
- conftest.py で `anyio_backend` fixture を設定
- `@pytest.mark.anyio(backends=["asyncio"])` でasyncio使用を明示

**MCPツール呼び出しAPI:**
- `server.mcp.list_tools()`: ツール一覧取得（Toolオブジェクトのリスト）
- `server.mcp.call_tool(name, args)`: ツール実行（戻り値: `(content_list, result_dict)` のタプル）
- `server.mcp.list_resources()`: リソース一覧取得（Resourceオブジェクトのリスト）
- `server.mcp.read_resource(uri)`: リソース読み込み（戻り値: `ReadResourceContents` オブジェクトのリスト）

### 6. JSONログ出力機能

**目的:**
- MCP通信の可視化とデバッグ支援
- リクエスト/レスポンスの詳細なトレース

**実装内容:**
- `calendar_mcp/server.py:17-28` に `log_json_data()` 関数を追加
- 全てのMCPツール（`get_events`, `create_event`, `list_calendars`）にログ出力を追加
- 全てのMCPリソース（`calendar://events`, `calendar://calendars`）にログ出力を追加
- 専用ロガー `json_logger` を設定（タイムスタンプ付きフォーマット）

**ログ出力形式:**
```
2024-09-18 10:30:15,123 - calendar_mcp.server.json_data - [INCOMING] TOOL REQUEST:
{
  "name": "get_events",
  "arguments": {
    "start_date": "2024-09-18",
    "end_date": "2024-09-25",
    "calendar_name": null
  }
}

2024-09-18 10:30:15,456 - calendar_mcp.server.json_data - [OUTGOING] TOOL RESPONSE:
[
  {
    "title": "Sample Event",
    "start": "2024-09-18 09:00:00",
    "end": "2024-09-18 10:00:00",
    "calendar": "Calendar",
    "notes": "",
    "allDay": false
  }
]
```

**ログの種類:**
- `[INCOMING]`: クライアントからのリクエスト
- `[OUTGOING]`: サーバーからのレスポンス

**対象データ:**
- ツールリクエスト/レスポンス（引数、戻り値）
- リソースリクエスト/レスポンス（URI、データ）
- JSON形式で整形された読みやすい出力

### 7. MCPエコシステムにおける設計原則とベストプラクティス

**背景:**
- AIエージェントはこれまで専用ツールとセットで開発されてきたが、MCPにより異なる開発元のエージェントやツールが協力し合う時代になる
- 複数のMCPサーバーが同時に存在すると「ツールスペース干渉(tool-space interference)」という問題が発生し、AIエージェントの性能を低下させる可能性がある

**ツールスペース干渉の問題点:**
- 様々なツールが同時に存在すると、互いに干渉し合ってAIエージェントの性能を落とす
- GitHub操作時にブラウザ、コマンドライン、専用ツールという複数の選択肢が生まれ、エージェントが混乱する
- 一部のサーバーは非常に多くのツールを提供し、AIモデルの処理能力を超えてしまう
- ツールからの応答が長すぎて、AIモデルが処理できる情報量の上限を超える
- ツール名が重複して区別できない、エラーメッセージが不親切、パラメータが複雑すぎるなどの問題

**このプロジェクトでの改善必要箇所:**

**⚠️ 命名規則の見直しが必要:**
- 現在：`get_events`, `create_event`, `list_calendars` (汎用的すぎる)
- 推奨：`get_macos_calendar_events`, `create_macos_calendar_event`, `list_macos_calendars` (固有的)
- 理由：他のカレンダーMCPサーバー（Google Calendar、Outlook等）との名前衝突を避けるため

**✅ 現在適用済みのベストプラクティス:**
- 適切なツール数の維持（3つのコアツールのみ）
- 構造化されたJSON レスポンス
- 明確なパラメータ設計
- 詳細なエラーハンドリングとログ出力

**今後の改善指針:**

**命名規則の修正:**
- ✅ `get_macos_calendar_events` (プラットフォーム固有で明確)
- ❌ `get_events` (汎用的すぎて衝突リスク)
- ✅ `create_macos_calendar_event` (固有性を保持)
- ❌ `create_event` (他のシステムと混同)

**ツールスペース干渉の回避策:**
- ツール名の衝突しない仕組みの導入検討
- リソース共有に関するルール整備
- 適切なツール説明文の提供
- エージェントが選択しやすい明確な機能分離

**レスポンス設計:**
- AIモデルの処理限界を考慮した情報量の調整
- 必要に応じたページネーションの実装
- 簡潔で構造化されたデータ形式の維持

**参考情報:**
- [Tool-space Interference in the MCP Era](https://www.microsoft.com/en-us/research/blog/tool-space-interference-in-the-mcp-era-designing-for-agent-compatibility-at-scale/)

### 8. パフォーマンス設計指針とEventKit技術仕様

**トークン数とコンテキスト制限:**
- AIモデル別コンテキストウィンドウ制限
  - GPT-4.1: 1,000,000 トークン
  - GPT-5: 400,000 トークン
  - GPT-4o/Llama 3.1: 128,000 トークン
  - Qwen 3: 32,000 トークン
  - Phi-4: 16,000 トークン
- OpenAI推奨：ツール数は20個未満で高精度を維持
- MCPツールレスポンス統計
  - 中央値: 98 トークン
  - 平均値: 4,431 トークン
  - 最大観測値: 557,766 トークン

**pyobjc-framework-EventKit パラメータ閾値:**
- EventStore初期化: `EventKit.EKEventStore.alloc().init()`
- エンティティタイプ: `EventKit.EKEntityTypeEvent` (イベント操作用)
- 時間範囲制限: Foundationフレームワークの`NSDate`制約に準拠
- カレンダーアクセス権限: システムレベルでのプライバシー制御が必要
- 最大パラメータスキーマ深度: 20レベル（一般的には2レベルを推奨）

**エラーハンドリングと回避策:**

**EventKit固有のエラーパターン:**
```python
# 権限エラーの処理
try:
    self.event_store = EventKit.EKEventStore.alloc().init()
except Exception as e:
    logger.error(f"EventKit initialization failed: {e}")
    return {"status": "unavailable", "reason": "EventKit access denied"}

# 利用不可時のフォールバック
if not EVENTKIT_AVAILABLE:
    return [{"error": "EventKit not available"}]
```

**一般的なエラー回避策:**
- MCPツール呼び出しエラー率: 59% (5,983回中3,536回にエラー含有)
- 低品質エラーメッセージの改善: 「error: job」→ 具体的なエラー内容の説明
- 日付形式検証: ISO 8601形式の厳密なバリデーション実装
- カレンダー名の存在確認: 指定されたカレンダーが存在しない場合の適切な処理

**応答速度最適化:**

**パフォーマンス劣化要因:**
- 大規模ツールスペース: 最大85%の性能低下
- 長すぎるレスポンス: 最大91%の性能低下
- 複雑なパラメータ構造: 処理時間の指数的増加

**最適化戦略:**
- EventKit操作の非同期化: `async/await`パターンの活用
- レスポンス分割: 大量イベント取得時のページネーション実装
- キャッシュ戦略: カレンダーリスト等の静的データのメモ化
- 接続プール: EventStore インスタンスの再利用

**実装における具体的な制限値:**
- 1回のクエリで取得するイベント数上限: 1000件 (推奨)
- レスポンスサイズ上限: 10MB (トークン制限考慮)
- タイムアウト設定: EventKit操作は5秒以内
- 同時接続数制限: EventStore インスタンス当たり最大10接続

**モニタリングとデバッグ:**
- JSONログによるリクエスト/レスポンス追跡
- EventKit操作のレイテンシ測定
- メモリ使用量の監視 (特にNSDate オブジェクトのリーク防止)
- エラー率の継続的測定と閾値アラート設定

### 9. FastMCPツールの適切な定義とベストプラクティス

**背景:**
- MCPクライアント（AIエージェント）に対してツールの使用方法を明確に伝える必要がある
- FastMCPの`@tool()`デコレータを使用して適切なツール説明とメタデータを提供することが重要
- `description`と`annotations`の両方を活用してツールスペース干渉を防ぐ

**FastMCP `@tool()`デコレータの正しい使用方法:**

**サポートされているパラメータ:**
- `name`: ツール名（省略時は関数名が使用される）
- `title`: 人間が読みやすいタイトル
- `description`: ツールの詳細説明（パラメータ説明・例も含める）
- `annotations`: ツールの動作特性を示すヒント（ToolAnnotationsオブジェクト）
- `structured_output`: 構造化出力の制御

**サポートされていないパラメータ（使用禁止）:**
- `parameters`: パラメータの詳細定義（FastMCPでは型アノテーションとdescriptionで代替）
- `examples`: 使用例（descriptionに記載する）

**推奨されるツール定義パターン:**

```python
from mcp.types import ToolAnnotations

@self.mcp.tool(
    name="get_macos_calendar_events",
    description=(
        "ツールの概要説明\\n\\n"
        "Parameters:\\n"
        "- param1 (type): パラメータ1の説明\\n"
        "- param2 (type, optional): パラメータ2の説明\\n\\n"
        "Examples:\\n"
        "- 例1: param1='value1', param2='value2'\\n"
        "- 例2: param1='value3'"
    ),
    annotations=ToolAnnotations(
        title="Human Readable Tool Title",
        readOnlyHint=True,      # 読み取り専用の操作
        idempotentHint=True,    # 冪等性がある操作
        openWorldHint=False     # 閉じた世界の仮定
    ),
)
async def get_macos_calendar_events(param1: str, param2: str = None) -> str:
    \"\"\"関数のdocstring\"\"\"
    # 実装
```

**ToolAnnotationsの使い分け:**

**読み取り専用ツール（データ取得系）:**
- `readOnlyHint=True`: システム状態を変更しない
- `idempotentHint=True`: 同じ入力で同じ結果が得られる
- `openWorldHint=False`: 定義された範囲内で動作

**書き込みツール（データ作成・変更系）:**
- `destructiveHint=True`: システム状態を変更する
- `idempotentHint=False`: 実行のたびに異なる結果になる可能性
- `openWorldHint=False`: 定義された範囲内で動作

**実装済みの改善例（calendar_mcp/server.py:95-231）:**

1. **get_macos_calendar_events（データ取得）:**
   - 詳細なパラメータ説明をdescriptionに記載
   - `readOnlyHint=True, idempotentHint=True` を設定
   - 日付フォーマット、オプショナルパラメータの説明を明示
   - 使用例を具体的に記載

2. **create_macos_calendar_event（データ作成）:**
   - パラメータの制約（文字数制限等）を明記
   - `destructiveHint=True, idempotentHint=False` を設定
   - 日時フォーマットの詳細説明
   - 権限要件とエラー条件の説明

3. **list_macos_calendars（メタデータ取得）:**
   - 戻り値の構造を詳細に説明
   - `readOnlyHint=True, idempotentHint=True` を設定
   - パラメータ不要であることを明示
   - 各プロパティの意味を説明

**AIエージェントの使いやすさを向上させる要素:**
- 明確なパラメータ説明（型、必須/オプション、制約）
- 具体的な使用例の提供
- エラー条件の説明
- 戻り値の形式説明
- 適切な動作ヒント（annotations）の設定

**注意事項:**
- FastMCPでは`parameters`パラメータが使用できないため、全ての説明をdescriptionに含める
- 型情報は関数の型アノテーションで提供
- 長い説明は適切に改行して88文字以内に収める
- ツール名は他のMCPサーバーとの衝突を避けるため固有性を持たせる
- descriptionでの改行は`\\n`のダブルエスケープが必要

**コード品質管理:**
- ruff formatによる自動整形で88文字制限を遵守
- pytest による動作検証（21テストケース全通過）
- MCPクライアントでの実際の使用テストを実施

### 10. MCPクライアントテストスクリプト（script/mcp_client_test）

**目的:**
- 実際のMCPクライアント実装によるMCPサーバーの動作検証
- `docs/05-call-methods-comparison.md#2-MCPクライアント経由の呼び出し` のシナリオ実証
- JSON-RPC プロトコルレベルでの詳細テスト

**実装概要:**
- ファイルパス: `script/mcp_client_test`
- 言語: Bash + 埋め込みPython（uv run python3 - <<'EOF'）
- 主要クラス: `MCPServerManager`, `MCPClient`
- 対象シナリオ: MCPクライアント経由の包括的ツール・リソーステスト

**テストシナリオ（9段階）:**
```bash
# 実行方法
script/mcp_client_test

# 実行される9段階のテストシナリオ:
# 1. カレンダーアクセス許可確認
# 2. MCPサーバー起動（stdio transport）
# 3. MCPクライアント初期化
# 4. MCPプロトコル初期化
# 5. 利用可能ツール一覧取得
# 6. カレンダー一覧取得（list_macos_calendars）
# 7. イベント一覧取得（get_macos_calendar_events）
# 8. リソース一覧取得
# 9. リソース読み取り（calendar://events）
```

**技術的特徴:**

**MCPプロトコル実装:**
- 標準JSON-RPC 2.0によるMCP通信
- `initialize` → `notifications/initialized` の正式ハンドシェイク
- プロトコルバージョン: 2024-11-05
- クライアント情報: name="mcp-client-test", version="1.0.0"

**サーバー管理機能:**
```python
class MCPServerManager:
    async def start_server(self, transport="stdio"):
        # script/server --transport stdio でサーバー起動
        # subprocess.Popen で stdin/stdout/stderr 管理
        # 2秒待機でサーバー起動確認

    def stop_server(self):
        # 適切な terminate() → wait() → kill() 処理
        # タイムアウト設定によるリソース保護
```

**MCPクライアント実装:**
```python
class MCPClient:
    def send_request(self, method, params=None):
        # JSON-RPC リクエスト生成・送信
        # レスポンス解析と構造化ログ出力
        # エラーハンドリングと復旧

    def send_notification(self, method, params=None):
        # レスポンス不要なノーティフィケーション送信
        # initialize 完了後の notifications/initialized 等
```

**包括的ログ出力:**
```
📤 [OUTGOING] MCP REQUEST: {"jsonrpc": "2.0", "method": "tools/call", "id": 3, "params": {"name": "get_macos_calendar_events", "arguments": {"start_date": "2024-09-22", "end_date": "2024-09-29"}}}

📥 [INCOMING] MCP RESPONSE: {
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"title\":\"Sample Event\",\"start_date\":\"2024-09-22 09:00:00\",...}]"
      }
    ]
  }
}
```

**エラーハンドリング機能:**
- EventKit利用可能性の事前確認
- カレンダーアクセス許可の検証
- MCPサーバー起動失敗の検出
- JSON-RPC通信エラーの適切な処理
- シグナルハンドリング（SIGINT、SIGTERM）

**pytest テストとの関係性:**
- `tests/test_tools.py`: MCPツール内部実装のユニットテスト
- `script/mcp_client_test`: 実際のMCPクライアント統合テスト
- 相互補完により包括的テストカバレッジを実現

**docs/05-call-methods-comparison.md との連携:**
- Section 2「MCPクライアント経由の呼び出し」の実証実装
- script/query（直接呼び出し）との動作・ログ出力の比較材料
- LLM+MCPクライアント統合アーキテクチャの基礎検証

**実行前提条件:**
```bash
# 1. EventKit フレームワークの利用可能性
# 2. macOS カレンダーアクセス許可
# 3. uv パッケージマネージャーのインストール
# 4. プロジェクト依存関係の解決（uv による）
```

**デバッグ用出力例:**
```
🚀 MCP クライアント テストスクリプトを開始
docs/05-call-methods-comparison.md#2-MCPクライアント経由の呼び出し のシナリオ

📋 Step 1: カレンダーアクセス許可を確認
✅ EventKit フレームワークが利用可能です
✅ カレンダーアクセス許可が確認されました

📋 Step 2: MCPサーバーを起動
🚀 MCPサーバーを起動中... (transport: stdio)
実行コマンド: /Users/.../script/server --transport stdio
✅ MCPサーバーが起動しました

📋 Step 3: MCPクライアントを初期化
📋 Step 4: MCPプロトコルを初期化
🔧 MCPサーバーを初期化中...
🔧 初期化完了通知を送信中...
✅ MCPサーバーの初期化が完了しました

📋 Step 5: 利用可能なツール一覧を取得
✅ 3 個のツールが利用可能です:
   - get_macos_calendar_events: macOSカレンダーからイベントを取得
   - create_macos_calendar_event: macOSカレンダーに新しいイベントを作成
   - list_macos_calendars: macOSで利用可能なカレンダー一覧を取得

📋 Step 6: カレンダー一覧を取得
⚡ ツール 'list_macos_calendars' を呼び出し中...
✅ カレンダー一覧取得成功

📋 Step 7: イベント一覧を取得（今日から1週間）
⚡ ツール 'get_macos_calendar_events' を呼び出し中...
✅ イベント取得成功
📅 2 件のイベントが見つかりました
   1. Sample Meeting
      📅 2024-09-22 09:00:00 - 2024-09-22 10:00:00
      📋 カレンダー: Work

📋 Step 8: 利用可能なリソース一覧を取得
✅ 2 個のリソースが利用可能です:
   - calendar://events: Calendar events resource
   - calendar://calendars: Calendar list resource

📋 Step 9: calendar://events リソースを読み取り
📖 リソース 'calendar://events' を読み取り中...
✅ calendar://events リソース読み取り成功

🎉 MCPクライアント経由の呼び出しシナリオが完了しました
✅ テストが正常に完了しました
```

**主要な検証項目:**
1. **プロトコル準拠性**: 標準MCP仕様への完全準拠
2. **ツール呼び出し**: 全MCPツールの動作確認
3. **リソースアクセス**: MCPリソースの読み取り検証
4. **エラー処理**: 異常系での適切な処理とクリーンアップ
5. **ログ品質**: 開発・デバッグに有用な構造化ログ出力

**運用での活用方法:**
- CI/CD パイプラインでの回帰テスト
- MCPサーバー変更後の動作確認
- 新しいMCPクライアント実装時の参考実装
- トラブルシューティング時の通信ログ確認
