#!/usr/bin/env python3
"""
リアリティコスト分析システム
既存のWFA結果にコスト・スリッページ・ドローダウン分析を適用
"""

import json
from datetime import datetime
from typing import Dict

import numpy as np


class RealityCostAnalyzer:
    """リアリティコスト分析クラス"""

    def __init__(self):
        # ChatGPT理論ガイダンス準拠のパラメータ
        self.cost_params = {
            "spread_pips": 1.5,  # OANDA標準スプレッド
            "commission_pips": 0.3,  # 往復手数料
            "fixed_slippage_pips": 0.2,  # 固定スリッページ
        }

    def apply_transaction_costs(self, raw_return: float, num_trades: int) -> Dict:
        """取引コスト適用"""
        spread_pips = self.cost_params["spread_pips"]
        commission_pips = self.cost_params["commission_pips"]

        # pipsを価格差に変換 (1 pip = 0.0001)
        cost_per_trade = (spread_pips + commission_pips) * 0.0001

        # 総コスト計算
        transaction_cost = cost_per_trade * num_trades
        net_return_after_costs = raw_return - transaction_cost

        return {
            "transaction_cost": transaction_cost,
            "cost_per_trade": cost_per_trade,
            "net_return_after_costs": net_return_after_costs,
        }

    def apply_slippage(self, net_return: float, num_trades: int) -> Dict:
        """スリッページ適用"""
        fixed_slippage_pips = self.cost_params["fixed_slippage_pips"]

        # 固定スリッページモデル
        slippage_per_trade = fixed_slippage_pips * 0.0001
        slippage_cost = slippage_per_trade * num_trades
        net_return_after_slippage = net_return - slippage_cost

        return {
            "slippage_cost": slippage_cost,
            "slippage_per_trade": slippage_per_trade,
            "net_return_after_slippage": net_return_after_slippage,
        }

    def calculate_reality_pf(
        self, original_pf: float, raw_return: float, final_return: float
    ) -> float:
        """リアリティPF計算"""
        if raw_return <= 0 or original_pf <= 0:
            return 0

        # コスト影響率を使用してPFを調整
        cost_impact_ratio = final_return / raw_return
        reality_pf = original_pf * cost_impact_ratio

        return max(0, reality_pf)

    def analyze_wfa_results(self, wfa_results_file: str) -> Dict:
        """WFA結果のリアリティ分析"""
        print("🔬 WFA結果のリアリティ分析開始")

        # 既存結果の読み込み
        try:
            with open(wfa_results_file) as f:
                data = json.load(f)

            if "wfa_results" not in data:
                raise ValueError("WFA結果が見つかりません")

            wfa_results = data["wfa_results"]
            print(f"   対象フォールド数: {len(wfa_results)}")

        except Exception as e:
            print(f"❌ ファイル読み込みエラー: {e}")
            return None

        # 各フォールドにリアリティ分析適用
        enhanced_results = []

        print("\n📊 リアリティパラメータ:")
        print(f"   スプレッド: {self.cost_params['spread_pips']} pips")
        print(f"   手数料: {self.cost_params['commission_pips']} pips")
        print(f"   スリッページ: {self.cost_params['fixed_slippage_pips']} pips")

        print("\n🔬 フォールド別分析結果:")

        for result in wfa_results:
            fold_id = result["fold_id"]
            oos_pf = result["oos_pf"]
            oos_trades = result["oos_trades"]
            oos_return = result["oos_return"]

            # 取引コスト適用
            cost_result = self.apply_transaction_costs(oos_return, oos_trades)

            # スリッページ適用
            slippage_result = self.apply_slippage(
                cost_result["net_return_after_costs"], oos_trades
            )

            # リアリティPF計算
            reality_pf = self.calculate_reality_pf(
                oos_pf, oos_return, slippage_result["net_return_after_slippage"]
            )

            # 総コスト計算
            total_cost = (
                cost_result["transaction_cost"] + slippage_result["slippage_cost"]
            )
            cost_impact_pct = (
                (total_cost / abs(oos_return)) * 100 if oos_return != 0 else 0
            )

            # 結果統合
            enhanced_result = result.copy()
            enhanced_result.update(
                {
                    "reality_pf": reality_pf,
                    "reality_return": slippage_result["net_return_after_slippage"],
                    "transaction_cost": cost_result["transaction_cost"],
                    "slippage_cost": slippage_result["slippage_cost"],
                    "total_cost": total_cost,
                    "cost_impact_pct": cost_impact_pct,
                }
            )

            enhanced_results.append(enhanced_result)

            # フォールド結果表示
            print(f"   フォールド{fold_id}:")
            print(f"     元PF: {oos_pf:.3f} → リアリティPF: {reality_pf:.3f}")
            print(f"     取引数: {oos_trades}, 総コスト: {total_cost:.6f}")
            print(f"     コスト影響: {cost_impact_pct:.1f}%")

        # 統計的分析
        statistical_results = self._perform_statistical_analysis(enhanced_results)

        # 最終判定
        final_judgment = self._perform_final_judgment(
            statistical_results, enhanced_results
        )

        # 結果パッケージ
        analysis_result = {
            "analysis_type": "reality_cost_analysis",
            "timestamp": datetime.now().isoformat(),
            "source_file": wfa_results_file,
            "cost_parameters": self.cost_params,
            "enhanced_results": enhanced_results,
            "statistical_results": statistical_results,
            "final_judgment": final_judgment,
        }

        # 結果保存
        output_file = "reality_cost_analysis_results.json"
        with open(output_file, "w") as f:
            json.dump(analysis_result, f, indent=2)

        print(f"\n💾 分析結果保存: {output_file}")

        return analysis_result

    def _perform_statistical_analysis(self, enhanced_results):
        """統計的分析"""
        reality_pfs = [r["reality_pf"] for r in enhanced_results if r["reality_pf"] > 0]

        if not reality_pfs:
            return {"error": "全フォールドでreality_pf <= 0"}

        # 基本統計
        avg_reality_pf = np.mean(reality_pfs)
        positive_folds = len([pf for pf in reality_pfs if pf > 1.0])
        total_folds = len(enhanced_results)
        consistency_ratio = positive_folds / total_folds

        # t検定
        if len(reality_pfs) > 1:
            std_error = np.std(reality_pfs, ddof=1) / np.sqrt(len(reality_pfs))
            t_stat = (avg_reality_pf - 1.0) / std_error if std_error > 0 else 0

            # 簡易p値計算（df=len-1）
            if len(reality_pfs) == 5:  # df=4の場合
                if abs(t_stat) > 2.776:
                    p_value = 0.01
                elif abs(t_stat) > 2.132:
                    p_value = 0.05
                else:
                    p_value = 0.10
            else:
                p_value = 0.05 if abs(t_stat) > 2.0 else 0.10
        else:
            t_stat = 0
            p_value = 1.0

        # コスト分析
        avg_cost_impact = np.mean([r["cost_impact_pct"] for r in enhanced_results])
        avg_total_cost = np.mean([r["total_cost"] for r in enhanced_results])

        return {
            "total_folds": total_folds,
            "positive_folds": positive_folds,
            "consistency_ratio": consistency_ratio,
            "avg_reality_pf": avg_reality_pf,
            "std_reality_pf": np.std(reality_pfs),
            "t_statistic": t_stat,
            "p_value": p_value,
            "statistical_significance": p_value <= 0.05,
            "avg_cost_impact_pct": avg_cost_impact,
            "avg_total_cost": avg_total_cost,
            "avg_oos_trades": np.mean([r["oos_trades"] for r in enhanced_results]),
        }

    def _perform_final_judgment(self, statistical_results, enhanced_results):
        """最終判定（ChatGPT理論ガイダンス準拠）"""
        if "error" in statistical_results:
            return {"reality_viability": False, "reason": statistical_results["error"]}

        # 評価基準（ChatGPT理論ガイダンス準拠）
        criteria = {
            "reality_pf_above_110": statistical_results["avg_reality_pf"] >= 1.10,
            "statistical_significance": statistical_results["statistical_significance"],
            "consistency_above_50": statistical_results["consistency_ratio"] >= 0.5,
            "cost_impact_acceptable": statistical_results["avg_cost_impact_pct"]
            <= 10.0,
            "sufficient_trades": statistical_results["avg_oos_trades"] >= 30,
        }

        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)

        return {
            "reality_viability": passed_criteria >= 4,  # 5つ中4つ以上
            "criteria_passed": passed_criteria,
            "criteria_total": total_criteria,
            "success_rate": passed_criteria / total_criteria,
            "criteria_details": criteria,
            "avg_reality_pf": statistical_results["avg_reality_pf"],
            "p_value": statistical_results["p_value"],
            "cost_impact_summary": f"{statistical_results['avg_cost_impact_pct']:.1f}%",
        }

    def display_results_summary(self, result):
        """結果サマリー表示"""
        if not result:
            print("❌ 分析結果がありません")
            return

        stats = result["statistical_results"]
        judgment = result["final_judgment"]

        print("\n🎯 リアリティ分析サマリー:")
        print(f"   平均リアリティPF: {stats['avg_reality_pf']:.3f}")
        print(
            f"   統計的有意性: {'✅ あり' if stats['statistical_significance'] else '❌ なし'} (p={stats['p_value']:.3f})"
        )
        print(
            f"   一貫性: {stats['consistency_ratio']*100:.0f}% ({stats['positive_folds']}/{stats['total_folds']})"
        )
        print(f"   平均コスト影響: {stats['avg_cost_impact_pct']:.1f}%")

        print("\n🏆 最終判定:")
        print(f"   実用性: {'✅ 合格' if judgment['reality_viability'] else '❌ 不合格'}")
        print(
            f"   基準達成: {judgment['criteria_passed']}/{judgment['criteria_total']} ({judgment['success_rate']*100:.0f}%)"
        )

        print("\n📋 詳細基準:")
        for criterion, passed in judgment["criteria_details"].items():
            status = "✅" if passed else "❌"
            print(f"   {criterion}: {status}")


if __name__ == "__main__":
    analyzer = RealityCostAnalyzer()

    # 最新のWFA結果を分析
    result = analyzer.analyze_wfa_results("minimal_wfa_results.json")

    if result:
        analyzer.display_results_summary(result)
        print("\n🎊 リアリティコスト分析完了")
    else:
        print("❌ 分析失敗")
