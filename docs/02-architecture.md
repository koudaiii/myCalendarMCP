# mycalendarMCP アーキテクチャ

## プロジェクト構造

```
mycalendarMCP/
├── calendar_mcp/
│   ├── __init__.py
│   ├── __main__.py          # エントリーポイント、シグナルハンドラー
│   └── server.py            # FastMCP サーバー実装
├── script/
│   ├── server               # サーバー起動スクリプト
│   ├── test                 # テスト実行スクリプト
│   └── debug_tools.py       # デバッグツール
├── tests/
│   ├── conftest.py          # pytest 設定
│   └── test_tools.py        # MCPツール包括的テスト
├── docs/                    # プロジェクトドキュメント
├── CLAUDE.md               # プロジェクトメモリ
├── README.md               # プロジェクト概要
└── pyproject.toml          # プロジェクト設定
```

## コアコンポーネント

### 1. エントリーポイント (`calendar_mcp/__main__.py`)

```python
def signal_handler(signum, frame):
    """シグナルハンドラー: Ctrl+C での安全な終了"""

async def main():
    """メインエントリーポイント"""
    # シグナルハンドラー設定
    # サーバーインスタンス作成と起動
```

**役割:**
- アプリケーションの起動処理
- シグナルハンドリング（Ctrl+C での安全な終了）
- asyncio イベントループの管理

### 2. MCPサーバー (`calendar_mcp/server.py`)

#### サーバークラス設計

```python
class CalendarMCPServer:
    def __init__(self):
        self.mcp = FastMCP("mycalendar")
        self.event_store = None
        self._setup_tools()
        self._setup_resources()
```

**FastMCP統合:**
- FastMCP フレームワークを使用
- 自動的なツール・リソース登録
- JSON-RPC over 複数トランスポート

#### EventKit統合

```python
# EventKit 初期化
if EVENTKIT_AVAILABLE:
    self.event_store = EventKit.EKEventStore.alloc().init()
```

**技術的詳細:**
- `pyobjc-framework-EventKit` を使用
- macOS ネイティブカレンダーアプリとの連携
- システム権限管理（プライバシー設定）

### 3. ツール実装アーキテクチャ

#### ツール定義パターン

```python
@self.mcp.tool(
    name="get_macos_calendar_events",
    description="詳細な説明とパラメータ仕様",
    annotations=ToolAnnotations(
        title="人間が読みやすいタイトル",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False
    ),
)
async def get_macos_calendar_events(
    start_date: str,
    end_date: str,
    calendar_name: str = None
) -> str:
```

**設計原則:**
- 非同期処理による高パフォーマンス
- 型ヒント活用による安全性
- 詳細なメタデータによるAIエージェント支援

#### 提供ツール

| ツール名 | 機能 | 特性 |
|---------|------|------|
| `get_macos_calendar_events` | イベント取得 | 読み取り専用、冪等 |
| `create_macos_calendar_event` | イベント作成 | 破壊的、非冪等 |
| `list_macos_calendars` | カレンダー一覧 | 読み取り専用、冪等 |

### 4. リソース実装アーキテクチャ

#### リソース定義パターン

```python
@self.mcp.resource("calendar://events")
async def calendar_events_resource() -> str:
    """近日のカレンダーイベント一覧リソース"""
```

**提供リソース:**
- `calendar://events`: 近日のイベント一覧
- `calendar://calendars`: 利用可能なカレンダー一覧

## データフロー

mycalendarMCPのデータフローは、ツール呼び出しからエラーハンドリング、初期化プロセスまでの主要な処理をシーケンス図とフローチャートで視覚化します。

### 1. 通常のMCPツール呼び出し

```mermaid
sequenceDiagram
    participant Client as MCPクライアント
    participant Server as CalendarMCPServer
    participant EventKit as EventKit Framework
    participant Calendar as macOS Calendar

    Client->>Server: ツール呼び出し (JSON-RPC)
    Server->>Server: ログ出力 (INCOMING)
    Server->>EventKit: EventKit API 呼び出し
    EventKit->>Calendar: システムレベルアクセス
    Calendar-->>EventKit: カレンダーデータ
    EventKit-->>Server: イベント情報
    Server->>Server: ログ出力 (OUTGOING)
    Server-->>Client: 構造化JSON レスポンス
```

### 2. サーバー初期化とトランスポート接続

```mermaid
sequenceDiagram
    participant Main as __main__.py
    participant Server as CalendarMCPServer
    participant FastMCP as FastMCP Framework
    participant EventKit as EventKit
    participant Transport as Transport Layer

    Main->>Server: CalendarMCPServer()初期化
    Server->>EventKit: EventStore初期化
    EventKit-->>Server: 権限チェック完了
    Server->>FastMCP: ツール・リソース登録
    FastMCP-->>Server: 登録完了
    Main->>Transport: 非同期トランスポート起動
    note over Transport: stdio/SSE/streamable-http
    Transport-->>Main: 接続待機状態
```

### 3. イベント作成フロー

```mermaid
sequenceDiagram
    participant Client as MCPクライアント
    participant Server as CalendarMCPServer
    participant EventKit as EventKit
    participant Calendar as macOS Calendar

    Client->>Server: create_macos_calendar_event
    Server->>Server: パラメータ検証
    Server->>EventKit: EKEvent作成
    EventKit->>Calendar: カレンダー選択
    Calendar-->>EventKit: カレンダー参照
    EventKit->>Calendar: イベント保存
    Calendar-->>EventKit: 保存確認
    EventKit-->>Server: 作成完了
    Server->>Server: 成功ログ出力
    Server-->>Client: 作成結果JSON
```

### 4. エラーハンドリングフロー

```mermaid
flowchart TD
    A[ツール呼び出し] --> B{EventKit利用可能?}
    B -->|No| C[フォールバック応答]
    B -->|Yes| D{権限チェック}
    D -->|拒否| E[権限エラー応答]
    D -->|許可| F[EventKit操作実行]
    F --> G{操作成功?}
    G -->|失敗| H[詳細エラー応答]
    G -->|成功| I[構造化データ応答]

    C --> J[エラーログ出力]
    E --> J
    H --> J
    I --> K[成功ログ出力]
    J --> L[クライアントへ応答]
    K --> L
```

### 5. LLMを含む完全なリソース取得フロー

LLMを含むリソース取得フローは、自然言語理解、動的判断、反復的問い合わせを含むプロセスです。ユーザーの自然言語入力から最終応答生成まで、LLMがMCPシステムと協調する流れを説明します。

#### 5.1. LLMによる自然言語理解と初期計画

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant LLM as LLM (Claude/GPT等)
    participant Client as MCPクライアント<br/>(アプリケーション)

    User->>LLM: "来週の重要な会議の準備は大丈夫？"
    LLM->>LLM: 自然言語解析<br/>- 「来週」→ 日付範囲計算<br/>- 「重要な会議」→ キーワード抽出<br/>- 「準備」→ 詳細情報が必要
    LLM->>Client: 初期計画指示<br/>1. 利用可能ツール確認<br/>2. 来週のイベント取得<br/>3. 会議情報の詳細分析

    note over LLM: LLMは実行せず計画のみ<br/>実際の実行はMCPクライアント
```

#### 5.2. MCPクライアントによるツール発見フェーズ

```mermaid
sequenceDiagram
    participant LLM as LLM
    participant Client as MCPクライアント
    participant Server as CalendarMCPServer

    LLM->>Client: ツール発見要求
    Client->>Server: tools/list (JSON-RPC)
    Server-->>Client: 利用可能ツール一覧<br/>- get_macos_calendar_events<br/>- create_macos_calendar_event<br/>- list_macos_calendars
    Client->>Client: ツール能力分析<br/>- パラメータ要件<br/>- 戻り値形式<br/>- 制約事項
    Client-->>LLM: ツール情報提供<br/>+ 実行可能性評価

    note over Client: MCPクライアントが<br/>ツールの詳細を解析
```

#### 5.3. 段階的ツール実行フェーズ

```mermaid
sequenceDiagram
    participant LLM as LLM
    participant Client as MCPクライアント
    participant Server as CalendarMCPServer
    participant EventKit as EventKit

    LLM->>Client: 実行計画<br/>Phase 1: カレンダー一覧<br/>Phase 2: 来週イベント取得<br/>Phase 3: 条件分析

    %% Phase 1: カレンダー情報取得
    rect rgb(240, 248, 255)
        note over LLM, EventKit: Phase 1: カレンダー情報収集
        Client->>Server: list_macos_calendars()
        Server->>EventKit: カレンダー一覧取得
        EventKit-->>Server: カレンダーデータ
        Server-->>Client: JSON応答
        Client->>Client: 応答分析<br/>- 利用可能カレンダー<br/>- 会議関連カレンダー特定
    end

    %% Phase 2: 並列イベント取得
    rect rgb(240, 255, 240)
        note over LLM, EventKit: Phase 2: 並列イベント取得
        par 並列実行
            Client->>Server: get_events(仕事カレンダー)
            Server->>EventKit: 仕事イベント取得
            EventKit-->>Server: 仕事イベントデータ
            Server-->>Client: JSON応答1
        and
            Client->>Server: get_events(プロジェクトカレンダー)
            Server->>EventKit: プロジェクトイベント取得
            EventKit-->>Server: プロジェクトイベントデータ
            Server-->>Client: JSON応答2
        end
        Client->>Client: 結果統合・重複除去
    end

    Client-->>LLM: 段階的結果報告<br/>- 発見されたカレンダー数<br/>- 取得イベント数<br/>- 会議候補イベント
```

#### 5.4. LLMによる動的判断と追加問い合わせ

```mermaid
sequenceDiagram
    participant LLM as LLM
    participant Client as MCPクライアント
    participant Server as CalendarMCPServer

    Client->>LLM: 中間結果提供<br/>「3つの会議が見つかりました」
    LLM->>LLM: 結果分析<br/>- 情報充足性評価<br/>- 追加調査の必要性判断<br/>- 詳細化戦略決定

    alt 情報が不十分な場合
        LLM->>Client: 追加調査指示<br/>「特定の期間に絞って詳細取得」

        rect rgb(255, 248, 240)
            note over LLM, Server: 追加問い合わせフェーズ
            Client->>Server: get_events(詳細期間指定)<br/>start_date: "2024-09-23"<br/>end_date: "2024-09-27"
            Server-->>Client: 詳細イベントデータ

            Client->>Server: get_events(異なる期間)<br/>start_date: "2024-09-30"<br/>end_date: "2024-10-04"
            Server-->>Client: 追加イベントデータ
        end

        Client->>LLM: 追加情報統合結果
        LLM->>LLM: 最終分析<br/>- パターン認識<br/>- 重要度評価<br/>- 準備状況判定
    else 情報が十分な場合
        LLM->>LLM: 直接応答生成処理
    end
```

#### 5.5. 反復的精緻化と最終応答生成

```mermaid
sequenceDiagram
    participant LLM as LLM
    participant Client as MCPクライアント
    participant Server as CalendarMCPServer
    participant User as ユーザー

    LLM->>LLM: 包括的分析<br/>- 全データ統合<br/>- コンテキスト理解<br/>- 応答戦略決定

    alt さらなる詳細が必要
        LLM->>Client: 最終確認問い合わせ<br/>「特定会議の詳細情報」

        loop 必要に応じて反復
            Client->>Server: 条件絞り込み問い合わせ
            Server-->>Client: 特定データ
            Client->>LLM: 段階的情報提供
            LLM->>LLM: 充足性評価
        end
    end

    LLM->>LLM: 最終応答生成<br/>- 自然言語変換<br/>- ユーザー文脈適応<br/>- アクション提案生成

    LLM-->>User: 統合応答<br/>「来週は3つの重要会議があります：<br/>1. プロジェクトレビュー（要準備）<br/>2. クライアント面談（資料確認済み）<br/>3. 四半期計画会議（追加準備推奨）」

    note over LLM: LLMが全情報を統合して<br/>ユーザーフレンドリーな<br/>実用的アドバイスを生成
```

#### 5.6. 実行パターンと最適化戦略

上記のフローにおいて、LLMとMCPクライアントは以下の実行パターンを採用します：

**並列実行の判断基準：**
- 独立性: 問い合わせが相互に依存しない場合（異なるカレンダー、異なる期間）
- 効率性: 同時実行により全体の応答時間を短縮できる場合
- リソース制約: MCPサーバーの処理能力とネットワーク帯域を考慮

**逐次実行の選択理由：**
- 依存関係: 前の結果に基づいて次の問い合わせパラメータを決定する必要がある場合
- 条件分岐: LLMが中間結果を評価して戦略を変更する必要がある場合
- エラー処理: 前の問い合わせが失敗した場合の代替戦略実行

**反復回数の動的制御：**
- 初期問い合わせ: 1-2回（基本情報収集）
- 精緻化問い合わせ: 0-3回（LLMの判断による）
- 最終確認問い合わせ: 0-1回（必要に応じて）
- 合計最大: 6回程度（タイムアウト制御含む）

この包括的フローにより、LLMはユーザー意図を理解し、動的な情報収集戦略を実行し、文脈に適した応答を生成します。

## トランスポート層の実装

### asyncio イベントループ統合

```python
# calendar_mcp/server.py:272-280
if args.transport == "sse":
    await server_instance.mcp.run_sse_async(mount_path=args.mount_path)
elif args.transport == "stdio":
    await server_instance.mcp.run_stdio_async()
elif args.transport == "streamable-http":
    await server_instance.mcp.run_streamable_http_async()
```

**技術的解決策:**
- FastMCP の `run()` は内部で `anyio.run()` を呼び出すため、既存の asyncio イベントループ内では使用不可
- 各トランスポート専用の async メソッドを使用
- 二重イベントループ問題の回避

### 利用可能なトランスポート

| トランスポート | 用途 | 特徴 |
|---------------|------|------|
| `stdio` | CLI/デバッグ | シンプル、デバッグ容易 |
| `sse` | Web統合 | リアルタイム、ブラウザ対応 |
| `streamable-http` | 高性能 | HTTP/2、大量データ転送 |

## ログ・監視アーキテクチャ

### JSON構造化ログ

```python
def log_json_data(logger, direction: str, data_type: str, data):
    """JSON形式でのログ出力"""
    logger.info(f"[{direction}] {data_type}:")
    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
```

**ログカテゴリ:**
- `[INCOMING]`: クライアントからのリクエスト
- `[OUTGOING]`: サーバーからのレスポンス

**出力フォーマット:**
```
2024-09-18 10:30:15,123 - calendar_mcp.server.json_data - [INCOMING] TOOL REQUEST:
{
  "name": "get_events",
  "arguments": {...}
}
```

## パフォーマンス設計

### EventKit最適化

```python
# EventStore インスタンスの再利用
self.event_store = EventKit.EKEventStore.alloc().init()

# 非同期処理パターン
async def get_macos_calendar_events(...) -> str:
    # EventKit操作の非同期化
```

**最適化戦略:**
- EventStore インスタンスの再利用
- 非同期処理による応答性向上
- レスポンスサイズの制限（推奨: 1000件/10MB以下）
- 適切なタイムアウト設定（5秒以内）

### メモリ管理

- NSDate オブジェクトのリーク防止
- EventKit リソースの適切な解放
- JSONログのローテーション対応

## セキュリティアーキテクチャ

### 権限管理

```python
# システムレベルのプライバシー制御
try:
    self.event_store = EventKit.EKEventStore.alloc().init()
except Exception as e:
    logger.error(f"EventKit initialization failed: {e}")
    return {"status": "unavailable", "reason": "EventKit access denied"}
```

**セキュリティ層:**
1. **システムレベル**: macOS プライバシー設定
2. **アプリケーションレベル**: EventKit権限チェック
3. **MCPレベル**: 入力検証とサニタイゼーション

### データ保護

- カレンダーデータの読み取り専用アクセス（get_events, list_calendars）
- 書き込み操作の明示的な許可（create_event）
- 機密情報のログ出力回避

## 拡張性設計

### 新しいツールの追加

```python
@self.mcp.tool(
    name="new_tool_name",
    description="ツール説明",
    annotations=ToolAnnotations(...)
)
async def new_tool_function(...) -> str:
    """新しいツールの実装"""
```

### 新しいトランスポートの対応

```python
# server.py での拡張例
elif args.transport == "new_transport":
    await server_instance.mcp.run_new_transport_async()
```

このアーキテクチャにより、高性能で拡張可能、安全なMCPサーバーを実現しています。

---

次の章では、MCPサーバー開発におけるベストプラクティスについて詳しく説明します。