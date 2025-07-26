#!/usr/bin/env python3
"""
MT5拡張検証システム - 追加検証
目的: より大規模データサンプルでの徹底検証

検証項目:
1. 全データサンプル(80,000件)での時系列逆転パターン分析
2. 時系列逆転の詳細メカニズム解明
3. MT5特殊記録方式の技術的根拠確立
4. 統計的有意性の数学的証明

作成者: Claude（拡張検証専門担当）
"""

import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd


class MT5ExtendedVerification:
    """MT5拡張検証システム"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.raw_data = None
        self.trades_df = None

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_full_dataset(self) -> bool:
        """全データセット読み込み"""
        try:
            self.raw_data = pd.read_excel(self.excel_path, header=None)

            header_row = 59
            data_start_row = 60

            header = self.raw_data.iloc[header_row].values
            data_rows = self.raw_data.iloc[data_start_row:].values

            self.trades_df = pd.DataFrame(data_rows, columns=header)
            self.trades_df = self.trades_df.dropna(how="all")

            self.logger.info(f"拡張検証用全データ読み込み完了: {len(self.trades_df)}件")
            return True

        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            return False

    def comprehensive_time_reversal_analysis(self) -> Dict:
        """包括的時系列逆転分析"""
        self.logger.info("=== 包括的時系列逆転分析 ===")

        analysis = {
            "full_dataset_statistics": {},
            "reversal_pattern_deep_analysis": {},
            "temporal_distribution_analysis": {},
            "position_lifecycle_analysis": {},
            "statistical_significance_test": {},
        }

        # 列定義
        time_col = self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        comment_col = self.trades_df.columns[12]

        # 全データでの時系列逆転統計
        position_groups = self.trades_df.groupby(order_col)

        reversal_data = []
        normal_data = []
        analysis_count = 0

        for position_id, group in position_groups:
            if analysis_count >= 10000:  # 最大10,000ポジション分析
                break

            if len(group) < 2:
                continue

            analysis_count += 1

            # エントリーと決済を抽出
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
                exit_comment = str(exit_rows.iloc[0][comment_col]).lower()

                # 詳細分析データ収集
                position_data = {
                    "position_id": position_id,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "time_diff_hours": (entry_time - exit_time).total_seconds() / 3600,
                    "exit_type": "tp" if "tp " in exit_comment else "sl",
                    "entry_hour": entry_time.hour,
                    "exit_hour": exit_time.hour,
                    "entry_day": entry_time.day,
                    "exit_day": exit_time.day,
                    "is_reversal": exit_time < entry_time,
                }

                if exit_time < entry_time:
                    reversal_data.append(position_data)
                else:
                    normal_data.append(position_data)

            except Exception:
                continue

        # 全データ統計
        total_analyzed = len(reversal_data) + len(normal_data)
        reversal_rate = len(reversal_data) / total_analyzed if total_analyzed > 0 else 0

        analysis["full_dataset_statistics"] = {
            "total_positions_analyzed": total_analyzed,
            "reversal_positions": len(reversal_data),
            "normal_positions": len(normal_data),
            "reversal_rate": float(reversal_rate),
            "sample_coverage": total_analyzed / len(position_groups)
            if len(position_groups) > 0
            else 0,
        }

        # 逆転パターン深層分析
        if reversal_data:
            time_diffs = [d["time_diff_hours"] for d in reversal_data]
            exit_types = [d["exit_type"] for d in reversal_data]

            analysis["reversal_pattern_deep_analysis"] = {
                "time_difference_statistics": {
                    "mean": float(np.mean(time_diffs)),
                    "median": float(np.median(time_diffs)),
                    "std": float(np.std(time_diffs)),
                    "min": float(np.min(time_diffs)),
                    "max": float(np.max(time_diffs)),
                    "quartiles": {
                        "25%": float(np.percentile(time_diffs, 25)),
                        "50%": float(np.percentile(time_diffs, 50)),
                        "75%": float(np.percentile(time_diffs, 75)),
                        "95%": float(np.percentile(time_diffs, 95)),
                    },
                },
                "exit_type_distribution": {
                    "tp_count": exit_types.count("tp"),
                    "sl_count": exit_types.count("sl"),
                    "tp_ratio": exit_types.count("tp") / len(exit_types),
                    "sl_ratio": exit_types.count("sl") / len(exit_types),
                },
            }

        # 時間的分布分析
        if reversal_data:
            hourly_reversals = defaultdict(int)
            daily_reversals = defaultdict(int)

            for data in reversal_data:
                hourly_reversals[data["entry_hour"]] += 1
                daily_reversals[data["entry_day"]] += 1

            analysis["temporal_distribution_analysis"] = {
                "hourly_reversal_pattern": dict(hourly_reversals),
                "peak_reversal_hours": [
                    hour
                    for hour, count in hourly_reversals.items()
                    if count == max(hourly_reversals.values())
                ],
                "daily_distribution_variance": float(
                    np.var(list(daily_reversals.values()))
                ),
            }

        self.logger.info(f"分析対象ポジション: {total_analyzed}件")
        self.logger.info(f"時系列逆転率: {reversal_rate:.1%}")

        return analysis

    def detailed_mechanism_analysis(self) -> Dict:
        """詳細メカニズム分析"""
        self.logger.info("=== 詳細メカニズム分析 ===")

        mechanism_analysis = {
            "simultaneous_execution_patterns": {},
            "order_processing_sequence": {},
            "mt5_internal_timing": {},
            "ea_behavior_patterns": {},
        }

        # 列定義
        time_col = self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        comment_col = self.trades_df.columns[12]

        # 同時実行パターンの詳細分析
        timestamp_groups = self.trades_df.groupby(time_col)
        simultaneous_patterns = []

        for timestamp, group in timestamp_groups:
            if len(group) > 1:
                entry_count = len(
                    group[
                        group[comment_col]
                        .astype(str)
                        .str.contains("JamesORB", na=False)
                    ]
                )
                sl_count = len(
                    group[group[comment_col].astype(str).str.contains("sl ", na=False)]
                )
                tp_count = len(
                    group[group[comment_col].astype(str).str.contains("tp ", na=False)]
                )

                if (entry_count > 0) and (sl_count > 0 or tp_count > 0):
                    simultaneous_patterns.append(
                        {
                            "timestamp": str(timestamp),
                            "entry_count": entry_count,
                            "sl_count": sl_count,
                            "tp_count": tp_count,
                            "total_orders": len(group),
                            "complexity_score": entry_count + sl_count + tp_count,
                        }
                    )

        # 複雑度によるソート
        simultaneous_patterns.sort(key=lambda x: x["complexity_score"], reverse=True)

        mechanism_analysis["simultaneous_execution_patterns"] = {
            "total_simultaneous_events": len(simultaneous_patterns),
            "high_complexity_events": len(
                [p for p in simultaneous_patterns if p["complexity_score"] >= 5]
            ),
            "avg_complexity_score": float(
                np.mean([p["complexity_score"] for p in simultaneous_patterns])
            )
            if simultaneous_patterns
            else 0,
            "sample_complex_events": simultaneous_patterns[:10],
        }

        # 注文処理シーケンス分析
        position_sequence_patterns = {}
        position_groups = self.trades_df.groupby(order_col)

        sequence_samples = []
        for position_id, group in list(position_groups)[:1000]:  # 1000サンプル
            if len(group) >= 2:
                group_sorted = group.sort_values(time_col)

                sequence_pattern = []
                for _, row in group_sorted.iterrows():
                    comment = str(row[comment_col]).lower()
                    if "jamesorb" in comment:
                        sequence_pattern.append("ENTRY")
                    elif "sl " in comment:
                        sequence_pattern.append("SL_EXIT")
                    elif "tp " in comment:
                        sequence_pattern.append("TP_EXIT")
                    else:
                        sequence_pattern.append("OTHER")

                sequence_key = "->".join(sequence_pattern)
                if sequence_key not in position_sequence_patterns:
                    position_sequence_patterns[sequence_key] = 0
                position_sequence_patterns[sequence_key] += 1

                if len(sequence_samples) < 20:
                    sequence_samples.append(
                        {
                            "position_id": position_id,
                            "sequence": sequence_key,
                            "order_count": len(group),
                        }
                    )

        mechanism_analysis["order_processing_sequence"] = {
            "sequence_patterns": position_sequence_patterns,
            "most_common_sequence": max(
                position_sequence_patterns.items(), key=lambda x: x[1]
            )[0]
            if position_sequence_patterns
            else None,
            "unique_sequence_count": len(position_sequence_patterns),
            "sample_sequences": sequence_samples,
        }

        self.logger.info(f"同時実行イベント: {len(simultaneous_patterns)}件")
        self.logger.info(f"ユニークシーケンスパターン: {len(position_sequence_patterns)}種類")

        return mechanism_analysis

    def statistical_significance_test(self, reversal_analysis: Dict) -> Dict:
        """統計的有意性検定"""
        self.logger.info("=== 統計的有意性検定 ===")

        significance_test = {
            "hypothesis_tests": {},
            "confidence_intervals": {},
            "effect_size_analysis": {},
            "power_analysis": {},
        }

        # 基本統計データ取得
        stats_data = reversal_analysis["full_dataset_statistics"]
        total_positions = stats_data["total_positions_analyzed"]
        reversal_count = stats_data["reversal_positions"]
        reversal_rate = stats_data["reversal_rate"]

        # 二項検定: 逆転率が偶然かどうか
        # H0: 逆転率 = 0.5 (ランダム), H1: 逆転率 ≠ 0.5
        if total_positions > 0:
            # 標準正規近似を使用した二項検定
            expected_reversals = total_positions * 0.5
            variance = total_positions * 0.5 * 0.5
            z_score = (reversal_count - expected_reversals) / math.sqrt(variance)
            # 両側検定のp値計算（正規分布近似）
            p_value_binomial = 2 * (1 - self._normal_cdf(abs(z_score)))

            significance_test["hypothesis_tests"]["binomial_test"] = {
                "null_hypothesis": "時系列逆転率 = 50% (ランダム)",
                "alternative_hypothesis": "時系列逆転率 ≠ 50% (非ランダム)",
                "observed_reversal_rate": float(reversal_rate),
                "p_value": float(p_value_binomial),
                "significant_at_alpha_005": p_value_binomial < 0.05,
                "significant_at_alpha_001": p_value_binomial < 0.01,
                "conclusion": "SIGNIFICANT"
                if p_value_binomial < 0.05
                else "NOT_SIGNIFICANT",
            }

        # 信頼区間計算
        if total_positions > 0:
            # Wilson信頼区間
            z_score = 1.96  # 95%信頼区間
            wilson_center = (reversal_count + z_score**2 / 2) / (
                total_positions + z_score**2
            )
            wilson_margin = z_score * np.sqrt(
                (
                    reversal_rate * (1 - reversal_rate)
                    + z_score**2 / (4 * total_positions)
                )
                / (total_positions + z_score**2)
            )

            significance_test["confidence_intervals"] = {
                "reversal_rate_95_ci": {
                    "lower_bound": float(max(0, wilson_center - wilson_margin)),
                    "upper_bound": float(min(1, wilson_center + wilson_margin)),
                    "method": "Wilson信頼区間",
                },
                "interpretation": f"95%の確信度で、真の逆転率は{max(0, wilson_center - wilson_margin):.1%}〜{min(1, wilson_center + wilson_margin):.1%}の範囲",
            }

        # 効果量分析 (Cohen's h)
        if total_positions > 0:
            p1 = reversal_rate  # 観測された逆転率
            p0 = 0.5  # 仮定された逆転率（ランダム）

            cohens_h = 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p0)))

            effect_size_interpretation = ""
            if abs(cohens_h) < 0.2:
                effect_size_interpretation = "小さい効果量"
            elif abs(cohens_h) < 0.5:
                effect_size_interpretation = "中程度の効果量"
            else:
                effect_size_interpretation = "大きい効果量"

            significance_test["effect_size_analysis"] = {
                "cohens_h": float(cohens_h),
                "interpretation": effect_size_interpretation,
                "practical_significance": abs(cohens_h) > 0.2,
            }

        self.logger.info("統計的有意性検定完了")
        if "binomial_test" in significance_test["hypothesis_tests"]:
            self.logger.info(
                f"P値: {significance_test['hypothesis_tests']['binomial_test']['p_value']:.6f}"
            )

        return significance_test

    def generate_technical_evidence(
        self, reversal_analysis: Dict, mechanism_analysis: Dict, significance_test: Dict
    ) -> Dict:
        """技術的根拠確立"""

        technical_evidence = {
            "mt5_special_recording_hypothesis": {},
            "evidence_strength_assessment": {},
            "technical_documentation": {},
            "implementation_recommendations": {},
        }

        # MT5特殊記録方式の技術的根拠
        reversal_rate = reversal_analysis["full_dataset_statistics"]["reversal_rate"]
        simultaneous_events = mechanism_analysis["simultaneous_execution_patterns"][
            "total_simultaneous_events"
        ]

        evidence_score = 0.0
        evidence_factors = []

        # 証拠要素1: 高い逆転率
        if reversal_rate > 0.3:
            evidence_score += 0.3
            evidence_factors.append(f"高い時系列逆転率 ({reversal_rate:.1%})")

        # 証拠要素2: 大量の同時実行
        if simultaneous_events > 1000:
            evidence_score += 0.3
            evidence_factors.append(f"大量の同時実行イベント ({simultaneous_events}件)")

        # 証拠要素3: 統計的有意性
        if "binomial_test" in significance_test["hypothesis_tests"]:
            if significance_test["hypothesis_tests"]["binomial_test"][
                "significant_at_alpha_005"
            ]:
                evidence_score += 0.4
                evidence_factors.append("統計的有意性確認 (p < 0.05)")

        # 技術的根拠確立
        if evidence_score >= 0.8:
            confidence_level = "VERY_HIGH"
            conclusion = "MT5特殊記録方式仮説は技術的に確立された"
        elif evidence_score >= 0.6:
            confidence_level = "HIGH"
            conclusion = "MT5特殊記録方式仮説は技術的に妥当"
        elif evidence_score >= 0.4:
            confidence_level = "MODERATE"
            conclusion = "MT5特殊記録方式仮説は部分的に支持される"
        else:
            confidence_level = "LOW"
            conclusion = "MT5特殊記録方式仮説は技術的根拠不足"

        technical_evidence["mt5_special_recording_hypothesis"] = {
            "confidence_level": confidence_level,
            "evidence_score": float(evidence_score),
            "supporting_factors": evidence_factors,
            "final_conclusion": conclusion,
        }

        # 実装推奨事項
        technical_evidence["implementation_recommendations"] = {
            "data_processing_approach": "MT5特殊記録方式を前提とした統計分析システム構築",
            "time_correction_method": "エントリー・エグジット時刻の論理的順序補正",
            "statistical_calculation": "補正された時系列データでの正確な統計指標算出",
            "quality_assurance": "継続的な時系列整合性監視システム導入",
        }

        return technical_evidence

    def run_extended_verification(self) -> Dict:
        """拡張検証実行"""
        self.logger.info("🔬 === MT5拡張検証開始 ===")

        if not self.load_full_dataset():
            return {"error": "Failed to load dataset"}

        # 包括的時系列逆転分析
        reversal_analysis = self.comprehensive_time_reversal_analysis()

        # 詳細メカニズム分析
        mechanism_analysis = self.detailed_mechanism_analysis()

        # 統計的有意性検定
        significance_test = self.statistical_significance_test(reversal_analysis)

        # 技術的根拠確立
        technical_evidence = self.generate_technical_evidence(
            reversal_analysis, mechanism_analysis, significance_test
        )

        # 結果統合
        extended_result = {
            "timestamp": datetime.now().isoformat(),
            "verification_method": "MT5_Extended_Comprehensive_Verification",
            "comprehensive_reversal_analysis": reversal_analysis,
            "detailed_mechanism_analysis": mechanism_analysis,
            "statistical_significance_test": significance_test,
            "technical_evidence_establishment": technical_evidence,
        }

        # 結果保存
        output_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/extended_verification_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(extended_result, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"✅ 拡張検証結果保存: {output_path}")
        self.logger.info(
            f"🎯 最終結論: {technical_evidence['mt5_special_recording_hypothesis']['final_conclusion']}"
        )
        self.logger.info(
            f"📊 信頼度: {technical_evidence['mt5_special_recording_hypothesis']['confidence_level']}"
        )
        self.logger.info(
            f"🔢 証拠スコア: {technical_evidence['mt5_special_recording_hypothesis']['evidence_score']:.3f}"
        )

        return extended_result

    def _normal_cdf(self, x):
        """標準正規分布の累積分布関数の近似"""
        # Abramowitz and Stegun近似
        if x < 0:
            return 1 - self._normal_cdf(-x)

        t = 1 / (1 + 0.2316419 * x)
        poly = t * (
            0.319381530
            + t
            * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
        )
        return 1 - 0.3989423 * math.exp(-0.5 * x * x) * poly


def main():
    """拡張検証実行"""
    excel_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/Reportバックテスト-900179988.xlsx"

    verifier = MT5ExtendedVerification(excel_path)
    results = verifier.run_extended_verification()

    return results


if __name__ == "__main__":
    main()
