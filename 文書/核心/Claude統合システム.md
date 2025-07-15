# Claude統合システム - 記憶・設定・参照一元化

**統合日時: 2025-07-12 22:40 JST**

## 🎯 統合設計思想
**問題**: 9個のmdファイル、50+個の.pyファイル → 記憶負荷過大
**解決**: 機能別統合により3-4ファイルに集約

---

## 📋 記憶・設定システム（統合版）

### セッション開始時必須実行
```bash
cat CLAUDE_UNIFIED_SYSTEM.md  # このファイル（全情報一元化）
```

### Git・システム確認
```bash
Scripts/start_auto_git.sh status
git log --oneline -3
```

---

## 🚨 基本設定（旧CLAUDE.md統合）

### 自動Git保存確認プロトコル
**セッション開始時に必ず実行:**
```bash
Scripts/start_auto_git.sh status
```

### 基本環境
- **OS**: WSL Ubuntu 22.04
- **プロジェクトパス**: `/mnt/e/Trading-Development/2.ブレイクアウト手法プロジェクト`
- **Git管理**: 自動保存システム稼働中

---

## 🧠 記憶システム（統合版）

### リアルタイム記憶追跡
- **30分間隔**: 自動時間チェック
- **30アクション毎**: Hooks強制実行
- **重要作業前**: このファイル確認

### 記憶更新ログ
- **実行履歴**: `docs/MEMORY_EXECUTION_HISTORY.md`
- **アクションカウント**: `.action_count`（自動管理）

---

## 🤝 3AI協働ルール（旧憲章統合）

### 役割分担
- **Claude Code**: 統合管理・実装・品質管理
- **Gemini**: 客観監査・技術検証・バイアス検出  
- **ChatGPT**: 戦略立案・実装支援・最適化
- **GitHub Copilot**: 無料枠活用でコード補完・実装効率化（月12,000補完まで）

### 意思決定プロセス
- **技術的事項**: Claude Codeが統合判断
- **戦略的事項**: にっかが最終決定
- **品質基準**: Geminiの客観的評価を重視

---

## 📊 現在の開発状況

### プロジェクト状況
- **Phase**: Phase 3（検証・監視）
- **問題**: 統計的有意性なし（p=0.1875 > 0.05）
- **解決策**: WFA原則遵守環境適応型システム完成（Gemini査読済み）
- **統合**: ファイル整理完了（9md→1統合ファイル）

### 最重要ファイル（実用中）
- `corrected_adaptive_wfa_system.py` - メインシステム（Gemini査読済み）
- `market_regime_detector.py` - 環境検出システム
- `cost_resistant_strategy.py` - 基本戦略
- `data_cache_system.py` - データ管理

### 🎯 **即実行タスク**
1. **ChatGPT Pythonリファクタリング依頼**（形式確認済み）
2. **修正版システム実行テスト**
3. **統計的有意性確認（p<0.05達成）**

### 完了事項（2025-07-12）
- [x] Look-ahead Bias修正（Gemini査読合格）
- [x] ファイル構造最適化（記憶負荷軽減）
- [x] 統合システム構築（このファイル）
- [x] Hooks自動化設定完了

---

## 📋 作業ルール（忘却防止）

### ChatGPT依頼形式（絶対遵守）
```markdown
# ChatGPT依頼内容

## 🚨 作業依頼 - [タイトル]

### 対象ファイル
**[ファイル名]** (現状説明)

### 提供ファイル一覧
- ファイル1 (役割)
- ファイル2 (役割)

### [問題/課題]
具体的問題の説明

### 作業内容
具体的作業要求

### 成果物形式
期待する成果物

### 品質要件
- 品質基準1
- 品質基準2

### 背景情報
プロジェクト文脈

### 技術的制約
制約事項

### 📁 **ChatGPT提供ファイル一覧（自動化用）**

**🔄 次回セッション開始タスク:**
```bash
# 次回開始時に実行
Gemini査読: corrected_optimized_functions.py + bias_prevention_analysis.md
```

**📁 最新ChatGPT成果物:**
```bash
3AI_collaboration/from_chatgpt/corrected_optimized_functions.py  # 修正版コード
3AI_collaboration/from_chatgpt/bias_prevention_analysis.md       # 問題分析レポート
```

**💡 提供手順:**
1. `docs/CHATGPT_TASK_REQUEST.md`をコピー
2. 問題ファイル`optimized_functions.py`を添付
3. 参考ファイル`corrected_adaptive_wfa_system.py`を添付
4. Gemini査読レポート内容をテキストで貼り付け

### 📁 **成果物ファイル指定（必須記載）**
**ChatGPTによる自動ファイル生成のため以下を必須記載:**
- **ファイル名**: `生成希望ファイル名.py`（snake_case推奨）
- **形式**: [Python/Markdown/JSON等]
- **命名規則**: プロジェクト規則に準拠
- **補足ファイル**: 解説用`.md`ファイルも同時生成希望

**例:**
```
ファイル名: optimized_wfa_system.py + optimization_explanation.md
形式: Python実装ファイル + Markdown解説ファイル
```

**注意**: 保存場所はClaude側で管理（`3AI_collaboration/from_chatgpt/`）

---

**この依頼は3AI協働開発憲章に基づく ChatGPT(戦略・実装コンサルタント) としての作業依頼です。**
```

### 命名規則・保存先
- **場所**: `docs/CHATGPT_TASK_REQUEST.md`
- **成果物**: `3AI_collaboration/from_chatgpt/`
- **日時**: 全mdファイルに日本時間必須

### 重要教訓（致命的ミス防止）
- **Look-ahead Bias**: 未来データ使用絶対禁止
- **WFA原則**: 各フォールド独立最適化必須
- **実装前査読**: Gemini監査必須実行
- **形式遵守**: 既存ファイル形式の完全準拠

---

## 🔧 開発技術標準

### ファイル命名規則
- **Python**: snake_case.py
- **Markdown**: UPPERCASE_WITH_UNDERSCORES.md
- **結果**: descriptive_name_YYYYMMDD_HHMMSS.json

### 品質基準
- **p値 < 0.05**: 統計的有意性の必須条件
- **十分な取引数**: 統計的十分性の確保
- **再現性**: 結果の検証可能性

### 🚀 **段階的アップグレード戦略**
- **現在**: Copilot無料枠（月12,000補完）+ 既存3AI体制
- **将来**: 開発実績→資金調達→Copilot Pro+アップグレード
- **戦略**: 無料枠最大活用で実装効率化、重要機能に集中投入

---

**🎯 このファイル1つで全記憶・設定・参照を一元管理（9mdファイル→1統合完了）**