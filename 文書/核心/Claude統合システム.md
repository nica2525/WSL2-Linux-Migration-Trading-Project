# Claude統合システム（2025年版）

**最終更新: 2025-07-25 JST**

## 🎯 現在のシステム構成

### 🔄 統合完了システム
- **記憶・設定**: CLAUDE.md（プロジェクト中核設定）
- **自動化**: cron（Git自動保存・システム監視）
- **hooks**: セッション記録・記憶継承
- **MCP統合**: システム・MCP・拡張機能統合ロードマップ.md

### 📁 システム確認プロトコル
```bash
# セッション開始時必須確認
cat CLAUDE.md
crontab -l
tail -5 .cron_git_auto_save.log
```

---

## 🚨 重要システム変更（2025年7月更新）

### cron自動化システム（現行）
- **Git自動保存**: 3分間隔（cron_git_auto_save.py）
- **システム監視**: 5分間隔（cron_system_monitor.py）
- **管理**: crontab コマンド
- **ログ**: .cron_*.log ファイル

### 🛑 廃止システム（重要）
- **systemd方式**: 完全廃止済み
- **start_auto_git.sh**: .DISABLED化済み
- **手動記憶システム**: hooks自動化により不要

## 🧠 hooks記憶継承システム

### 自動記憶システム
- **セッション記録**: hooks自動生成
- **記憶継承**: セッション開始時自動確認
- **設定場所**: ~/.claude/settings.json

### セッション記録管理
- **記録場所**: 文書/記録/セッション記録*.md
- **同日追記**: 既存ファイルに「## 追加セッション」として追記
- **重複防止**: 同日新規作成を厳禁

---

## 🤝 3AI開発体制（更新版）

### 開発役割分担
- **kiro**: 設計者・計画立案者（設計書・要件定義・アーキテクチャ）
- **Claude Code**: 実装担当者（kiroの設計に基づく実装のみ）
- **Gemini**: 客観監査・技術検証・品質査読
- **ChatGPT**: 戦略分析・実装支援・最適化提案

### Claude制限事項（重要）
- **設計書・要件定義の作成禁止**
- **kiroの設計計画に準拠した実装のみ**
- **余計な設計文書作成は即座に削除対象**

---

## 📊 現在のプロジェクト状況（2025-07-25）

### MT5フェーズ状況
- **MT5データ構造問題**: 完全解決（44.1%時系列逆転を5層検証で解明）
- **JamesORB統計分析**: 完了（年利30.6%、PF1.205、DD43.8%）
- **デモ運用**: 開始済み（300万円、EURUSD、2025-07-24 23:47開始）

### 次フェーズ準備
- **新EA開発目標**: DD20-25%、RR1.5以上
- **開発判断**: JamesORBデモ取引発生後に開始

## 📋 統合システム管理（2025年版）

### MCP・拡張機能統合
- **統合ドキュメント**: システム・MCP・拡張機能統合ロードマップ.md
- **新規MCP関連MDファイル作成禁止**
- **全情報を統合ロードマップに集約**

### セッション記録ルール
- **最新確認**: `ls -la 文書/記録/セッション記録*.md | tail -5`
- **同日追記**: 既存ファイルに「## 追加セッション」
- **重複防止**: 同日新規ファイル作成を厳禁

---

## 📋 旧システム参考情報（削除予定）

### 旧ChatGPT依頼形式（参考のみ）
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

---

**🎯 2025年版統合完了**: CLAUDE.md + hooks + cron + MCP統合ロードマップによる一元管理
**管理者**: Claude Code（実装担当）
**次回更新**: 新EA開発開始時
