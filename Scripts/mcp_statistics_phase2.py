#!/usr/bin/env python3
"""
MCP統合統計計算システム - Phase 1 第2優先指標
作成日: 2025-07-26
作成者: Claude Code（実装担当）

第2優先統計指標（5項目）:
1. シャープレシオ（Sharpe Ratio）
2. カルマーレシオ（Calmar Ratio）
3. 期待値（Expected Value）
4. 連続負け回数（Max Consecutive Losses）
5. 破産確率（Risk of Ruin）
"""

import json
import logging
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_statistics_phase2.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class Phase2StatisticsCalculator:
    """Phase 1 第2優先統計指標計算クラス"""

    def __init__(self):
        """初期化"""
        self.results = {}
        self.trades_df = None

    def load_trade_data(self, file_path: str) -> bool:
        """取引データの読み込み"""
        try:
            logger.info(f"Loading trade data from: {file_path}")

            # 直接Excelファイルを読み込み（MT5形式）
            # MT5のExcelは通常ヘッダーが16行目あたりにある
            try:
                # まず構造を確認
                pd.read_excel(file_path, nrows=30)
                header_row = None

                # "Time"カラムを含む行を探す
                for i in range(30):
                    try:
                        df_temp = pd.read_excel(file_path, header=i, nrows=1)
                        if "Time" in df_temp.columns:
                            header_row = i
                            break
                    except:
                        continue

                if header_row is None:
                    header_row = 15  # デフォルト値

                self.trades_df = pd.read_excel(file_path, header=header_row)
                logger.info(
                    f"Loaded {len(self.trades_df)} trades from header row {header_row}"
                )
                return True

            except Exception as e:
                logger.error(f"Error reading Excel file: {e}")
                return False

        except Exception as e:
            logger.error(f"Error loading trade data: {e}")
            return False

    def calculate_sharpe_ratio(
        self, annual_return: float, returns: List[float], risk_free_rate: float = 0.02
    ) -> float:
        """
        シャープレシオの計算

        Args:
            annual_return: 年間収益率（%）
            returns: 各取引の収益率リスト
            risk_free_rate: リスクフリーレート（デフォルト2%）

        Returns:
            シャープレシオ
        """
        try:
            if not returns:
                return 0.0

            # 日次リターンの標準偏差を年率換算（250営業日）
            daily_std = np.std(returns)
            annual_std = daily_std * np.sqrt(250)

            if annual_std == 0:
                return 0.0

            sharpe = (annual_return / 100 - risk_free_rate) / annual_std
            return round(sharpe, 3)

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0

    def calculate_calmar_ratio(
        self, annual_return: float, max_drawdown: float
    ) -> float:
        """
        カルマーレシオの計算

        Args:
            annual_return: 年間収益率（%）
            max_drawdown: 最大ドローダウン（%）

        Returns:
            カルマーレシオ
        """
        try:
            if max_drawdown == 0:
                return 0.0

            calmar = annual_return / max_drawdown
            return round(calmar, 3)

        except Exception as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return 0.0

    def calculate_expected_value(
        self, win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        """
        期待値の計算

        Args:
            win_rate: 勝率（%）
            avg_win: 平均利益（pips）
            avg_loss: 平均損失（pips）

        Returns:
            期待値（pips）
        """
        try:
            win_rate_decimal = win_rate / 100
            expected_value = (win_rate_decimal * avg_win) - (
                (1 - win_rate_decimal) * abs(avg_loss)
            )
            return round(expected_value, 2)

        except Exception as e:
            logger.error(f"Error calculating expected value: {e}")
            return 0.0

    def calculate_max_consecutive_losses(self, trades: List[Dict]) -> int:
        """
        最大連続負け回数の計算

        Args:
            trades: 取引リスト（profit情報を含む）

        Returns:
            最大連続負け回数
        """
        try:
            max_consecutive = 0
            current_consecutive = 0

            for trade in trades:
                if trade.get("profit", 0) < 0:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0

            return max_consecutive

        except Exception as e:
            logger.error(f"Error calculating max consecutive losses: {e}")
            return 0

    def calculate_risk_of_ruin(
        self,
        win_rate: float,
        risk_reward_ratio: float,
        risk_per_trade: float = 1.0,
        target_ruin: float = 10.0,
    ) -> float:
        """
        破産確率の計算（簡易版）

        Args:
            win_rate: 勝率（%）
            risk_reward_ratio: リスクリワード比
            risk_per_trade: 1取引あたりのリスク（%）
            target_ruin: 破産とみなす残高減少率（%）

        Returns:
            破産確率（%）
        """
        try:
            win_rate_decimal = win_rate / 100

            # Kelly基準による最適リスク
            if risk_reward_ratio > 0:
                kelly_fraction = (
                    win_rate_decimal * risk_reward_ratio - (1 - win_rate_decimal)
                ) / risk_reward_ratio
            else:
                kelly_fraction = 0

            if kelly_fraction <= 0:
                # 期待値がマイナスの場合、破産確率100%
                return 100.0

            # 簡易的な破産確率計算
            # 実際のリスクがKelly基準を超える場合、破産確率が急上昇
            if risk_per_trade > kelly_fraction * 100:
                risk_multiplier = risk_per_trade / (kelly_fraction * 100)
                ruin_probability = min(100, 50 * risk_multiplier)
            else:
                # Monte Carlo simulation の簡易版
                ruin_probability = 100 * np.exp(
                    -2 * kelly_fraction * (target_ruin / 100)
                )

            return round(min(100, max(0, ruin_probability)), 2)

        except Exception as e:
            logger.error(f"Error calculating risk of ruin: {e}")
            return 100.0

    def analyze_trades(self) -> Dict:
        """取引データの分析と第2優先指標の計算"""
        try:
            if self.trades_df is None or self.trades_df.empty:
                logger.error("No trade data loaded")
                return {}

            # 基本統計の計算（第1優先指標から必要な値を取得）
            total_trades = len(self.trades_df)
            profits = self.trades_df["Profit"].values

            # 勝ち負けの分離
            winning_trades = profits[profits > 0]
            losing_trades = profits[profits < 0]

            # 基本指標
            win_rate = (
                (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
            )

            # 平均利益・損失（pips換算 - EURUSDの場合）
            avg_win_pips = (
                np.mean(winning_trades) * 10000 if len(winning_trades) > 0 else 0
            )
            avg_loss_pips = (
                np.mean(losing_trades) * 10000 if len(losing_trades) > 0 else 0
            )

            # リスクリワード比
            risk_reward_ratio = (
                abs(avg_win_pips / avg_loss_pips) if avg_loss_pips != 0 else 0
            )

            # 年間収益率（仮定: 初期残高10,000）
            initial_balance = 10000
            final_balance = initial_balance + np.sum(profits)
            annual_return = ((final_balance - initial_balance) / initial_balance) * 100

            # 最大ドローダウン（簡易計算）
            cumulative_returns = np.cumsum(profits)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = running_max - cumulative_returns
            max_drawdown_value = np.max(drawdowns) if len(drawdowns) > 0 else 0
            max_drawdown_percent = (max_drawdown_value / initial_balance) * 100

            # 日次リターンの計算（取引ごとのリターン）
            returns = profits / initial_balance

            # 第2優先指標の計算
            self.results = {
                "第2優先統計指標": {
                    "1_シャープレシオ": self.calculate_sharpe_ratio(
                        annual_return, returns.tolist()
                    ),
                    "2_カルマーレシオ": self.calculate_calmar_ratio(
                        annual_return, max_drawdown_percent
                    ),
                    "3_期待値_pips": self.calculate_expected_value(
                        win_rate, avg_win_pips, avg_loss_pips
                    ),
                    "4_最大連続負け回数": self.calculate_max_consecutive_losses(
                        [{"profit": p} for p in profits]
                    ),
                    "5_破産確率_%": self.calculate_risk_of_ruin(
                        win_rate, risk_reward_ratio
                    ),
                },
                "算出基礎データ": {
                    "総取引数": total_trades,
                    "勝率_%": round(win_rate, 2),
                    "平均利益_pips": round(avg_win_pips, 2),
                    "平均損失_pips": round(avg_loss_pips, 2),
                    "リスクリワード比": round(risk_reward_ratio, 3),
                    "年間収益率_%": round(annual_return, 2),
                    "最大DD_%": round(max_drawdown_percent, 2),
                },
                "評価": self._evaluate_results(
                    self.calculate_sharpe_ratio(annual_return, returns.tolist()),
                    self.calculate_calmar_ratio(annual_return, max_drawdown_percent),
                    self.calculate_expected_value(
                        win_rate, avg_win_pips, avg_loss_pips
                    ),
                    self.calculate_max_consecutive_losses(
                        [{"profit": p} for p in profits]
                    ),
                    self.calculate_risk_of_ruin(win_rate, risk_reward_ratio),
                ),
            }

            return self.results

        except Exception as e:
            logger.error(f"Error analyzing trades: {e}")
            return {}

    def _evaluate_results(
        self,
        sharpe: float,
        calmar: float,
        expected_value: float,
        max_losses: int,
        risk_of_ruin: float,
    ) -> Dict:
        """結果の評価"""
        evaluations = {
            "シャープレシオ評価": "優秀" if sharpe > 1.0 else "良好" if sharpe > 0.5 else "要改善",
            "カルマーレシオ評価": "優秀" if calmar > 3.0 else "良好" if calmar > 1.0 else "要改善",
            "期待値評価": "利益期待" if expected_value > 0 else "損失期待",
            "連続損失リスク": "低" if max_losses < 5 else "中" if max_losses < 10 else "高",
            "破産リスク": "低" if risk_of_ruin < 5 else "中" if risk_of_ruin < 20 else "高",
        }

        # 総合評価
        if sharpe > 0.5 and calmar > 1.0 and expected_value > 0 and risk_of_ruin < 20:
            evaluations["総合評価"] = "投資適格"
        elif expected_value > 0 and risk_of_ruin < 50:
            evaluations["総合評価"] = "改善必要だが可能性あり"
        else:
            evaluations["総合評価"] = "投資不適格・大幅改善必要"

        return evaluations

    def save_results(self, output_file: str = "mcp_statistics_phase2.json") -> None:
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
    # 最新のバックテスト結果ファイルを探す
    import glob

    pattern = "MT5/Results/Backtest/**/Report*.xlsx"
    files = glob.glob(pattern, recursive=True)

    if not files:
        logger.error("No backtest result files found")
        return

    # 最新のファイルを選択
    latest_file = max(files, key=os.path.getmtime)
    logger.info(f"Using latest file: {latest_file}")

    # 計算実行
    calculator = Phase2StatisticsCalculator()

    if calculator.load_trade_data(latest_file):
        results = calculator.analyze_trades()

        if results:
            # 結果の表示
            print("\n" + "=" * 60)
            print("Phase 1 第2優先統計指標 計算結果")
            print("=" * 60)

            for category, values in results.items():
                print(f"\n【{category}】")
                for key, value in values.items():
                    print(f"  {key}: {value}")

            # 結果の保存
            calculator.save_results()

            print("\n✅ 第2優先指標の計算が完了しました")
        else:
            logger.error("Failed to analyze trades")
    else:
        logger.error("Failed to load trade data")


if __name__ == "__main__":
    main()
