#!/usr/bin/env python3
"""
最小限WFA実行システム
タイムアウト対策と統計的有意性の実証
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
import json
import math
from datetime import datetime, timedelta

class MinimalWFAExecution:
    """最小限WFA実行システム"""
    
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
        
    def run_minimal_wfa(self):
        """最小限WFA実行"""
        print("🚀 最小限WFA実行開始")
        print("   目標: 統計的有意性の実証")
        
        # 完全データ取得（汚染源修正）
        raw_data = self.cache_manager.get_full_data()
        # ultra_light_data = raw_data[::10]  # 🚨 CONTAMINATED: 90%データ破棄による統計的信頼性破綻
        full_data = raw_data  # 完全データを使用
        
        print(f"\n📊 データ情報:")
        print(f"   使用データ: {len(full_data):,}バー（完全データ）")
        
        # シンプルWFA実行
        wfa_results = self._execute_simple_wfa(full_data)
        
        if not wfa_results:
            print("⚠️ WFA実行失敗")
            return None, None
        
        # 統計的分析
        statistical_results = self._perform_statistical_analysis(wfa_results)
        
        # 最終判定
        final_judgment = self._final_judgment(statistical_results)
        
        return wfa_results, statistical_results, final_judgment
    
    def _execute_simple_wfa(self, data):
        """シンプルWFA実行"""
        print(f"\n📋 シンプルWFA実行:")
        
        # データ期間確認
        start_date = data[0]['datetime']
        end_date = data[-1]['datetime']
        total_days = (end_date - start_date).days
        
        if total_days < 180:  # 6ヶ月未満の場合
            print(f"   データ期間不足: {total_days}日 < 180日")
            return None
        
        # 3フォールドのみで実行
        folds = self._create_minimal_folds(data)
        
        if len(folds) < 3:
            print(f"   フォールド不足: {len(folds)}個")
            return None
        
        print(f"   フォールド数: {len(folds)}")
        
        # 各フォールド実行
        results = []
        
        for i, fold in enumerate(folds, 1):
            print(f"   フォールド{i}: {fold['is_start'].strftime('%Y-%m')} - {fold['oos_end'].strftime('%Y-%m')}")
            
            try:
                # ISデータ取得
                is_data = [bar for bar in data if fold['is_start'] <= bar['datetime'] <= fold['is_end']]
                oos_data = [bar for bar in data if fold['oos_start'] <= bar['datetime'] <= fold['oos_end']]
                
                if len(is_data) < 100 or len(oos_data) < 50:
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
                    'oos_win_rate': oos_result['win_rate']
                }
                
                results.append(fold_result)
                print(f"     IS: PF={is_result['profit_factor']:.3f}, 取引={is_result['total_trades']}")
                print(f"     OOS: PF={oos_result['profit_factor']:.3f}, 取引={oos_result['total_trades']}")
                
            except Exception as e:
                print(f"     エラー: {str(e)}")
                continue
        
        return results
    
    def _create_minimal_folds(self, data):
        """最小限フォールド作成"""
        start_date = data[0]['datetime']
        end_date = data[-1]['datetime']
        total_days = (end_date - start_date).days
        
        # 4ヶ月IS / 2ヶ月OOS / 2ヶ月ステップ
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
            
            if fold_id > 5:  # 最大5フォールド
                break
        
        return folds
    
    def _perform_statistical_analysis(self, wfa_results):
        """統計的分析"""
        print(f"\n🔬 統計的分析:")
        
        if not wfa_results:
            return None
        
        # 基本統計
        total_folds = len(wfa_results)
        positive_folds = sum(1 for r in wfa_results if r['oos_return'] > 0)
        consistency_ratio = positive_folds / total_folds if total_folds > 0 else 0
        
        # OOS平均値
        avg_oos_pf = sum(r['oos_pf'] for r in wfa_results) / len(wfa_results)
        avg_oos_trades = sum(r['oos_trades'] for r in wfa_results) / len(wfa_results)
        oos_returns = [r['oos_return'] for r in wfa_results]
        
        # WFA効率
        total_is_return = sum(r['is_return'] for r in wfa_results)
        total_oos_return = sum(r['oos_return'] for r in wfa_results)
        wfa_efficiency = total_oos_return / total_is_return if total_is_return > 0 else 0
        
        # t検定実行
        if len(oos_returns) > 1:
            mean_return = sum(oos_returns) / len(oos_returns)
            
            # 分散計算
            variance = sum((r - mean_return) ** 2 for r in oos_returns) / (len(oos_returns) - 1)
            std_error = math.sqrt(variance / len(oos_returns)) if variance > 0 else 0.001
            
            # t統計量
            t_statistic = mean_return / std_error if std_error > 0 else 0
            
            # 自由度
            df = len(oos_returns) - 1
            
            # p値計算（簡易版）
            p_value = self._calculate_p_value(t_statistic, df)
            
        else:
            mean_return = oos_returns[0] if oos_returns else 0
            t_statistic = 0
            p_value = 1.0
        
        statistical_significance = p_value < 0.05
        
        print(f"   フォールド数: {total_folds}")
        print(f"   正の結果: {positive_folds}/{total_folds} ({consistency_ratio:.1%})")
        print(f"   平均OOS PF: {avg_oos_pf:.3f}")
        print(f"   平均取引数: {avg_oos_trades:.0f}")
        print(f"   WFA効率: {wfa_efficiency:.3f}")
        print(f"   t統計量: {t_statistic:.3f}")
        print(f"   p値: {p_value:.4f}")
        print(f"   統計的有意性: {'✅ あり' if statistical_significance else '❌ なし'}")
        
        return {
            'total_folds': total_folds,
            'positive_folds': positive_folds,
            'consistency_ratio': consistency_ratio,
            'avg_oos_pf': avg_oos_pf,
            'avg_oos_trades': avg_oos_trades,
            'wfa_efficiency': wfa_efficiency,
            't_statistic': t_statistic,
            'p_value': p_value,
            'statistical_significance': statistical_significance,
            'mean_oos_return': mean_return
        }
    
    def _calculate_p_value(self, t_stat, df):
        """簡易p値計算"""
        # 簡易版：t分布の近似
        abs_t = abs(t_stat)
        
        if df >= 10:
            # 正規分布近似
            p_value = 2 * (1 - self._norm_cdf(abs_t))
        else:
            # 簡易t分布近似
            if abs_t > 3.0:
                p_value = 0.01
            elif abs_t > 2.5:
                p_value = 0.02
            elif abs_t > 2.0:
                p_value = 0.05
            elif abs_t > 1.5:
                p_value = 0.10
            else:
                p_value = 0.20
        
        return min(p_value, 1.0)
    
    def _norm_cdf(self, x):
        """正規分布累積分布関数"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _final_judgment(self, stats):
        """最終判定"""
        print(f"\n🏆 最終判定:")
        
        if not stats:
            return {'success': False, 'reason': 'statistical_analysis_failed'}
        
        # 判定基準
        criteria = {
            'statistical_significance': stats['statistical_significance'],
            'avg_pf_above_1_05': stats['avg_oos_pf'] >= 1.05,
            'consistency_above_50': stats['consistency_ratio'] >= 0.5,
            'sufficient_trades': stats['avg_oos_trades'] >= 10
        }
        
        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)
        
        print(f"   判定基準:")
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"     {criterion}: {status}")
        
        # 最終判定
        reform_success = passed_criteria >= 3  # 4基準中3つ以上
        
        print(f"\n🎊 最終判定: {'✅ 成功' if reform_success else '❌ 部分的成功'}")
        print(f"   達成基準: {passed_criteria}/{total_criteria}")
        
        if reform_success:
            print(f"\n🏅 6週間改革プラン真の完遂！")
            if stats['statistical_significance']:
                print(f"   🔬 統計的有意性確認 (p={stats['p_value']:.3f})")
            print(f"   🚀 科学的システムトレーダーへの進化完遂")
        
        return {
            'reform_success': reform_success,
            'criteria_passed': passed_criteria,
            'criteria_total': total_criteria,
            'success_rate': passed_criteria / total_criteria,
            'statistical_significance': stats['statistical_significance'],
            'p_value': stats['p_value']
        }

def main():
    """メイン実行"""
    print("🚀 最小限WFA実行開始")
    print("   真の統計的有意性の実証")
    
    executor = MinimalWFAExecution()
    
    try:
        wfa_results, statistical_results, final_judgment = executor.run_minimal_wfa()
        
        if wfa_results and statistical_results:
            print(f"\n✅ 最小限WFA実行完了")
            
            # 結果保存
            results = {
                'execution_type': 'minimal_wfa',
                'timestamp': datetime.now().isoformat(),
                'wfa_results': wfa_results,
                'statistical_results': statistical_results,
                'final_judgment': final_judgment
            }
            
            with open('minimal_wfa_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 結果保存: minimal_wfa_results.json")
            
        else:
            print(f"\n⚠️ 最小限WFA実行失敗")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {str(e)}")
        return None, None, None
    
    return wfa_results, statistical_results, final_judgment

if __name__ == "__main__":
    wfa_results, stats, judgment = main()