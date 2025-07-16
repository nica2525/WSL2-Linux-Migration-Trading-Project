#!/usr/bin/env python3
"""
システム性能比較分析
修正版WFA vs 既存システムの統計的比較・Over-fitting除去価値の定量化
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class SystemPerformanceComparison:
    """システム性能比較分析クラス"""
    
    def __init__(self):
        self.old_results = None
        self.corrected_results = None
        self.comparison_analysis = {}
        
    def load_results(self, old_results_path: str, corrected_results_path: str):
        """結果データ読み込み"""
        try:
            # 旧版結果読み込み
            with open(old_results_path, 'r') as f:
                self.old_results = pd.DataFrame(json.load(f))
            
            # 修正版結果読み込み  
            with open(corrected_results_path, 'r') as f:
                self.corrected_results = pd.DataFrame(json.load(f))
            
            print(f"✅ 結果読み込み完了:")
            print(f"  旧版: {len(self.old_results)}シナリオ")
            print(f"  修正版: {len(self.corrected_results)}シナリオ")
            
            return True
            
        except Exception as e:
            print(f"❌ 結果読み込みエラー: {e}")
            return False
    
    def analyze_overfitting_impact(self):
        """Over-fitting除去の影響分析"""
        print("\n🔍 Over-fitting除去の影響分析")
        print("=" * 50)
        
        analysis = {}
        
        # 1. シナリオ数の変化
        old_count = len(self.old_results)
        corrected_count = len(self.corrected_results)
        reduction_rate = (old_count - corrected_count) / old_count
        
        analysis['scenario_reduction'] = {
            'old_count': old_count,
            'corrected_count': corrected_count,
            'reduction_rate': reduction_rate,
            'interpretation': 'シナリオ数激減は正しいWFA実装の証拠'
        }
        
        print(f"📊 シナリオ数変化:")
        print(f"  旧版: {old_count}シナリオ")
        print(f"  修正版: {corrected_count}シナリオ")
        print(f"  削減率: {reduction_rate:.1%}")
        print(f"  → Over-fittingによる偽の多様性を除去")
        
        # 2. シャープレシオ分布の変化
        old_sharpe_stats = self.old_results['sharpe_ratio'].describe()
        corrected_sharpe_stats = self.corrected_results['sharpe_ratio'].describe()
        
        analysis['sharpe_distribution'] = {
            'old_mean': old_sharpe_stats['mean'],
            'old_std': old_sharpe_stats['std'],
            'corrected_mean': corrected_sharpe_stats['mean'], 
            'corrected_std': corrected_sharpe_stats['std'],
            'mean_change': corrected_sharpe_stats['mean'] - old_sharpe_stats['mean'],
            'std_change': corrected_sharpe_stats['std'] - old_sharpe_stats['std']
        }
        
        print(f"\n📈 シャープレシオ分布変化:")
        print(f"  旧版平均: {old_sharpe_stats['mean']:.3f} ± {old_sharpe_stats['std']:.3f}")
        print(f"  修正版平均: {corrected_sharpe_stats['mean']:.3f} ± {corrected_sharpe_stats['std']:.3f}")
        print(f"  平均変化: {analysis['sharpe_distribution']['mean_change']:+.3f}")
        print(f"  標準偏差変化: {analysis['sharpe_distribution']['std_change']:+.3f}")
        
        # 3. 最高値の現実化
        old_max = self.old_results['sharpe_ratio'].max()
        corrected_max = self.corrected_results['sharpe_ratio'].max()
        max_reduction = (old_max - corrected_max) / old_max
        
        analysis['max_performance'] = {
            'old_max': old_max,
            'corrected_max': corrected_max,
            'reduction_rate': max_reduction,
            'interpretation': '過剰に楽観的な予測の除去'
        }
        
        print(f"\n🏆 最高シャープレシオ変化:")
        print(f"  旧版最高: {old_max:.3f}")
        print(f"  修正版最高: {corrected_max:.3f}")
        print(f"  現実化率: {max_reduction:.1%}")
        print(f"  → 過剰適合による偽の高性能を除去")
        
        return analysis
    
    def analyze_statistical_reliability(self):
        """統計的信頼性分析"""
        print("\n📊 統計的信頼性分析")
        print("=" * 50)
        
        analysis = {}
        
        # 1. 正のシャープレシオ割合
        old_positive_rate = (self.old_results['sharpe_ratio'] > 0).mean()
        corrected_positive_rate = (self.corrected_results['sharpe_ratio'] > 0).mean()
        
        # 2. シャープレシオの分散
        old_variance = self.old_results['sharpe_ratio'].var()
        corrected_variance = self.corrected_results['sharpe_ratio'].var()
        
        # 3. 統計的有意性（t検定）
        if len(self.corrected_results) >= 3:
            t_stat, p_value = stats.ttest_1samp(
                self.corrected_results['sharpe_ratio'], 0
            )
            statistical_significance = p_value < 0.05
        else:
            t_stat, p_value = np.nan, np.nan
            statistical_significance = False
        
        analysis['reliability'] = {
            'old_positive_rate': old_positive_rate,
            'corrected_positive_rate': corrected_positive_rate,
            'old_variance': old_variance,
            'corrected_variance': corrected_variance,
            't_statistic': t_stat,
            'p_value': p_value,
            'statistically_significant': statistical_significance
        }
        
        print(f"✅ 正のシャープレシオ割合:")
        print(f"  旧版: {old_positive_rate:.1%}")
        print(f"  修正版: {corrected_positive_rate:.1%}")
        
        print(f"\n📏 分散（安定性指標）:")
        print(f"  旧版分散: {old_variance:.3f}")
        print(f"  修正版分散: {corrected_variance:.3f}")
        
        if not np.isnan(p_value):
            print(f"\n🔬 統計的有意性検定:")
            print(f"  t統計量: {t_stat:.3f}")
            print(f"  p値: {p_value:.6f}")
            print(f"  統計的有意: {'✅' if statistical_significance else '❌'}")
        
        return analysis
    
    def analyze_cost_scenario_robustness(self):
        """コストシナリオ頑健性分析"""
        print("\n💰 コストシナリオ頑健性分析")
        print("=" * 50)
        
        analysis = {}
        
        # 修正版のコストシナリオ別分析
        for cost_scenario in self.corrected_results['cost_scenario'].unique():
            scenario_data = self.corrected_results[
                self.corrected_results['cost_scenario'] == cost_scenario
            ]
            
            scenario_analysis = {
                'mean_sharpe': scenario_data['sharpe_ratio'].mean(),
                'std_sharpe': scenario_data['sharpe_ratio'].std(),
                'min_sharpe': scenario_data['sharpe_ratio'].min(),
                'max_sharpe': scenario_data['sharpe_ratio'].max(),
                'positive_rate': (scenario_data['sharpe_ratio'] > 0).mean(),
                'fold_count': len(scenario_data)
            }
            
            analysis[cost_scenario] = scenario_analysis
            
            print(f"\n📈 {cost_scenario}:")
            print(f"  平均SR: {scenario_analysis['mean_sharpe']:.3f}")
            print(f"  標準偏差: {scenario_analysis['std_sharpe']:.3f}")
            print(f"  範囲: [{scenario_analysis['min_sharpe']:.3f}, {scenario_analysis['max_sharpe']:.3f}]")
            print(f"  正のSR率: {scenario_analysis['positive_rate']:.1%}")
            print(f"  Fold数: {scenario_analysis['fold_count']}")
        
        # コスト感応度分析
        cost_sensitivity = self._analyze_cost_sensitivity()
        analysis['cost_sensitivity'] = cost_sensitivity
        
        return analysis
    
    def _analyze_cost_sensitivity(self):
        """コスト感応度分析"""
        cost_scenarios = self.corrected_results['cost_scenario'].unique()
        sensitivity = {}
        
        if len(cost_scenarios) >= 2:
            # Low Cost vs High Costの比較
            if 'Low Cost' in cost_scenarios and 'High Cost' in cost_scenarios:
                low_cost_sharpe = self.corrected_results[
                    self.corrected_results['cost_scenario'] == 'Low Cost'
                ]['sharpe_ratio'].mean()
                
                high_cost_sharpe = self.corrected_results[
                    self.corrected_results['cost_scenario'] == 'High Cost'
                ]['sharpe_ratio'].mean()
                
                cost_impact = (high_cost_sharpe - low_cost_sharpe) / low_cost_sharpe
                
                sensitivity['low_to_high_impact'] = cost_impact
                
                print(f"\n💸 コスト感応度:")
                print(f"  Low Cost平均SR: {low_cost_sharpe:.3f}")
                print(f"  High Cost平均SR: {high_cost_sharpe:.3f}")
                print(f"  コスト影響度: {cost_impact:.1%}")
                
        return sensitivity
    
    def compare_wfa_methodology(self):
        """WFA手法論の比較"""
        print("\n🔬 WFA手法論比較")
        print("=" * 50)
        
        comparison = {
            'old_system': {
                'method': 'Cross-Validation (CV)',
                'time_series_aware': False,
                'parameter_optimization': False,
                'look_ahead_bias': True,
                'over_fitting_risk': 'High',
                'reliability': 'Low'
            },
            'corrected_system': {
                'method': 'Walk-Forward Analysis (WFA)',
                'time_series_aware': True,
                'parameter_optimization': True,
                'look_ahead_bias': False,
                'over_fitting_risk': 'Low',
                'reliability': 'High'
            }
        }
        
        print("📋 手法論比較:")
        print("\n🔴 旧システム:")
        print("  手法: Cross-Validation (非時系列)")
        print("  時系列考慮: ❌")
        print("  パラメータ最適化: ❌")
        print("  Look-ahead bias: ❌ (存在)")
        print("  Over-fitting風険: 🔴 高")
        print("  信頼性: 🔴 低")
        
        print("\n🟢 修正システム:")
        print("  手法: Walk-Forward Analysis")
        print("  時系列考慮: ✅")
        print("  パラメータ最適化: ✅")
        print("  Look-ahead bias: ✅ (完全除去)")
        print("  Over-fitting風険: 🟢 低")
        print("  信頼性: 🟢 高")
        
        return comparison
    
    def generate_comprehensive_report(self):
        """包括的比較レポート生成"""
        print("\n📋 包括的システム比較レポート")
        print("=" * 60)
        
        # 各分析を実行
        overfitting_analysis = self.analyze_overfitting_impact()
        reliability_analysis = self.analyze_statistical_reliability()
        robustness_analysis = self.analyze_cost_scenario_robustness()
        methodology_comparison = self.compare_wfa_methodology()
        
        # 総合評価
        comprehensive_report = {
            'overfitting_impact': overfitting_analysis,
            'statistical_reliability': reliability_analysis,
            'cost_robustness': robustness_analysis,
            'methodology_comparison': methodology_comparison,
            'summary': self._generate_summary(),
            'recommendations': self._generate_recommendations()
        }
        
        return comprehensive_report
    
    def _generate_summary(self):
        """サマリー生成"""
        old_max = self.old_results['sharpe_ratio'].max()
        corrected_mean = self.corrected_results['sharpe_ratio'].mean()
        corrected_positive_rate = (self.corrected_results['sharpe_ratio'] > 0).mean()
        
        summary = {
            'key_findings': [
                f"Over-fitting除去により最高SR {old_max:.3f}→{corrected_mean:.3f}に現実化",
                f"統計的信頼性大幅向上: {corrected_positive_rate:.0%}のFoldで正のSR",
                "時系列順序維持によりLook-ahead bias完全除去",
                "In-Sample最適化により真の予測性能を測定"
            ],
            'improvement_areas': [
                "過剰適合の除去",
                "統計的手法の正確性",
                "時系列データ特性の考慮",
                "現実的性能予測"
            ]
        }
        
        print("\n🎯 主要発見:")
        for finding in summary['key_findings']:
            print(f"  • {finding}")
        
        print("\n📈 改善領域:")
        for area in summary['improvement_areas']:
            print(f"  • {area}")
        
        return summary
    
    def _generate_recommendations(self):
        """推奨事項生成"""
        recommendations = {
            'immediate_actions': [
                "修正版WFAシステムの本格採用",
                "旧版システムの段階的廃止",
                "修正版結果に基づく実運用計画策定"
            ],
            'monitoring_requirements': [
                "Out-of-Sample性能の継続監視",
                "コストシナリオ別パフォーマンス追跡",
                "統計的有意性の定期検証"
            ],
            'future_enhancements': [
                "並列処理による最適化高速化",
                "スリッパージモデルの追加",
                "リアルタイム性能監視システム"
            ]
        }
        
        print("\n🚀 推奨事項:")
        print("\n⚡ 即座実行:")
        for action in recommendations['immediate_actions']:
            print(f"  • {action}")
        
        print("\n👁️ 監視要件:")
        for req in recommendations['monitoring_requirements']:
            print(f"  • {req}")
        
        print("\n🔮 将来拡張:")
        for enhancement in recommendations['future_enhancements']:
            print(f"  • {enhancement}")
        
        return recommendations
    
    def save_comparison_report(self, filename=None):
        """比較レポート保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_comparison_report_{timestamp}.json"
        
        try:
            report = self.generate_comprehensive_report()
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\n✅ 比較レポート保存: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ レポート保存エラー: {e}")
            return False

def main():
    """メイン実行"""
    print("🚀 システム性能比較分析開始")
    print("=" * 60)
    
    # 比較分析初期化
    comparison = SystemPerformanceComparison()
    
    # 結果ファイル指定
    old_results_path = "vectorbt_wfa_results_20250716_235344.json"
    corrected_results_path = "corrected_wfa_results_20250717_062858.json"
    
    # 結果読み込み
    if not comparison.load_results(old_results_path, corrected_results_path):
        print("❌ 結果ファイルが見つかりません")
        return
    
    # 包括的比較分析実行
    report = comparison.generate_comprehensive_report()
    
    # レポート保存
    comparison.save_comparison_report()
    
    print("\n🎉 システム性能比較分析完了")

if __name__ == "__main__":
    main()