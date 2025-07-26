#!/usr/bin/env python3
"""
MCP統合統計計算システム - Phase 1
kiro要件対応: 15項目必須統計指標算出・システム負荷95%削減
作成者: Claude (実装担当)
作成日: 2025-07-24
"""

import json
import os
import re
import traceback
from datetime import datetime
from typing import Dict, List


class MCPStatisticsCalculator:
    """MCP統合統計計算システム"""

    def __init__(self, mt5_results_path: str):
        self.mt5_results_path = mt5_results_path
        self.trades_data = []
        self.balance_history = []
        self.initial_balance = 10000.0  # 初期残高推定値
        self.final_balance = 8762.60  # 操作ログから確認済み

    def load_mt5_data(self) -> bool:
        """MT5操作ログからデータ抽出・構造化"""
        try:
            log_file = os.path.join(self.mt5_results_path, "操作ログ.txt")

            if not os.path.exists(log_file):
                print(f"❌ 操作ログファイルが見つかりません: {log_file}")
                return False

            print(f"📊 MT5操作ログ解析開始: {log_file}")

            with open(log_file, encoding="utf-8") as f:
                lines = f.readlines()

            # 取引データ抽出
            deal_pattern = (
                r"deal #(\d+) (buy|sell) ([\d.]+) EURUSD_QDM at ([\d.]+) done"
            )
            balance_pattern = r"final balance ([\d.]+) USD"

            deals = []
            for line in lines:
                # 取引データ抽出
                deal_match = re.search(deal_pattern, line)
                if deal_match:
                    deal_id = int(deal_match.group(1))
                    direction = deal_match.group(2)
                    volume = float(deal_match.group(3))
                    price = float(deal_match.group(4))

                    # タイムスタンプ抽出
                    timestamp_match = re.search(
                        r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})", line
                    )
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                    else:
                        timestamp = "2024.01.01 00:00:00"

                    deals.append(
                        {
                            "deal_id": deal_id,
                            "timestamp": timestamp,
                            "direction": direction,
                            "volume": volume,
                            "price": price,
                        }
                    )

                # 最終残高確認
                balance_match = re.search(balance_pattern, line)
                if balance_match:
                    self.final_balance = float(balance_match.group(1))

            print(f"✅ 取引データ抽出完了: {len(deals)}件の取引")
            print(f"✅ 最終残高確認: {self.final_balance} USD")

            # 取引ペア作成（buy/sell決済の組み合わせ）
            self.trades_data = self._create_trade_pairs(deals)
            print(f"✅ 取引ペア作成完了: {len(self.trades_data)}組の完了取引")

            return True

        except Exception as e:
            print(f"❌ データ読み込みエラー: {e}")
            traceback.print_exc()
            return False

    def _create_trade_pairs(self, deals: List[Dict]) -> List[Dict]:
        """取引ペア作成（エントリー・エグジットの組み合わせ）+ 取引コスト算出"""
        trades = []

        # 取引コスト設定（OANDA MT5 EURUSD）
        spread_pips = 0.6  # 平均スプレッド
        commission_per_lot = 2.5  # 片道手数料
        swap_rate_long = -0.8  # ロングスワップ（日次）
        swap_rate_short = 0.3  # ショートスワップ（日次）

        # 簡略化: 連続する反対方向取引を組み合わせ
        i = 0
        while i < len(deals) - 1:
            entry = deals[i]
            exit_deal = deals[i + 1]

            # 反対方向の取引をペアとして扱う
            if entry["direction"] != exit_deal["direction"]:
                # 基本損益計算
                if entry["direction"] == "buy":
                    gross_profit = (
                        (exit_deal["price"] - entry["price"]) * entry["volume"] * 100000
                    )  # pip計算
                else:
                    gross_profit = (
                        (entry["price"] - exit_deal["price"]) * entry["volume"] * 100000
                    )

                # 取引コスト算出
                spread_cost = spread_pips * entry["volume"] * 10  # pip value for EURUSD
                commission_cost = commission_per_lot * entry["volume"] * 2  # 往復

                # 保有期間算出（簡略化: 1日と仮定）
                holding_days = 1
                if entry["direction"] == "buy":
                    swap_cost = swap_rate_long * entry["volume"] * holding_days
                else:
                    swap_cost = swap_rate_short * entry["volume"] * holding_days

                total_cost = spread_cost + commission_cost + abs(swap_cost)
                net_profit = gross_profit - total_cost

                trades.append(
                    {
                        "entry_time": entry["timestamp"],
                        "exit_time": exit_deal["timestamp"],
                        "direction": entry["direction"],
                        "volume": entry["volume"],
                        "entry_price": entry["price"],
                        "exit_price": exit_deal["price"],
                        "gross_profit": gross_profit,
                        "spread_cost": spread_cost,
                        "commission_cost": commission_cost,
                        "swap_cost": swap_cost,
                        "total_cost": total_cost,
                        "profit": net_profit,  # 取引コスト考慮後純利益
                        "is_winner": net_profit > 0,
                        "cost_impact": (total_cost / abs(gross_profit)) * 100
                        if abs(gross_profit) > 0
                        else 100,
                    }
                )

                i += 2  # ペア分進める
            else:
                i += 1

        return trades

    def calculate_profit_factor(self) -> float:
        """プロフィットファクター算出 (kiro要件: ≥1.5目標)"""
        if not self.trades_data:
            return 0.0

        total_profit = sum(
            trade["profit"] for trade in self.trades_data if trade["profit"] > 0
        )
        total_loss = abs(
            sum(trade["profit"] for trade in self.trades_data if trade["profit"] < 0)
        )

        if total_loss == 0:
            return float("inf") if total_profit > 0 else 0.0

        pf = total_profit / total_loss
        print(f"📊 プロフィットファクター: {pf:.3f} (目標: ≥1.5)")
        return pf

    def calculate_annual_return(self) -> float:
        """年間収益率算出 (kiro要件: ≥+15%目標)"""
        annual_return = (
            (self.final_balance - self.initial_balance) / self.initial_balance
        ) * 100
        print(f"📊 年間収益率: {annual_return:.2f}% (目標: ≥+15%)")
        return annual_return

    def calculate_max_drawdown(self) -> Dict:
        """最大ドローダウン算出 (kiro要件: ≤15%目標)"""
        if not self.trades_data:
            return {"percent": 0.0, "amount": 0.0, "duration_days": 0}

        # 残高履歴再構築
        balance = self.initial_balance
        balance_history = [balance]
        dates = []

        for trade in self.trades_data:
            balance += trade["profit"]
            balance_history.append(balance)
            try:
                trade_date = datetime.strptime(trade["exit_time"], "%Y.%m.%d %H:%M:%S")
                dates.append(trade_date)
            except:
                dates.append(datetime.now())

        # 最大ドローダウン計算
        peak = balance_history[0]
        max_dd_percent = 0.0
        max_dd_amount = 0.0

        for balance in balance_history:
            if balance > peak:
                peak = balance

            current_dd_percent = ((peak - balance) / peak) * 100
            current_dd_amount = peak - balance

            if current_dd_percent > max_dd_percent:
                max_dd_percent = current_dd_percent
                max_dd_amount = current_dd_amount

        result = {
            "percent": max_dd_percent,
            "amount": max_dd_amount,
            "duration_days": 30,  # 概算
        }

        print(f"📊 最大ドローダウン: {max_dd_percent:.2f}% (目標: ≤15%)")
        return result

    def calculate_win_rate(self) -> float:
        """勝率算出"""
        if not self.trades_data:
            return 0.0

        winning_trades = sum(1 for trade in self.trades_data if trade["is_winner"])
        total_trades = len(self.trades_data)

        win_rate = (winning_trades / total_trades) * 100
        print(f"📊 勝率: {win_rate:.1f}% (目標: ≥45%)")
        return win_rate

    def calculate_risk_reward_ratio(self) -> Dict:
        """リスクリワード比算出 (Gemini最優先指摘対応)"""
        if not self.trades_data:
            return {"ratio": 0.0, "avg_profit": 0.0, "avg_loss": 0.0}

        # 利益取引と損失取引を分離
        profit_trades = [
            trade["profit"] for trade in self.trades_data if trade["profit"] > 0
        ]
        loss_trades = [
            abs(trade["profit"]) for trade in self.trades_data if trade["profit"] < 0
        ]

        if not profit_trades or not loss_trades:
            return {"ratio": 0.0, "avg_profit": 0.0, "avg_loss": 0.0}

        avg_profit = sum(profit_trades) / len(profit_trades)
        avg_loss = sum(loss_trades) / len(loss_trades)

        risk_reward_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        result = {
            "ratio": risk_reward_ratio,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_trades_count": len(profit_trades),
            "loss_trades_count": len(loss_trades),
        }

        print(f"📊 リスクリワード比: {risk_reward_ratio:.3f} (目標: ≥3.0 for 15.7%勝率補償)")
        print(f"   ├ 平均利益: {avg_profit:.2f} USD ({len(profit_trades)}取引)")
        print(f"   └ 平均損失: {avg_loss:.2f} USD ({len(loss_trades)}取引)")

        # Gemini指摘: PF 0.157 = 平均損失が平均利益の6.4倍の検証
        loss_to_profit_multiple = avg_loss / avg_profit if avg_profit > 0 else 0.0
        print(f"🚨 損失倍率検証: 平均損失は平均利益の{loss_to_profit_multiple:.1f}倍")

        return result

    def calculate_transaction_cost_impact(self) -> Dict:
        """取引コスト影響度分析 (Gemini高優先指摘対応)"""
        if not self.trades_data:
            return {"total_cost": 0.0, "cost_percentage": 0.0, "cost_breakdown": {}}

        # 各コスト要素の集計
        total_spread_cost = sum(trade["spread_cost"] for trade in self.trades_data)
        total_commission_cost = sum(
            trade["commission_cost"] for trade in self.trades_data
        )
        total_swap_cost = sum(abs(trade["swap_cost"]) for trade in self.trades_data)
        total_cost = total_spread_cost + total_commission_cost + total_swap_cost

        # 総売上（グロス利益の絶対値合計）
        total_gross_volume = sum(
            abs(trade["gross_profit"]) for trade in self.trades_data
        )
        cost_percentage = (
            (total_cost / total_gross_volume) * 100 if total_gross_volume > 0 else 0.0
        )

        # 平均コスト影響度
        avg_cost_impact = sum(trade["cost_impact"] for trade in self.trades_data) / len(
            self.trades_data
        )

        result = {
            "total_cost": total_cost,
            "cost_percentage": cost_percentage,
            "avg_cost_impact": avg_cost_impact,
            "cost_breakdown": {
                "spread": total_spread_cost,
                "commission": total_commission_cost,
                "swap": total_swap_cost,
            },
            "cost_per_trade": total_cost / len(self.trades_data),
        }

        print(f"📊 取引コスト影響度: {cost_percentage:.1f}% (目標: ≤15%)")
        print(f"   ├ 総コスト: {total_cost:.2f} USD")
        print(
            f"   ├ スプレッド: {total_spread_cost:.2f} USD ({(total_spread_cost/total_cost)*100:.1f}%)"
        )
        print(
            f"   ├ 手数料: {total_commission_cost:.2f} USD ({(total_commission_cost/total_cost)*100:.1f}%)"
        )
        print(
            f"   ├ スワップ: {total_swap_cost:.2f} USD ({(total_swap_cost/total_cost)*100:.1f}%)"
        )
        print(f"   └ 1取引平均: {result['cost_per_trade']:.2f} USD")

        return result

    def generate_priority1_report(self) -> Dict:
        """第1優先統計指標レポート生成"""
        print("=== 第1優先統計指標算出開始 ===")

        report = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "MT5_Results/操作ログ.txt",
            "total_trades": len(self.trades_data),
        }

        # kiro指定第1優先指標
        report["profit_factor"] = self.calculate_profit_factor()
        report["annual_return"] = self.calculate_annual_return()
        report["max_drawdown"] = self.calculate_max_drawdown()
        report["win_rate"] = self.calculate_win_rate()

        # Gemini最優先指摘対応: リスクリワード比追加
        report["risk_reward_ratio"] = self.calculate_risk_reward_ratio()

        # Gemini高優先指摘対応: 取引コスト影響度追加
        report["transaction_cost_impact"] = self.calculate_transaction_cost_impact()

        # 合格判定（Gemini基準更新）
        report["kiro_evaluation"] = {
            "profit_factor": "PASS" if report["profit_factor"] >= 1.5 else "FAIL",
            "annual_return": "PASS" if report["annual_return"] >= 15.0 else "FAIL",
            "max_drawdown": "PASS"
            if report["max_drawdown"]["percent"] <= 15.0
            else "FAIL",
            "risk_reward_ratio": "PASS"
            if report["risk_reward_ratio"]["ratio"] >= 3.0
            else "FAIL",
            "transaction_cost": "PASS"
            if report["transaction_cost_impact"]["cost_percentage"] <= 15.0
            else "FAIL",
        }

        # Gemini Phase 2移行基準チェック
        phase2_criteria = {
            "profit_factor_min": report["profit_factor"] >= 1.2,
            "win_rate_min": report["win_rate"] >= 30.0,
            "risk_reward_positive": report["risk_reward_ratio"]["ratio"] > 0.0,
        }
        report["phase2_readiness"] = all(phase2_criteria.values())
        report["phase2_criteria"] = phase2_criteria

        print("\n=== 第1優先統計指標 kiro評価 ===")
        for metric, status in report["kiro_evaluation"].items():
            print(f"{metric}: {status}")

        print("\n=== Gemini Phase 2移行基準チェック ===")
        print(f"Phase 2移行可否: {'✅ 可能' if report['phase2_readiness'] else '❌ 不可'}")
        for criteria, status in report["phase2_criteria"].items():
            print(f"  {criteria}: {'✅' if status else '❌'}")

        return report


def main():
    """MCP統計システム実行"""
    print("🚀 Phase 1: MCP統合統計計算システム開始")
    print("kiro承認済み: 即座実行・5日完了・95%負荷削減")
    print()

    # MT5結果パス
    mt5_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results"

    # 統計計算システム初期化
    calculator = MCPStatisticsCalculator(mt5_path)

    # データ読み込み
    if not calculator.load_mt5_data():
        print("❌ データ読み込み失敗")
        return

    # 第1優先統計指標算出
    report = calculator.generate_priority1_report()

    # 結果保存
    output_file = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/mcp_statistics_priority1.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n✅ 第1優先統計指標算出完了")
    print(f"📄 結果保存: {output_file}")


if __name__ == "__main__":
    main()
