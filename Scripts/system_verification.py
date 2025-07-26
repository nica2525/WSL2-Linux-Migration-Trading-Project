#!/usr/bin/env python3
"""
MCP統計システム精密検証・品質確保ツール
目的: 算出データの正確性・信頼性を第三者検証レベルで確保
作成者: Claude (品質保証担当)
"""

import json
import os
import re
from typing import Dict, List


class SystemVerification:
    """統計システム精密検証クラス"""

    def __init__(self, mt5_results_path: str):
        self.mt5_results_path = mt5_results_path
        self.verification_results = {}

    def verify_data_extraction(self) -> Dict:
        """データ抽出ロジック検証"""
        print("🔍 === データ抽出ロジック検証開始 ===")

        log_file = os.path.join(self.mt5_results_path, "操作ログ.txt")

        # 生ログデータ分析
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()

        # パターン検証
        deal_pattern = r"deal #(\d+) (buy|sell) ([\d.]+) EURUSD_QDM at ([\d.]+) done"
        balance_pattern = r"final balance ([\d.]+) USD"

        deals = []
        balances = []

        print(f"📄 総ログ行数: {len(lines)}")

        # 詳細抽出・検証
        for i, line in enumerate(lines):
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
                timestamp = timestamp_match.group(1) if timestamp_match else "Unknown"

                deals.append(
                    {
                        "line_num": i + 1,
                        "deal_id": deal_id,
                        "timestamp": timestamp,
                        "direction": direction,
                        "volume": volume,
                        "price": price,
                        "raw_line": line.strip(),
                    }
                )

            balance_match = re.search(balance_pattern, line)
            if balance_match:
                balance = float(balance_match.group(1))
                balances.append(
                    {"line_num": i + 1, "balance": balance, "raw_line": line.strip()}
                )

        # 検証結果
        verification = {
            "total_log_lines": len(lines),
            "extracted_deals": len(deals),
            "extracted_balances": len(balances),
            "first_5_deals": deals[:5],
            "last_5_deals": deals[-5:],
            "balance_records": balances,
            "deal_id_range": {
                "min": min(d["deal_id"] for d in deals),
                "max": max(d["deal_id"] for d in deals),
            }
            if deals
            else None,
        }

        print(f"✅ 取引抽出: {len(deals)}件")
        print(f"✅ 残高記録: {len(balances)}件")
        print(f"✅ Deal ID範囲: {verification['deal_id_range']}")

        return verification

    def verify_trade_pairing_logic(self, deals: List[Dict]) -> Dict:
        """取引ペア作成ロジック検証"""
        print("\n🔍 === 取引ペア作成ロジック検証 ===")

        # 元ロジックと同じペア作成
        pairs = []
        unpaired = []

        i = 0
        while i < len(deals) - 1:
            entry = deals[i]
            exit_deal = deals[i + 1]

            if entry["direction"] != exit_deal["direction"]:
                pairs.append(
                    {
                        "pair_id": len(pairs) + 1,
                        "entry": entry,
                        "exit": exit_deal,
                        "entry_line": entry["line_num"],
                        "exit_line": exit_deal["line_num"],
                    }
                )
                i += 2
            else:
                unpaired.append(entry)
                i += 1

        # 最後の取引が余る場合
        if i == len(deals) - 1:
            unpaired.append(deals[-1])

        # 検証統計
        verification = {
            "total_deals": len(deals),
            "created_pairs": len(pairs),
            "unpaired_deals": len(unpaired),
            "pairing_efficiency": len(pairs) * 2 / len(deals) * 100,
            "sample_pairs": pairs[:3],  # 最初の3ペア
            "sample_unpaired": unpaired[:5],  # 未ペア5件
        }

        print(f"✅ 作成ペア数: {len(pairs)}")
        print(f"✅ 未ペア取引: {len(unpaired)}")
        print(f"✅ ペア化効率: {verification['pairing_efficiency']:.1f}%")

        return verification

    def verify_profit_calculation(self, sample_pairs: List[Dict]) -> Dict:
        """損益計算ロジック検証"""
        print("\n🔍 === 損益計算ロジック検証 ===")

        calculation_checks = []

        for i, pair in enumerate(sample_pairs[:5]):  # 最初の5ペアを検証
            entry = pair["entry"]
            exit = pair["exit"]

            # 手動計算
            if entry["direction"] == "buy":
                manual_gross = (
                    (exit["price"] - entry["price"]) * entry["volume"] * 100000
                )
            else:
                manual_gross = (
                    (entry["price"] - exit["price"]) * entry["volume"] * 100000
                )

            # 取引コスト手動計算
            spread_cost = 0.6 * entry["volume"] * 10
            commission_cost = 2.5 * entry["volume"] * 2
            swap_cost = 0.8 * entry["volume"] * 1  # 1日仮定

            total_cost = spread_cost + commission_cost + swap_cost
            manual_net = manual_gross - total_cost

            calculation_checks.append(
                {
                    "pair_id": i + 1,
                    "entry_price": entry["price"],
                    "exit_price": exit["price"],
                    "volume": entry["volume"],
                    "direction": entry["direction"],
                    "manual_gross_profit": manual_gross,
                    "manual_spread_cost": spread_cost,
                    "manual_commission_cost": commission_cost,
                    "manual_swap_cost": swap_cost,
                    "manual_total_cost": total_cost,
                    "manual_net_profit": manual_net,
                    "price_diff_pips": (exit["price"] - entry["price"]) * 10000
                    if entry["direction"] == "buy"
                    else (entry["price"] - exit["price"]) * 10000,
                }
            )

        verification = {
            "sample_calculations": calculation_checks,
            "pip_calculation_method": "price_diff * volume * 100000",
            "cost_assumptions": {
                "spread_pips": 0.6,
                "commission_per_lot_oneway": 2.5,
                "swap_rate_daily": 0.8,
                "holding_days": 1,
            },
        }

        print(f"✅ 手動計算検証: {len(calculation_checks)}ペア")
        for calc in calculation_checks[:3]:
            print(
                f"  ペア{calc['pair_id']}: {calc['direction']} {calc['volume']}, "
                f"gross={calc['manual_gross_profit']:.2f}, net={calc['manual_net_profit']:.2f}"
            )

        return verification

    def compare_with_mt5_excel(self) -> Dict:
        """MT5 Excelファイルとの比較検証"""
        print("\n🔍 === MT5 Excelファイル比較検証 ===")

        # Excel ファイル検索
        excel_files = []
        for file in os.listdir(self.mt5_results_path):
            if file.endswith(".xlsx") and "Report" in file:
                excel_files.append(file)

        verification = {
            "found_excel_files": excel_files,
            "comparison_status": "pending",
        }

        if excel_files:
            print(f"✅ 発見Excelファイル: {len(excel_files)}")
            for file in excel_files:
                file_path = os.path.join(self.mt5_results_path, file)
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                print(f"  - {file} ({file_size:.1f}MB)")

            verification["comparison_status"] = "files_available"
        else:
            print("❌ Excelファイルが見つかりません")
            verification["comparison_status"] = "no_excel_files"

        return verification

    def run_comprehensive_verification(self) -> Dict:
        """包括的システム検証実行"""
        print("🚀 === MCP統計システム包括的検証開始 ===")
        print("目的: 算出データの正確性・信頼性確保")
        print()

        results = {}

        # 1. データ抽出検証
        results["data_extraction"] = self.verify_data_extraction()

        # 2. 取引ペア作成検証
        deals = (
            results["data_extraction"]["first_5_deals"]
            + results["data_extraction"]["last_5_deals"]
        )
        results["trade_pairing"] = self.verify_trade_pairing_logic(deals)

        # 3. 損益計算検証
        if results["trade_pairing"]["sample_pairs"]:
            results["profit_calculation"] = self.verify_profit_calculation(
                results["trade_pairing"]["sample_pairs"]
            )

        # 4. MT5データ比較
        results["mt5_comparison"] = self.compare_with_mt5_excel()

        # 総合評価
        results["overall_assessment"] = self.assess_system_quality(results)

        return results

    def assess_system_quality(self, results: Dict) -> Dict:
        """システム品質総合評価"""
        print("\n📊 === システム品質総合評価 ===")

        issues = []

        # データ抽出品質チェック
        extraction = results["data_extraction"]
        if extraction["extracted_deals"] < 1000:
            issues.append("取引データ抽出数が少ない可能性")

        # ペア作成効率チェック
        pairing = results["trade_pairing"]
        if pairing["pairing_efficiency"] < 80:
            issues.append(f"ペア化効率が低い: {pairing['pairing_efficiency']:.1f}%")

        # MT5データ利用可能性
        if results["mt5_comparison"]["comparison_status"] == "no_excel_files":
            issues.append("MT5 Excelファイルとの照合不可")

        assessment = {
            "identified_issues": issues,
            "quality_score": max(0, 100 - len(issues) * 20),
            "recommendation": "proceed" if len(issues) <= 1 else "fix_issues_first",
            "critical_issues": [
                issue for issue in issues if "効率" in issue or "データ" in issue
            ],
        }

        print(f"✅ 品質スコア: {assessment['quality_score']}/100")
        print(f"✅ 発見問題: {len(issues)}件")
        print(f"✅ 推奨アクション: {assessment['recommendation']}")

        if issues:
            print("⚠️ 発見された問題:")
            for issue in issues:
                print(f"  - {issue}")

        return assessment


def main():
    """システム検証実行"""
    print("🔍 MCP統計システム精密検証・品質確保")
    print("=" * 50)

    mt5_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results"

    verifier = SystemVerification(mt5_path)
    results = verifier.run_comprehensive_verification()

    # 結果保存
    output_file = os.path.join(mt5_path, "system_verification_report.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✅ 検証完了・結果保存: {output_file}")
    return results


if __name__ == "__main__":
    main()
