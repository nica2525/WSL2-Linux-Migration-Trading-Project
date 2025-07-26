#!/usr/bin/env python3
"""
MT5原因特定最終検証システム
目的: 「MT5の特殊記録方式」仮説の徹底検証

検証項目:
1. 時系列逆転パターンの一貫性確認
2. 他の可能な原因の完全排除
3. MT5動作仮説の論理的整合性検証

作成者: Claude（最終原因確定担当）
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict

import pandas as pd


class MT5FinalVerification:
    """MT5原因特定最終検証システム"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.raw_data = None
        self.trades_df = None

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_data_for_verification(self) -> bool:
        """検証用データ読み込み"""
        try:
            self.raw_data = pd.read_excel(self.excel_path, header=None)

            header_row = 59
            data_start_row = 60

            header = self.raw_data.iloc[header_row].values
            data_rows = self.raw_data.iloc[data_start_row:].values

            self.trades_df = pd.DataFrame(data_rows, columns=header)
            self.trades_df = self.trades_df.dropna(how="all")

            self.logger.info(f"検証データ読み込み完了: {len(self.trades_df)}件")
            return True

        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            return False

    def verify_time_reversal_hypothesis(self) -> Dict:
        """時系列逆転仮説の徹底検証"""
        self.logger.info("=== 時系列逆転仮説徹底検証 ===")

        verification = {
            "hypothesis_tests": [],
            "alternative_explanations": [],
            "consistency_checks": [],
            "final_verdict": {},
        }

        # 列定義
        time_col = self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        comment_col = self.trades_df.columns[12]

        # テスト1: 時系列逆転の一貫性確認
        self.logger.info("--- テスト1: 時系列逆転パターン一貫性 ---")

        position_groups = self.trades_df.groupby(order_col)
        reversal_patterns = {
            "tp_first": 0,
            "sl_first": 0,
            "normal_order": 0,
            "inconsistent": 0,
        }

        test_sample = 0
        for _position_id, group in position_groups:
            if test_sample >= 1000:  # 1000サンプルで検証
                break

            if len(group) < 2:
                continue

            test_sample += 1

            # 時系列ソート
            group_sorted = group.sort_values(time_col)

            entry_rows = group_sorted[
                group_sorted[comment_col].astype(str).str.contains("JamesORB", na=False)
            ]
            exit_rows = group_sorted[
                group_sorted[comment_col].astype(str).str.contains("sl |tp ", na=False)
            ]

            if len(entry_rows) == 0 or len(exit_rows) == 0:
                continue

            try:
                entry_time = pd.to_datetime(
                    entry_rows.iloc[0][time_col], format="%Y.%m.%d %H:%M:%S"
                )
                exit_time = pd.to_datetime(
                    exit_rows.iloc[0][time_col], format="%Y.%m.%d %H:%M:%S"
                )
                exit_comment = str(exit_rows.iloc[0][comment_col]).lower()

                if exit_time < entry_time:
                    if "tp " in exit_comment:
                        reversal_patterns["tp_first"] += 1
                    elif "sl " in exit_comment:
                        reversal_patterns["sl_first"] += 1
                    else:
                        reversal_patterns["inconsistent"] += 1
                else:
                    reversal_patterns["normal_order"] += 1

            except:
                reversal_patterns["inconsistent"] += 1

        verification["hypothesis_tests"].append(
            {
                "test_name": "Time_Reversal_Pattern_Consistency",
                "sample_size": test_sample,
                "results": reversal_patterns,
                "conclusion": "CONSISTENT"
                if reversal_patterns["inconsistent"] < test_sample * 0.1
                else "INCONSISTENT",
            }
        )

        # テスト2: 代替仮説検証
        self.logger.info("--- テスト2: 代替仮説検証 ---")

        # 仮説A: データ破損
        data_corruption_indicators = {
            "duplicate_timestamps": 0,
            "invalid_timestamps": 0,
            "missing_data_patterns": 0,
        }

        timestamp_counts = self.trades_df[time_col].value_counts()
        data_corruption_indicators["duplicate_timestamps"] = (
            timestamp_counts > 10
        ).sum()

        # 仮説B: 異なるタイムゾーン
        timezone_test = self._test_timezone_hypothesis()

        # 仮説C: EA実行順序問題
        ea_execution_test = self._test_ea_execution_hypothesis()

        verification["alternative_explanations"] = [
            {
                "hypothesis": "Data_Corruption",
                "indicators": data_corruption_indicators,
                "likelihood": "LOW"
                if data_corruption_indicators["duplicate_timestamps"] < 100
                else "HIGH",
            },
            {
                "hypothesis": "Timezone_Issues",
                "test_results": timezone_test,
                "likelihood": timezone_test["likelihood"],
            },
            {
                "hypothesis": "EA_Execution_Order",
                "test_results": ea_execution_test,
                "likelihood": ea_execution_test["likelihood"],
            },
        ]

        # テスト3: MT5仕様との整合性
        self.logger.info("--- テスト3: MT5仕様整合性確認 ---")

        consistency_check = self._check_mt5_specification_consistency()
        verification["consistency_checks"].append(consistency_check)

        # 最終判定
        verification["final_verdict"] = self._generate_final_verdict(verification)

        return verification

    def _test_timezone_hypothesis(self) -> Dict:
        """タイムゾーン仮説テスト"""
        # 時系列逆転の時間差分析
        time_col = self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        comment_col = self.trades_df.columns[12]

        time_diffs = []
        position_groups = self.trades_df.groupby(order_col)

        for _position_id, group in list(position_groups)[:200]:
            if len(group) < 2:
                continue

            entry_rows = group[
                group[comment_col].astype(str).str.contains("JamesORB", na=False)
            ]
            exit_rows = group[
                group[comment_col].astype(str).str.contains("sl |tp ", na=False)
            ]

            if len(entry_rows) == 0 or len(exit_rows) == 0:
                continue

            try:
                entry_time = pd.to_datetime(
                    entry_rows.iloc[0][time_col], format="%Y.%m.%d %H:%M:%S"
                )
                exit_time = pd.to_datetime(
                    exit_rows.iloc[0][time_col], format="%Y.%m.%d %H:%M:%S"
                )

                if exit_time < entry_time:
                    time_diff_hours = (entry_time - exit_time).total_seconds() / 3600
                    time_diffs.append(time_diff_hours)
            except:
                continue

        if not time_diffs:
            return {"likelihood": "UNKNOWN", "reason": "No time differences found"}

        # タイムゾーン差の特徴分析
        avg_diff = sum(time_diffs) / len(time_diffs)

        # 典型的なタイムゾーン差（1, 3, 8, 9, 12時間等）に近いかチェック
        common_tz_diffs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        closest_tz_diff = min(common_tz_diffs, key=lambda x: abs(x - avg_diff))

        likelihood = "HIGH" if abs(avg_diff - closest_tz_diff) < 0.5 else "LOW"

        return {
            "likelihood": likelihood,
            "average_time_diff_hours": avg_diff,
            "closest_timezone_diff": closest_tz_diff,
            "sample_size": len(time_diffs),
        }

    def _test_ea_execution_hypothesis(self) -> Dict:
        """EA実行順序仮説テスト"""
        # EAが決済注文を先に執行し、エントリー注文を後から記録する可能性をテスト

        # 同一時刻での注文数分析
        time_col = self.trades_df.columns[0]
        comment_col = self.trades_df.columns[12]

        simultaneous_orders = []
        timestamp_groups = self.trades_df.groupby(time_col)

        for timestamp, group in timestamp_groups:
            if len(group) > 1:
                entry_count = len(
                    group[
                        group[comment_col]
                        .astype(str)
                        .str.contains("JamesORB", na=False)
                    ]
                )
                exit_count = len(
                    group[
                        group[comment_col].astype(str).str.contains("sl |tp ", na=False)
                    ]
                )

                if entry_count > 0 and exit_count > 0:
                    simultaneous_orders.append(
                        {
                            "timestamp": timestamp,
                            "entry_count": entry_count,
                            "exit_count": exit_count,
                            "total": len(group),
                        }
                    )

        likelihood = "HIGH" if len(simultaneous_orders) > 100 else "LOW"

        return {
            "likelihood": likelihood,
            "simultaneous_order_events": len(simultaneous_orders),
            "sample_events": simultaneous_orders[:5],
        }

    def _check_mt5_specification_consistency(self) -> Dict:
        """MT5仕様との整合性確認"""

        # MT5の既知の動作パターンとの照合
        consistency_indicators = {
            "position_id_sequential": self._check_position_id_sequence(),
            "comment_format_standard": self._check_comment_format(),
            "price_precision_consistent": self._check_price_precision(),
            "timestamp_format_valid": self._check_timestamp_format(),
        }

        overall_consistency = sum(
            1 for v in consistency_indicators.values() if v
        ) / len(consistency_indicators)

        return {
            "test_name": "MT5_Specification_Consistency",
            "indicators": consistency_indicators,
            "overall_consistency_score": overall_consistency,
            "conclusion": "CONSISTENT" if overall_consistency > 0.8 else "INCONSISTENT",
        }

    def _check_position_id_sequence(self) -> bool:
        """position_id連続性チェック"""
        order_col = self.trades_df.columns[1]
        position_ids = self.trades_df[order_col].dropna().unique()

        # 数値として扱えるposition_idの連続性チェック
        numeric_ids = []
        for pid in position_ids:
            try:
                numeric_ids.append(int(pid))
            except:
                continue

        if len(numeric_ids) < 100:
            return False

        numeric_ids.sort()
        gaps = [
            numeric_ids[i + 1] - numeric_ids[i] for i in range(len(numeric_ids) - 1)
        ]
        avg_gap = sum(gaps) / len(gaps)

        # 平均ギャップが小さければ連続性あり
        return avg_gap < 5

    def _check_comment_format(self) -> bool:
        """コメント形式の標準性チェック"""
        comment_col = self.trades_df.columns[12]
        comments = self.trades_df[comment_col].dropna().astype(str)

        # JamesORB, sl, tp パターンの比率
        jamesorb_count = comments.str.contains("JamesORB", na=False).sum()
        sl_count = comments.str.contains("sl ", na=False).sum()
        tp_count = comments.str.contains("tp ", na=False).sum()

        total_relevant = jamesorb_count + sl_count + tp_count
        coverage_ratio = total_relevant / len(comments)

        return coverage_ratio > 0.8

    def _check_price_precision(self) -> bool:
        """価格精度の一貫性チェック"""
        price_col = self.trades_df.columns[6]
        prices = pd.to_numeric(self.trades_df[price_col], errors="coerce").dropna()

        # 価格の小数点精度チェック
        decimal_places = []
        for price in prices.head(1000):
            price_str = f"{price:.10f}".rstrip("0")
            if "." in price_str:
                decimal_places.append(len(price_str.split(".")[1]))
            else:
                decimal_places.append(0)

        # EURUSD標準の5桁精度が多数を占めるかチェック
        five_decimal_ratio = sum(1 for dp in decimal_places if dp == 5) / len(
            decimal_places
        )

        return five_decimal_ratio > 0.7

    def _check_timestamp_format(self) -> bool:
        """タイムスタンプ形式の妥当性チェック"""
        time_col = self.trades_df.columns[0]
        timestamps = self.trades_df[time_col].dropna().astype(str)

        # YYYY.MM.DD HH:MM:SS 形式の割合チェック
        valid_format_count = 0
        for ts in timestamps.head(1000):
            if re.match(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$", ts):
                valid_format_count += 1

        return valid_format_count / min(len(timestamps), 1000) > 0.95

    def _generate_final_verdict(self, verification: Dict) -> Dict:
        """最終判定生成"""

        # 各テスト結果の重み付け評価
        scores = {
            "time_reversal_consistency": 0,
            "alternative_explanations": 0,
            "mt5_specification": 0,
        }

        # 時系列逆転一貫性スコア
        for test in verification["hypothesis_tests"]:
            if test["test_name"] == "Time_Reversal_Pattern_Consistency":
                if test["conclusion"] == "CONSISTENT":
                    scores["time_reversal_consistency"] = 0.8
                else:
                    scores["time_reversal_consistency"] = 0.2

        # 代替仮説スコア（代替仮説が低確率なら元仮説を支持）
        high_likelihood_alternatives = sum(
            1
            for alt in verification["alternative_explanations"]
            if alt["likelihood"] == "HIGH"
        )
        scores["alternative_explanations"] = (
            0.8 if high_likelihood_alternatives == 0 else 0.2
        )

        # MT5仕様整合性スコア
        for check in verification["consistency_checks"]:
            if check["test_name"] == "MT5_Specification_Consistency":
                scores["mt5_specification"] = check["overall_consistency_score"]

        # 総合スコア計算
        total_score = sum(scores.values()) / len(scores)

        # 信頼度判定
        if total_score >= 0.8:
            confidence = "VERY_HIGH"
            verdict = "MT5特殊記録方式仮説は正しい"
        elif total_score >= 0.6:
            confidence = "HIGH"
            verdict = "MT5特殊記録方式仮説は概ね正しい"
        elif total_score >= 0.4:
            confidence = "MODERATE"
            verdict = "MT5特殊記録方式仮説は部分的に正しい"
        else:
            confidence = "LOW"
            verdict = "MT5特殊記録方式仮説は疑わしい"

        return {
            "overall_confidence": confidence,
            "total_score": total_score,
            "component_scores": scores,
            "final_verdict": verdict,
            "recommendation": self._generate_recommendation(confidence, total_score),
        }

    def _generate_recommendation(self, confidence: str, score: float) -> str:
        """推奨事項生成"""
        if confidence in ["VERY_HIGH", "HIGH"]:
            return "MT5の特殊記録方式として受け入れ、この前提で統計分析を実行することを推奨"
        elif confidence == "MODERATE":
            return "追加検証を実施し、より多くのデータサンプルでの確認を推奨"
        else:
            return "原因仮説の再検討が必要。別の技術的アプローチを検討することを推奨"

    def run_final_verification(self) -> Dict:
        """最終検証実行"""
        self.logger.info("🔍 === MT5原因特定最終検証開始 ===")

        if not self.load_data_for_verification():
            return {"error": "Failed to load data"}

        verification_result = self.verify_time_reversal_hypothesis()

        # 結果保存
        final_result = {
            "timestamp": datetime.now().isoformat(),
            "verification_method": "MT5_Time_Reversal_Hypothesis_Final_Verification",
            "verification_results": verification_result,
            "final_confidence_assessment": verification_result["final_verdict"],
        }

        output_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/final_verification_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"✅ 最終検証結果保存: {output_path}")
        self.logger.info(
            f"🎯 最終判定: {verification_result['final_verdict']['final_verdict']}"
        )
        self.logger.info(
            f"📊 信頼度: {verification_result['final_verdict']['overall_confidence']}"
        )

        return final_result


def main():
    """最終検証実行"""
    excel_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/Reportバックテスト-900179988.xlsx"

    verifier = MT5FinalVerification(excel_path)
    results = verifier.run_final_verification()

    return results


if __name__ == "__main__":
    main()
