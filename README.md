# ブレイクアウト手法プロジェクト

## プロジェクト概要
シンプルなブレイクアウト戦略の開発プロジェクトです。
前プロジェクト（黄金WW手法）の課題である取引頻度不足を解決し、実用的な自動売買システムの構築を目指します。

## 戦略コンセプト
- **サポート・レジスタンス**: OANDA_Support_Resistance.ex4
- **移動平均線**: OANDA_Multi_5MA.ex4
- **ボリンジャーバンド**: OANDA_BB_width.ex4
- **チャネル**: OANDA_Channels.ex4
- **アラート**: OANDA_MA_PO_Alert.ex4

## 開発目標
1. **取引頻度確保**: 月3-5回以上の取引機会
2. **リスク管理**: 1.5%以下のリスク率維持
3. **多通貨対応**: USD/JPY、GBP/JPY、EUR/USD
4. **実用性**: バックテスト勝率50%以上

## 前プロジェクトからの改善点
- 取引頻度: 0.35回/月 → 3-5回/月（目標）
- 手法: パターン検出 → ブレイクアウト
- インジケータ: カスタム → シンプル

## プロジェクト番号
**2** （開発順序: 1.黄金WW手法 → 2.ブレイクアウト手法）

## プロジェクト構造（2025-07-21更新）

### **現在のディレクトリ構成**
```
/
├── core/                    # 核心システム（27ファイル）
│   ├── phase3_integrated_system.py    # 統合取引システム
│   ├── realtime_signal_generator.py   # リアルタイムシグナル
│   ├── risk_management.py             # リスク管理
│   └── automation_compatibility.py    # 自動化互換性
├── strategies/              # 戦略実装（4ファイル）
│   ├── cost_resistant_strategy.py     # コスト耐性戦略
│   └── multi_timeframe_breakout_strategy.py
├── wfa/                     # Walk Forward Analysis（7ファイル）
│   ├── enhanced_parallel_wfa_with_slippage.py
│   └── unified_wfa_framework.py
├── tests/                   # テスト関連（8ファイル）
├── utilities/               # ユーティリティ（5ファイル）
├── MT4_EA/                  # MT4実装
│   ├── BreakoutEA_Complete.mq4        # 修正済みEA
│   └── JamesORB_Standalone.mq4        # シンプル参考EA
├── Scripts/                 # 自動化スクリプト
│   ├── cron_git_auto_save.py          # Git自動保存
│   └── cron_system_monitor.py         # システム監視
└── 文書/                    # ドキュメント
    ├── 記録/                # セッション記録
    ├── 技術/                # 技術仕様
    └── 管理/                # 管理情報
```

### **現在の開発状況**
- **Phase3統合システム**: 完成（2025-07-19）
- **MT4 EA修正**: 完了（0シグナル→67シグナル復旧）
- **JamesORB分析**: シンプル戦略研究中
- **プロジェクト整理**: 66→27ファイル（59%削減完了）
- `DIRECTORY_MAP.md`: ファイル構造図
- `PROJECT_FINAL_SUMMARY.md`: 完了時の成果報告

---
**開始日**: 2025-06-25  
**ステータス**: 開発開始  
**プロジェクト管理**: 標準5ファイル構造（v1.1）準拠