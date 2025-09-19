# LLMとMCPクライアントの正確な関係

## はじめに - MCPにおけるLLMの役割の誤解

MCPクライアントについて語る際、「LLMが動的に実行している」という誤解が生じがちです。実際には、**LLM自体はMCPツールを直接実行しない**のが正確な理解です。この章では、LLMとMCPクライアントの正確な関係と、実際のアーキテクチャを明確にします。

## 正確なMCPアーキテクチャ

### 1. LLMの実際の役割

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant LLM as LLM (Claude/GPT等)
    participant Client as MCPクライアント<br/>(アプリケーション)
    participant Server as MCPサーバー
    participant Data as データソース

    User->>LLM: "今日の予定を教えて"
    LLM->>LLM: 意図理解・推論
    LLM->>Client: ツール呼び出し指示<br/>(JSON形式)

    Note over LLM: LLMは実行環境から離脱<br/>以降は非LLM処理

    Client->>Server: MCP JSON-RPC呼び出し
    Server->>Data: データアクセス
    Data-->>Server: カレンダーデータ
    Server-->>Client: JSON レスポンス
    Client->>Client: 結果処理・フォーマット
    Client-->>LLM: 処理結果
    LLM->>LLM: 最終応答生成
    LLM-->>User: "今日は会議が3つあります..."
```

**重要な点:**
- **LLMは推論・意図理解のみ**: ツール実行の判断と結果解釈
- **実際の実行はMCPクライアント**: LLMとは独立したプロセス
- **LLMは実行中に関与しない**: ツール呼び出し後はMCPクライアントが処理

### 2. script/queryとの対比

#### script/query: 直接実行モデル
```bash
# ユーザーが直接実行
./script/query "今日の予定"
# ↓ 人間が意図を事前に構造化済み
# ↓ スクリプトが直接サーバーメソッド呼び出し
```

#### LLM + MCPクライアント: 分離モデル
```json
// 1. LLMが意図を構造化
{
  "思考": "ユーザーは今日の予定を知りたがっている",
  "ツール": "get_macos_calendar_events",
  "パラメータ": {
    "start_date": "2024-09-19",
    "end_date": "2024-09-19"
  }
}

// 2. MCPクライアントが実行 (LLMは関与しない)
// 3. LLMが結果を解釈・応答生成
```

## 実際のMCPクライアント実装例

### 1. Claude Desktop での実際の動作

```typescript
// Claude Desktop (MCPクライアント) の内部処理例
class ClaudeDesktopMCPClient {
  async handleLLMToolRequest(toolCall: LLMToolCall): Promise<ToolResult> {
    // LLMからのツール呼び出し指示を受信
    const { name, arguments: args } = toolCall;

    try {
      // MCPサーバーへの実際の呼び出し (LLMは関与しない)
      const response = await this.mcpConnection.sendRequest({
        jsonrpc: "2.0",
        method: "tools/call",
        params: { name, arguments: args },
        id: this.generateId()
      });

      // 結果をLLMに返却
      return {
        content: response.result.content,
        isError: false
      };
    } catch (error) {
      // エラーもLLMに返却
      return {
        content: `Error: ${error.message}`,
        isError: true
      };
    }
  }
}
```

**重要な理解:**
- **LLMはツール呼び出しを「依頼」するだけ**
- **実際の実行はClaudeデスクトップアプリが担当**
- **LLMは結果を受け取って解釈・応答生成**

### 2. カスタムMCPクライアントの実装

```python
# カスタムAIアシスタントでのMCP統合例
class CustomAIAssistant:
    def __init__(self):
        self.llm = OpenAIClient()  # LLM API
        self.mcp_client = MCPClient()  # MCPクライアント

    async def process_user_query(self, user_input: str) -> str:
        # Phase 1: LLMによる意図理解・ツール選択
        llm_response = await self.llm.complete([
            {"role": "system", "content": "利用可能なツール: get_macos_calendar_events"},
            {"role": "user", "content": user_input}
        ], tools=self.get_available_tools())

        # Phase 2: LLMがツール呼び出しを決定した場合
        if llm_response.tool_calls:
            tool_results = []

            for tool_call in llm_response.tool_calls:
                # MCPクライアントが実際にツール実行 (LLMは関与しない)
                result = await self.execute_mcp_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
                tool_results.append(result)

            # Phase 3: LLMが結果を解釈して最終応答生成
            final_response = await self.llm.complete([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": "", "tool_calls": llm_response.tool_calls},
                {"role": "tool", "content": json.dumps(tool_results)}
            ])

            return final_response.content

    async def execute_mcp_tool(self, tool_name: str, args: dict) -> dict:
        """LLMとは独立したMCPツール実行"""
        try:
            response = await self.mcp_client.call_tool(tool_name, args)
            return {
                "success": True,
                "data": response.content[0].text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

## LLMの制約と分離の理由

### 1. LLMがツールを直接実行できない技術的理由

#### セキュリティ分離
```python
# ❌ LLMが直接実行する場合の危険性
def dangerous_llm_direct_execution():
    """
    LLMが直接システムにアクセスする場合:
    - 予期しないコマンド実行
    - セキュリティ境界の破綻
    - 監査証跡の欠如
    """
    llm_output = "rm -rf /"  # LLMの予期しない出力
    os.system(llm_output)    # 危険な直接実行

# ✅ MCP による安全な分離
class SafeMCPExecution:
    def execute_tool(self, tool_name: str, args: dict):
        # 1. ツール名の検証
        if tool_name not in self.allowed_tools:
            raise SecurityError("Unauthorized tool")

        # 2. パラメータの検証
        validated_args = self.validate_parameters(args)

        # 3. 権限チェック
        if not self.check_permissions(tool_name):
            raise PermissionError("Insufficient permissions")

        # 4. 安全な実行
        return self.execute_safely(tool_name, validated_args)
```

#### プロセス分離
```yaml
# Docker での分離例
version: '3.8'
services:
  llm-service:
    image: llm-runtime
    # LLMは推論のみ、システムアクセスなし
    networks:
      - llm-network
    volumes: []  # ファイルシステムアクセスなし

  mcp-client:
    image: mcp-client
    # MCPクライアントのみがシステムアクセス
    networks:
      - llm-network
      - mcp-network
    volumes:
      - /var/calendar:/data:ro

  mcp-server:
    image: mycalendar-mcp
    # MCPサーバーが実際のデータアクセス
    networks:
      - mcp-network
    volumes:
      - /Users/user/Library/Calendars:/calendars:ro
```

### 2. 責任分離の設計思想

#### LLMの責務（推論層）
- **自然言語理解**: ユーザー意図の解釈
- **文脈推論**: 過去の会話履歴からの判断
- **ツール選択**: 適切なツールとパラメータの決定
- **結果解釈**: ツール実行結果の人間向け変換

#### MCPクライアントの責務（実行層）
- **プロトコル処理**: JSON-RPC通信の管理
- **エラーハンドリング**: 接続エラー、タイムアウト処理
- **リソース管理**: 接続プール、キャッシュ管理
- **セキュリティ**: 認証、認可、監査ログ

#### MCPサーバーの責務（データ層）
- **データアクセス**: 実際のシステムリソースへのアクセス
- **ビジネスロジック**: ドメイン固有の処理
- **システム統合**: EventKit、ファイルシステム等との連携

## 実世界での動作例

### 1. Claude Desktop + mycalendarMCP

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Claude as Claude (LLM)
    participant Desktop as Claude Desktop<br/>(MCPクライアント)
    participant MCP as mycalendarMCP<br/>サーバー
    participant EventKit as EventKit

    User->>Claude: "明日の会議は何時から？"

    Note over Claude: LLMが推論:<br/>「明日の予定を取得する必要がある」

    Claude->>Desktop: ツール呼び出し指示<br/>get_macos_calendar_events<br/>start_date: "2024-09-20"<br/>end_date: "2024-09-20"

    Note over Claude: LLMは待機状態<br/>実行には関与しない

    Desktop->>MCP: JSON-RPC呼び出し
    MCP->>EventKit: カレンダーデータアクセス
    EventKit-->>MCP: イベントデータ
    MCP-->>Desktop: JSON レスポンス

    Desktop-->>Claude: ツール実行結果

    Note over Claude: LLMが結果を解釈:<br/>「会議データを人間向けに整形」

    Claude-->>User: "明日は午前10時から<br/>チームミーティングがあります"
```

### 2. script/query との処理時間比較

| フェーズ | script/query | LLM + MCPクライアント |
|---------|-------------|----------------------|
| **意図理解** | 0ms (人間が事前実行) | 200ms (LLM推論) |
| **パラメータ構築** | 0ms (スクリプト内で固定) | 0ms (LLMが既に構築) |
| **ツール実行** | 150ms (直接呼び出し) | 180ms (MCP経由) |
| **結果整形** | 50ms (固定フォーマット) | 100ms (LLM生成) |
| **合計** | **200ms** | **480ms** |

**LLMを使う価値:**
- **柔軟性**: 「明日の会議」「来週の重要な予定」等の自然言語対応
- **文脈理解**: 過去の会話を踏まえた適切な応答
- **応答品質**: 人間に優しい自然な表現

## 開発者への実装ガイダンス

### 1. LLM統合時の注意点

```python
# ❌ 間違った理解
class WrongLLMIntegration:
    async def process(self, user_input):
        # LLMにツール実行まで任せてしまう
        return await self.llm.execute_tools_directly(user_input)

# ✅ 正しい実装
class CorrectLLMIntegration:
    async def process(self, user_input):
        # 1. LLMは推論のみ
        llm_decision = await self.llm.plan_tools(user_input)

        # 2. アプリケーションがMCPツール実行
        results = []
        for tool_call in llm_decision.tool_calls:
            result = await self.mcp_client.execute(
                tool_call.name,
                tool_call.arguments
            )
            results.append(result)

        # 3. LLMが結果解釈
        return await self.llm.synthesize_response(user_input, results)
```

### 2. エラーハンドリングの分離

```python
class ProperErrorHandling:
    async def handle_mcp_error(self, error: MCPError) -> str:
        """MCPエラーをLLMが理解できる形に変換"""

        if isinstance(error, MCPConnectionError):
            return "カレンダーサービスに接続できませんでした。後でもう一度お試しください。"

        elif isinstance(error, MCPPermissionError):
            return "カレンダーへのアクセス権限がありません。システム設定を確認してください。"

        elif isinstance(error, MCPTimeoutError):
            return "カレンダーの読み込みに時間がかかっています。しばらくお待ちください。"

        else:
            # 予期しないエラーもLLMに適切に伝達
            return f"カレンダー処理中にエラーが発生しました: {error.user_message}"

    async def process_with_error_handling(self, user_input: str):
        try:
            # 通常のLLM + MCP処理
            return await self.normal_process(user_input)

        except MCPError as e:
            # MCPエラーを人間向けメッセージに変換
            error_message = await self.handle_mcp_error(e)

            # LLMに文脈を保持させつつエラー報告
            return await self.llm.generate_error_response(user_input, error_message)
```

## 結論: 正確な理解の重要性

### LLMとMCPの正しい関係

1. **LLM**: 推論・意図理解・応答生成の専門家
2. **MCPクライアント**: ツール実行・エラー処理・リソース管理の専門家
3. **MCPサーバー**: データアクセス・システム統合の専門家

### 誤解と正しい理解

| 誤解 | 正しい理解 |
|-----|-----------|
| LLMがツールを直接実行 | LLMは実行指示のみ、実行はMCPクライアント |
| LLMが常に関与 | ツール実行中はLLMは待機状態 |
| LLMがシステムアクセス | システムアクセスはMCPサーバーのみ |
| 動的な実行判断 | 事前の推論に基づく静的な実行指示 |

## 他のAIアシスタントとの比較

### GitHub Copilot、Claude Code との共通点と違い

**共通するアーキテクチャパターン:**
```
ユーザー → LLM推論 → クライアントアプリ → ツール実行 → 結果統合
```

#### 比較表

| 項目 | GitHub Copilot | Claude Code | MCP AIアシスタント |
|------|---------------|-------------|-------------------|
| **LLMの役割** | 推論・コード生成 | 推論・タスク計画 | **推論・意図理解** |
| **クライアントの役割** | VS Code Extension | CLI アプリ | **標準MCPクライアント** |
| **ツール実行** | GitHub/Git API | Bash/File操作 | **標準MCPプロトコル** |
| **対象ドメイン** | 開発・GitHub | 開発・ファイル | **あらゆるドメイン** |
| **拡張性** | GitHub Apps | Claude固有 | **任意のMCPサーバー** |
| **標準化** | GitHub固有 | Anthropic固有 | **業界標準プロトコル** |

#### アーキテクチャの進化

```mermaid
graph TB
    subgraph "特化型AIアシスタント"
        GH[GitHub Copilot<br/>↓<br/>開発ドメイン特化]
        CC[Claude Code<br/>↓<br/>開発ツール統合]
    end

    subgraph "汎用型AIアシスタント"
        MCP[MCP AIアシスタント<br/>↓<br/>ドメイン非依存<br/>標準プロトコル]
    end

    GH -.->|"ドメイン拡張"| MCP
    CC -.->|"プロトコル標準化"| MCP
```

#### 実装例の比較

**GitHub Copilot:**
```typescript
// VS Code内でのコード補完
async onCodeCompletion(context: CodeContext) {
  const suggestions = await this.githubLLM.generateCode(context);
  return suggestions; // GitHub/Git専用
}
```

**Claude Code:**
```typescript
// CLI環境での開発タスク
async handleDevTask(input: string) {
  const plan = await this.claude.plan(input);
  await this.executeDevTools(plan); // 開発ツール専用
}
```

**MCP AIアシスタント:**
```typescript
// 汎用ドメインタスク
async handleAnyTask(input: string) {
  const plan = await this.llm.plan(input, this.getAllMCPTools());
  await this.executeMCPTools(plan); // あらゆるドメイン対応
}
```

### MCP AIアシスタントの独自価値

1. **ドメイン非依存**: カレンダー、メール、データベース、IoT等あらゆる領域
2. **標準プロトコル**: 複数ベンダーのツールを統一インターフェースで利用
3. **エコシステム**: 開発者が独自MCPサーバーを作成・共有可能
4. **相互運用性**: 異なるLLM・クライアントでも同じMCPサーバーを利用

この正確な理解により、安全で効率的なLLM + MCP統合システムを構築できるようになります。

---

MCP AIアシスタントは、GitHub CopilotやClaude Codeの進化形として、特定ドメインに限定されない汎用的なAIアシスタントアーキテクチャを実現しています。