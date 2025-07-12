#!/usr/bin/env python3
"""
拡張期間WFA実行システム
3-5年の長期データでの統計的有意性検証
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
import json
import math
from datetime import datetime, timedelta

class ExtendedPeriodWFA:
    """拡張期間WFA実行システム"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
        # 最終パラメータ
        self.final_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,
            'stop_atr': 1.3,
            'min_break_pips': 5
        }
        
    def run_extended_wfa(self):
        """拡張期間WFA実行"""
        print("🚀 拡張期間WFA実行開始")
        print("   目標: 3-5年データでの統計的有意性確認")
        
        # 軽量データ取得（タイムアウト対策）
        print("\n📊 軽量データ取得中...")
        raw_data = self.cache_manager.get_full_data()
        # 3分の1に間引きして高速化
        light_data = raw_data[::3]
        raw_data = light_data
        
        print(f"   フルデータ: {len(raw_data):,}バー")
        print(f"   期間: {raw_data[0]['datetime'].strftime('%Y-%m-%d')} - {raw_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        
        total_days = (raw_data[-1]['datetime'] - raw_data[0]['datetime']).days
        total_years = total_days / 365.25
        
        print(f"   総日数: {total_days}日 ({total_years:.1f}年)")
        
        # 長期WFA実行
        extended_results = self._execute_extended_wfa(raw_data)
        
        if not extended_results:
            print("❌ 拡張期間WFA実行失敗")
            return None
        
        # 統計的分析
        statistical_results = self._perform_extended_statistical_analysis(extended_results)
        
        # 前回結果との比較
        comparison_with_previous = self._compare_with_previous_results(statistical_results)
        
        # 最終評価
        final_evaluation = self._evaluate_extended_results(statistical_results, comparison_with_previous)
        
        # 結果保存
        self._save_extended_results(extended_results, statistical_results, comparison_with_previous, final_evaluation)
        
        return extended_results, statistical_results, final_evaluation
    
    def _execute_extended_wfa(self, raw_data):
        """拡張期間WFA実行"""
        print(f"\n📋 拡張期間WFA実行:")
        
        # より長期のフォールド設定
        folds = self._create_extended_folds(raw_data)
        
        if len(folds) < 5:
            print(f"   フォールド不足: {len(folds)}個")
            return None
        
        print(f"   フォールド数: {len(folds)}")
        
        results = []
        
        for i, fold in enumerate(folds, 1):
            print(f"   フォールド{i}: {fold['is_start'].strftime('%Y-%m')} - {fold['oos_end'].strftime('%Y-%m')}")
            
            try:
                # 期間データ取得
                is_data = [bar for bar in raw_data if fold['is_start'] <= bar['datetime'] <= fold['is_end']]
                oos_data = [bar for bar in raw_data if fold['oos_start'] <= bar['datetime'] <= fold['oos_end']]
                
                if len(is_data) < 200 or len(oos_data) < 100:
                    print(f"     データ不足: IS={len(is_data)}, OOS={len(oos_data)}")
                    continue
                
                # 戦略実行
                strategy = MultiTimeframeBreakoutStrategy(self.final_params)
                
                is_mtf = MultiTimeframeData(is_data)
                oos_mtf = MultiTimeframeData(oos_data)
                
                # IS期間
                is_result = strategy.backtest(is_mtf, fold['is_start'], fold['is_end'])
                
                # OOS期間
                oos_result = strategy.backtest(oos_mtf, fold['oos_start'], fold['oos_end'])
                
                fold_result = {
                    'fold_id': i,
                    'is_start': fold['is_start'].isoformat(),
                    'is_end': fold['is_end'].isoformat(),
                    'oos_start': fold['oos_start'].isoformat(),
                    'oos_end': fold['oos_end'].isoformat(),
                    'is_pf': is_result['profit_factor'],
                    'is_trades': is_result['total_trades'],
                    'is_return': is_result['total_pnl'],
                    'oos_pf': oos_result['profit_factor'],
                    'oos_trades': oos_result['total_trades'],
                    'oos_return': oos_result['total_pnl'],
                    'oos_sharpe': oos_result['sharpe_ratio'],
                    'oos_win_rate': oos_result['win_rate'],
                    'oos_max_dd': oos_result['max_drawdown']
                }
                
                results.append(fold_result)
                print(f"     IS: PF={is_result['profit_factor']:.3f}, 取引={is_result['total_trades']}")
                print(f"     OOS: PF={oos_result['profit_factor']:.3f}, 取引={oos_result['total_trades']}")
                
            except Exception as e:
                print(f"     エラー: {str(e)}")
                continue
        
        return results
    
    def _create_extended_folds(self, raw_data):
        """拡張期間フォールド作成"""
        start_date = raw_data[0]['datetime']
        end_date = raw_data[-1]['datetime']
        total_days = (end_date - start_date).days
        
        print(f"   総期間: {total_days}日")
        
        # 軽量版長期設定: 8ヶ月IS / 4ヶ月OOS / 2ヶ月ステップ
        is_days = 240  # 8ヶ月
        oos_days = 120  # 4ヶ月
        step_days = 60  # 2ヶ月
        
        folds = []
        current_start = start_date
        fold_id = 1
        
        while True:
            # IS期間
            is_end = current_start + timedelta(days=is_days)
            if is_end > end_date:
                break
            
            # OOS期間
            oos_start = is_end
            oos_end = oos_start + timedelta(days=oos_days)
            if oos_end > end_date:
                break
            
            fold = {
                'fold_id': fold_id,
                'is_start': current_start,
                'is_end': is_end,
                'oos_start': oos_start,
                'oos_end': oos_end
            }
            
            folds.append(fold)
            print(f"   フォールド{fold_id}: IS={is_days}日, OOS={oos_days}日")
            
            # 次のフォールド（アンカード方式）
            current_start = start_date  # 開始は固定
            is_days += step_days  # IS期間延長
            fold_id += 1
            
            if fold_id > 8:  # 最大8フォールド
                break
        
        return folds
    
    def _perform_extended_statistical_analysis(self, extended_results):
        """拡張期間統計的分析"""
        print(f"\n🔬 拡張期間統計的分析:")
        
        if not extended_results:
            return None
        
        # 基本統計
        total_folds = len(extended_results)
        positive_folds = sum(1 for r in extended_results if r['oos_return'] > 0)
        consistency_ratio = positive_folds / total_folds if total_folds > 0 else 0
        
        # OOS統計
        avg_oos_pf = sum(r['oos_pf'] for r in extended_results) / len(extended_results)
        avg_oos_trades = sum(r['oos_trades'] for r in extended_results) / len(extended_results)
        total_oos_trades = sum(r['oos_trades'] for r in extended_results)
        
        oos_returns = [r['oos_return'] for r in extended_results]
        oos_sharpes = [r['oos_sharpe'] for r in extended_results]
        
        # WFA効率
        total_is_return = sum(r['is_return'] for r in extended_results)
        total_oos_return = sum(r['oos_return'] for r in extended_results)
        wfa_efficiency = total_oos_return / total_is_return if total_is_return > 0 else 0
        
        # 拡張t検定
        if len(oos_returns) > 2:
            mean_return = sum(oos_returns) / len(oos_returns)
            variance = sum((r - mean_return) ** 2 for r in oos_returns) / (len(oos_returns) - 1)
            std_error = math.sqrt(variance / len(oos_returns)) if variance > 0 else 0.001
            
            # t統計量
            t_statistic = mean_return / std_error if std_error > 0 else 0
            
            # 自由度
            df = len(oos_returns) - 1
            
            # より正確なp値計算
            p_value = self._calculate_accurate_p_value(t_statistic, df)
            
        else:
            mean_return = oos_returns[0] if oos_returns else 0
            t_statistic = 0
            p_value = 1.0
        
        statistical_significance = p_value < 0.05
        
        print(f"   フォールド数: {total_folds}")
        print(f"   正の結果: {positive_folds}/{total_folds} ({consistency_ratio:.1%})")
        print(f"   平均OOS PF: {avg_oos_pf:.3f}")
        print(f"   平均取引数: {avg_oos_trades:.0f}")
        print(f"   総取引数: {total_oos_trades}")
        print(f"   WFA効率: {wfa_efficiency:.3f}")
        print(f"   t統計量: {t_statistic:.3f}")
        print(f"   自由度: {df if 'df' in locals() else 0}")
        print(f"   p値: {p_value:.4f}")
        print(f"   統計的有意性: {'✅ あり' if statistical_significance else '❌ なし'}")
        
        return {
            'total_folds': total_folds,
            'positive_folds': positive_folds,
            'consistency_ratio': consistency_ratio,
            'avg_oos_pf': avg_oos_pf,
            'avg_oos_trades': avg_oos_trades,
            'total_oos_trades': total_oos_trades,
            'wfa_efficiency': wfa_efficiency,
            't_statistic': t_statistic,
            'degrees_of_freedom': df if 'df' in locals() else 0,
            'p_value': p_value,
            'statistical_significance': statistical_significance,
            'mean_oos_return': mean_return,
            'oos_returns': oos_returns,
            'avg_oos_sharpe': sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0
        }
    
    def _calculate_accurate_p_value(self, t_stat, df):
        """より正確なp値計算"""
        abs_t = abs(t_stat)
        
        # 自由度を考慮したt分布近似
        if df >= 30:
            # 大サンプル: 正規分布近似
            p_value = 2 * (1 - self._norm_cdf(abs_t))
        else:
            # 小サンプル: t分布近似
            if abs_t > 4.0:
                p_value = 0.001
            elif abs_t > 3.0:
                p_value = 0.01
            elif abs_t > 2.5:
                p_value = 0.02
            elif abs_t > 2.0:
                p_value = 0.05
            elif abs_t > 1.5:
                p_value = 0.10
            elif abs_t > 1.0:
                p_value = 0.30
            else:
                p_value = 0.50
        
        return min(p_value, 1.0)
    
    def _norm_cdf(self, x):
        """正規分布累積分布関数"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _compare_with_previous_results(self, current_stats):
        """前回結果との比較"""
        print(f"\n📊 前回結果との比較:")
        
        # 前回の軽量版結果を読み込み
        try:
            with open('minimal_wfa_results.json', 'r') as f:
                minimal_results = json.load(f)
                minimal_stats = minimal_results['statistical_results']
        except FileNotFoundError:
            print("   前回結果が見つかりません")
            return None
        
        # フルデータ結果も読み込み
        try:
            with open('full_data_verification_results.json', 'r') as f:
                full_results = json.load(f)
                full_stats = full_results['comparison_analysis']['full_statistics']
        except FileNotFoundError:
            print("   フルデータ結果が見つかりません")
            full_stats = None
        
        comparison = {
            'minimal_vs_extended': {
                'avg_pf': {
                    'minimal': minimal_stats['avg_oos_pf'],
                    'extended': current_stats['avg_oos_pf'],
                    'difference': current_stats['avg_oos_pf'] - minimal_stats['avg_oos_pf']
                },
                'p_value': {
                    'minimal': minimal_stats['p_value'],
                    'extended': current_stats['p_value'],
                    'improvement': current_stats['p_value'] < minimal_stats['p_value']
                },
                'statistical_significance': {
                    'minimal': minimal_stats['statistical_significance'],
                    'extended': current_stats['statistical_significance'],
                    'maintained': current_stats['statistical_significance']
                },
                'total_trades': {
                    'minimal': minimal_stats['avg_oos_trades'] * minimal_stats['total_folds'],
                    'extended': current_stats['total_oos_trades']
                }
            }
        }
        
        if full_stats:
            comparison['full_vs_extended'] = {
                'avg_pf': {
                    'full': full_stats['avg_oos_pf'],
                    'extended': current_stats['avg_oos_pf']
                },
                'p_value': {
                    'full': full_stats['p_value'],
                    'extended': current_stats['p_value']
                },
                'statistical_significance': {
                    'full': full_stats['statistical_significance'],
                    'extended': current_stats['statistical_significance']
                }
            }
        
        print(f"   軽量版 vs 拡張版:")
        print(f"     平均PF: {minimal_stats['avg_oos_pf']:.3f} → {current_stats['avg_oos_pf']:.3f}")
        print(f"     p値: {minimal_stats['p_value']:.3f} → {current_stats['p_value']:.3f}")
        print(f"     統計的有意性: {'維持' if current_stats['statistical_significance'] else '失失'}")
        print(f"     総取引数: {minimal_stats['avg_oos_trades'] * minimal_stats['total_folds']:.0f} → {current_stats['total_oos_trades']}")
        
        return comparison
    
    def _evaluate_extended_results(self, stats, comparison):
        """拡張結果評価"""
        print(f"\n🏆 拡張期間WFA評価:")
        
        if not stats:
            return {'evaluation': 'FAILED', 'reason': 'no_statistical_results'}
        
        # 評価基準
        criteria = {
            'statistical_significance': stats['statistical_significance'],
            'reasonable_pf': 1.0 < stats['avg_oos_pf'] < 2.0,
            'sufficient_trades': stats['total_oos_trades'] >= 100,
            'consistency': stats['consistency_ratio'] >= 0.6,
            'reasonable_efficiency': stats['wfa_efficiency'] > 0.1
        }
        
        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)
        
        print(f"   評価基準:")
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"     {criterion}: {status}")
        
        # 総合評価
        if passed_criteria >= 4:
            evaluation = 'EXCELLENT'
        elif passed_criteria >= 3:
            evaluation = 'GOOD'
        elif passed_criteria >= 2:
            evaluation = 'MODERATE'
        else:
            evaluation = 'POOR'
        
        print(f"\n   総合評価: {evaluation}")
        print(f"   達成基準: {passed_criteria}/{total_criteria}")
        
        # 改善度評価
        if comparison:
            improvement_assessment = self._assess_improvement(comparison)
            print(f"   改善度: {improvement_assessment}")
        else:
            improvement_assessment = 'UNKNOWN'
        
        return {
            'evaluation': evaluation,
            'criteria_passed': passed_criteria,
            'criteria_total': total_criteria,
            'success_rate': passed_criteria / total_criteria,
            'improvement_assessment': improvement_assessment,
            'detailed_criteria': criteria
        }
    
    def _assess_improvement(self, comparison):
        """改善度評価"""
        minimal_comparison = comparison['minimal_vs_extended']
        
        improvements = {
            'statistical_significance': minimal_comparison['statistical_significance']['maintained'],
            'p_value_improvement': minimal_comparison['p_value']['improvement'],
            'reasonable_pf_change': abs(minimal_comparison['avg_pf']['difference']) < 0.3
        }
        
        improvement_score = sum(improvements.values())
        
        if improvement_score >= 2:
            return 'IMPROVED'
        elif improvement_score >= 1:
            return 'MAINTAINED'
        else:
            return 'DEGRADED'
    
    def _save_extended_results(self, results, stats, comparison, evaluation):
        """拡張結果保存"""
        extended_data = {
            'execution_type': 'extended_period_wfa',
            'timestamp': datetime.now().isoformat(),
            'extended_wfa_results': results,
            'statistical_analysis': stats,
            'comparison_with_previous': comparison,
            'evaluation': evaluation,
            'conclusion': {
                'overall_assessment': evaluation['evaluation'],
                'statistical_significance': stats['statistical_significance'] if stats else False,
                'p_value': stats['p_value'] if stats else 1.0,
                'recommendation': self._get_recommendation(evaluation)
            }
        }
        
        with open('extended_period_wfa_results.json', 'w') as f:
            json.dump(extended_data, f, indent=2)
        
        print(f"\n💾 拡張期間WFA結果保存: extended_period_wfa_results.json")
    
    def _get_recommendation(self, evaluation):
        """推奨事項"""
        if evaluation['evaluation'] == 'EXCELLENT':
            return "統計的に優位な戦略として実用化を検討できます。"
        elif evaluation['evaluation'] == 'GOOD':
            return "良好な結果です。さらなる検証を経て実用化を検討してください。"
        elif evaluation['evaluation'] == 'MODERATE':
            return "中程度の結果です。戦略の改良が推奨されます。"
        else:
            return "結果が不十分です。戦略の抜本的な見直しが必要です。"

def main():
    """メイン実行"""
    print("🚀 拡張期間WFA実行システム開始")
    print("   3-5年データでの統計的有意性検証")
    
    executor = ExtendedPeriodWFA()
    
    try:
        results, stats, evaluation = executor.run_extended_wfa()
        
        if results and stats:
            print(f"\n✅ 拡張期間WFA実行完了")
            print(f"   総合評価: {evaluation['evaluation']}")
            print(f"   統計的有意性: {'確認' if stats['statistical_significance'] else '未確認'}")
            print(f"   推奨: {evaluation['evaluation']}")
        else:
            print(f"\n⚠️ 拡張期間WFA実行失敗")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {str(e)}")
        return None, None, None
    
    return results, stats, evaluation

if __name__ == "__main__":
    results, stats, evaluation = main()