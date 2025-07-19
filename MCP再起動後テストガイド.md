# MCP再起動後テストガイド

**⚠️ 重要: このファイルは一時的なテスト用です。確認完了後は削除してください。**

**作成日**: 2025年7月19日  
**用途**: Claude Code再起動後のMCP動作確認  
**削除タイミング**: 全テスト完了後

---

## 🔄 テスト実行手順

### Phase 1: 基本MCP動作確認

#### 1. ✅ Context7 MCP テスト
```
"MetaTrader 5 API の最新ドキュメントを調べて。use context7"
```
**期待結果**: 外部ドキュメントから最新情報取得

#### 2. ✅ Draw.io MCP テスト  
```
"ブレイクアウト戦略のフローチャートを作成して"
```
**期待結果**: Draw.io図表生成・表示

#### 3. ✅ Jupyter MCP テスト（新規修復）
```python
# 簡単なバックテストコード実行
import pandas as pd
data = pd.DataFrame({'price': [100, 105, 98, 110, 95]})
print(data.head())
```
**期待結果**: NotebookRead、NotebookEdit、executeCodeツール使用可能

### Phase 2: 既存MCP継続確認

#### 4. ✅ Gemini CLI テスト
```
"Phase2プロジェクトの進捗を分析して。use gemini"
```
**期待結果**: AI分析・監査機能動作

#### 5. ✅ DuckDB/SQLite テスト
```sql
-- バックテストデータ確認
SELECT * FROM trades LIMIT 5;
```
**期待結果**: DB接続・クエリ実行成功

### Phase 3: 統合動作確認

#### 6. ✅ 複合タスクテスト
```
1. Context7で最新MT5情報収集
2. その情報をもとにDraw.ioで戦略図作成
3. Jupyterでバックテスト実装
4. Geminiで結果分析・改善提案
```
**期待結果**: 全MCP連携動作

---

## 📋 チェックリスト

### 基本動作確認
- [ ] Context7: 外部情報取得成功
- [ ] Draw.io: 図表生成成功  
- [ ] Jupyter: ノートブック操作成功
- [ ] Gemini: AI分析成功
- [ ] Database: クエリ実行成功

### エラー対応確認
- [ ] MCP接続エラー時の適切な表示
- [ ] タイムアウト時の処理
- [ ] 依存関係不足時の警告

### パフォーマンス確認
- [ ] MCPサーバー起動時間（<5秒）
- [ ] レスポンス速度（<10秒）
- [ ] メモリ使用量（適正範囲内）

---

## 🚨 問題発生時の対処

### Jupyter MCP接続失敗の場合
```bash
# 依存関係再確認
pip list | grep -E "(websockets|jupyter-client)"

# パス確認
ls -la /home/trader/mcp-servers/jupyter-notebook-mcp/src/jupyter_mcp_server.py
```

### Draw.io MCP接続失敗の場合
```bash
# ビルドファイル確認
ls -la mcp-servers/drawio-mcp-server/build/index.js

# 再ビルド（必要時）
cd mcp-servers/drawio-mcp-server && npx tsc
```

### Context7 MCP接続失敗の場合
```bash
# パッケージ確認
npx -y @upstash/context7-mcp --help
```

---

## ✅ テスト完了アクション

### 成功時
1. このファイル（MCP再起動後テストガイド.md）を削除
2. 文書/技術/MCP実装ガイド.md を正式運用文書として確定
3. Phase2実装でMCP活用開始

### 失敗時
1. エラー内容を文書/技術/MCP実装ガイド.md に追記
2. 修復作業実施
3. 再テスト実行

---

**🗑️ 削除指示: 全テスト完了確認後、このファイルを必ず削除してください。**