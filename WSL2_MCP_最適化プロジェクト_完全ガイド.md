# WSL2 MCP最適化プロジェクト 完全実行ガイド

**プロジェクト開始**: 2025-07-30  
**Gemini査読**: 完了（技術的妥当性・実現可能性確認済み）  
**現在ステータス**: Phase 1実装完了、WSL再起動待ち  

## 🎯 プロジェクト概要

### 解決すべき問題
- Claude Code v1.0.63でMCPサーバー（filesystem, fetch, context7）が「Connected」表示されるが実際には動作しない
- `ListMcpResourcesTool`が空配列を返す（stdio transport処理バグ）
- WSL2環境の127.0.0.1バインディング問題
- Sub-Agent機能が完全活用できない状況

### 解決目標
- MCP・Sub-Agent機能の完全活用実現
- ブート切り替えなしでの最大機能利用
- Windows環境での開発効率最大化

## 📚 重要な技術背景

### 関連GitHub Issues
- **Issue #3426**: stdio transport処理バグ（同様事例）
- **Issue #1461, #1611, #357**: WSL2環境でのMCP接続問題

### Gemini査読結果サマリー
- ✅ **技術的妥当性**: networkingMode=mirroredは最新最効果的解決策
- ✅ **実装順序**: Phase 1→2→3は論理的で依存関係明確
- ⚠️ **重要修正**: firewall=false禁止、Docker積極採用、具体的成功指標必要

## 🚀 3フェーズ実行計画（詳細版）

### **Phase 1: WSL2ネットワーク設定修正（セキュリティ強化版）** ✅完了
**実装済み内容**:
- `/home/trader/.wslconfig`作成完了
- セキュア設定適用（mirrored mode + firewall=true）
- Windows側実行手順文書化完了

**設定内容**:
```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
firewall=true
autoProxy=false
systemd=true
appendWindowsPath=false
memory=4GB
processors=2
```

**WSL再起動後の確認手順**:
```bash
# 1. ネットワーク設定確認
wsl.exe hostname -I

# 2. mirrored mode動作確認
curl http://127.0.0.1:80 2>/dev/null && echo "✅ 127.0.0.1通信成功" || echo "❌ 通信失敗"

# 3. MCP接続状況確認
claude mcp list
```

**成功指標**:
- [ ] WSL2 mirrored mode有効化確認
- [ ] 127.0.0.1双方向通信成功
- [ ] Windows Firewall受信規則追加完了

### **Phase 2: MCP設定最適化＋Docker積極採用** 🔄待機中

**実行予定手順**:

1. **Node.js環境完全クリーンアップ**:
```bash
# npm cache完全削除
npm cache clean --force
rm -rf ~/.npm
rm -rf ~/.nvm

# Node.js再インストール確認
node --version
npm --version
```

2. **現在のMCP設定確認**:
```bash
# 設定ファイル確認
cat ~/.claude.json
cat ~/.claude/settings.json

# MCP接続テスト
claude mcp list
```

3. **Docker-based MCP servers実装**（Gemini推奨で積極採用）:
```bash
# Dockerファイル作成
# MCP servers個別コンテナ化
# docker-compose.yml管理システム構築
```

**成功指標**:
- [ ] Node.js環境クリーン完了
- [ ] `ListMcpResourcesTool`正常動作
- [ ] stdio transportエラー解消
- [ ] Docker MCP servers動作確認

### **Phase 3: 段階的機能検証と実用性確認** 🔄待機中

**検証項目**:

1. **個別MCP機能テスト**:
```bash
# filesystem MCP
# - ファイル作成/読み込み/削除
# - ディレクトリ操作
# - プロジェクト構造把握

# fetch MCP  
# - 外部URL取得
# - MQL5公式ドキュメント取得
# - GitHub情報取得

# context7 MCP
# - 最新技術情報取得
# - エラーコード詳細取得
# - ライブラリ使用例取得
```

2. **Sub-Agent機能活用**:
```bash
# 独立コンテキストでの専門作業
# MQL5技術検証エージェント
# コードレビューエージェント
```

3. **複合タスク実行テスト**:
```bash
# 例: 「MQL5公式からOrderSend情報取得→要約をファイル保存→Git commit」
# 複数MCP連携動作確認
```

**成功指標**:
- [ ] filesystem操作完全成功
- [ ] Web取得・文書参照成功
- [ ] Sub-Agent独立動作成功
- [ ] 複合タスク完全実行成功

## 📁 関連ファイル・設定

### 設定ファイル場所
- **WSL設定**: `/home/trader/.wslconfig` ✅作成済み
- **Claude設定**: `~/.claude.json`, `~/.claude/settings.json`
- **実行ガイド**: `/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/wsl2_mcp_optimization_guide.md` ✅作成済み

### MCP設定状況
```json
// ~/.claude.json 抜粋
"mcpServers": {
  "filesystem": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/trader/Trading-Development"]
  },
  "fetch": {
    "type": "stdio", 
    "command": "npx",
    "args": ["-y", "@kazuph/mcp-fetch"]
  },
  "context7": {
    "type": "stdio",
    "command": "npx", 
    "args": ["-y", "@upstash/context7-mcp"]
  }
}
```

### 動作確認済みMCP
- ✅ **gemini-cli**: 正常動作（Gemini査読で活用済み）
- ✅ **jupyter**: 正常動作
- ⚠️ **sqlite, duckdb**: 接続エラー（別途対処必要）

## 🛠️ トラブルシューティング

### よくある問題と解決策

1. **WSL再起動後もMCP接続失敗**:
```bash
# Windows Firewall確認
# MCP servers手動起動テスト
npx @modelcontextprotocol/server-filesystem /home/trader/Trading-Development
```

2. **Node.js関連エラー**:
```bash
# 権限問題解決
sudo chown -R $USER ~/.npm
sudo chown -R $USER ~/.nvm
```

3. **Docker実装困難時**:
```bash
# stdio transport代替設定
# ポート指定明示的設定
```

## 📊 プロジェクト進捗管理

### 現在のTodoリスト
- [x] Geminiによる3フェーズ最適化戦略の徹底的査読完了
- [x] Phase 1: WSL2ネットワーク設定修正（セキュリティ強化版）実行
- [ ] Phase 2: MCP設定最適化＋Docker積極採用実装
- [ ] Phase 3: 段階的機能検証と実用性確認

### 次回セッション開始時の確認事項
1. **WSL再起動確認**: `wsl.exe hostname -I`でIP確認
2. **MCP接続状況**: `claude mcp list`で状況確認  
3. **Phase 1成功判定**: 127.0.0.1通信テスト実行
4. **Phase 2準備**: Node.js環境状況確認

## 🎯 最終目標達成指標

### MCP・Sub-Agent完全活用状態
- [ ] 全MCPサーバー（filesystem/fetch/context7）正常動作
- [ ] Sub-Agent独立コンテキスト活用
- [ ] 複合タスク（ファイル操作+Web取得+AI分析）実行成功
- [ ] 開発効率大幅向上実感

### 成功時の利用例
- **MQL5開発**: context7でリファレンス即座取得→filesystemでコード管理→fetch で最新情報確認
- **品質管理**: Sub-Agent専門レビュー→自動ドキュメント生成→Git統合
- **プロジェクト管理**: 自動セッション記録→進捗追跡→品質チェック

---

**📌 重要**: WSL再起動後、このファイルを最初に確認してPhase 2から継続実行してください。全手順・設定・背景情報を記載済みです。