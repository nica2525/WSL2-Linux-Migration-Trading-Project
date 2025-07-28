#!/usr/bin/env python3
"""
MT5修正済み分析システム - 根本原因解決版
解決事項:
1. コメント列から決済価格抽出（sl 1.11441 → 1.11441）
2. 時系列ソート修正
3. 正確なpip計算

根本原因: MT5「価格」列はエントリー価格のみ、決済価格はコメント内に記載

作成者: Claude（根本原因解決・正確実装担当）
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List

import pandas as pd


class MT5CorrectedAnalyzer:
    """MT5修正済み分析システム（正確な価格抽出）"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.raw_data = None
        self.trades_df = None
        self.paired_trades = []

        # ログ設定
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_data_structure(self) -> bool:
        """確認済み構造でデータ読み込み"""
        self.logger.info("=== MT5データ読み込み（修正版） ===")

        try:
            self.raw_data = pd.read_excel(self.excel_path, header=None)

            # 確定構造：ヘッダー行59、データ開始60
            header_row = 59
            data_start_row = 60

            header = self.raw_data.iloc[header_row].values
            data_rows = self.raw_data.iloc[data_start_row:].values

            self.trades_df = pd.DataFrame(data_rows, columns=header)
            self.trades_df = self.trades_df.dropna(how="all")

            self.logger.info(f"取引データ: {len(self.trades_df)}件")
            return True

        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            return False

    def extract_exit_price_from_comment(self, comment: str) -> float:
        """コメントから決済価格抽出"""
        if pd.isna(comment) or not isinstance(comment, str):
            return 0.0

        # sl 1.11441 や tp 1.11356 のパターンをマッチ
        pattern = r"(sl|tp)\s+([0-9]+\.?[0-9]*)"
        match = re.search(pattern, comment.lower())

        if match:
            try:
                return float(match.group(2))
            except ValueError:
                return 0.0

        return 0.0

    def create_corrected_pairs(self) -> List[Dict]:
        """修正済みペア化ロジック"""
        self.logger.info("=== 修正済みペア化実行 ===")

        pairs = []

        # 列定義
        time_col = self.trades_df.columns[0]  # 約定時刻
        order_col = self.trades_df.columns[1]  # 注文
        price_col = self.trades_df.columns[6]  # 価格（エントリー価格）
        comment_col = self.trades_df.columns[12]  # コメント

        # position_idでグループ化
        position_groups = self.trades_df.groupby(order_col)

        successful_pairs = 0
        failed_pairs = 0

        for position_id, group in position_groups:
            if len(group) < 2:
                continue

            # 時系列ソート（修正版）
            group_sorted = group.sort_values(time_col)

            # JamesORBエントリー検索
            entry_rows = group_sorted[
                group_sorted[comment_col].astype(str).str.contains("JamesORB", na=False)
            ]

            # sl/tp決済検索
            exit_rows = group_sorted[
                group_sorted[comment_col].astype(str).str.contains("sl |tp ", na=False)
            ]

            if len(entry_rows) == 0 or len(exit_rows) == 0:
                failed_pairs += 1
                continue

            # 最初のエントリーと最後の決済
            entry = entry_rows.iloc[0]
            exit_trade = exit_rows.iloc[-1]

            try:
                # エントリー価格（価格列から）
                entry_price = (
                    float(entry[price_col]) if pd.notna(entry[price_col]) else 0.0
                )

                # 決済価格（コメントから抽出）★修正ポイント
                exit_price = self.extract_exit_price_from_comment(
                    exit_trade[comment_col]
                )

                # 価格検証
                if entry_price <= 0 or exit_price <= 0:
                    failed_pairs += 1
                    continue

                # 時系列検証
                try:
                    entry_time = pd.to_datetime(
                        entry[time_col], format="%Y.%m.%d %H:%M:%S"
                    )
                    exit_time = pd.to_datetime(
                        exit_trade[time_col], format="%Y.%m.%d %H:%M:%S"
                    )

                    # 時系列逆転チェック
                    if exit_time < entry_time:
                        self.logger.warning(
                            f"時系列逆転: position_id={position_id}, entry={entry_time}, exit={exit_time}"
                        )
                        failed_pairs += 1
                        continue

                except Exception:
                    failed_pairs += 1
                    continue

                # 取引方向判定
                is_buy = "buy" in str(entry[comment_col]).lower()

                # 正確なpip損益計算（EURUSD）
                if is_buy:
                    pip_profit = (exit_price - entry_price) * 10000
                else:
                    pip_profit = (entry_price - exit_price) * 10000

                # 金額計算（標準0.01ロット）
                volume = 0.01
                gross_profit = pip_profit * volume * 1.0  # $1 per pip for 0.01 lot

                # 取引コスト
                spread_cost = 0.6 * volume * 10
                commission = 2.5 * volume * 2
                total_cost = spread_cost + commission

                net_profit = gross_profit - total_cost

                # 決済タイプ特定
                exit_type = (
                    "stop_loss"
                    if "sl" in str(exit_trade[comment_col]).lower()
                    else "take_profit"
                )

                pair = {
                    "position_id": position_id,
                    "entry_time": str(entry_time),
                    "exit_time": str(exit_time),
                    "direction": "buy" if is_buy else "sell",
                    "volume": volume,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pip_profit": pip_profit,
                    "gross_profit": gross_profit,
                    "spread_cost": spread_cost,
                    "commission": commission,
                    "total_cost": total_cost,
                    "net_profit": net_profit,
                    "is_winner": net_profit > 0,
                    "exit_type": exit_type,
                    "holding_minutes": (exit_time - entry_time).total_seconds() / 60,
                    "entry_comment": str(entry[comment_col]),
                    "exit_comment": str(exit_trade[comment_col]),
                }

                pairs.append(pair)
                successful_pairs += 1

            except Exception as e:
                self.logger.warning(f"ペア化エラー position_id={position_id}: {e}")
                failed_pairs += 1
                continue

        self.logger.info(f"成功ペア: {successful_pairs}, 失敗: {failed_pairs}")
        self.logger.info(
            f"ペア化効率: {successful_pairs/(successful_pairs+failed_pairs)*100:.1f}%"
        )

        return pairs

    def calculate_corrected_statistics(self, trades: List[Dict]) -> Dict:
        """修正済み統計算出"""
        self.logger.info("=== 修正済み統計算出 ===")

        if not trades:
            return {"error": "No valid trades"}

        # 基本統計
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["is_winner"]]
        losing_trades = [t for t in trades if not t["is_winner"]]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)

        total_profit = sum(t["net_profit"] for t in winning_trades)
        total_loss = abs(sum(t["net_profit"] for t in losing_trades))
        net_profit = sum(t["net_profit"] for t in trades)

        # 統計指標算出
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
        win_rate = (win_count / total_trades) * 100

        avg_win = total_profit / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # ドローダウン計算
        initial_balance = 10000
        balance_curve = [initial_balance]
        for trade in trades:
            balance_curve.append(balance_curve[-1] + trade["net_profit"])

        peak = initial_balance
        max_dd = 0
        for balance in balance_curve:
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak * 100
            if dd > max_dd:
                max_dd = dd

        annual_return = (net_profit / initial_balance) * 100

        # 連勝連敗
        consecutive_wins = consecutive_losses = 0
        max_wins = max_losses = 0

        for trade in trades:
            if trade["is_winner"]:
                consecutive_wins += 1
                consecutive_losses = 0
                max_wins = max(max_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_losses = max(max_losses, consecutive_losses)

        # 期待値
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)

        # 平均保有時間
        holding_times = [
            t["holding_minutes"] for t in trades if t["holding_minutes"] > 0
        ]
        avg_holding_minutes = (
            sum(holding_times) / len(holding_times) if holding_times else 0
        )

        statistics = {
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate_percent": win_rate,
            "profit_factor": profit_factor,
            "annual_return_percent": annual_return,
            "max_drawdown_percent": max_dd,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "risk_reward_ratio": risk_reward_ratio,
            "net_profit": net_profit,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
            "expectancy": expectancy,
            "avg_holding_minutes": avg_holding_minutes,
            "final_balance": balance_curve[-1],
        }

        # 結果表示
        self.logger.info("=== 修正済み統計結果 ===")
        self.logger.info(f"総取引: {total_trades}")
        self.logger.info(f"勝率: {win_rate:.1f}%")
        self.logger.info(f"プロフィットファクター: {profit_factor:.3f}")
        self.logger.info(f"年間収益率: {annual_return:.2f}%")
        self.logger.info(f"最大ドローダウン: {max_dd:.2f}%")
        self.logger.info(f"純利益: ${net_profit:.2f}")
        self.logger.info(f"期待値: ${expectancy:.2f}")

        return statistics

    def run_corrected_analysis(self) -> Dict:
        """修正済み完全分析実行"""
        self.logger.info("🔧 === MT5修正済み分析システム開始 ===")

        # 1. データ読み込み
        if not self.load_data_structure():
            return {"error": "Failed to load data"}

        # 2. 修正済みペア化
        pairs = self.create_corrected_pairs()
        if not pairs:
            return {"error": "No valid pairs created"}

        # 3. 修正済み統計算出
        statistics = self.calculate_corrected_statistics(pairs)

        # 4. 結果構築
        results = {
            "timestamp": datetime.now().isoformat(),
            "analysis_method": "corrected_price_extraction_from_comments",
            "corrections_applied": [
                "Exit price extracted from comment column (sl/tp values)",
                "Time sequence validation implemented",
                "Accurate pip calculation for EURUSD",
                "Data validation and error handling added",
            ],
            "data_quality": {
                "total_records": len(self.trades_df),
                "valid_pairs_created": len(pairs),
                "success_rate": len(pairs)
                / len(self.trades_df.groupby(self.trades_df.columns[1]))
                * 100,
            },
            "trade_pairs": pairs[:100],  # 最初の100件保存
            "statistics": statistics,
        }

        # 5. 結果保存
        output_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/corrected_analysis_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"✅ 修正済み分析結果保存: {output_path}")

        return results


def main():
    """修正済み分析実行"""
    excel_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/Reportバックテスト-900179988.xlsx"

    analyzer = MT5CorrectedAnalyzer(excel_path)
    results = analyzer.run_corrected_analysis()

    return results


if __name__ == "__main__":
    main()
