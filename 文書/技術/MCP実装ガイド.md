# MCP実装ガイド

**最終更新**: 2025年7月19日  
**作成者**: Claude（実装担当）  
**目的**: 実装済みMCPの統合運用ガイド

---

## 🚀 実装済みMCP一覧

### 1. ✅ **Context7 MCP** (正常動作)
- **パッケージ**: @upstash/context7-mcp
- **用途**: 外部ドキュメント最新情報取得
- **使用例**: `"Next.js 14の最新機能について教えて。use context7"`

### 2. ✅ **Draw.io MCP** (正常動作)
- **場所**: mcp-servers/drawio-mcp-server/build/index.js
- **用途**: システム図・アーキテクチャ図自動生成
- **使用例**: `"Phase2アーキテクチャ図を生成して"`

### 3. ⚠️ **Jupyter MCP** (依存関係要インストール)
- **場所**: /home/trader/mcp-servers/jupyter-notebook-mcp/src/jupyter_mcp_server.py
- **用途**: Jupyterノートブック連携・バックテスト分析
- **必要作業**: `pip install websockets` 実行

### 4. ✅ **既存MCP** (継続運用)
- **DuckDB**: バックテスト分析DB
- **Neon**: クラウドDB
- **SQLite**: ローカルDB
- **PostgreSQL**: 高性能DB
- **GitHub**: リポジトリ操作
- **Docker**: コンテナ管理
- **Gemini CLI**: AI分析支援

---

## 🔧 現在の設定 (settings.json)

```json
{
  "mcpServers": {
    // 既存MCP継続
    "duckdb": { /* 既存設定 */ },
    "neon": { /* 既存設定 */ },
    "sqlite": { /* 既存設定 */ },
    "postgres": { /* 既存設定 */ },
    "github": { /* 既存設定 */ },
    "docker": { /* 既存設定 */ },
    "gemini-cli": { /* 既存設定 */ },
    
    // 新規追加MCP
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": { "NODE_ENV": "production" }
    },
    "jupyter": {
      "command": "python3",
      "args": ["/home/trader/mcp-servers/jupyter-notebook-mcp/src/jupyter_mcp_server.py"],
      "env": { "PYTHONPATH": "/home/trader/mcp-servers/jupyter-notebook-mcp/src" }
    },
    "drawio": {
      "command": "node",
      "args": ["/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/mcp-servers/drawio-mcp-server/build/index.js"],
      "env": { "NODE_ENV": "production" }
    }
  }
}
```

---

## 🛠️ 使用方法

### Context7での外部情報取得
```
"MetaTrader 5の最新API機能について教えて。use context7"
"Python 3.12の新機能について調べて。use context7"
```

### Draw.ioでの図表生成
```
"ブレイクアウト戦略のフローチャートを作成して"
"Phase2システムのアーキテクチャ図を生成して"
"MCP連携構成図を描いて"
```

### Jupyter Notebook連携 (修復後)
```python
# バックテストデータ分析
# MCPツール経由でセル操作・実行・結果取得
# リアルタイムチャート生成
```

---

## ⚠️ Jupyter MCP修復手順

**1. 依存関係インストール**
```bash
pip install websockets jupyter-client
```

**2. Claude Code再起動**
```bash
# Claude Code完全終了後、再起動
```

**3. 動作確認**
- Jupyter MCPツールが利用可能になる
- NotebookRead、NotebookEdit、executeCodeツール使用可能

---

## 🎯 活用シナリオ

### 1. **戦略分析強化**
- Context7: 最新市場情報・技術資料取得
- Jupyter: リアルタイムバックテスト実行
- DuckDB/PostgreSQL: 大量データ分析

### 2. **ドキュメント自動生成**
- Draw.io: システム設計図・フローチャート
- GitHub: 設計書・コード管理
- Gemini: 品質レビュー・監査

### 3. **開発効率化**
- Docker: 環境統一・デプロイ自動化
- SQLite: 高速プロトタイプ開発
- Neon: 本番データベース運用

---

## ✅ 次のステップ

1. **Jupyter MCP修復** (pip install websockets)
2. **Claude Code再起動** (新MCP反映)
3. **統合テスト実行** (全MCP動作確認)
4. **Phase2実装加速** (MCP活用開発)

---

**📋 重要**: このガイドが唯一のMCP運用文書です。他のMCP関連MDファイルは削除対象。