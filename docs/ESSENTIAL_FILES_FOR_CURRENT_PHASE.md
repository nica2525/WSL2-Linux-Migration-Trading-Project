# 現在フェーズで必要なファイル一覧

## 🎯 保持必須ファイル

### コア学習成果ファイル
- [x] `CURRENT_STATUS_AND_NEXT_TASKS.md` - 現在の進捗状況
- [x] `PHASE1_COMPLETION_SUMMARY.md` - フェーズ1完了報告
- [x] `PHASE2_WFA_RESULTS_ANALYSIS.md` - フェーズ2結果分析
- [x] `CLAUDE.md` - 設定とプロトコル

### 理論・手法文書
- [x] `PURGED_EMBARGOED_WFA_SPECIFICATION.md` - WFA実装仕様
- [x] `SCIENTIFIC_DEVELOPMENT_CHECKLIST.md` - 開発チェックリスト
- [x] `STATISTICAL_TRAP_AVOIDANCE_PROTOCOL.md` - 統計的罠回避
- [x] `HYPOTHESIS_DRIVEN_DEVELOPMENT_GUIDE.md` - 仮説駆動開発ガイド

### 戦略・分析関連
- [x] `MINIMAL_VIABLE_STRATEGY.md` - 最小実行可能戦略
- [x] `47EA_simple_analysis.py` - 47EA分析スクリプト
- [x] `wfa_prototype.py` - WFAプロトタイプ
- [x] `integrated_wfa_strategy.py` - 統合WFA戦略システム

### 基盤システム
- [x] `Scripts/start_auto_git.sh` - 自動Git保存
- [x] `README.md` - プロジェクト概要

## ❌ 削除対象ファイル

### 47EA開発時の古いファイル群
- `DEVELOPMENT_PARTNER_BRIEFING.md`
- `MCP_*` 関連ファイル群（学習には不要）
- `EA_Files/` 全体（47EA時代の産物）
- `docs/` 内の古いガイド類
- `results/` 内の古い結果ファイル
- `tests/` 内のスクリーンショット等

### 設定・データファイル
- `gemini_*` 関連ファイル（コスト管理以外）
- `mcp_data/` 内の古いデータファイル
- `node_modules/` とパッケージファイル
- `data/` 内の古いデータベース

### その他不要ファイル
- `duckdb_analyzer.py`
- `setup_*.py`
- `test_*.py`
- `neon_setup.py`