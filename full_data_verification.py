#!/usr/bin/env python3
"""
フルデータ検証システム
軽量版結果とフルデータ結果の比較検証
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
import json
import math
from datetime import datetime, timedelta
import os

class FullDataVerification:
    """フルデータ検証システム"""
    
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
        
        # 軽量版結果を読み込み
        self.light_results = self._load_light_results()
        
    def _load_light_results(self):
        """軽量版結果読み込み"""
        try:
            with open('minimal_wfa_results.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ 軽量版結果が見つかりません")
            return None
    
    def run_full_verification(self):
        """フルデータ検証実行"""
        print("🔍 フルデータ検証実行開始")
        print("   目標: 軽量版結果の信頼性確認")
        
        # フルデータ取得
        print("\n📊 フルデータ取得中...")
        raw_data = self.cache_manager.get_full_data()
        
        print(f"   フルデータ: {len(raw_data):,}バー")
        print(f"   期間: {raw_data[0]['datetime'].strftime('%Y-%m-%d')} - {raw_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        
        # 軽量版と同じ期間でのフルデータ検証
        full_wfa_results = self._execute_full_wfa(raw_data)
        
        if not full_wfa_results:
            print("❌ フルデータ検証失敗")
            return None
        
        # 結果比較分析
        comparison_results = self._compare_results(full_wfa_results)
        
        # 信頼性評価
        reliability_assessment = self._assess_reliability(comparison_results)
        
        # 結果保存
        self._save_verification_results(full_wfa_results, comparison_results, reliability_assessment)
        
        return full_wfa_results, comparison_results, reliability_assessment
    
    def _execute_full_wfa(self, raw_data):
        """フルデータでのWFA実行"""
        print(f"\n📋 フルデータでのWFA実行:")
        
        # 軽量版と同じ期間でフォールド作成
        folds = self._create_matching_folds(raw_data)
        
        if len(folds) < 3:
            print(f"   フォールド不足: {len(folds)}個")
            return None
        
        print(f"   フォールド数: {len(folds)}")
        
        results = []
        
        for i, fold in enumerate(folds, 1):
            print(f"   フォールド{i}: {fold['is_start'].strftime('%Y-%m')} - {fold['oos_end'].strftime('%Y-%m')}")
            
            try:
                # フルデータでの期間データ取得
                is_data = [bar for bar in raw_data if fold['is_start'] <= bar['datetime'] <= fold['is_end']]
                oos_data = [bar for bar in raw_data if fold['oos_start'] <= bar['datetime'] <= fold['oos_end']]
                
                if len(is_data) < 500 or len(oos_data) < 250:
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
    
    def _create_matching_folds(self, raw_data):
        """軽量版と同じ期間のフォールド作成"""
        start_date = raw_data[0]['datetime']
        end_date = raw_data[-1]['datetime']
        
        # 軽量版と同じ設定
        is_days = 120  # 4ヶ月
        oos_days = 60  # 2ヶ月
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
            
            # 次のフォールド
            current_start = start_date  # アンカード
            is_days += step_days
            fold_id += 1
            
            if fold_id > 5:
                break
        
        return folds
    
    def _compare_results(self, full_results):
        """結果比較分析"""
        print(f"\n🔍 結果比較分析:")
        
        if not self.light_results or not full_results:
            print("   比較データ不足")
            return None
        
        light_wfa = self.light_results['wfa_results']
        full_wfa = full_results
        
        # フォールド別比較
        fold_comparisons = []
        
        for i in range(min(len(light_wfa), len(full_wfa))):
            light_fold = light_wfa[i]
            full_fold = full_wfa[i]
            
            comparison = {
                'fold_id': i + 1,
                'light_oos_pf': light_fold['oos_pf'],
                'full_oos_pf': full_fold['oos_pf'],
                'pf_difference': full_fold['oos_pf'] - light_fold['oos_pf'],
                'light_oos_trades': light_fold['oos_trades'],
                'full_oos_trades': full_fold['oos_trades'],
                'trades_ratio': full_fold['oos_trades'] / light_fold['oos_trades'] if light_fold['oos_trades'] > 0 else 0
            }
            
            fold_comparisons.append(comparison)
            
            print(f"   フォールド{i+1}:")
            print(f"     PF: {light_fold['oos_pf']:.3f} → {full_fold['oos_pf']:.3f} (差: {comparison['pf_difference']:+.3f})")
            print(f"     取引: {light_fold['oos_trades']} → {full_fold['oos_trades']} (倍率: {comparison['trades_ratio']:.1f}x)")
        
        # 全体比較
        light_stats = self.light_results['statistical_results']
        full_stats = self._calculate_full_stats(full_results)
        
        overall_comparison = {
            'avg_pf_light': light_stats['avg_oos_pf'],
            'avg_pf_full': full_stats['avg_oos_pf'],
            'pf_consistency': abs(full_stats['avg_oos_pf'] - light_stats['avg_oos_pf']) / light_stats['avg_oos_pf'],
            'p_value_light': light_stats['p_value'],
            'p_value_full': full_stats['p_value'],
            'significance_maintained': full_stats['statistical_significance']
        }
        
        print(f"\n   全体比較:")
        print(f"     平均PF: {light_stats['avg_oos_pf']:.3f} → {full_stats['avg_oos_pf']:.3f}")
        print(f"     PF一貫性: {overall_comparison['pf_consistency']:.1%} 誤差")
        print(f"     p値: {light_stats['p_value']:.3f} → {full_stats['p_value']:.3f}")
        print(f"     統計的有意性: {'維持' if full_stats['statistical_significance'] else '失失'}")
        
        return {
            'fold_comparisons': fold_comparisons,
            'overall_comparison': overall_comparison,
            'full_statistics': full_stats
        }
    
    def _calculate_full_stats(self, full_results):
        """フルデータ結果の統計計算"""
        if not full_results:
            return None
        
        # 基本統計
        total_folds = len(full_results)
        positive_folds = sum(1 for r in full_results if r['oos_return'] > 0)
        consistency_ratio = positive_folds / total_folds
        
        avg_oos_pf = sum(r['oos_pf'] for r in full_results) / len(full_results)
        oos_returns = [r['oos_return'] for r in full_results]
        
        # t検定
        if len(oos_returns) > 1:
            mean_return = sum(oos_returns) / len(oos_returns)
            variance = sum((r - mean_return) ** 2 for r in oos_returns) / (len(oos_returns) - 1)
            std_error = math.sqrt(variance / len(oos_returns)) if variance > 0 else 0.001
            t_statistic = mean_return / std_error if std_error > 0 else 0
            
            # p値計算
            abs_t = abs(t_statistic)
            if abs_t > 2.5:
                p_value = 0.02
            elif abs_t > 2.0:
                p_value = 0.05
            elif abs_t > 1.5:
                p_value = 0.10
            else:
                p_value = 0.20
        else:
            t_statistic = 0
            p_value = 1.0
        
        return {
            'avg_oos_pf': avg_oos_pf,
            'consistency_ratio': consistency_ratio,
            't_statistic': t_statistic,
            'p_value': p_value,
            'statistical_significance': p_value < 0.05
        }
    
    def _assess_reliability(self, comparison_results):
        """信頼性評価"""
        print(f"\n🔍 信頼性評価:")
        
        if not comparison_results:
            return {'reliability': 'LOW', 'reason': 'comparison_failed'}
        
        overall = comparison_results['overall_comparison']
        
        # 信頼性判定基準
        criteria = {
            'pf_consistency': overall['pf_consistency'] < 0.2,  # 20%以内の誤差
            'significance_maintained': overall['significance_maintained'],
            'reasonable_pf_range': 1.0 < overall['avg_pf_full'] < 3.0
        }
        
        passed_criteria = sum(criteria.values())
        
        if passed_criteria >= 3:
            reliability = 'HIGH'
        elif passed_criteria >= 2:
            reliability = 'MEDIUM'
        else:
            reliability = 'LOW'
        
        print(f"   信頼性評価: {reliability}")
        
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"     {criterion}: {status}")
        
        return {
            'reliability': reliability,
            'criteria': criteria,
            'passed_criteria': passed_criteria,
            'assessment': self._get_reliability_assessment(reliability, criteria)
        }
    
    def _get_reliability_assessment(self, reliability, criteria):
        """信頼性評価コメント"""
        if reliability == 'HIGH':
            return "軽量版結果はフルデータでも再現され、高い信頼性を示しています。"
        elif reliability == 'MEDIUM':
            return "軽量版結果はおおむね信頼できますが、さらなる検証が推奨されます。"
        else:
            return "軽量版結果は信頼性が低く、慶重な検証が必要です。"
    
    def _save_verification_results(self, full_results, comparison, reliability):
        """検証結果保存"""
        verification_data = {
            'verification_type': 'full_data_verification',
            'timestamp': datetime.now().isoformat(),
            'full_wfa_results': full_results,
            'comparison_analysis': comparison,
            'reliability_assessment': reliability,
            'conclusion': {
                'reliability_level': reliability['reliability'],
                'recommendation': reliability['assessment']
            }
        }
        
        with open('full_data_verification_results.json', 'w') as f:
            json.dump(verification_data, f, indent=2)
        
        print(f"\n💾 検証結果保存: full_data_verification_results.json")

def main():
    """メイン実行"""
    print("🔍 フルデータ検証システム開始")
    print("   軽量版結果の信頼性確認")
    
    verifier = FullDataVerification()
    
    try:
        full_results, comparison, reliability = verifier.run_full_verification()
        
        if full_results and comparison and reliability:
            print(f"\n✅ フルデータ検証完了")
            print(f"   信頼性レベル: {reliability['reliability']}")
            print(f"   推奨事項: {reliability['assessment']}")
        else:
            print(f"\n⚠️ フルデータ検証失敗")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {str(e)}")
        return None, None, None
    
    return full_results, comparison, reliability

if __name__ == "__main__":
    full_results, comparison, reliability = main()