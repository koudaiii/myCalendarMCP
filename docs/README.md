# mycalendarMCP ドキュメント

macOSカレンダーとAIエージェントを繋ぐModel Context Protocol (MCP) サーバーの包括的ドキュメント

## ドキュメント構成

### [01. MCPとは - Model Context Protocol概要](./01-mcp-overview.md)
- MCPの基本概念と革新性
- MCPアーキテクチャの基本要素
- トランスポート層（stdio, SSE, streamable-http）
- ツール、リソース、プロンプトの概念
- MCPエコシステムの現状と課題
- 次世代AI開発基盤としての位置づけ

### [02. アーキテクチャ](./02-architecture.md)
- プロジェクト構造とコアコンポーネント
- EventKit統合とFastMCP統合
- ツール・リソース実装パターン
- データフローとエラーハンドリング
- トランスポート層実装（asyncio統合）
- ログ・監視アーキテクチャ
- パフォーマンス設計とセキュリティ

### [03. ベストプラクティス](./03-best-practices.md)
- ツールスペース干渉の回避策
- 固有性を持つツール名の採用
- FastMCPツール定義のベストプラクティス
- パフォーマンス最適化手法
- エラーハンドリング戦略
- ログ・監視の実装方法
- テスト設計とデプロイメント

### [04. トラブルシューティング](./04-troubleshooting.md)
- よくある問題と解決策
  - Asyncio Event Loop競合エラー
  - EventKitアクセス権限エラー
  - テスト実行エラー
  - JSONログ出力の問題
  - パフォーマンス問題
  - MCPクライアント接続エラー
  - 日付フォーマットエラー
- デバッグツールと監視方法
- システム要件確認スクリプト

### [05. 呼び出し方法の比較](./05-call-methods-comparison.md)
- script/query（直接呼び出し）vs MCPクライアント（プロトコル経由）
- 技術的特徴と実装方法の詳細比較
- パフォーマンス・セキュリティ・運用面での違い
- 使用場面に応じた適用指針
- データフロー・出力形式・ログの比較
- ハイブリッドアプローチと移行戦略

### [06. MCPクライアントの意義](./06-mcp-client-significance.md)
- script/queryとの比較から見えるサーバー・クライアントの役割分担
- MCPクライアントの戦略的価値とアーキテクチャ進化
- AIエージェント統合とエンタープライズ統合の実現
- 分散システムアーキテクチャによるエコシステム形成
- プロトコル設計から見るMCPの革新性
- 実世界での適用シナリオと技術的優位性

### [07. LLMとMCPの正確な関係](./07-llm-mcp-relationship.md)
- LLMの役割と制約の正確な理解
- LLM・MCPクライアント・MCPサーバーの責任分離
- セキュリティとプロセス分離の設計思想
- 実際のClaude Desktop等での動作メカニズム
- 開発者向けの実装ガイダンスとエラーハンドリング
- 誤解の訂正と正しいアーキテクチャ理解

## クイックスタート

### 1. ドキュメントの読み方

**初めてMCPに触れる方:**
1. [01-mcp-overview.md](./01-mcp-overview.md) - MCPの全体像を理解
2. [05-call-methods-comparison.md](./05-call-methods-comparison.md) - 使用方法の選択指針
3. [07-llm-mcp-relationship.md](./07-llm-mcp-relationship.md) - LLMとMCPの正確な関係
4. [06-mcp-client-significance.md](./06-mcp-client-significance.md) - MCPクライアントの価値を理解
5. [02-architecture.md](./02-architecture.md) - 実装アーキテクチャを学習
6. [03-best-practices.md](./03-best-practices.md) - 開発のコツを習得

**既存の開発者:**
1. [02-architecture.md](./02-architecture.md) - 技術的詳細を確認
2. [05-call-methods-comparison.md](./05-call-methods-comparison.md) - 実装手法の比較検討
3. [06-mcp-client-significance.md](./06-mcp-client-significance.md) - アーキテクチャ設計の深い理解
4. [03-best-practices.md](./03-best-practices.md) - 改善点を把握
5. [04-troubleshooting.md](./04-troubleshooting.md) - 問題解決方法を習得

**AIエージェント開発者:**
1. [07-llm-mcp-relationship.md](./07-llm-mcp-relationship.md) - **必読**: LLMとMCPの正確な関係
2. [06-mcp-client-significance.md](./06-mcp-client-significance.md) - エージェント統合の戦略的価値
3. [05-call-methods-comparison.md](./05-call-methods-comparison.md) - 統合アプローチの選択
4. [02-architecture.md](./02-architecture.md) - システム連携の技術的詳細

**運用担当者:**
1. [04-troubleshooting.md](./04-troubleshooting.md) - 障害対応を優先
2. [05-call-methods-comparison.md](./05-call-methods-comparison.md) - 運用方式の選択
3. [02-architecture.md](./02-architecture.md) - システム理解を深化

### 2. 実践的な学習パス

**1週目: MCP基礎理解**
- MCP概要とプロトコル仕様の学習
- script/query による直接呼び出しの実践
- MCPクライアント経由での動作確認
- 呼び出し方法の違いと使い分けの理解

**2週目: 開発スキル習得**
- ツール実装のベストプラクティス学習
- エラーハンドリングパターンの実践
- ログ出力とデバッグ手法の習得
- テスト実装による品質確保

**3週目: 運用・最適化**
- パフォーマンス監視の設定
- 本番環境での呼び出し方法の選択
- トラブルシューティング手順の習得
- ハイブリッドアプローチの実装

## 参考資料

### プロジェクト固有ドキュメント
- [CLAUDE.md](../CLAUDE.md) - 開発過程での学習と問題解決記録
- [README.md](../README.md) - プロジェクト概要と使用方法
- [pyproject.toml](../pyproject.toml) - 依存関係と設定

### 外部リソース
- [FastMCP Documentation](https://github.com/jlowin/fastmcp) - FastMCPフレームワーク
- [MCP Specification](https://spec.modelcontextprotocol.io/) - MCPプロトコル仕様
- [Apple EventKit Documentation](https://developer.apple.com/documentation/eventkit) - EventKit API
- [Tool-space Interference Research](https://www.microsoft.com/en-us/research/blog/tool-space-interference-in-the-mcp-era-designing-for-agent-compatibility-at-scale/) - MCP設計指針

## コミュニティとサポート

### 問題報告
- **バグ報告**: GitHubリポジトリのIssueを作成
- **機能要求**: Discussionで提案・議論
- **セキュリティ問題**: メンテナーに直接連絡

### 貢献方法
1. **ドキュメント改善**: 誤字脱字の修正、説明の改善
2. **コード改善**: バグ修正、機能追加、テスト追加
3. **ベストプラクティス共有**: 新しい知見の追加

### 学習コミュニティ
- **開発者フォーラム**: MCP開発者との情報交換
- **技術ブログ**: 実装ノウハウの共有
- **オンラインセミナー**: 最新動向の把握

## 更新履歴

- **v1.1.0** (2024-09): 呼び出し方法比較ドキュメント追加
  - script/query（直接呼び出し）vs MCPクライアント（プロトコル経由）の詳細比較
  - パフォーマンス・セキュリティ・運用面での違いの分析
  - 使用場面に応じた適用指針とハイブリッドアプローチの提案

- **v1.0.0** (2024-09): 初版リリース
  - MCP概要、アーキテクチャ、ベストプラクティス、トラブルシューティングの包括的ドキュメント
  - CLAUDE.mdに蓄積された知見の体系化
  - 21テストケース全通過の品質確保

---

**注意**: このドキュメントは継続的に更新されます。最新の情報については、GitHubリポジトリを確認してください。