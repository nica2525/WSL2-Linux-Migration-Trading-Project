#!/usr/bin/env python3
"""
MT5データ検証システム - 異常結果原因究明・正確解決
目的: 95707%収益率等の異常値の根本原因特定・修正

検証項目:
1. exit_price=0.0の原因
2. 時系列矛盾の原因
3. 異常pip_profit計算の原因
4. 実際のMT5データ構造との齟齬

作成者: Claude（異常値根本解決担当）
"""

import json
import logging
from datetime import datetime
from typing import Dict

import pandas as pd


class MT5DataVerificationSystem:
    """MT5データ検証・異常値原因究明システム"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.raw_data = None
        self.trades_df = None

        # ログ設定
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_raw_data_for_inspection(self) -> bool:
        """生データ読み込み・詳細検査用"""
        self.logger.info("=== 生データ詳細検査読み込み ===")

        try:
            # 全データ読み込み
            self.raw_data = pd.read_excel(self.excel_path, header=None)
            self.logger.info(f"全データ読み込み: {self.raw_data.shape}")

            # 行59周辺の詳細確認
            self.logger.info("=== 行59周辺のデータ構造確認 ===")
            for i in range(55, 65):
                if i < len(self.raw_data):
                    row_data = self.raw_data.iloc[i].values
                    self.logger.info(f"行{i}: {row_data}")

            # ヘッダー確定・データ抽出
            header_row = 59
            data_start_row = 60

            header = self.raw_data.iloc[header_row].values
            data_rows = self.raw_data.iloc[data_start_row:].values

            self.trades_df = pd.DataFrame(data_rows, columns=header)
            self.trades_df = self.trades_df.dropna(how="all")

            self.logger.info(f"取引データ抽出: {len(self.trades_df)}件")
            self.logger.info(f"列名: {list(self.trades_df.columns)}")

            return True

        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            import traceback

            traceback.print_exc()
            return False

    def inspect_data_quality_issues(self) -> Dict:
        """データ品質問題詳細検査"""
        self.logger.info("=== データ品質問題詳細検査 ===")

        issues = {
            "zero_prices": [],
            "time_inconsistencies": [],
            "missing_data_patterns": [],
            "column_data_types": {},
            "sample_data_inspection": {},
        }

        # 列インデックス定義
        time_col = self.trades_df.columns[0]  # 約定時刻
        order_col = self.trades_df.columns[1]  # 注文
        price_col = self.trades_df.columns[6]  # 価格
        comment_col = self.trades_df.columns[12]  # コメント

        # 1. ゼロ価格調査
        self.logger.info("--- ゼロ価格問題調査 ---")
        zero_price_rows = self.trades_df[
            (pd.to_numeric(self.trades_df[price_col], errors="coerce") == 0)
            | (self.trades_df[price_col].isna())
        ]

        self.logger.info(f"ゼロ/NULL価格件数: {len(zero_price_rows)}")

        # サンプル表示
        for i, (idx, row) in enumerate(zero_price_rows.head(10).iterrows()):
            issues["zero_prices"].append(
                {
                    "row_index": idx,
                    "order_id": row[order_col],
                    "time": row[time_col],
                    "price": row[price_col],
                    "comment": row[comment_col],
                }
            )
            self.logger.info(
                f"ゼロ価格例{i+1}: 注文{row[order_col]}, 時刻{row[time_col]}, 価格{row[price_col]}, コメント{row[comment_col]}"
            )

        # 2. 時系列矛盾調査
        self.logger.info("--- 時系列矛盾調査 ---")

        # position_idでグループ化して時系列チェック
        position_groups = self.trades_df.groupby(order_col)
        time_issues = 0

        for position_id, group in list(position_groups)[:100]:  # 最初の100グループ
            if len(group) >= 2:
                # 時間を datetime に変換してソート
                group_with_time = group.copy()
                try:
                    group_with_time["parsed_time"] = pd.to_datetime(
                        group_with_time[time_col], format="%Y.%m.%d %H:%M:%S"
                    )
                    sorted_group = group_with_time.sort_values("parsed_time")

                    # JamesORBエントリーと決済の時系列チェック
                    entry_rows = sorted_group[
                        sorted_group[comment_col]
                        .astype(str)
                        .str.contains("JamesORB", na=False)
                    ]
                    exit_rows = sorted_group[
                        sorted_group[comment_col]
                        .astype(str)
                        .str.contains("sl |tp ", na=False)
                    ]

                    if len(entry_rows) > 0 and len(exit_rows) > 0:
                        entry_time = entry_rows.iloc[0]["parsed_time"]
                        exit_time = exit_rows.iloc[-1]["parsed_time"]

                        if exit_time < entry_time:
                            time_issues += 1
                            issues["time_inconsistencies"].append(
                                {
                                    "position_id": position_id,
                                    "entry_time": str(entry_time),
                                    "exit_time": str(exit_time),
                                    "time_diff_minutes": (
                                        entry_time - exit_time
                                    ).total_seconds()
                                    / 60,
                                }
                            )

                            if time_issues <= 5:  # 最初の5件表示
                                self.logger.info(
                                    f"時系列矛盾: position_id={position_id}, entry={entry_time}, exit={exit_time}"
                                )

                except Exception:
                    continue

        self.logger.info(f"時系列矛盾件数: {time_issues}")

        # 3. データ型・パターン分析
        self.logger.info("--- データ型・パターン分析 ---")

        for i, col in enumerate(self.trades_df.columns):
            if i > 12 or pd.isna(col):  # 主要列のみ、NaN列スキップ
                continue

            try:
                sample_series = self.trades_df[col].dropna().head(20)
                sample_data = sample_series.values.tolist()
                unique_types = {
                    type(val).__name__ for val in sample_data if pd.notna(val)
                }
            except Exception as e:
                sample_data = []
                unique_types = []
                self.logger.warning(f"列{i}処理エラー: {e}")

            issues["column_data_types"][f"col_{i}_{col}"] = {
                "unique_types": list(unique_types),
                "sample_values": [str(val) for val in sample_data[:5]],
                "null_count": self.trades_df[col].isna().sum(),
                "total_count": len(self.trades_df),
            }

        # 4. 価格データ分布調査
        self.logger.info("--- 価格データ分布調査 ---")

        price_numeric = pd.to_numeric(self.trades_df[price_col], errors="coerce")
        price_stats = {
            "min": price_numeric.min(),
            "max": price_numeric.max(),
            "mean": price_numeric.mean(),
            "std": price_numeric.std(),
            "zero_count": (price_numeric == 0).sum(),
            "null_count": price_numeric.isna().sum(),
            "valid_count": price_numeric.notna().sum(),
        }

        issues["price_distribution"] = price_stats

        self.logger.info(
            f"価格統計: min={price_stats['min']}, max={price_stats['max']}, mean={price_stats['mean']:.5f}"
        )
        self.logger.info(
            f"ゼロ価格: {price_stats['zero_count']}, NULL: {price_stats['null_count']}, 有効: {price_stats['valid_count']}"
        )

        return issues

    def analyze_specific_problematic_trades(self) -> Dict:
        """具体的問題取引の詳細分析"""
        self.logger.info("=== 問題取引詳細分析 ===")

        analysis = {
            "zero_exit_price_trades": [],
            "extreme_profit_trades": [],
            "time_reversal_trades": [],
        }

        # 列定義
        order_col = self.trades_df.columns[1]  # 注文
        time_col = self.trades_df.columns[0]  # 約定時刻
        price_col = self.trades_df.columns[6]  # 価格
        comment_col = self.trades_df.columns[12]  # コメント

        # 問題のあるposition_idを特定
        position_groups = self.trades_df.groupby(order_col)

        for position_id, group in list(position_groups)[:1000]:  # 最初の1000グループ
            if len(group) < 2:
                continue

            # JamesORBエントリーと決済を抽出
            entry_rows = group[
                group[comment_col].astype(str).str.contains("JamesORB", na=False)
            ]
            exit_rows = group[
                group[comment_col].astype(str).str.contains("sl |tp ", na=False)
            ]

            if len(entry_rows) == 0 or len(exit_rows) == 0:
                continue

            entry = entry_rows.iloc[0]
            exit_trade = exit_rows.iloc[-1]

            # 価格データ変換
            try:
                entry_price = (
                    float(entry[price_col]) if pd.notna(entry[price_col]) else 0.0
                )
                exit_price = (
                    float(exit_trade[price_col])
                    if pd.notna(exit_trade[price_col])
                    else 0.0
                )
            except:
                entry_price = 0.0
                exit_price = 0.0

            # 1. ゼロ決済価格の取引
            if exit_price == 0.0:
                analysis["zero_exit_price_trades"].append(
                    {
                        "position_id": position_id,
                        "entry_time": str(entry[time_col]),
                        "exit_time": str(exit_trade[time_col]),
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "entry_comment": str(entry[comment_col]),
                        "exit_comment": str(exit_trade[comment_col]),
                        "group_size": len(group),
                    }
                )

            # 2. 異常利益の取引（1000pip以上）
            if entry_price > 0 and exit_price > 0:
                pip_diff = abs(entry_price - exit_price) * 10000
                if pip_diff > 1000:  # 1000pip以上
                    analysis["extreme_profit_trades"].append(
                        {
                            "position_id": position_id,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "pip_difference": pip_diff,
                            "entry_comment": str(entry[comment_col]),
                            "exit_comment": str(exit_trade[comment_col]),
                        }
                    )

            # 3. 時系列逆転取引
            try:
                entry_time = pd.to_datetime(entry[time_col], format="%Y.%m.%d %H:%M:%S")
                exit_time = pd.to_datetime(
                    exit_trade[time_col], format="%Y.%m.%d %H:%M:%S"
                )

                if exit_time < entry_time:
                    analysis["time_reversal_trades"].append(
                        {
                            "position_id": position_id,
                            "entry_time": str(entry_time),
                            "exit_time": str(exit_time),
                            "time_diff_hours": (entry_time - exit_time).total_seconds()
                            / 3600,
                        }
                    )
            except:
                continue

        # 結果サマリー
        self.logger.info(f"ゼロ決済価格取引: {len(analysis['zero_exit_price_trades'])}件")
        self.logger.info(f"異常利益取引(>1000pip): {len(analysis['extreme_profit_trades'])}件")
        self.logger.info(f"時系列逆転取引: {len(analysis['time_reversal_trades'])}件")

        # サンプル表示
        for category, trades in analysis.items():
            if trades and len(trades) > 0:
                self.logger.info(f"\n{category} サンプル:")
                for i, trade in enumerate(trades[:3]):
                    self.logger.info(f"  {i+1}: {trade}")

        return analysis

    def identify_root_cause_and_solution(
        self, quality_issues: Dict, problem_trades: Dict
    ) -> Dict:
        """根本原因特定・解決策提案"""
        self.logger.info("=== 根本原因特定・解決策提案 ===")

        root_causes = {
            "primary_issues": [],
            "data_structure_problems": [],
            "calculation_logic_errors": [],
            "solutions": [],
        }

        # 1. 主要問題特定
        zero_exit_count = len(problem_trades["zero_exit_price_trades"])
        time_reversal_count = len(problem_trades["time_reversal_trades"])
        extreme_profit_count = len(problem_trades["extreme_profit_trades"])

        if zero_exit_count > 100:
            root_causes["primary_issues"].append(
                {
                    "issue": "massive_zero_exit_prices",
                    "count": zero_exit_count,
                    "severity": "CRITICAL",
                    "description": "大量のゼロ決済価格 - データ構造理解不完全",
                }
            )

        if time_reversal_count > 50:
            root_causes["primary_issues"].append(
                {
                    "issue": "time_sequence_errors",
                    "count": time_reversal_count,
                    "severity": "HIGH",
                    "description": "時系列逆転 - データソート・フィルタリング問題",
                }
            )

        # 2. データ構造問題分析
        price_stats = quality_issues.get("price_distribution", {})
        zero_price_ratio = price_stats.get("zero_count", 0) / price_stats.get(
            "total_count", 1
        )

        if zero_price_ratio > 0.1:  # 10%以上がゼロ価格
            root_causes["data_structure_problems"].append(
                {
                    "problem": "incorrect_price_column_identification",
                    "ratio": zero_price_ratio,
                    "description": "価格列の誤特定 - 列6が実際の価格列でない可能性",
                }
            )

        # 3. 計算ロジックエラー特定
        if extreme_profit_count > 0:
            root_causes["calculation_logic_errors"].append(
                {
                    "error": "pip_calculation_magnitude_error",
                    "count": extreme_profit_count,
                    "description": "pip計算の桁数エラー - 10000倍の重複適用疑い",
                }
            )

        # 4. 解決策提案
        root_causes["solutions"] = [
            {
                "priority": 1,
                "solution": "correct_price_column_identification",
                "description": "正確な価格列特定 - 手動サンプリング確認",
                "implementation": "実際の取引レコード10-20件を手動確認し、どの列が正確な価格か特定",
            },
            {
                "priority": 2,
                "solution": "fix_time_sequence_logic",
                "description": "時系列ソート修正",
                "implementation": "データ抽出時の時系列ソートロジック見直し・修正",
            },
            {
                "priority": 3,
                "solution": "recalibrate_pip_calculation",
                "description": "pip計算ロジック再調整",
                "implementation": "EURUSD標準pip計算 (price_diff * 10000) の検証・修正",
            },
            {
                "priority": 4,
                "solution": "implement_data_validation",
                "description": "データ妥当性検証システム",
                "implementation": "異常値検出・除外システムの実装",
            },
        ]

        return root_causes

    def run_complete_verification(self) -> Dict:
        """完全検証実行"""
        self.logger.info("🔍 === MT5データ完全検証システム開始 ===")

        # 1. データ読み込み
        if not self.load_raw_data_for_inspection():
            return {"error": "Failed to load data"}

        # 2. 品質問題検査
        quality_issues = self.inspect_data_quality_issues()

        # 3. 問題取引分析
        problem_trades = self.analyze_specific_problematic_trades()

        # 4. 根本原因特定
        root_analysis = self.identify_root_cause_and_solution(
            quality_issues, problem_trades
        )

        # 5. 検証結果統合
        verification_result = {
            "timestamp": datetime.now().isoformat(),
            "verification_method": "comprehensive_data_quality_inspection",
            "data_quality_issues": quality_issues,
            "problematic_trades_analysis": problem_trades,
            "root_cause_analysis": root_analysis,
            "summary": {
                "critical_issues_found": len(
                    [
                        issue
                        for issue in root_analysis["primary_issues"]
                        if issue["severity"] == "CRITICAL"
                    ]
                ),
                "total_problems_identified": len(root_analysis["primary_issues"])
                + len(root_analysis["data_structure_problems"])
                + len(root_analysis["calculation_logic_errors"]),
                "recommended_actions": len(root_analysis["solutions"]),
            },
        }

        # 6. 結果保存
        output_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/data_verification_report.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(verification_result, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"✅ 検証レポート保存: {output_path}")
        self.logger.info(
            f"🚨 重大問題: {verification_result['summary']['critical_issues_found']}件"
        )
        self.logger.info(
            f"📋 解決策: {verification_result['summary']['recommended_actions']}項目"
        )

        return verification_result


def main():
    """検証実行メイン"""
    excel_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/Reportバックテスト-900179988.xlsx"

    verifier = MT5DataVerificationSystem(excel_path)
    result = verifier.run_complete_verification()

    return result


if __name__ == "__main__":
    main()
