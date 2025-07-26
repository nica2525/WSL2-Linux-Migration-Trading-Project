#!/usr/bin/env python3
"""
MT5データ破損仮説精密検証システム
目的: MT5データが何らかの破損・不整合を起こしている可能性の徹底検証

検証項目:
1. 重複タイムスタンプの詳細分析
2. タイムスタンプ順序整合性検証
3. データ欠損パターン解析
4. ファイル構造整合性検証
5. 論理的整合性チェック

作成者: Claude（データ破損仮説専門検証担当）
"""

import json
import logging
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd


class MT5DataCorruptionVerification:
    """MT5データ破損仮説精密検証システム"""

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.raw_data = None
        self.trades_df = None

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_data_for_corruption_analysis(self) -> bool:
        """データ破損分析用データ読み込み"""
        try:
            self.raw_data = pd.read_excel(self.excel_path, header=None)

            header_row = 59
            data_start_row = 60

            header = self.raw_data.iloc[header_row].values
            data_rows = self.raw_data.iloc[data_start_row:].values

            self.trades_df = pd.DataFrame(data_rows, columns=header)
            self.trades_df = self.trades_df.dropna(how="all")

            self.logger.info(f"データ破損分析データ読み込み完了: {len(self.trades_df)}件")
            return True

        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            return False

    def analyze_duplicate_timestamps(self) -> Dict:
        """重複タイムスタンプ詳細分析"""
        self.logger.info("=== 重複タイムスタンプ詳細分析 ===")

        analysis = {
            "duplicate_statistics": {},
            "duplicate_patterns": [],
            "temporal_clustering": {},
            "data_integrity_impact": {},
        }

        # 列定義
        time_col = self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        comment_col = self.trades_df.columns[12]

        # タイムスタンプ重複統計
        timestamp_counts = self.trades_df[time_col].value_counts()
        duplicates = timestamp_counts[timestamp_counts > 1]

        analysis["duplicate_statistics"] = {
            "total_timestamps": len(timestamp_counts),
            "unique_timestamps": len(timestamp_counts),
            "duplicate_timestamps": len(duplicates),
            "max_duplicates_per_timestamp": int(duplicates.max())
            if len(duplicates) > 0
            else 0,
            "total_duplicate_records": int(duplicates.sum() - len(duplicates))
            if len(duplicates) > 0
            else 0,
        }

        # 重複パターン詳細分析
        duplicate_patterns = []
        for timestamp, count in duplicates.head(20).items():  # 上位20個の重複タイムスタンプ
            duplicate_records = self.trades_df[self.trades_df[time_col] == timestamp]

            # 同一タイムスタンプ内のデータ分析
            position_ids = duplicate_records[order_col].tolist()
            comments = duplicate_records[comment_col].astype(str).tolist()

            # パターン分類
            jamesorb_count = sum(1 for c in comments if "JamesORB" in str(c))
            sl_count = sum(1 for c in comments if "sl " in str(c))
            tp_count = sum(1 for c in comments if "tp " in str(c))

            duplicate_patterns.append(
                {
                    "timestamp": str(timestamp),
                    "duplicate_count": int(count),
                    "position_ids": position_ids[:10],  # 最初の10個のみ
                    "comment_distribution": {
                        "JamesORB": jamesorb_count,
                        "stop_loss": sl_count,
                        "take_profit": tp_count,
                        "other": len(comments) - jamesorb_count - sl_count - tp_count,
                    },
                    "data_consistency": {
                        "unique_position_ids": len(set(position_ids)),
                        "position_id_range": [min(position_ids), max(position_ids)]
                        if position_ids
                        else [None, None],
                    },
                }
            )

        analysis["duplicate_patterns"] = duplicate_patterns

        # 時系列クラスタリング分析
        if len(duplicates) > 0:
            # 重複タイムスタンプの時系列分布
            duplicate_timestamps = list(duplicates.index)

            try:
                # タイムスタンプをdatetimeに変換
                duplicate_datetimes = [
                    pd.to_datetime(ts, format="%Y.%m.%d %H:%M:%S")
                    for ts in duplicate_timestamps[:100]  # 最初の100個
                ]

                # 時間間隔分析
                if len(duplicate_datetimes) > 1:
                    duplicate_datetimes.sort()
                    intervals = [
                        (
                            duplicate_datetimes[i + 1] - duplicate_datetimes[i]
                        ).total_seconds()
                        / 60
                        for i in range(len(duplicate_datetimes) - 1)
                    ]

                    analysis["temporal_clustering"] = {
                        "avg_interval_minutes": float(np.mean(intervals)),
                        "min_interval_minutes": float(np.min(intervals)),
                        "max_interval_minutes": float(np.max(intervals)),
                        "intervals_under_1min": sum(1 for i in intervals if i < 1),
                        "intervals_under_1hour": sum(1 for i in intervals if i < 60),
                    }
            except Exception as e:
                self.logger.warning(f"時系列クラスタリング分析エラー: {e}")

        self.logger.info(
            f"重複タイムスタンプ: {analysis['duplicate_statistics']['duplicate_timestamps']}個"
        )
        self.logger.info(
            f"最大重複数: {analysis['duplicate_statistics']['max_duplicates_per_timestamp']}"
        )

        return analysis

    def verify_timestamp_sequence_integrity(self) -> Dict:
        """タイムスタンプ順序整合性検証"""
        self.logger.info("=== タイムスタンプ順序整合性検証 ===")

        integrity_analysis = {
            "sequence_violations": [],
            "chronological_gaps": {},
            "reverse_sequences": {},
            "data_order_consistency": {},
        }

        time_col = self.trades_df.columns[0]
        self.trades_df.columns[1]

        # タイムスタンプを datetime に変換
        valid_timestamps = []
        invalid_count = 0

        for idx, timestamp in enumerate(self.trades_df[time_col]):
            try:
                dt = pd.to_datetime(timestamp, format="%Y.%m.%d %H:%M:%S")
                valid_timestamps.append((idx, dt, timestamp))
            except:
                invalid_count += 1
                if invalid_count <= 10:  # 最初の10個の無効タイムスタンプを記録
                    integrity_analysis["sequence_violations"].append(
                        {
                            "row_index": idx,
                            "invalid_timestamp": str(timestamp),
                            "issue": "invalid_format",
                        }
                    )

        # 時系列順序チェック
        if len(valid_timestamps) > 1:
            reverse_sequences = 0
            large_gaps = 0

            for i in range(len(valid_timestamps) - 1):
                current_idx, current_dt, current_ts = valid_timestamps[i]
                next_idx, next_dt, next_ts = valid_timestamps[i + 1]

                # 逆順序チェック
                if next_dt < current_dt:
                    reverse_sequences += 1
                    if len(integrity_analysis["sequence_violations"]) < 50:
                        integrity_analysis["sequence_violations"].append(
                            {
                                "row_indices": [current_idx, next_idx],
                                "timestamps": [str(current_ts), str(next_ts)],
                                "time_difference_hours": (
                                    current_dt - next_dt
                                ).total_seconds()
                                / 3600,
                                "issue": "reverse_sequence",
                            }
                        )

                # 異常な時間ギャップチェック（1週間以上）
                time_gap = abs((next_dt - current_dt).total_seconds() / 3600)
                if time_gap > 168:  # 1週間
                    large_gaps += 1

            integrity_analysis["reverse_sequences"] = {
                "total_reverse_sequences": reverse_sequences,
                "reverse_sequence_rate": reverse_sequences / len(valid_timestamps),
            }

            integrity_analysis["chronological_gaps"] = {
                "large_gaps_count": large_gaps,
                "valid_timestamp_pairs": len(valid_timestamps) - 1,
            }

        self.logger.info(f"無効タイムスタンプ: {invalid_count}個")
        self.logger.info(
            f"逆順序シーケンス: {integrity_analysis.get('reverse_sequences', {}).get('total_reverse_sequences', 0)}個"
        )

        return integrity_analysis

    def analyze_data_missing_patterns(self) -> Dict:
        """データ欠損パターン解析"""
        self.logger.info("=== データ欠損パターン解析 ===")

        missing_analysis = {
            "column_missing_stats": {},
            "missing_patterns": {},
            "data_completeness_score": 0.0,
            "systematic_missing_evidence": {},
        }

        # 列別欠損統計
        total_rows = len(self.trades_df)

        for i, col in enumerate(self.trades_df.columns):
            if pd.isna(col):
                col_name = f"column_{i}_unnamed"
            else:
                col_name = str(col)

            missing_count = self.trades_df.iloc[:, i].isna().sum()
            missing_rate = missing_count / total_rows

            missing_analysis["column_missing_stats"][col_name] = {
                "missing_count": int(missing_count),
                "missing_rate": float(missing_rate),
                "data_type": str(self.trades_df.iloc[:, i].dtype),
                "unique_values": int(self.trades_df.iloc[:, i].nunique()),
            }

        # データ完全性スコア計算
        non_null_rates = [
            1 - stats["missing_rate"]
            for stats in missing_analysis["column_missing_stats"].values()
        ]
        missing_analysis["data_completeness_score"] = float(np.mean(non_null_rates))

        # 系統的欠損パターンの検出
        # 重要列での欠損パターン分析
        important_cols = [0, 1, 6, 12]  # 時刻、注文、価格、コメント

        systematic_missing = {}
        for col_idx in important_cols:
            if col_idx < len(self.trades_df.columns):
                col_data = self.trades_df.iloc[:, col_idx]
                missing_mask = col_data.isna()

                if missing_mask.sum() > 0:
                    # 欠損の連続性チェック
                    missing_runs = []
                    current_run = 0
                    for is_missing in missing_mask:
                        if is_missing:
                            current_run += 1
                        else:
                            if current_run > 0:
                                missing_runs.append(current_run)
                            current_run = 0
                    if current_run > 0:
                        missing_runs.append(current_run)

                    systematic_missing[f"column_{col_idx}"] = {
                        "missing_runs": missing_runs[:10],  # 最初の10個
                        "max_consecutive_missing": max(missing_runs)
                        if missing_runs
                        else 0,
                        "total_missing_blocks": len(missing_runs),
                    }

        missing_analysis["systematic_missing_evidence"] = systematic_missing

        self.logger.info(
            f"データ完全性スコア: {missing_analysis['data_completeness_score']:.3f}"
        )

        return missing_analysis

    def verify_logical_consistency(self) -> Dict:
        """論理的整合性チェック"""
        self.logger.info("=== 論理的整合性チェック ===")

        logical_analysis = {
            "position_id_consistency": {},
            "comment_logic_consistency": {},
            "price_data_consistency": {},
            "temporal_logic_violations": [],
        }

        # 列定義
        self.trades_df.columns[0]
        order_col = self.trades_df.columns[1]
        price_col = self.trades_df.columns[6]
        comment_col = self.trades_df.columns[12]

        # position_id の論理性チェック
        position_ids = pd.to_numeric(
            self.trades_df[order_col], errors="coerce"
        ).dropna()

        logical_analysis["position_id_consistency"] = {
            "sequential_ids": len(position_ids) > 0,
            "id_range": [int(position_ids.min()), int(position_ids.max())]
            if len(position_ids) > 0
            else [None, None],
            "missing_ids_count": 0,
            "duplicate_ids_count": int(position_ids.duplicated().sum()),
        }

        # ID の連続性チェック
        if len(position_ids) > 0:
            id_set = set(position_ids.astype(int))
            expected_range = set(
                range(int(position_ids.min()), int(position_ids.max()) + 1)
            )
            missing_ids = expected_range - id_set
            logical_analysis["position_id_consistency"]["missing_ids_count"] = len(
                missing_ids
            )

        # コメントロジック整合性
        comments = self.trades_df[comment_col].astype(str)
        jamesorb_count = comments.str.contains("JamesORB", na=False).sum()
        sl_count = comments.str.contains("sl ", na=False).sum()
        tp_count = comments.str.contains("tp ", na=False).sum()

        logical_analysis["comment_logic_consistency"] = {
            "jamesorb_entries": int(jamesorb_count),
            "stop_loss_exits": int(sl_count),
            "take_profit_exits": int(tp_count),
            "entry_exit_ratio": float((sl_count + tp_count) / jamesorb_count)
            if jamesorb_count > 0
            else 0,
            "expected_ratio_range": [0.8, 1.2],  # 期待される比率範囲
            "ratio_within_expected": 0.8
            <= ((sl_count + tp_count) / jamesorb_count)
            <= 1.2
            if jamesorb_count > 0
            else False,
        }

        # 価格データ整合性
        prices = pd.to_numeric(self.trades_df[price_col], errors="coerce").dropna()

        if len(prices) > 0:
            logical_analysis["price_data_consistency"] = {
                "valid_price_count": len(prices),
                "price_range": [float(prices.min()), float(prices.max())],
                "zero_prices": int((prices == 0).sum()),
                "negative_prices": int((prices < 0).sum()),
                "abnormal_prices": int(
                    ((prices < 0.5) | (prices > 5.0)).sum()
                ),  # EURUSD の異常値
                "price_precision_issues": int(
                    (prices * 100000 % 1 != 0).sum()
                ),  # 5桁精度チェック
            }

        self.logger.info(
            f"position_id重複: {logical_analysis['position_id_consistency']['duplicate_ids_count']}個"
        )
        self.logger.info(
            f"エントリー/エグジット比率: {logical_analysis['comment_logic_consistency']['entry_exit_ratio']:.2f}"
        )

        return logical_analysis

    def generate_corruption_hypothesis_verdict(
        self,
        duplicate_analysis: Dict,
        integrity_analysis: Dict,
        missing_analysis: Dict,
        logical_analysis: Dict,
    ) -> Dict:
        """データ破損仮説最終判定"""

        verdict = {
            "corruption_evidence_score": 0.0,
            "corruption_indicators": [],
            "data_quality_issues": [],
            "confidence_level": "LOW",
            "final_conclusion": "",
            "severity_assessment": {},
        }

        evidence_scores = []

        # 1. 重複タイムスタンプの深刻度
        if "duplicate_statistics" in duplicate_analysis:
            dup_stats = duplicate_analysis["duplicate_statistics"]
            dup_rate = dup_stats["duplicate_timestamps"] / dup_stats["total_timestamps"]

            if dup_rate > 0.1:  # 10%以上重複
                evidence_scores.append(0.8)
                verdict["corruption_indicators"].append(
                    f"大量の重複タイムスタンプ ({dup_rate:.1%})"
                )
            elif dup_rate > 0.05:
                evidence_scores.append(0.6)
                verdict["corruption_indicators"].append(
                    f"中程度の重複タイムスタンプ ({dup_rate:.1%})"
                )
            else:
                evidence_scores.append(0.2)

        # 2. 時系列順序違反の深刻度
        if "reverse_sequences" in integrity_analysis:
            reverse_rate = integrity_analysis["reverse_sequences"][
                "reverse_sequence_rate"
            ]

            if reverse_rate > 0.3:  # 30%以上逆順
                evidence_scores.append(0.9)
                verdict["corruption_indicators"].append(
                    f"大量の時系列順序違反 ({reverse_rate:.1%})"
                )
            elif reverse_rate > 0.1:
                evidence_scores.append(0.7)
                verdict["corruption_indicators"].append(
                    f"中程度の時系列順序違反 ({reverse_rate:.1%})"
                )
            else:
                evidence_scores.append(0.3)

        # 3. データ完全性の問題
        completeness_score = missing_analysis.get("data_completeness_score", 1.0)
        if completeness_score < 0.8:
            evidence_scores.append(0.7)
            verdict["data_quality_issues"].append(
                f"データ完全性低下 ({completeness_score:.1%})"
            )
        elif completeness_score < 0.95:
            evidence_scores.append(0.4)
            verdict["data_quality_issues"].append(
                f"軽微なデータ欠損 ({completeness_score:.1%})"
            )
        else:
            evidence_scores.append(0.1)

        # 4. 論理的整合性の問題
        if "comment_logic_consistency" in logical_analysis:
            logic = logical_analysis["comment_logic_consistency"]
            if not logic["ratio_within_expected"]:
                evidence_scores.append(0.6)
                verdict["data_quality_issues"].append(
                    f"エントリー/エグジット比率異常 ({logic['entry_exit_ratio']:.2f})"
                )
            else:
                evidence_scores.append(0.2)

        # 総合スコア計算
        if evidence_scores:
            verdict["corruption_evidence_score"] = sum(evidence_scores) / len(
                evidence_scores
            )

        # 信頼度レベル決定
        if verdict["corruption_evidence_score"] >= 0.8:
            verdict["confidence_level"] = "VERY_HIGH"
            verdict["final_conclusion"] = "データ破損仮説は極めて妥当"
        elif verdict["corruption_evidence_score"] >= 0.6:
            verdict["confidence_level"] = "HIGH"
            verdict["final_conclusion"] = "データ破損仮説は妥当"
        elif verdict["corruption_evidence_score"] >= 0.4:
            verdict["confidence_level"] = "MODERATE"
            verdict["final_conclusion"] = "データ破損仮説は部分的に妥当"
        else:
            verdict["confidence_level"] = "LOW"
            verdict["final_conclusion"] = "データ破損仮説は疑わしい"

        # 深刻度評価
        verdict["severity_assessment"] = {
            "data_unusable": verdict["corruption_evidence_score"] > 0.8,
            "requires_cleaning": verdict["corruption_evidence_score"] > 0.6,
            "minor_issues_only": verdict["corruption_evidence_score"] < 0.4,
        }

        return verdict

    def run_comprehensive_corruption_verification(self) -> Dict:
        """包括的データ破損仮説検証実行"""
        self.logger.info("🔧 === MT5データ破損仮説包括検証開始 ===")

        if not self.load_data_for_corruption_analysis():
            return {"error": "Failed to load data"}

        # 検証1: 重複タイムスタンプ分析
        duplicate_analysis = self.analyze_duplicate_timestamps()

        # 検証2: タイムスタンプ順序整合性
        integrity_analysis = self.verify_timestamp_sequence_integrity()

        # 検証3: データ欠損パターン
        missing_analysis = self.analyze_data_missing_patterns()

        # 検証4: 論理的整合性
        logical_analysis = self.verify_logical_consistency()

        # 最終判定
        final_verdict = self.generate_corruption_hypothesis_verdict(
            duplicate_analysis, integrity_analysis, missing_analysis, logical_analysis
        )

        # 結果統合
        comprehensive_result = {
            "timestamp": datetime.now().isoformat(),
            "verification_method": "MT5_Data_Corruption_Hypothesis_Comprehensive_Verification",
            "duplicate_timestamp_analysis": duplicate_analysis,
            "timestamp_integrity_analysis": integrity_analysis,
            "data_missing_analysis": missing_analysis,
            "logical_consistency_analysis": logical_analysis,
            "final_verdict": final_verdict,
        }

        # 結果保存
        output_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/data_corruption_verification.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                comprehensive_result, f, indent=2, ensure_ascii=False, default=str
            )

        self.logger.info(f"✅ データ破損仮説検証結果保存: {output_path}")
        self.logger.info(f"🎯 最終結論: {final_verdict['final_conclusion']}")
        self.logger.info(f"📊 信頼度: {final_verdict['confidence_level']}")
        self.logger.info(f"🔢 破損証拠スコア: {final_verdict['corruption_evidence_score']:.3f}")

        return comprehensive_result


def main():
    """データ破損仮説検証実行"""
    excel_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/Reportバックテスト-900179988.xlsx"

    verifier = MT5DataCorruptionVerification(excel_path)
    results = verifier.run_comprehensive_corruption_verification()

    return results


if __name__ == "__main__":
    main()
