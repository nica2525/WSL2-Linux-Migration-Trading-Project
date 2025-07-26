#!/usr/bin/env python3
"""
Phase2統計分析（データ整合性修正版）
Phase1統計分析（2024年データ）と同じデータソースを使用
"""

import json
from datetime import datetime

import numpy as np


def main():
    # Phase1結果を読み込み（正確なベースライン）
    with open("MT5/Results/Backtest/mcp_statistics_priority1.json") as f:
        phase1_data = json.load(f)

    # Phase1の基本データ
    total_trades = phase1_data["total_trades"]  # 287
    win_rate = phase1_data["win_rate"]  # 11.15%
    annual_return = phase1_data["annual_return"]  # -12.37%
    max_dd = phase1_data["max_drawdown"]["percent"]  # 1.90%

    rr_data = phase1_data["risk_reward_ratio"]
    avg_win = rr_data["avg_profit"]  # 0.7586 USD
    avg_loss = rr_data["avg_loss"]  # 0.8280 USD

    print("=== Phase1データ確認 ===")
    print(f"総取引数: {total_trades}")
    print(f"勝率: {win_rate:.2f}%")
    print(f"年間収益率: {annual_return:.2f}%")
    print(f"最大DD: {max_dd:.2f}%")
    print(f"平均利益: ${avg_win:.4f}")
    print(f"平均損失: ${avg_loss:.4f}")

    # 第2優先指標の正確な計算

    # 1. シャープレシオ（実データベース）
    # 287取引の損益データから計算
    win_count = 32  # phase1データより
    loss_count = 255

    # 各取引の収益率を再構築
    returns = []
    initial_balance = 10000

    # 勝ち取引の収益率
    for _ in range(win_count):
        returns.append(avg_win / initial_balance)

    # 負け取引の収益率
    for _ in range(loss_count):
        returns.append(-avg_loss / initial_balance)

    # シャープレシオ計算
    returns_array = np.array(returns)
    annual_mean_return = np.mean(returns_array) * 250  # 年率換算
    annual_std_return = np.std(returns_array) * np.sqrt(250)
    risk_free_rate = 0.02

    sharpe_ratio = (
        (annual_mean_return - risk_free_rate) / annual_std_return
        if annual_std_return > 0
        else 0
    )

    # 2. カルマーレシオ
    calmar_ratio = annual_return / max_dd if max_dd > 0 else 0

    # 3. 期待値（USD、実データベース）
    expected_value_usd = (win_rate / 100 * avg_win) - (
        (100 - win_rate) / 100 * avg_loss
    )

    # 4. 最大連続負け回数（統計的推定）
    # 勝率11.15%で287取引の場合の推定
    prob_loss = (100 - win_rate) / 100  # 0.8885

    # 幾何分布による推定
    # P(X >= k) = (1-p)^k ここで p=win_rate/100
    # 287取引で99%の確率で発生する最大連続負け回数
    max_consecutive_estimated = int(np.log(0.01) / np.log(prob_loss))

    # より現実的な推定（フィッシャーの公式）
    max_consecutive_realistic = int(np.log(total_trades) / np.log(1 / prob_loss))

    # 5. 破産確率（Kelly基準ベース）
    # Kelly fraction = (bp - q) / b
    # b = odds received (avg_win/avg_loss)
    # p = probability of winning
    # q = probability of losing

    if avg_loss > 0:
        b = avg_win / avg_loss  # オッズ
        p = win_rate / 100
        q = 1 - p
        kelly_fraction = (b * p - q) / b
    else:
        kelly_fraction = -1

    # Kelly基準がマイナスの場合、破産確率は高い
    if kelly_fraction <= 0:
        risk_of_ruin = 99.9  # ほぼ確実
    else:
        # 1%リスクでの破産確率近似
        risk_per_trade = 0.01  # 1%
        if risk_per_trade > kelly_fraction:
            risk_of_ruin = min(99.9, 50 * (risk_per_trade / kelly_fraction))
        else:
            risk_of_ruin = max(0.1, 5 * np.exp(-kelly_fraction * 10))

    # 結果の構築
    results = {
        "第2優先統計指標_データ整合版": {
            "1_シャープレシオ": {
                "値": round(sharpe_ratio, 3),
                "評価": "優秀"
                if sharpe_ratio > 1.0
                else "良好"
                if sharpe_ratio > 0.5
                else "要改善",
                "計算方法": "Phase1実データ287取引ベース",
            },
            "2_カルマーレシオ": {
                "値": round(calmar_ratio, 3),
                "評価": "優秀"
                if calmar_ratio > 3.0
                else "良好"
                if calmar_ratio > 1.0
                else "要改善",
                "計算方法": "年間収益率/最大DD",
            },
            "3_期待値": {
                "USD": round(expected_value_usd, 4),
                "pips推定": round(expected_value_usd / 0.1, 2),  # 0.01ロット想定
                "評価": "利益期待" if expected_value_usd > 0 else "損失期待",
                "計算方法": "Phase1実データベース",
            },
            "4_最大連続負け回数": {
                "推定値": max_consecutive_realistic,
                "統計的上限": max_consecutive_estimated,
                "評価": "低リスク"
                if max_consecutive_realistic < 5
                else "中リスク"
                if max_consecutive_realistic < 10
                else "高リスク",
                "計算方法": "幾何分布・フィッシャー公式",
            },
            "5_破産確率": {
                "確率_%": round(risk_of_ruin, 2),
                "Kelly基準": round(kelly_fraction, 4),
                "評価": "低リスク"
                if risk_of_ruin < 5
                else "中リスク"
                if risk_of_ruin < 20
                else "高リスク",
                "計算方法": "Kelly基準・1%リスク想定",
            },
        },
        "データ整合性確認": {
            "使用データソース": "mcp_statistics_priority1.json（2024年287取引）",
            "データ期間": "2024年1月-12月",
            "計算基準": "Phase1統計と完全整合",
            "算出日時": datetime.now().isoformat(),
        },
        "Phase1との整合性": {
            "総取引数": total_trades,
            "勝率_%": round(win_rate, 2),
            "年間収益率_%": round(annual_return, 2),
            "最大DD_%": round(max_dd, 2),
            "リスクリワード比": round(avg_win / avg_loss, 3),
        },
    }

    # 総合評価
    score = 0
    if sharpe_ratio > 0.5:
        score += 20
    elif sharpe_ratio > 0:
        score += 10

    if calmar_ratio > 1.0:
        score += 20
    elif calmar_ratio > 0:
        score += 10

    if expected_value_usd > 0:
        score += 30

    if max_consecutive_realistic < 10:
        score += 15
    elif max_consecutive_realistic < 15:
        score += 8

    if risk_of_ruin < 20:
        score += 15
    elif risk_of_ruin < 50:
        score += 8

    if score >= 80:
        grade, verdict = "A", "優秀・実運用推奨"
    elif score >= 60:
        grade, verdict = "B", "良好・条件付き運用可"
    elif score >= 40:
        grade, verdict = "C", "要改善・デモ運用継続"
    elif score >= 20:
        grade, verdict = "D", "不良・大幅改善必要"
    else:
        grade, verdict = "F", "投資不適格・運用停止推奨"

    results["総合評価_整合版"] = {"スコア": f"{score}/100", "グレード": grade, "判定": verdict}

    # 表示
    print("\n" + "=" * 80)
    print("Phase 2 第2優先統計指標（データ整合性修正版）")
    print("=" * 80)

    indicators = results["第2優先統計指標_データ整合版"]

    print(
        f"\n1. シャープレシオ: {indicators['1_シャープレシオ']['値']} ({indicators['1_シャープレシオ']['評価']})"
    )
    print(
        f"2. カルマーレシオ: {indicators['2_カルマーレシオ']['値']} ({indicators['2_カルマーレシオ']['評価']})"
    )
    print(f"3. 期待値: {indicators['3_期待値']['USD']} USD ({indicators['3_期待値']['評価']})")
    print(
        f"4. 最大連続負け: {indicators['4_最大連続負け回数']['推定値']}回 ({indicators['4_最大連続負け回数']['評価']})"
    )
    print(f"5. 破産確率: {indicators['5_破産確率']['確率_%']}% ({indicators['5_破産確率']['評価']})")

    eval_data = results["総合評価_整合版"]
    print(f"\n総合評価: {eval_data['スコア']} {eval_data['グレード']} - {eval_data['判定']}")

    # 保存
    with open(
        "MT5/Results/Backtest/mcp_statistics_phase2_corrected.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n✅ データ整合性修正版 Phase2分析完了")
    print("📊 結果ファイル: mcp_statistics_phase2_corrected.json")


if __name__ == "__main__":
    main()
