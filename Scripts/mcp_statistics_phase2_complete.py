#!/usr/bin/env python3
"""
MCP統合統計計算システム - Phase 1 第2優先指標（完全版）
作成日: 2025-07-26
作成者: Claude Code（実装担当）

第2優先統計指標（5項目）- 実データベース完全計算版
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict

import numpy as np

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_statistics_phase2_complete.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class CompletePhase2Calculator:
    """Phase 1 第2優先統計指標計算クラス（完全版）"""

    def __init__(self):
        """初期化"""
        self.results = {}
        self.trades_data = []
        self.daily_returns = []

    def load_mt5_data(self, file_path: str) -> bool:
        """MT5データの読み込み（既存の分析済みデータを活用）"""
        try:
            # 既存の分析結果を読み込み
            analysis_files = {
                "corrected": "MT5/Results/Backtest/corrected_analysis_results.json",
                "accurate": "MT5/Results/Backtest/accurate_trade_analysis_results.json",
                "phase1": "MT5/Results/Backtest/mcp_statistics_priority1.json",
            }

            # Phase1データを読み込み
            with open(analysis_files["phase1"]) as f:
                self.phase1_data = json.load(f)

            # 詳細な取引データを読み込み（accurate_trade_analysisから）
            if os.path.exists(analysis_files["accurate"]):
                with open(analysis_files["accurate"]) as f:
                    accurate_data = json.load(f)
                    if "trade_pairs" in accurate_data:
                        self.trades_data = accurate_data["trade_pairs"]
                        logger.info(f"Loaded {len(self.trades_data)} trade pairs")
                        return True

            # 代替: corrected_analysisから
            if os.path.exists(analysis_files["corrected"]):
                with open(analysis_files["corrected"]) as f:
                    corrected_data = json.load(f)
                    if "trades" in corrected_data:
                        self.trades_data = corrected_data["trades"]
                        logger.info(
                            f"Loaded {len(self.trades_data)} trades from corrected analysis"
                        )
                        return True

            logger.error("No detailed trade data found")
            return False

        except Exception as e:
            logger.error(f"Error loading MT5 data: {e}")
            return False

    def calculate_actual_sharpe_ratio(self) -> float:
        """実データに基づくシャープレシオ計算"""
        try:
            if not self.trades_data:
                return 0.0

            # 日次リターンの計算（取引ごとの収益率）
            initial_balance = 10000
            returns = []

            for trade in self.trades_data:
                if isinstance(trade, dict):
                    # profit、pip_profit、またはpip_net_profitを探す
                    profit = None
                    if "profit" in trade:
                        profit = float(trade["profit"])
                    elif "pip_profit" in trade:
                        # pip_profitをUSDに変換（0.01ロット、EURUSD想定）
                        profit = float(trade["pip_profit"]) * 0.1
                    elif "pip_net_profit" in trade:
                        profit = float(trade["pip_net_profit"]) * 0.1

                    if profit is not None:
                        daily_return = profit / initial_balance
                        returns.append(daily_return)

            if not returns:
                return 0.0

            # 年率換算（250営業日）
            returns_array = np.array(returns)
            mean_return = np.mean(returns_array) * 250
            std_return = np.std(returns_array) * np.sqrt(250)

            # リスクフリーレート（2%）
            risk_free_rate = 0.02

            if std_return == 0:
                return 0.0

            sharpe = (mean_return - risk_free_rate) / std_return
            return round(sharpe, 3)

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0

    def calculate_actual_calmar_ratio(self) -> float:
        """実データに基づくカルマーレシオ計算"""
        try:
            annual_return = self.phase1_data.get("annual_return", 0)
            max_dd = self.phase1_data.get("max_drawdown", {}).get("percent", 0)

            if max_dd == 0:
                return 0.0

            calmar = annual_return / max_dd
            return round(calmar, 3)

        except Exception as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return 0.0

    def calculate_actual_expected_value(self) -> Dict:
        """実データに基づく期待値計算"""
        try:
            if not self.trades_data:
                return {"pips": 0, "usd": 0}

            # 勝ち負けの分離
            winning_trades = []
            losing_trades = []

            for trade in self.trades_data:
                if isinstance(trade, dict):
                    # profit、pip_profit、またはpip_net_profitを探す
                    profit = None
                    if "profit" in trade:
                        profit = float(trade["profit"])
                    elif "pip_profit" in trade:
                        profit = float(trade["pip_profit"]) * 0.1
                    elif "pip_net_profit" in trade:
                        profit = float(trade["pip_net_profit"]) * 0.1

                    if profit is not None:
                        if profit > 0:
                            winning_trades.append(profit)
                        elif profit < 0:
                            losing_trades.append(profit)

            # 統計計算
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            total_trades = win_count + loss_count

            if total_trades == 0:
                return {"pips": 0, "usd": 0}

            win_rate = win_count / total_trades
            avg_win = np.mean(winning_trades) if winning_trades else 0
            avg_loss = abs(np.mean(losing_trades)) if losing_trades else 0

            # 期待値（USD）
            expected_value_usd = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

            # pips換算（EURUSDと仮定、1pip = 0.0001）
            # 0.01ロットの場合、1pip = 0.1 USD
            expected_value_pips = expected_value_usd / 0.1

            return {
                "pips": round(expected_value_pips, 2),
                "usd": round(expected_value_usd, 4),
                "win_rate": round(win_rate * 100, 2),
                "avg_win": round(avg_win, 4),
                "avg_loss": round(avg_loss, 4),
            }

        except Exception as e:
            logger.error(f"Error calculating expected value: {e}")
            return {"pips": 0, "usd": 0}

    def calculate_actual_consecutive_losses(self) -> Dict:
        """実データに基づく連続負け回数計算"""
        try:
            if not self.trades_data:
                return {"max": 0, "current": 0, "sequences": []}

            max_consecutive = 0
            current_consecutive = 0
            loss_sequences = []

            for _i, trade in enumerate(self.trades_data):
                if isinstance(trade, dict):
                    # profit、pip_profit、またはpip_net_profitを探す
                    profit = None
                    if "profit" in trade:
                        profit = float(trade["profit"])
                    elif "pip_profit" in trade:
                        profit = float(trade["pip_profit"]) * 0.1
                    elif "pip_net_profit" in trade:
                        profit = float(trade["pip_net_profit"]) * 0.1

                    if profit is not None:
                        if profit < 0:
                            current_consecutive += 1
                        else:
                            if current_consecutive > 0:
                                loss_sequences.append(current_consecutive)
                                max_consecutive = max(
                                    max_consecutive, current_consecutive
                                )
                            current_consecutive = 0

            # 最後のシーケンスも確認
            if current_consecutive > 0:
                loss_sequences.append(current_consecutive)
                max_consecutive = max(max_consecutive, current_consecutive)

            # 統計情報
            return {
                "max": max_consecutive,
                "current": current_consecutive,
                "sequences": loss_sequences,
                "avg_sequence": round(np.mean(loss_sequences), 1)
                if loss_sequences
                else 0,
                "total_sequences": len(loss_sequences),
            }

        except Exception as e:
            logger.error(f"Error calculating consecutive losses: {e}")
            return {"max": 0, "current": 0, "sequences": []}

    def calculate_risk_of_ruin_monte_carlo(self, simulations: int = 10000) -> Dict:
        """モンテカルロシミュレーションによる破産確率計算"""
        try:
            # 基本パラメータ
            win_rate = self.phase1_data.get("win_rate", 0) / 100
            rr_data = self.phase1_data.get("risk_reward_ratio", {})
            avg_win = rr_data.get("avg_profit", 0)
            avg_loss = rr_data.get("avg_loss", 0)

            if win_rate == 0 or avg_loss == 0:
                return {"probability": 100.0, "avg_ruin_trades": 0}

            # シミュレーション設定
            initial_balance = 1000  # 正規化
            ruin_threshold = 100  # 90%損失で破産
            risk_per_trade = 10  # 1%リスク

            ruin_count = 0
            ruin_trades = []

            for _ in range(simulations):
                balance = initial_balance
                trades = 0

                while balance > ruin_threshold and trades < 10000:
                    trades += 1

                    # 勝敗をランダムに決定
                    if np.random.random() < win_rate:
                        # 勝ち
                        balance += risk_per_trade * (avg_win / avg_loss)
                    else:
                        # 負け
                        balance -= risk_per_trade

                if balance <= ruin_threshold:
                    ruin_count += 1
                    ruin_trades.append(trades)

            ruin_probability = (ruin_count / simulations) * 100
            avg_ruin_trades = np.mean(ruin_trades) if ruin_trades else 0

            return {
                "probability": round(ruin_probability, 2),
                "avg_ruin_trades": round(avg_ruin_trades, 0),
                "simulations": simulations,
                "ruin_events": ruin_count,
            }

        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {e}")
            return {"probability": 100.0, "avg_ruin_trades": 0}

    def analyze_complete(self) -> Dict:
        """完全な第2優先指標分析"""
        try:
            # 各指標の計算
            sharpe = self.calculate_actual_sharpe_ratio()
            calmar = self.calculate_actual_calmar_ratio()
            expected_value = self.calculate_actual_expected_value()
            consecutive_losses = self.calculate_actual_consecutive_losses()
            risk_of_ruin = self.calculate_risk_of_ruin_monte_carlo()

            # 結果の構築
            self.results = {
                "第2優先統計指標_完全版": {
                    "1_シャープレシオ": {
                        "値": sharpe,
                        "評価": "優秀" if sharpe > 1.0 else "良好" if sharpe > 0.5 else "要改善",
                    },
                    "2_カルマーレシオ": {
                        "値": calmar,
                        "評価": "優秀" if calmar > 3.0 else "良好" if calmar > 1.0 else "要改善",
                    },
                    "3_期待値": {
                        "pips": expected_value["pips"],
                        "usd": expected_value["usd"],
                        "評価": "利益期待" if expected_value["pips"] > 0 else "損失期待",
                    },
                    "4_連続負け": {
                        "最大": consecutive_losses["max"],
                        "平均": consecutive_losses["avg_sequence"],
                        "評価": "低リスク"
                        if consecutive_losses["max"] < 5
                        else "中リスク"
                        if consecutive_losses["max"] < 10
                        else "高リスク",
                    },
                    "5_破産確率": {
                        "確率_%": risk_of_ruin["probability"],
                        "平均破産取引数": risk_of_ruin["avg_ruin_trades"],
                        "評価": "低リスク"
                        if risk_of_ruin["probability"] < 5
                        else "中リスク"
                        if risk_of_ruin["probability"] < 20
                        else "高リスク",
                    },
                },
                "詳細データ": {
                    "期待値詳細": expected_value,
                    "連続損失詳細": consecutive_losses,
                    "破産確率詳細": risk_of_ruin,
                },
                "算出基礎データ": {
                    "総取引数": self.phase1_data.get("total_trades", 0),
                    "勝率_%": self.phase1_data.get("win_rate", 0),
                    "リスクリワード比": self.phase1_data.get("risk_reward_ratio", {}).get(
                        "ratio", 0
                    ),
                    "年間収益率_%": self.phase1_data.get("annual_return", 0),
                    "最大DD_%": self.phase1_data.get("max_drawdown", {}).get(
                        "percent", 0
                    ),
                },
                "総合評価": self._comprehensive_evaluation(
                    sharpe,
                    calmar,
                    expected_value["pips"],
                    consecutive_losses["max"],
                    risk_of_ruin["probability"],
                ),
                "算出日時": datetime.now().isoformat(),
            }

            return self.results

        except Exception as e:
            logger.error(f"Error in complete analysis: {e}")
            return {}

    def _comprehensive_evaluation(
        self,
        sharpe: float,
        calmar: float,
        expected_pips: float,
        max_losses: int,
        ruin_prob: float,
    ) -> Dict:
        """総合的な評価"""

        # スコアリングシステム
        score = 0
        max_score = 100

        # シャープレシオ（20点）
        if sharpe > 1.0:
            score += 20
        elif sharpe > 0.5:
            score += 10
        elif sharpe > 0:
            score += 5

        # カルマーレシオ（20点）
        if calmar > 3.0:
            score += 20
        elif calmar > 1.0:
            score += 10
        elif calmar > 0:
            score += 5

        # 期待値（30点）
        if expected_pips > 5:
            score += 30
        elif expected_pips > 0:
            score += 15

        # 連続損失（15点）
        if max_losses < 5:
            score += 15
        elif max_losses < 10:
            score += 8

        # 破産確率（15点）
        if ruin_prob < 5:
            score += 15
        elif ruin_prob < 20:
            score += 8
        elif ruin_prob < 50:
            score += 3

        # 評価
        if score >= 80:
            grade = "A"
            verdict = "優秀・実運用推奨"
        elif score >= 60:
            grade = "B"
            verdict = "良好・条件付き運用可"
        elif score >= 40:
            grade = "C"
            verdict = "要改善・デモ運用継続"
        elif score >= 20:
            grade = "D"
            verdict = "不良・大幅改善必要"
        else:
            grade = "F"
            verdict = "投資不適格・運用停止推奨"

        return {
            "総合スコア": f"{score}/{max_score}",
            "グレード": grade,
            "判定": verdict,
            "詳細スコア": {
                "シャープレシオ": f"{min(20, max(0, int(sharpe * 20)))}/20",
                "カルマーレシオ": f"{min(20, max(0, int(calmar * 6.67)))}/20",
                "期待値": f"{30 if expected_pips > 5 else 15 if expected_pips > 0 else 0}/30",
                "連続損失": f"{15 if max_losses < 5 else 8 if max_losses < 10 else 0}/15",
                "破産確率": f"{15 if ruin_prob < 5 else 8 if ruin_prob < 20 else 3 if ruin_prob < 50 else 0}/15",
            },
        }

    def save_results(
        self, output_file: str = "mcp_statistics_phase2_complete.json"
    ) -> None:
        """結果の保存"""
        try:
            output_path = os.path.join("MT5/Results/Backtest", output_file)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            logger.info(f"Results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")


def main():
    """メイン実行関数"""
    logger.info("Starting Phase 2 Complete Analysis...")

    calculator = CompletePhase2Calculator()

    # データ読み込み
    if calculator.load_mt5_data("dummy_path"):  # 既存のJSONデータを使用
        # 分析実行
        results = calculator.analyze_complete()

        if results:
            # 結果の表示
            print("\n" + "=" * 80)
            print("Phase 1 第2優先統計指標 計算結果【完全版】")
            print("=" * 80)

            # 主要指標の表示
            phase2_data = results.get("第2優先統計指標_完全版", {})

            print("\n【第2優先統計指標】")
            print(
                f"1. シャープレシオ: {phase2_data['1_シャープレシオ']['値']} ({phase2_data['1_シャープレシオ']['評価']})"
            )
            print(
                f"2. カルマーレシオ: {phase2_data['2_カルマーレシオ']['値']} ({phase2_data['2_カルマーレシオ']['評価']})"
            )
            print(
                f"3. 期待値: {phase2_data['3_期待値']['pips']} pips ({phase2_data['3_期待値']['評価']})"
            )
            print(
                f"4. 最大連続負け: {phase2_data['4_連続負け']['最大']}回 ({phase2_data['4_連続負け']['評価']})"
            )
            print(
                f"5. 破産確率: {phase2_data['5_破産確率']['確率_%']}% ({phase2_data['5_破産確率']['評価']})"
            )

            # 総合評価
            eval_data = results.get("総合評価", {})
            print("\n【総合評価】")
            print(f"スコア: {eval_data['総合スコア']}")
            print(f"グレード: {eval_data['グレード']}")
            print(f"判定: {eval_data['判定']}")

            # 結果の保存
            calculator.save_results()

            print("\n✅ Phase 2 完全版分析が完了しました")
        else:
            logger.error("Failed to analyze data")
    else:
        logger.error("Failed to load MT5 data")


if __name__ == "__main__":
    main()
