# Claude Code メモリ

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