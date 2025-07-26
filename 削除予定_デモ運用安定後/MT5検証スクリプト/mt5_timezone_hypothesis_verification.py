#!/usr/bin/env python3
"""
MT5タイムゾーン仮説精密検証システム
目的: 14.6時間の時間差がタイムゾーン起因かの徹底検証

検証項目:
1. 時間差の分布統計解析
2. 標準タイムゾーン差との照合
3. 季節変動（サマータイム）影響分析
4. 地理的時差パターン解析
5. MT5サーバー時間設定検証

作成者: Claude（タイムゾーン仮説専門検証担当）
"""

import json
import logging
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd


class MT5TimezoneHypothesisVerification:
    """MT5タイムゾーン仮説精密検証システム"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.raw_data = None
        self.trades_df = None

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # 世界主要タイムゾーン差（UTC基準）
        self.major_timezones = {
            "UTC+0": 0,
            "London": 0,  # GMT
            "Frankfurt": 1,  # CET
            "Moscow": 3,  # MSK
            "Dubai": 4,  # GST
            "Tokyo": 9,  # JST
            "Sydney": 10,  # AEST
            "New_York": -5,  # EST
            "Chicago": -6,  # CST
            "Los_Angeles": -8,  # PST
        }

        # MT5主要サーバーとその時差
        self.mt5_server_timezones = {
            "Alpari": 2,  # EET
            "FXDD": -5,  # EST
            "FXTM": 2,  # EET
            "XM": 2,  # EET
            "IC_Markets": 2,  # EET
            "Pepperstone": 2,  # EET
            "OANDA": -5,  # EST (推定)
        }

    def load_data_for_timezone_analysis(self) -> bool:
        """タイムゾーン分析用データ読み込み"""
        try:
            self.raw_data = pd.read_excel(self.excel_path, header=None)

            header_row = 59
            data_start_row = 60

            header = self.raw_data.iloc[header_row].values
            data_rows = self.raw_data.iloc[data_start_row:].values

            self.trades_df = pd.DataFrame(data_rows, columns=header)
            self.trades_df = self.trades_df.dropna(how="all")

            self.logger.info(f"タイムゾーン分析データ読み込み完了: {len(self.trades_df)}件")
            return True

        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            return False

    def analyze_time_difference_distribution(self) -> Dict:
        """時間差分布統計解析"""
        self.logger.info("=== 時間差分布統計解析 ===")

        analysis = {
            "time_differences": [],
            "statistical_summary": {},
            "distribution_patterns": {},
            "timezone_correlation": {},
        }

        # 列定義
        time_col = self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        comment_col = self.trades_df.columns[12]

        # position_idでグループ化し、時間差を収集
        position_groups = self.trades_df.groupby(order_col)

        time_diffs_hours = []
        time_diffs_minutes = []
        reversal_cases = []

        sample_count = 0
        for position_id, group in position_groups:
            if sample_count >= 2000:  # 2000サンプルで詳細分析
                break

            if len(group) < 2:
                continue

            sample_count += 1

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

                # 時間差計算
                time_diff = entry_time - exit_time
                total_seconds = time_diff.total_seconds()

                if total_seconds > 0:  # エントリー > エグジット（逆転）
                    hours_diff = total_seconds / 3600
                    minutes_diff = total_seconds / 60

                    time_diffs_hours.append(hours_diff)
                    time_diffs_minutes.append(minutes_diff)

                    reversal_cases.append(
                        {
                            "position_id": position_id,
                            "entry_time": entry_time,
                            "exit_time": exit_time,
                            "hours_diff": hours_diff,
                            "minutes_diff": minutes_diff,
                            "exit_comment": str(exit_rows.iloc[0][comment_col]),
                        }
                    )

            except Exception:
                continue

        # 統計サマリー
        if time_diffs_hours:
            analysis["statistical_summary"] = {
                "sample_size": len(time_diffs_hours),
                "mean_hours": float(np.mean(time_diffs_hours)),
                "median_hours": float(np.median(time_diffs_hours)),
                "std_hours": float(np.std(time_diffs_hours)),
                "min_hours": float(np.min(time_diffs_hours)),
                "max_hours": float(np.max(time_diffs_hours)),
                "percentiles": {
                    "25th": float(np.percentile(time_diffs_hours, 25)),
                    "75th": float(np.percentile(time_diffs_hours, 75)),
                    "90th": float(np.percentile(time_diffs_hours, 90)),
                    "95th": float(np.percentile(time_diffs_hours, 95)),
                },
            }

            # 分布パターン分析
            # 1時間刻みでの分布
            hour_bins = np.arange(0, max(time_diffs_hours) + 1, 1)
            hour_distribution, _ = np.histogram(time_diffs_hours, bins=hour_bins)

            analysis["distribution_patterns"] = {
                "hourly_distribution": {
                    f"{int(hour_bins[i])}-{int(hour_bins[i+1])}h": int(count)
                    for i, count in enumerate(hour_distribution)
                },
                "peak_hours": [
                    int(hour_bins[i])
                    for i, count in enumerate(hour_distribution)
                    if count == max(hour_distribution)
                ],
            }

        analysis["time_differences"] = reversal_cases[:100]  # サンプル保存

        self.logger.info(f"時間差サンプル数: {len(time_diffs_hours)}")
        if time_diffs_hours:
            self.logger.info(f"平均時間差: {np.mean(time_diffs_hours):.2f}時間")
            self.logger.info(f"中央値: {np.median(time_diffs_hours):.2f}時間")
            self.logger.info(f"標準偏差: {np.std(time_diffs_hours):.2f}時間")

        return analysis

    def verify_standard_timezone_correlation(self, time_analysis: Dict) -> Dict:
        """標準タイムゾーン差との相関検証"""
        self.logger.info("=== 標準タイムゾーン差相関検証 ===")

        if not time_analysis["statistical_summary"]:
            return {"error": "No time difference data available"}

        mean_diff = time_analysis["statistical_summary"]["mean_hours"]
        std_diff = time_analysis["statistical_summary"]["std_hours"]

        correlation_analysis = {
            "timezone_matches": [],
            "best_matches": [],
            "seasonal_variation_test": {},
            "server_timezone_hypothesis": {},
        }

        # 主要タイムゾーン差との比較
        for tz_name, tz_offset in self.major_timezones.items():
            # 日本時間（JST = UTC+9）との差を計算
            jst_offset = 9
            expected_diff = abs(jst_offset - tz_offset)

            # サマータイム考慮（±1時間）
            matches = []
            for seasonal_adjust in [0, 1, -1]:  # 標準時、サマータイム、逆サマータイム
                adjusted_diff = expected_diff + seasonal_adjust

                if abs(mean_diff - adjusted_diff) <= 2 * std_diff:  # 2σ内なら一致
                    confidence = max(
                        0, 1 - abs(mean_diff - adjusted_diff) / (2 * std_diff)
                    )
                    matches.append(
                        {
                            "timezone": tz_name,
                            "expected_diff": adjusted_diff,
                            "actual_diff": mean_diff,
                            "difference": abs(mean_diff - adjusted_diff),
                            "confidence": confidence,
                            "seasonal_adjustment": seasonal_adjust,
                        }
                    )

            if matches:
                correlation_analysis["timezone_matches"].extend(matches)

        # MT5サーバータイムゾーンとの比較
        for server_name, server_tz in self.mt5_server_timezones.items():
            jst_offset = 9
            expected_diff = abs(jst_offset - server_tz)

            if abs(mean_diff - expected_diff) <= 2 * std_diff:
                correlation_analysis["server_timezone_hypothesis"][server_name] = {
                    "expected_diff": expected_diff,
                    "actual_diff": mean_diff,
                    "match_probability": max(
                        0, 1 - abs(mean_diff - expected_diff) / (2 * std_diff)
                    ),
                }

        # ベストマッチを特定
        all_matches = correlation_analysis["timezone_matches"]
        if all_matches:
            correlation_analysis["best_matches"] = sorted(
                all_matches, key=lambda x: x["difference"]
            )[:5]

        return correlation_analysis

    def analyze_seasonal_patterns(self, time_analysis: Dict) -> Dict:
        """季節変動（サマータイム）パターン分析"""
        self.logger.info("=== 季節変動パターン分析 ===")

        seasonal_analysis = {
            "monthly_patterns": {},
            "daylight_saving_evidence": {},
            "seasonal_consistency": {},
        }

        # 月別時間差分析
        if "time_differences" in time_analysis:
            monthly_diffs = {}

            for case in time_analysis["time_differences"]:
                try:
                    entry_time = pd.to_datetime(case["entry_time"])
                    month = entry_time.month

                    if month not in monthly_diffs:
                        monthly_diffs[month] = []

                    monthly_diffs[month].append(case["hours_diff"])
                except:
                    continue

            # 月別統計
            for month, diffs in monthly_diffs.items():
                if len(diffs) >= 5:  # 最低5サンプル
                    seasonal_analysis["monthly_patterns"][f"month_{month}"] = {
                        "sample_size": len(diffs),
                        "mean_hours": float(np.mean(diffs)),
                        "std_hours": float(np.std(diffs)),
                        "median_hours": float(np.median(diffs)),
                    }

            # サマータイム期間の検証
            # 一般的なサマータイム期間: 3月最終日曜日 - 10月最終日曜日（ヨーロッパ）
            summer_months = [4, 5, 6, 7, 8, 9]  # 4-9月をサマータイム期間として仮定
            winter_months = [1, 2, 3, 10, 11, 12]

            summer_diffs = []
            winter_diffs = []

            for month, stats in seasonal_analysis["monthly_patterns"].items():
                month_num = int(month.split("_")[1])
                if month_num in summer_months:
                    summer_diffs.append(stats["mean_hours"])
                elif month_num in winter_months:
                    winter_diffs.append(stats["mean_hours"])

            if summer_diffs and winter_diffs:
                seasonal_analysis["daylight_saving_evidence"] = {
                    "summer_avg_hours": float(np.mean(summer_diffs)),
                    "winter_avg_hours": float(np.mean(winter_diffs)),
                    "seasonal_difference": float(
                        np.mean(summer_diffs) - np.mean(winter_diffs)
                    ),
                    "dst_hypothesis": "SUPPORTED"
                    if abs(np.mean(summer_diffs) - np.mean(winter_diffs)) >= 0.8
                    else "NOT_SUPPORTED",
                }

        return seasonal_analysis

    def verify_geographical_time_patterns(self, time_analysis: Dict) -> Dict:
        """地理的時差パターン検証"""
        self.logger.info("=== 地理的時差パターン検証 ===")

        geo_analysis = {
            "market_session_analysis": {},
            "trading_hours_correlation": {},
            "regional_patterns": {},
        }

        # 主要市場セッション時間との相関分析
        market_sessions = {
            "Tokyo": {"start": 0, "end": 9, "timezone_offset": 0},  # JST基準
            "London": {"start": 16, "end": 1, "timezone_offset": -9},  # GMT vs JST
            "New_York": {"start": 22, "end": 7, "timezone_offset": -14},  # EST vs JST
            "Sydney": {"start": 21, "end": 6, "timezone_offset": 1},  # AEST vs JST
        }

        if "time_differences" in time_analysis and time_analysis["time_differences"]:
            for session_name, session_info in market_sessions.items():
                session_time_diffs = []

                for case in time_analysis["time_differences"]:
                    try:
                        entry_time = pd.to_datetime(case["entry_time"])
                        entry_hour = entry_time.hour

                        # セッション時間内かチェック
                        session_start = session_info["start"]
                        session_end = session_info["end"]

                        in_session = False
                        if session_start <= session_end:
                            in_session = session_start <= entry_hour <= session_end
                        else:  # 日をまたぐセッション
                            in_session = (
                                entry_hour >= session_start or entry_hour <= session_end
                            )

                        if in_session:
                            session_time_diffs.append(case["hours_diff"])

                    except:
                        continue

                if len(session_time_diffs) >= 3:
                    expected_tz_diff = abs(session_info["timezone_offset"])
                    actual_avg_diff = np.mean(session_time_diffs)

                    geo_analysis["market_session_analysis"][session_name] = {
                        "sample_size": len(session_time_diffs),
                        "avg_time_diff": float(actual_avg_diff),
                        "expected_tz_diff": expected_tz_diff,
                        "correlation_strength": max(
                            0,
                            1
                            - abs(actual_avg_diff - expected_tz_diff)
                            / max(actual_avg_diff, expected_tz_diff),
                        ),
                    }

        return geo_analysis

    def generate_timezone_hypothesis_verdict(
        self,
        time_analysis: Dict,
        tz_correlation: Dict,
        seasonal_analysis: Dict,
        geo_analysis: Dict,
    ) -> Dict:
        """タイムゾーン仮説最終判定"""

        verdict = {
            "hypothesis_strength": 0.0,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "confidence_level": "LOW",
            "final_conclusion": "",
            "alternative_explanations": [],
        }

        evidence_scores = []

        # 1. 標準タイムゾーン差との一致度
        if "best_matches" in tz_correlation and tz_correlation["best_matches"]:
            best_match = tz_correlation["best_matches"][0]
            if best_match["confidence"] > 0.7:
                evidence_scores.append(0.8)
                verdict["supporting_evidence"].append(
                    f"標準タイムゾーン'{best_match['timezone']}'と高い一致度 ({best_match['confidence']:.2f})"
                )
            elif best_match["confidence"] > 0.4:
                evidence_scores.append(0.5)
                verdict["supporting_evidence"].append(
                    f"標準タイムゾーン'{best_match['timezone']}'と中程度の一致度 ({best_match['confidence']:.2f})"
                )
            else:
                evidence_scores.append(0.2)
                verdict["contradicting_evidence"].append(
                    f"標準タイムゾーンとの一致度が低い ({best_match['confidence']:.2f})"
                )

        # 2. 季節変動（サマータイム）の証拠
        if (
            "daylight_saving_evidence" in seasonal_analysis
            and seasonal_analysis["daylight_saving_evidence"]
        ):
            dst_evidence = seasonal_analysis["daylight_saving_evidence"]
            if dst_evidence.get("dst_hypothesis") == "SUPPORTED":
                evidence_scores.append(0.7)
                verdict["supporting_evidence"].append(
                    f"サマータイム変動を確認 (夏冬差: {dst_evidence['seasonal_difference']:.2f}時間)"
                )
            else:
                evidence_scores.append(0.3)
                verdict["contradicting_evidence"].append(
                    f"サマータイム変動が不明確 (夏冬差: {dst_evidence.get('seasonal_difference', 0):.2f}時間)"
                )

        # 3. 時間差の一貫性
        if "statistical_summary" in time_analysis:
            stats = time_analysis["statistical_summary"]
            cv = (
                stats["std_hours"] / stats["mean_hours"]
                if stats["mean_hours"] > 0
                else 1
            )

            if cv < 0.2:  # 変動係数20%未満なら一貫性高
                evidence_scores.append(0.8)
                verdict["supporting_evidence"].append(f"時間差の一貫性が高い (変動係数: {cv:.2f})")
            elif cv < 0.5:
                evidence_scores.append(0.5)
                verdict["supporting_evidence"].append(f"時間差の一貫性が中程度 (変動係数: {cv:.2f})")
            else:
                evidence_scores.append(0.2)
                verdict["contradicting_evidence"].append(
                    f"時間差のばらつきが大きい (変動係数: {cv:.2f})"
                )

        # 総合スコア計算
        if evidence_scores:
            verdict["hypothesis_strength"] = sum(evidence_scores) / len(evidence_scores)

        # 信頼度レベル決定
        if verdict["hypothesis_strength"] >= 0.8:
            verdict["confidence_level"] = "VERY_HIGH"
            verdict["final_conclusion"] = "タイムゾーン仮説は極めて妥当"
        elif verdict["hypothesis_strength"] >= 0.6:
            verdict["confidence_level"] = "HIGH"
            verdict["final_conclusion"] = "タイムゾーン仮説は妥当"
        elif verdict["hypothesis_strength"] >= 0.4:
            verdict["confidence_level"] = "MODERATE"
            verdict["final_conclusion"] = "タイムゾーン仮説は部分的に妥当"
        else:
            verdict["confidence_level"] = "LOW"
            verdict["final_conclusion"] = "タイムゾーン仮説は疑わしい"

        return verdict

    def run_comprehensive_timezone_verification(self) -> Dict:
        """包括的タイムゾーン仮説検証実行"""
        self.logger.info("🕐 === MT5タイムゾーン仮説包括検証開始 ===")

        if not self.load_data_for_timezone_analysis():
            return {"error": "Failed to load data"}

        # 検証1: 時間差分布統計解析
        time_analysis = self.analyze_time_difference_distribution()

        # 検証2: 標準タイムゾーン差相関検証
        tz_correlation = self.verify_standard_timezone_correlation(time_analysis)

        # 検証3: 季節変動パターン分析
        seasonal_analysis = self.analyze_seasonal_patterns(time_analysis)

        # 検証4: 地理的時差パターン検証
        geo_analysis = self.verify_geographical_time_patterns(time_analysis)

        # 最終判定
        final_verdict = self.generate_timezone_hypothesis_verdict(
            time_analysis, tz_correlation, seasonal_analysis, geo_analysis
        )

        # 結果統合
        comprehensive_result = {
            "timestamp": datetime.now().isoformat(),
            "verification_method": "MT5_Timezone_Hypothesis_Comprehensive_Verification",
            "time_difference_analysis": time_analysis,
            "timezone_correlation_analysis": tz_correlation,
            "seasonal_pattern_analysis": seasonal_analysis,
            "geographical_pattern_analysis": geo_analysis,
            "final_verdict": final_verdict,
        }

        # 結果保存
        output_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/timezone_hypothesis_verification.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                comprehensive_result, f, indent=2, ensure_ascii=False, default=str
            )

        self.logger.info(f"✅ タイムゾーン仮説検証結果保存: {output_path}")
        self.logger.info(f"🎯 最終結論: {final_verdict['final_conclusion']}")
        self.logger.info(f"📊 信頼度: {final_verdict['confidence_level']}")
        self.logger.info(f"🔢 仮説強度: {final_verdict['hypothesis_strength']:.3f}")

        return comprehensive_result


def main():
    """タイムゾーン仮説検証実行"""
    excel_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/Reportバックテスト-900179988.xlsx"

    verifier = MT5TimezoneHypothesisVerification(excel_path)
    results = verifier.run_comprehensive_timezone_verification()

    return results


if __name__ == "__main__":
    main()
