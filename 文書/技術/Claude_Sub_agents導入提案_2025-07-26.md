# Claude Code Sub agents 導入提案
**作成日**: 2025年7月26日
**提案者**: Claude Code（実装担当）

## 📋 導入価値評価

### 現在の課題
1. **コンテキスト枯渇**: 長時間セッションで過去の作業内容を忘れる
2. **役割の混在**: EA開発、データ分析、文書管理が混在
3. **効率低下**: 全ての情報を毎回読み込むオーバーヘッド

### Sub agents導入のメリット
1. **専門性の向上**: 各エージェントが特定分野に集中
2. **コンテキスト効率**: 必要な情報のみを保持
3. **並行作業**: 複数のエージェントで効率的な作業分担

## 🎯 提案するSub agents構成

### 1. EA Developer（EA開発専門）
```bash
mkdir -p .claude/agents
cat > .claude/agents/ea-developer.md << 'EOF'
---
name: EA Developer
description: MT5 EA開発・改善専門エージェント
tools:
  - Read
  - Write
  - Edit
  - MultiEdit
  - Bash
  - WebSearch
---

## 責務
- MQL5コードの作成・修正・最適化
- バックテスト実行と結果分析
- エントリー/エグジット条件の改善
- リスク管理機能の実装

## 作業原則
1. **リスクリワード比**: 最低1.5以上を維持
2. **勝率目標**: 45%以上を目指す
3. **コード品質**: 保守性・拡張性を重視
4. **テスト駆動**: 変更前後でのバックテスト必須

## ワークフロー
1. 現在のEA（JamesORB）の問題点分析
2. 改善案の設計・実装
3. バックテストでの検証
4. デモ取引での実証
5. 本番環境への適用判断

## 現在の重要課題
- JamesORBのRR比改善（0.62→1.5以上）
- ブレイク&リテスト戦略の実装
- ボリュームフィルターの追加
- 動的ロットサイズ計算の実装
EOF'
```

### 2. Data Analyst（データ分析専門）
```bash
cat > .claude/agents/data-analyst.md << 'EOF'
---
name: MT5 Data Analyst
description: 取引データ分析・統計計算専門
tools:
  - Read
  - Write
  - Bash
  - mcp__jupyter__insert_and_execute_cell
  - mcp__jupyter__get_cells_info
  - WebFetch
---

## 責務
- バックテスト結果の詳細分析
- デモ/実取引データの統計処理
- パフォーマンス指標の算出
- 視覚化レポートの作成

## 分析指標
1. **収益性**: PF、年間収益率、期待値
2. **リスク**: 最大DD、連続負け、破産確率
3. **安定性**: シャープレシオ、標準偏差
4. **効率性**: 取引頻度、保有時間分析

## データソース
- MT5/Results/Backtest/*.xlsx
- MT5/Logs/操作ログ.txt
- MT5/Logs/エキスパート.txt
- Scripts/mt5_*.py 分析スクリプト群

## 現在のタスク
- JamesORBデモ取引の週次分析
- バックテストとの乖離要因特定
- 改善効果の定量的評価
EOF'
```

### 3. Project Manager（プロジェクト管理）
```bash
cat > .claude/agents/project-manager.md << 'EOF'
---
name: Project Manager
description: プロジェクト全体管理・文書整理
tools:
  - Read
  - Write
  - LS
  - Glob
  - TodoWrite
  - Bash
---

## 責務
- セッション記録の作成・管理
- タスク進捗管理（TodoWrite）
- 文書の整理・統合
- kiroとの連携調整

## 管理対象
1. **セッション記録**: 文書/記録/セッション記録_*.md
2. **技術文書**: 文書/技術/*.md
3. **品質管理**: 文書/管理/*.md
4. **削除予定**: 削除予定_デモ運用安定後/

## 作業ルール
- セッション記録は同日追記（重複作成禁止）
- 削除は慎重に（デモ運用安定後）
- 統合文書への情報集約を優先
- kiroへの定期報告準備

## 現在の状況
- 文書整理: 70→37ファイル（47%削減）完了
- JamesORBデモ: 2025-07-24開始、監視中
- 次フェーズ: 新EA開発準備
EOF'
```

## 🔧 導入手順

### 1. agentsフォルダ作成とファイル配置
```bash
# フォルダ作成
mkdir -p .claude/agents

# 上記3つのmarkdownファイルを作成
```

### 2. 使用方法
```bash
# EA開発タスク
Claude: "I'll use the EA Developer agent for this task"

# データ分析タスク
Claude: "Let me switch to the Data Analyst agent"

# 文書管理タスク
Claude: "The Project Manager agent will handle this"
```

### 3. 既存環境との統合
- 現在のhooks設定はそのまま維持
- slashCommandsも継続使用
- Sub agentsは追加機能として動作

## 📊 期待される効果

### 1. **効率向上**
- 各タスクで20-30%の時間短縮
- コンテキスト切り替えのオーバーヘッド削減
- 専門知識の集約による品質向上

### 2. **品質改善**
- 役割明確化によるミス削減
- 専門性向上による深い分析
- 一貫性のある作業フロー

### 3. **スケーラビリティ**
- 新しいエージェントの追加が容易
- 複雑なプロジェクトへの対応力向上
- チーム開発への拡張可能性

## 🎯 活用例

### ケース1: 月曜日の作業
```
1. Data Analyst: デモ取引の週末データ分析
2. EA Developer: 分析結果に基づく改善実装
3. Project Manager: セッション記録作成・タスク管理
```

### ケース2: 新EA開発
```
1. Project Manager: kiro設計書の確認・タスク分解
2. EA Developer: 設計に基づく実装
3. Data Analyst: テスト結果の検証・分析
```

### ケース3: 定期メンテナンス
```
1. Project Manager: 文書整理・削除予定確認
2. Data Analyst: 週次/月次レポート作成
3. EA Developer: バグ修正・最適化
```

## 🚀 推奨事項

### 即座に導入すべき理由
1. **現在のプロジェクト複雑性**: EA開発と分析が並行
2. **長期的な保守性**: 役割分担による持続可能性
3. **kiroとの協業**: 明確な責任範囲の定義

### 導入リスク
- 初期設定の手間（30分程度）
- エージェント切り替えの習熟期間
- 過度な細分化の可能性

### 結論
**導入価値: 高い** - 特に現在のような複合的なプロジェクトでは、Sub agentsによる専門性の向上とコンテキスト管理の効率化は大きなメリットとなります。

---
**次のアクション**:
1. .claude/agentsフォルダの作成
2. 3つの基本エージェント設定
3. 月曜日から実運用開始
