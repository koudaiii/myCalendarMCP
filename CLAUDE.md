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