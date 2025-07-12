#!/usr/bin/env python3
"""
強化戦略検証システム
リスク管理システムを統合した強化戦略の包括的検証
"""

import json
import math
from datetime import datetime, timedelta
from data_cache_system import DataCacheManager
from enhanced_breakout_strategy import EnhancedBreakoutStrategy
from multi_timeframe_breakout_strategy import MultiTimeframeData

class EnhancedStrategyValidator:
    """強化戦略検証システム"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
        # 強化戦略パラメータ
        self.enhanced_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,
            'stop_atr': 1.3,
            'min_break_pips': 5
        }
        
    def run_enhanced_validation(self):
        """強化戦略検証実行"""
        print("🚀 強化戦略検証開始")
        print("   目標: リスク管理統合による性能改善確認")
        
        # データ取得（汚染源修正）
        raw_data = self.cache_manager.get_full_data()
        # validation_data = raw_data[::10]  # 🚨 CONTAMINATED: 90%データ破棄による統計的信頼性破綻
        validation_data = raw_data  # 完全データを使用
        
        print(f"\\n📊 検証データ:")
        print(f"   総データ: {len(validation_data):,}バー")
        print(f"   期間: {validation_data[0]['datetime'].strftime('%Y-%m-%d')} - {validation_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        
        # 検証期間設定
        start_date = validation_data[0]['datetime'] + timedelta(days=200)  # 初期データをスキップ
        end_date = validation_data[-1]['datetime'] - timedelta(days=30)   # 最終データをスキップ
        
        print(f"   検証期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        
        # 強化戦略実行
        enhanced_results = self._run_enhanced_backtest(validation_data, start_date, end_date)
        
        if not enhanced_results:
            print("❌ 強化戦略実行失敗")
            return None
        
        # 元戦略との比較
        original_results = self._run_original_backtest(validation_data, start_date, end_date)
        
        # 比較分析
        comparison_analysis = self._compare_strategies(enhanced_results, original_results)
        
        # リスク管理効果分析
        risk_management_analysis = self._analyze_risk_management_effect(enhanced_results)
        
        # 最終評価
        final_evaluation = self._evaluate_enhancement(enhanced_results, comparison_analysis, risk_management_analysis)
        
        # 結果保存
        self._save_enhanced_validation_results(enhanced_results, original_results, comparison_analysis, risk_management_analysis, final_evaluation)
        
        return enhanced_results, comparison_analysis, final_evaluation
    
    def _run_enhanced_backtest(self, validation_data, start_date, end_date):
        """強化戦略バックテスト実行"""
        print(f"\\n🛡️ 強化戦略バックテスト:")
        
        try:
            # 強化戦略初期化
            enhanced_strategy = EnhancedBreakoutStrategy(self.enhanced_params)
            
            # データ準備
            mtf_data = MultiTimeframeData(validation_data)
            
            # バックテスト実行
            results = enhanced_strategy.backtest_enhanced_strategy(mtf_data, start_date, end_date)
            
            print(f"   強化戦略結果:")
            print(f"     総取引: {results['total_trades']}")
            print(f"     勝率: {results['win_rate']:.1%}")
            print(f"     PF: {results['profit_factor']:.3f}")
            print(f"     総PnL: {results['total_pnl']:.2f}")
            print(f"     最大DD: {results['max_drawdown']:.1%}")
            print(f"     シャープ比: {results['sharpe_ratio']:.3f}")
            
            # シグナル統計
            signal_stats = results['signal_statistics']
            print(f"     生成シグナル: {signal_stats['signals_generated']}")
            print(f"     フィルタリング: {signal_stats['signals_filtered']}")
            print(f"     実行率: {signal_stats['execution_ratio']:.1%}")
            
            return results
            
        except Exception as e:
            print(f"   エラー: {str(e)}")
            return None
    
    def _run_original_backtest(self, validation_data, start_date, end_date):
        """元戦略バックテスト実行"""
        print(f"\\n📊 元戦略バックテスト:")
        
        try:
            # 元戦略の簡易実装（比較用）
            from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy
            
            original_strategy = MultiTimeframeBreakoutStrategy(self.enhanced_params)
            mtf_data = MultiTimeframeData(validation_data)
            
            # 元戦略バックテスト
            results = original_strategy.backtest(mtf_data, start_date, end_date)
            
            print(f"   元戦略結果:")
            print(f"     総取引: {results['total_trades']}")
            print(f"     勝率: {results['win_rate']:.1%}")
            print(f"     PF: {results['profit_factor']:.3f}")
            print(f"     総PnL: {results['total_pnl']:.2f}")
            print(f"     最大DD: {results['max_drawdown']:.1%}")
            print(f"     シャープ比: {results['sharpe_ratio']:.3f}")
            
            return results
            
        except Exception as e:
            print(f"   エラー: {str(e)}")
            return None
    
    def _compare_strategies(self, enhanced_results, original_results):
        """戦略比較分析"""
        print(f"\\n🔍 戦略比較分析:")
        
        if not enhanced_results or not original_results:
            return None
        
        # 性能比較
        performance_comparison = {
            'total_trades': {
                'enhanced': enhanced_results['total_trades'],
                'original': original_results['total_trades'],
                'difference': enhanced_results['total_trades'] - original_results['total_trades']
            },
            'win_rate': {
                'enhanced': enhanced_results['win_rate'],
                'original': original_results['win_rate'],
                'difference': enhanced_results['win_rate'] - original_results['win_rate']
            },
            'profit_factor': {
                'enhanced': enhanced_results['profit_factor'],
                'original': original_results['profit_factor'],
                'difference': enhanced_results['profit_factor'] - original_results['profit_factor']
            },
            'total_pnl': {
                'enhanced': enhanced_results['total_pnl'],
                'original': original_results['total_pnl'],
                'difference': enhanced_results['total_pnl'] - original_results['total_pnl']
            },
            'max_drawdown': {
                'enhanced': enhanced_results['max_drawdown'],
                'original': original_results['max_drawdown'],
                'difference': enhanced_results['max_drawdown'] - original_results['max_drawdown']
            },
            'sharpe_ratio': {
                'enhanced': enhanced_results['sharpe_ratio'],
                'original': original_results['sharpe_ratio'],
                'difference': enhanced_results['sharpe_ratio'] - original_results['sharpe_ratio']
            }
        }
        
        # 改善度評価
        improvements = {
            'trade_quality': enhanced_results['win_rate'] > original_results['win_rate'],
            'risk_adjusted_return': enhanced_results['sharpe_ratio'] > original_results['sharpe_ratio'],
            'drawdown_control': enhanced_results['max_drawdown'] < original_results['max_drawdown'],
            'profit_factor_improvement': enhanced_results['profit_factor'] > original_results['profit_factor']
        }
        
        improvement_score = sum(improvements.values()) / len(improvements)
        
        print(f"   改善項目:")
        for metric, improved in improvements.items():
            status = "✅" if improved else "❌"
            print(f"     {metric}: {status}")
        
        print(f"   改善スコア: {improvement_score:.1%}")
        
        return {
            'performance_comparison': performance_comparison,
            'improvements': improvements,
            'improvement_score': improvement_score
        }
    
    def _analyze_risk_management_effect(self, enhanced_results):
        """リスク管理効果分析"""
        print(f"\\n🛡️ リスク管理効果分析:")
        
        if not enhanced_results:
            return None
        
        # シグナル統計
        signal_stats = enhanced_results['signal_statistics']
        filter_effect = signal_stats['filter_ratio']
        
        # 信頼度別分析
        confidence_analysis = enhanced_results.get('confidence_analysis', {})
        
        # リスク指標
        risk_metrics = {
            'signal_filtering_rate': filter_effect,
            'trade_execution_rate': signal_stats['execution_ratio'],
            'max_drawdown_control': enhanced_results['max_drawdown'],
            'sharpe_ratio_improvement': enhanced_results['sharpe_ratio']
        }
        
        # 効果評価
        risk_effectiveness = {
            'signal_quality_filter': filter_effect > 0.2,  # 20%以上のフィルタリング
            'drawdown_control': enhanced_results['max_drawdown'] < 0.15,  # 15%以下のDD
            'risk_adjusted_performance': enhanced_results['sharpe_ratio'] > 0.5,  # 0.5以上のシャープ比
            'confidence_differentiation': len(confidence_analysis) > 1  # 信頼度の差別化
        }
        
        effectiveness_score = sum(risk_effectiveness.values()) / len(risk_effectiveness)
        
        print(f"   リスク管理効果:")
        print(f"     フィルタリング率: {filter_effect:.1%}")
        print(f"     実行率: {signal_stats['execution_ratio']:.1%}")
        print(f"     最大DD: {enhanced_results['max_drawdown']:.1%}")
        print(f"     シャープ比: {enhanced_results['sharpe_ratio']:.3f}")
        print(f"   効果スコア: {effectiveness_score:.1%}")
        
        return {
            'risk_metrics': risk_metrics,
            'risk_effectiveness': risk_effectiveness,
            'effectiveness_score': effectiveness_score,
            'confidence_analysis': confidence_analysis
        }
    
    def _evaluate_enhancement(self, enhanced_results, comparison_analysis, risk_management_analysis):
        """強化効果評価"""
        print(f"\\n🏆 強化効果総合評価:")
        
        if not enhanced_results or not comparison_analysis or not risk_management_analysis:
            return {'evaluation': 'FAILED', 'reason': 'insufficient_data'}
        
        # 評価基準
        criteria = {
            'performance_improvement': comparison_analysis['improvement_score'] >= 0.5,
            'risk_management_effectiveness': risk_management_analysis['effectiveness_score'] >= 0.6,
            'statistical_significance': enhanced_results['total_trades'] >= 50,
            'practical_viability': enhanced_results['profit_factor'] > 1.1 and enhanced_results['max_drawdown'] < 0.20
        }
        
        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)
        
        # 総合評価
        if passed_criteria >= 4:
            evaluation = 'EXCELLENT'
        elif passed_criteria >= 3:
            evaluation = 'GOOD'
        elif passed_criteria >= 2:
            evaluation = 'MODERATE'
        else:
            evaluation = 'POOR'
        
        print(f"   評価基準:")
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"     {criterion}: {status}")
        
        print(f"   総合評価: {evaluation}")
        print(f"   達成基準: {passed_criteria}/{total_criteria}")
        
        # 推奨事項
        recommendations = self._generate_recommendations(evaluation, enhanced_results, comparison_analysis)
        
        return {
            'evaluation': evaluation,
            'criteria_passed': passed_criteria,
            'criteria_total': total_criteria,
            'success_rate': passed_criteria / total_criteria,
            'detailed_criteria': criteria,
            'recommendations': recommendations
        }
    
    def _generate_recommendations(self, evaluation, enhanced_results, comparison_analysis):
        """推奨事項生成"""
        recommendations = []
        
        if evaluation == 'EXCELLENT':
            recommendations.append("強化戦略は実用化準備完了です。")
            recommendations.append("デモ環境でのリアルタイムテストを開始してください。")
        elif evaluation == 'GOOD':
            recommendations.append("強化戦略は良好な結果を示しています。")
            recommendations.append("更なる最適化を検討してください。")
        elif evaluation == 'MODERATE':
            recommendations.append("強化戦略は中程度の改善を示しています。")
            recommendations.append("リスク管理パラメータの調整が必要です。")
        else:
            recommendations.append("強化戦略は期待した効果を示していません。")
            recommendations.append("リスク管理システムの見直しが必要です。")
        
        # 具体的な改善提案
        if enhanced_results['max_drawdown'] > 0.15:
            recommendations.append("ドローダウン制御を強化してください。")
        
        if enhanced_results['sharpe_ratio'] < 0.5:
            recommendations.append("リスク調整後リターンの改善が必要です。")
        
        return recommendations
    
    def _save_enhanced_validation_results(self, enhanced_results, original_results, comparison_analysis, risk_management_analysis, final_evaluation):
        """強化検証結果保存"""
        validation_data = {
            'validation_type': 'enhanced_strategy_validation',
            'timestamp': datetime.now().isoformat(),
            'enhanced_results': enhanced_results,
            'original_results': original_results,
            'comparison_analysis': comparison_analysis,
            'risk_management_analysis': risk_management_analysis,
            'final_evaluation': final_evaluation,
            'conclusion': {
                'enhancement_success': final_evaluation['evaluation'] in ['EXCELLENT', 'GOOD'],
                'risk_management_effective': risk_management_analysis['effectiveness_score'] >= 0.6,
                'ready_for_deployment': final_evaluation['evaluation'] == 'EXCELLENT',
                'next_steps': final_evaluation['recommendations']
            }
        }
        
        with open('enhanced_strategy_validation_results.json', 'w') as f:
            json.dump(validation_data, f, indent=2)
        
        print(f"\\n💾 強化戦略検証結果保存: enhanced_strategy_validation_results.json")

def main():
    """メイン実行"""
    print("🚀 強化戦略検証システム開始")
    print("   リスク管理統合による戦略改善検証")
    
    validator = EnhancedStrategyValidator()
    
    try:
        enhanced_results, comparison_analysis, final_evaluation = validator.run_enhanced_validation()
        
        if enhanced_results and comparison_analysis and final_evaluation:
            print(f"\\n✅ 強化戦略検証完了")
            print(f"   総合評価: {final_evaluation['evaluation']}")
            print(f"   改善スコア: {comparison_analysis['improvement_score']:.1%}")
            print(f"   実用化準備: {'完了' if final_evaluation['evaluation'] == 'EXCELLENT' else '要調整'}")
        else:
            print(f"\\n⚠️ 強化戦略検証失敗")
            
    except Exception as e:
        print(f"\\n❌ エラー発生: {str(e)}")
        return None, None, None
    
    return enhanced_results, comparison_analysis, final_evaluation

if __name__ == "__main__":
    enhanced_results, comparison_analysis, final_evaluation = main()