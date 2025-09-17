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