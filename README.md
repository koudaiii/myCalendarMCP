# macOS Calendar MCP Server

macOS の Calendar アプリ（EventKit）にアクセスするための MCP（Model Context Protocol）サーバーです。

## 機能

- カレンダーイベントの取得
- 新しいイベントの作成
- イベントの更新・削除
- カレンダー一覧の取得

## 必要な環境

- macOS (Apple Silicon 対応)
- Python 3.8+
- EventKit フレームワークへのアクセス許可

## セットアップ

```bash
# 環境セットアップ（uvを使用）
./script/setup
```

## 使用方法

```bash
# MCPサーバーを起動
./script/server

# テストを実行
./script/test
```

## スクリプト

- `./script/setup` - uvを使った環境セットアップ
- `./script/server` - MCPサーバーの起動
- `./script/test` - テスト実行とコード品質チェック

## MCP 設定

Kiro の MCP 設定に以下を追加：

```json
{
  "mcpServers": {
    "calendar": {
      "command": "uv",
      "args": ["run", "python", "-m", "calendar_mcp"],
      "cwd": ".",
      "disabled": false,
      "autoApprove": ["list_calendars", "get_events", "create_event"]
    }
  }
}
```