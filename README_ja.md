# macOS Calendar MCP Server

macOS の Calendar アプリ（EventKit）にアクセスするための MCP（Model Context Protocol）サーバーです。

<!-- TOC -->
- [概要](#macos-calendar-mcp-server)
- [機能](#機能)
- [必要な環境](#必要な環境)
  - [macOS プライバシー設定](#macos-プライバシー設定)
- [セットアップ](#セットアップ)
- [MCPサーバー起動](#mcpサーバー起動)
  - [HTTPトランスポートの特徴と制限](#httpトランスポートの特徴と制限)
    - [SSEトランスポート接続](#sseトランスポート接続)
    - [Streamable HTTPトランスポート接続](#streamable-httptランスポート接続)
- [VS Code (Claude Code) での設定](#vs-code-claude-code-での設定)
- [CLI から直接使用](#cli-から直接使用)
- [トラブルシューティング](#トラブルシューティング)
  - [カレンダーにアクセスできない](#❌-カレンダーにアクセスできない)
  - [uv コマンドが見つからない](#❌-uv-コマンドが見つからない)
<!-- /TOC -->

## 機能

- カレンダーイベントの取得
- 新しいイベントの作成
- イベントの更新・削除
- カレンダー一覧の取得

## 必要な環境

- macOS (Apple Silicon 対応)
- Python 3.8+
- EventKit フレームワークへのアクセス許可

### macOS プライバシー設定

カレンダーにアクセスするには、macOS のプライバシー設定でアクセス許可が必要です：

1. **システム設定** > **プライバシーとセキュリティ** > **カレンダー**
2. 以下のアプリケーションを **オン** にしてください：
   - Terminal/iTerm2 (CLI で使用する場合)

**注意**: 設定変更後は、アプリケーションを再起動してください。

## セットアップ

```bash
# 環境セットアップ（uvを使用）
./script/setup
```

## MCPサーバー起動

```bash
# MCPサーバーを起動（Streamable HTTPトランスポート - 推奨）
./script/server

# トランスポート方式をカスタマイズ
# MCP 2025-03-26仕様に基づく推奨順位: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
./script/server --transport streamable-http  # Streamable HTTP (リモートサーバー推奨)
./script/server --transport stdio      # 標準入出力 (ローカルプロセス推奨)
./script/server --transport sse        # レガシーSSE (非推奨、互換性のみ)

# テストを実行
./script/test
```

**HTTPエンドポイント**:
- SSE: `http://127.0.0.1:8000/sse` でアクセス可能
- Streamable HTTP: `http://127.0.0.1:8000` でアクセス可能（MCP クライアント用）

### HTTPトランスポートの特徴と制限

**SSEトランスポート接続:**
- エンドポイント: `http://127.0.0.1:8000/sse`
- プロトコル: Server-Sent Events (SSE)
- メッセージ送信: POST `http://127.0.0.1:8000/messages`

**Streamable HTTPトランスポート接続:**
- エンドポイント: `http://127.0.0.1:8000/`
- プロトコル: HTTP/1.1 ストリーミング
- 双方向通信対応


### VS Code (Claude Code) での設定

- `$ script/server --transport streamable-http` (推奨)
- `$ script/server --transport sse` (レガシー互換性)

**SSEトランスポート用設定 (settings.json または .vscode/settings.json):**
```json
{
  "claude.mcpServers": {
    "calendar-mcp": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

**Streamable HTTPトランスポート用設定 (settings.json または .vscode/settings.json):**

- `$ script/server --transport streamable-http` (MCP 2025-03-26仕様推奨)

```json
{
  "claude.mcpServers": {
    "calendar-mcp": {
      "url": "http://127.0.0.1:8000/"
    }
  }
}
```

## CLI から直接使用

```bash
# 直近7日間のイベントを取得
./script/query "直近の一覧を教えて"

# 3日間のイベントを取得
./script/query -d 3 "今日から3日間のイベント"

# 特定のカレンダーのイベントを取得
./script/query -c "仕事" "仕事カレンダーのイベント"

# 利用可能なカレンダー一覧を表示
./script/query -l "カレンダー一覧を表示"

# ヘルプを表示
./script/query -h
```

## MCPクライアントテスト

標準MCPプロトコルに従ったクライアント側からのアプローチでMCPサーバーをテストします：

```bash
# MCPクライアントシナリオのテスト（stdio トランスポート）
./script/mcp_client_test
```

このテストスクリプトの機能：
- stdio トランスポートでMCPサーバーを起動
- JSON-RPC プロトコルを使用してMCPクライアントとして接続
- 利用可能な全ツールをテスト（get_events、create_event、list_calendars）
- リソース読み取りをテスト（calendar://events、calendar://calendars）
- MCP通信の詳細ログを提供
- 完全なMCP統合ワークフローを検証

**特徴:**
- 完全なMCPプロトコル初期化とハンドシェイク
- 並列および逐次ツール実行
- 全MCP通信の構造化JSONログ
- エラーハンドリングとサーバークリーンアップ
- `docs/05-call-methods-comparison.md` に対応した包括的シナリオテスト

## トラブルシューティング

### ❌ カレンダーにアクセスできない

**問題**: "EventKit not available" または空のイベント一覧

**解決方法**:
1. **プライバシー設定を確認**
   ```
   システム設定 > プライバシーとセキュリティ > カレンダー
   ```
   使用している Terminal をオンにする

2. **アプリケーションを再起動**
   設定変更後は必ずアプリケーションを再起動してください


### ❌ uv コマンドが見つからない

**問題**: "command not found: uv"

**解決方法**:
```bash
# uv をインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# または Homebrew 経由で
brew install uv
```
