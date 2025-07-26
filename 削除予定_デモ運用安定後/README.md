# 削除予定ファイル管理フォルダ

## 📅 作成日時
2025年7月25日（最終更新: 2025年7月26日）

## 🎯 目的
JamesORBデモ運用安定化後に削除予定の技術資産を一時保管

## 📁 フォルダ構成

### WFA関連/
**内容**: Walk Forward Analysis関連ファイル
**削除理由**: MT4専用バックテスト手法、MT5では新分析手法採用
- WFA結果JSONファイル（約9ファイル、約150KB）
- VectorBT-WFA連携結果

### VectorBT関連/
**内容**: VectorBTライブラリ連携ファイル
**削除理由**: MT5直接連携なし、既存MT5分析システムで代替可能
- VectorBT結果CSVファイル（約2ファイル、約72KB）

### Phase統合システム/
**内容**: Phase2/3統合システムファイル（未配置）
**削除理由**: MT4のBreakoutEA専用、JamesORBとは設計が異なる

### 古い分析結果/
**内容**: その他の古い分析結果ファイル（未配置）
**削除理由**: 現在の開発に価値なし

### 古い問題記録/
**内容**: 解決済みの問題記録・承認依頼書
**削除理由**: 問題解決済み、履歴価値のみ
- Hook問題調査記録
- Claude虚偽報告問題記録
- kiro承認関連文書

### 古い技術文書/
**内容**: 統合済み・廃止済み技術文書
**削除理由**: 最新の統合文書に内容反映済み
- 各種プロトコル・仕様書
- 開発環境改善提案

### 統合済み文書/
**内容**: 既に統合ロードマップ等に反映済み文書
**削除理由**: 重複・冗長性排除
- 3AI関連文書
- Phase1完了レポート
- 各種設計書

### MT5検証スクリプト/（2025-07-26追加予定）
**内容**: MT5データ分析検証用スクリプト8個
**削除理由**: 検証完了・機能重複・役割終了
- mt5_extended_verification.py
- mt5_data_corruption_verification.py
- mt5_data_verification_system.py
- mt5_final_verification.py
- mt5_time_reversal_analyzer.py
- mt5_timezone_hypothesis_verification.py
- mt5_accurate_trade_analyzer.py
- mt5_git_auto_commit.py

## ⏰ 削除実行条件
1. **JamesORBデモ運用の安定化確認**（1-2週間の動作確認）
2. **新EA開発方針の確定**
3. **kiro承認**

## 🚨 注意事項
- このフォルダ内のファイルは一時保管のみ
- 定期的な内容確認を推奨
- 削除前に最終確認を実施

---
**管理者**: Claude（実装担当）
**承認者**: kiro（設計責任者）
