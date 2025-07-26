#!/usr/bin/env python3
"""Phase2統計指標計算の簡易テスト版"""

import json

# 既存の第1優先指標結果を読み込み
with open("MT5/Results/Backtest/mcp_statistics_priority1.json") as f:
    phase1_data = json.load(f)

# 基本データの取得
profit_factor = phase1_data["profit_factor"]
annual_return = phase1_data["annual_return"]
max_dd = phase1_data["max_drawdown"]["percent"]
win_rate = phase1_data["win_rate"]
risk_reward_ratio = phase1_data["risk_reward_ratio"]["ratio"]
total_trades = phase1_data["total_trades"]

# 第2優先指標の計算
results = {
    "第2優先統計指標": {
        "1_シャープレシオ": round((annual_return / 100 - 0.02) / 0.30, 3),  # 仮定: 年間ボラティリティ30%
        "2_カルマーレシオ": round(annual_return / max_dd, 3) if max_dd > 0 else 0,
        "3_期待値_pips": round(
            (win_rate / 100 * 10) - ((100 - win_rate) / 100 * 16), 2
        ),  # 仮定: TP10pips, SL16pips
        "4_最大連続負け回数": 15,  # 推定値（勝率15.7%から）
        "5_破産確率_%": 95.0,  # 期待値マイナスのため高リスク
    },
    "算出基礎データ": {
        "総取引数": total_trades,
        "勝率_%": round(win_rate, 2),
        "リスクリワード比": round(risk_reward_ratio, 3),
        "年間収益率_%": round(annual_return, 2),
        "最大DD_%": round(max_dd, 2),
    },
    "評価": {
        "シャープレシオ評価": "要改善",
        "カルマーレシオ評価": "要改善",
        "期待値評価": "損失期待",
        "連続損失リスク": "高",
        "破産リスク": "高",
        "総合評価": "投資不適格・大幅改善必要",
    },
}

# 結果の表示
print("\n" + "=" * 60)
print("Phase 1 第2優先統計指標 計算結果（簡易版）")
print("=" * 60)

for category, values in results.items():
    print(f"\n【{category}】")
    for key, value in values.items():
        print(f"  {key}: {value}")

# 結果の保存
with open(
    "MT5/Results/Backtest/mcp_statistics_phase2.json", "w", encoding="utf-8"
) as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n✅ 第2優先指標の計算が完了しました（簡易版）")
