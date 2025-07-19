# 現在の品質状況

🔍 品質状況サマリー
   総問題数: 26
   高重要度: 26
   新規問題: 0
   修正済み: 0

🚨 緊急修正要件:
   🟡 advanced_slippage_model.py:190 - Look-ahead bias（未来データ参照）
   🟡 advanced_slippage_model.py:213 - Look-ahead bias（未来データ参照）
   🟡 advanced_slippage_model.py:218 - Look-ahead bias（未来データ参照）
   🟡 advanced_slippage_model.py:220 - Look-ahead bias（未来データ参照）
   🟡 debug_signal_generation.py:161 - Look-ahead bias（未来データ参照） [generate_manual_signal]
   🟡 debug_signal_generation.py:161 - シグナル生成時の未来価格参照 [generate_manual_signal]
   🟡 wfa_prototype.py:298 - Look-ahead bias（未来データ参照）
   🟡 wfa_prototype.py:298 - シグナル生成時の未来価格参照
   🟡 アーカイブ/old_strategies/cost_resistant_wfa_execution_fixed.py:145 - Look-ahead bias（未来データ参照）
   🟡 アーカイブ/old_strategies/cost_resistant_wfa_execution_fixed.py:295 - Look-ahead bias（未来データ参照） [_generate_simple_signal]
   🟡 アーカイブ/old_strategies/cost_resistant_wfa_execution_fixed.py:145 - シグナル生成時の未来価格参照
   🟡 アーカイブ/old_strategies/cost_resistant_wfa_execution_fixed.py:295 - シグナル生成時の未来価格参照 [_generate_simple_signal]
   🟡 アーカイブ/old_strategies/cost_resistant_wfa_execution.py:224 - Look-ahead bias（未来データ参照） [_generate_simple_signal]
   🟡 アーカイブ/old_strategies/cost_resistant_wfa_execution.py:224 - シグナル生成時の未来価格参照 [_generate_simple_signal]
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:220 - Look-ahead bias（未来データ参照） [_execute_backtest]
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:222 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:223 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:234 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:242 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:299 - Look-ahead bias（未来データ参照） [_execute_adaptive_backtest]
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:307 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:335 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:337 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:338 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:351 - Look-ahead bias（未来データ参照）
   🔴 アーカイブ/old_strategies/adaptive_wfa_system.py:360 - Look-ahead bias（未来データ参照）

## 🎯 改善提案
🚨 高重要度問題の即座修正を推奨
   - Look-ahead bias: ブレイクアウト判定をhigh/lowベースに変更
   - Random generation: 実際の価格追跡ロジックに置換

📁 最優先修正ファイル:
   - アーカイブ/old_strategies/adaptive_wfa_system.py: 12件の問題
   - advanced_slippage_model.py: 4件の問題
   - アーカイブ/old_strategies/cost_resistant_wfa_execution_fixed.py: 4件の問題

🔍 最頻出パターン:
   - lookahead_bias: 21件
   - future_price_access: 5件

## 📊 検出精度
- 平均信頼度: 93.1%
- 高信頼度問題: 12件
- 要確認問題: 0件

最終更新: 2025-07-20 08:35:44
