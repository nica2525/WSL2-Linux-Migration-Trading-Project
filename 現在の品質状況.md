# 現在の品質状況

🔍 品質状況サマリー
   総問題数: 15
   高重要度: 14
   新規問題: 0
   修正済み: 0

🚨 緊急修正要件:
   🔴 corrected_adaptive_wfa_system.py:108 - Look-ahead bias（未来データ参照）
   🔴 corrected_adaptive_wfa_system.py:137 - Look-ahead bias（未来データ参照）
   🔴 corrected_adaptive_wfa_system.py:159 - Look-ahead bias（未来データ参照）
   🟡 debug_signal_generation.py:161 - Look-ahead bias（未来データ参照） [generate_manual_signal]
   🟡 debug_signal_generation.py:161 - シグナル生成時の未来価格参照 [generate_manual_signal]
   🔴 unified_wfa_framework.py:196 - Look-ahead bias（未来データ参照） [_generate_simple_breakout_signal]
   🔴 unified_wfa_framework.py:196 - シグナル生成時の未来価格参照 [_generate_simple_breakout_signal]
   🟡 wfa_prototype.py:298 - Look-ahead bias（未来データ参照）
   🟡 wfa_prototype.py:298 - シグナル生成時の未来価格参照
   🔴 Scripts/test_quality_checker.py:70 - バックテスト結果のランダム生成（偽装） [calculate_backtest_results]
   🔴 Scripts/test_quality_checker.py:175 - バックテスト結果のランダム生成（偽装） [bad_strategy]
   🔴 Scripts/test_quality_checker.py:34 - Look-ahead bias（未来データ参照） [generate_signal]
   🔴 Scripts/test_quality_checker.py:104 - Look-ahead bias（未来データ参照） [some_function]
   🔴 Scripts/test_quality_checker.py:174 - Look-ahead bias（未来データ参照） [bad_strategy]

## 🎯 改善提案
🚨 高重要度問題の即座修正を推奨
   - Look-ahead bias: ブレイクアウト判定をhigh/lowベースに変更
   - Random generation: 実際の価格追跡ロジックに置換

📁 最優先修正ファイル:
   - Scripts/test_quality_checker.py: 6件の問題
   - corrected_adaptive_wfa_system.py: 3件の問題
   - debug_signal_generation.py: 2件の問題

🔍 最頻出パターン:
   - lookahead_bias: 9件
   - future_price_access: 3件

## 📊 検出精度
- 平均信頼度: 94.7%
- 高信頼度問題: 11件
- 要確認問題: 0件

最終更新: 2025-07-14 06:32:32
