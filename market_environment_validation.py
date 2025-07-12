#!/usr/bin/env python3
"""
市場環境検証システム
2020-2024年の異なる市場環境での戦略性能検証
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
import json
import math
from datetime import datetime, timedelta

class MarketEnvironmentValidation:
    """市場環境検証システム"""
    
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
        
    def run_market_environment_validation(self):
        """市場環境検証実行"""
        print("🚀 市場環境検証実行開始")
        print("   目標: 2020-2024年の異なる市場環境での性能検証")
        
        # データ取得と期間分割
        raw_data = self.cache_manager.get_full_data()
        light_data = raw_data[::3]  # 軽量化
        
        print(f"\n📊 データ情報:")
        print(f"   総データ: {len(light_data):,}バー")
        print(f"   期間: {light_data[0]['datetime'].strftime('%Y-%m-%d')} - {light_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        
        # 市場環境別分析
        market_periods = self._define_market_periods(light_data)
        
        # 各市場環境での検証
        environment_results = self._validate_across_environments(light_data, market_periods)
        
        if not environment_results:
            print("❌ 市場環境検証失敗")
            return None
        
        # 環境間比較分析
        cross_environment_analysis = self._analyze_cross_environment_performance(environment_results)
        
        # 市場適応性評価
        adaptability_assessment = self._assess_market_adaptability(cross_environment_analysis)
        
        # 結果保存
        self._save_market_validation_results(environment_results, cross_environment_analysis, adaptability_assessment)
        
        return environment_results, cross_environment_analysis, adaptability_assessment
    
    def _define_market_periods(self, data):
        """市場環境期間定義"""
        print(f"\n📊 市場環境期間定義:")
        
        start_date = data[0]['datetime']
        end_date = data[-1]['datetime']
        
        # 市場環境の定義
        periods = {
            'covid_crash': {
                'name': 'COVID-19クラッシュ期',
                'start': datetime(2020, 1, 1),
                'end': datetime(2020, 6, 30),
                'characteristics': '極度のボラティリティ、急落、急反発'
            },
            'recovery_bull': {
                'name': '回復ブルマーケット期',
                'start': datetime(2020, 7, 1),
                'end': datetime(2021, 12, 31),
                'characteristics': '強い上昇トレンド、低ボラティリティ'
            },
            'inflation_concerns': {
                'name': 'インフレ懸念期',
                'start': datetime(2022, 1, 1),
                'end': datetime(2022, 12, 31),
                'characteristics': '金利上昇、インフレ懸念、不安定な相場'
            },
            'normalization': {
                'name': '正常化期',
                'start': datetime(2023, 1, 1),
                'end': min(datetime(2024, 4, 26), end_date),
                'characteristics': '正常化、温和なボラティリティ'
            }
        }
        
        # 実際のデータ範囲で調整
        valid_periods = {}
        for period_name, period_info in periods.items():
            if period_info['start'] >= start_date and period_info['end'] <= end_date:
                valid_periods[period_name] = period_info
                print(f"   {period_info['name']}: {period_info['start'].strftime('%Y-%m-%d')} - {period_info['end'].strftime('%Y-%m-%d')}")
                print(f"     特徴: {period_info['characteristics']}")
        
        return valid_periods
    
    def _validate_across_environments(self, data, market_periods):
        """各市場環境での検証"""
        print(f"\n📋 各市場環境での検証:")
        
        environment_results = {}
        
        for period_name, period_info in market_periods.items():
            print(f"\n   ▶️ {period_info['name']} 検証:")
            
            # 期間データ抽出
            period_data = [
                bar for bar in data 
                if period_info['start'] <= bar['datetime'] <= period_info['end']
            ]
            
            if len(period_data) < 100:
                print(f"     データ不足: {len(period_data)}バー")
                continue
            
            print(f"     データ: {len(period_data)}バー")
            
            # 期間内でのWFA実行
            period_wfa_results = self._execute_period_wfa(period_data, period_info)
            
            if period_wfa_results:
                environment_results[period_name] = {
                    'period_info': period_info,
                    'wfa_results': period_wfa_results,
                    'statistics': self._calculate_period_statistics(period_wfa_results)
                }
            
        return environment_results
    
    def _execute_period_wfa(self, period_data, period_info):
        """期間内WFA実行"""
        if len(period_data) < 200:
            return None
        
        # 期間内での簡易WFA
        total_days = (period_data[-1]['datetime'] - period_data[0]['datetime']).days
        
        if total_days < 120:  # 4ヶ月未満の場合
            # 単一フォールドで実行
            return self._execute_single_fold(period_data, period_info)
        else:
            # 複数フォールドで実行
            return self._execute_multiple_folds(period_data, period_info)
    
    def _execute_single_fold(self, period_data, period_info):
        """単一フォールド実行"""
        # 70%/30%分割
        split_point = int(len(period_data) * 0.7)
        is_data = period_data[:split_point]
        oos_data = period_data[split_point:]
        
        try:
            strategy = MultiTimeframeBreakoutStrategy(self.final_params)
            
            is_mtf = MultiTimeframeData(is_data)
            oos_mtf = MultiTimeframeData(oos_data)
            
            is_start = is_data[0]['datetime']
            is_end = is_data[-1]['datetime']
            oos_start = oos_data[0]['datetime']
            oos_end = oos_data[-1]['datetime']
            
            # IS期間
            is_result = strategy.backtest(is_mtf, is_start, is_end)
            
            # OOS期間
            oos_result = strategy.backtest(oos_mtf, oos_start, oos_end)
            
            fold_result = {
                'fold_id': 1,
                'fold_type': 'single',
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
            
            print(f"     単一フォールド: IS PF={is_result['profit_factor']:.3f}, OOS PF={oos_result['profit_factor']:.3f}")
            print(f"     取引数: IS={is_result['total_trades']}, OOS={oos_result['total_trades']}")
            
            return [fold_result]
            
        except Exception as e:
            print(f"     エラー: {str(e)}")
            return None
    
    def _execute_multiple_folds(self, period_data, period_info):
        """複数フォールド実行"""
        # 3ヶ月IS / 2ヶ月OOS / 1ヶ月ステップ
        is_days = 90
        oos_days = 60
        step_days = 30
        
        start_date = period_data[0]['datetime']
        end_date = period_data[-1]['datetime']
        
        folds = []
        current_start = start_date
        fold_id = 1
        
        while True:
            is_end = current_start + timedelta(days=is_days)
            if is_end > end_date:
                break
            
            oos_start = is_end
            oos_end = oos_start + timedelta(days=oos_days)
            if oos_end > end_date:
                break
            
            # データ取得
            is_data = [bar for bar in period_data if current_start <= bar['datetime'] <= is_end]
            oos_data = [bar for bar in period_data if oos_start <= bar['datetime'] <= oos_end]
            
            if len(is_data) < 50 or len(oos_data) < 30:
                current_start += timedelta(days=step_days)
                continue
            
            try:
                strategy = MultiTimeframeBreakoutStrategy(self.final_params)
                
                is_mtf = MultiTimeframeData(is_data)
                oos_mtf = MultiTimeframeData(oos_data)
                
                is_result = strategy.backtest(is_mtf, current_start, is_end)
                oos_result = strategy.backtest(oos_mtf, oos_start, oos_end)
                
                fold_result = {
                    'fold_id': fold_id,
                    'fold_type': 'multiple',
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
                
                folds.append(fold_result)
                print(f"     フォールド{fold_id}: IS PF={is_result['profit_factor']:.3f}, OOS PF={oos_result['profit_factor']:.3f}")
                
                fold_id += 1
                
            except Exception as e:
                print(f"     フォールド{fold_id} エラー: {str(e)}")
            
            current_start += timedelta(days=step_days)
            
            if fold_id > 6:  # 最大6フォールド
                break
        
        return folds if folds else None
    
    def _calculate_period_statistics(self, period_results):
        """期間統計計算"""
        if not period_results:
            return None
        
        # 基本統計
        total_folds = len(period_results)
        positive_folds = sum(1 for r in period_results if r['oos_return'] > 0)
        consistency_ratio = positive_folds / total_folds
        
        avg_oos_pf = sum(r['oos_pf'] for r in period_results) / len(period_results)
        avg_oos_trades = sum(r['oos_trades'] for r in period_results) / len(period_results)
        total_oos_trades = sum(r['oos_trades'] for r in period_results)
        
        oos_returns = [r['oos_return'] for r in period_results]
        
        # 簡易統計検定
        if len(oos_returns) > 1:
            mean_return = sum(oos_returns) / len(oos_returns)
            variance = sum((r - mean_return) ** 2 for r in oos_returns) / len(oos_returns)
            std_return = math.sqrt(variance) if variance > 0 else 0.001
            
            t_statistic = (mean_return - 0) / (std_return / math.sqrt(len(oos_returns)))
            
            # 簡易p値
            abs_t = abs(t_statistic)
            if abs_t > 2.0:
                p_value = 0.05
            elif abs_t > 1.5:
                p_value = 0.10
            else:
                p_value = 0.20
        else:
            mean_return = oos_returns[0] if oos_returns else 0
            t_statistic = 0
            p_value = 1.0
        
        return {
            'total_folds': total_folds,
            'positive_folds': positive_folds,
            'consistency_ratio': consistency_ratio,
            'avg_oos_pf': avg_oos_pf,
            'avg_oos_trades': avg_oos_trades,
            'total_oos_trades': total_oos_trades,
            'mean_oos_return': mean_return,
            't_statistic': t_statistic,
            'p_value': p_value,
            'statistical_significance': p_value < 0.05
        }
    
    def _analyze_cross_environment_performance(self, environment_results):
        """環境間性能分析"""
        print(f"\n🔍 環境間性能分析:")
        
        if not environment_results:
            return None
        
        # 環境別性能サマリー
        environment_summary = {}
        
        for env_name, env_data in environment_results.items():
            stats = env_data['statistics']
            if stats:
                environment_summary[env_name] = {
                    'period_name': env_data['period_info']['name'],
                    'avg_pf': stats['avg_oos_pf'],
                    'consistency': stats['consistency_ratio'],
                    'total_trades': stats['total_oos_trades'],
                    'statistical_significance': stats['statistical_significance'],
                    'p_value': stats['p_value']
                }
                
                print(f"   {env_data['period_info']['name']}:")
                print(f"     平均PF: {stats['avg_oos_pf']:.3f}")
                print(f"     一貫性: {stats['consistency_ratio']:.1%}")
                print(f"     総取引数: {stats['total_oos_trades']}")
                print(f"     統計的有意性: {'✅' if stats['statistical_significance'] else '❌'}")
        
        # 環境間比較
        cross_analysis = self._perform_cross_environment_analysis(environment_summary)
        
        return {
            'environment_summary': environment_summary,
            'cross_analysis': cross_analysis
        }
    
    def _perform_cross_environment_analysis(self, environment_summary):
        """環境間分析実行"""
        if len(environment_summary) < 2:
            return None
        
        # 性能変動を分析
        pf_values = [env['avg_pf'] for env in environment_summary.values()]
        consistency_values = [env['consistency'] for env in environment_summary.values()]
        
        # 統計指標
        avg_pf = sum(pf_values) / len(pf_values)
        pf_std = math.sqrt(sum((pf - avg_pf) ** 2 for pf in pf_values) / len(pf_values))
        pf_cv = pf_std / avg_pf if avg_pf > 0 else 0  # 変動係数
        
        avg_consistency = sum(consistency_values) / len(consistency_values)
        
        # 統計的有意性の環境
        significant_environments = sum(1 for env in environment_summary.values() if env['statistical_significance'])
        
        print(f"\n   環境間性能分析:")
        print(f"     平均PF: {avg_pf:.3f} (標準偏差: {pf_std:.3f})")
        print(f"     PF変動係数: {pf_cv:.3f}")
        print(f"     平均一貫性: {avg_consistency:.1%}")
        print(f"     統計的有意性環境: {significant_environments}/{len(environment_summary)}")
        
        return {
            'avg_pf_across_environments': avg_pf,
            'pf_standard_deviation': pf_std,
            'pf_coefficient_of_variation': pf_cv,
            'avg_consistency_across_environments': avg_consistency,
            'significant_environments': significant_environments,
            'total_environments': len(environment_summary),
            'performance_stability': 'HIGH' if pf_cv < 0.2 else 'MEDIUM' if pf_cv < 0.4 else 'LOW'
        }
    
    def _assess_market_adaptability(self, cross_analysis):
        """市場適応性評価"""
        print(f"\n🏆 市場適応性評価:")
        
        if not cross_analysis:
            return {'adaptability': 'UNKNOWN', 'reason': 'insufficient_data'}
        
        cross_stats = cross_analysis['cross_analysis']
        
        # 適応性判定基準
        criteria = {
            'performance_stability': cross_stats['performance_stability'] in ['HIGH', 'MEDIUM'],
            'positive_avg_pf': cross_stats['avg_pf_across_environments'] > 1.0,
            'reasonable_consistency': cross_stats['avg_consistency_across_environments'] > 0.5,
            'some_significance': cross_stats['significant_environments'] > 0
        }
        
        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)
        
        print(f"   適応性判定基準:")
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"     {criterion}: {status}")
        
        # 適応性レベル判定
        if passed_criteria >= 4:
            adaptability = 'HIGH'
        elif passed_criteria >= 3:
            adaptability = 'MEDIUM'
        elif passed_criteria >= 2:
            adaptability = 'LOW'
        else:
            adaptability = 'POOR'
        
        print(f"\n   市場適応性: {adaptability}")
        print(f"   達成基準: {passed_criteria}/{total_criteria}")
        
        return {
            'adaptability': adaptability,
            'criteria_passed': passed_criteria,
            'criteria_total': total_criteria,
            'success_rate': passed_criteria / total_criteria,
            'detailed_criteria': criteria,
            'performance_across_environments': cross_stats,
            'recommendation': self._get_adaptability_recommendation(adaptability, cross_stats)
        }
    
    def _get_adaptability_recommendation(self, adaptability, cross_stats):
        """適応性推奨事項"""
        if adaptability == 'HIGH':
            return "戦略は異なる市場環境でも安定して機能します。実用化を推奨します。"
        elif adaptability == 'MEDIUM':
            return "戦略はおおむね市場環境に適応します。注意深く実用化を検討してください。"
        elif adaptability == 'LOW':
            return "戦略は特定の市場環境でのみ機能します。改善が必要です。"
        else:
            return "戦略は市場環境に適応していません。抜本的な見直しが必要です。"
    
    def _save_market_validation_results(self, environment_results, cross_analysis, adaptability):
        """市場検証結果保存"""
        validation_data = {
            'validation_type': 'market_environment_validation',
            'timestamp': datetime.now().isoformat(),
            'environment_results': environment_results,
            'cross_environment_analysis': cross_analysis,
            'adaptability_assessment': adaptability,
            'final_conclusion': {
                'market_adaptability': adaptability['adaptability'],
                'recommendation': adaptability['recommendation'],
                'validation_summary': self._create_validation_summary(environment_results, adaptability)
            }
        }
        
        # JSONシリアライズ用に日付を文字列に変換
        self._convert_dates_to_strings(validation_data)
        
        with open('market_environment_validation_results.json', 'w') as f:
            json.dump(validation_data, f, indent=2)
        
        print(f"\n💾 市場環境検証結果保存: market_environment_validation_results.json")
    
    def _convert_dates_to_strings(self, data):
        """日付を文字列に変換"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._convert_dates_to_strings(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._convert_dates_to_strings(item)
    
    def _create_validation_summary(self, environment_results, adaptability):
        """検証サマリー作成"""
        environments_tested = len(environment_results)
        successful_environments = sum(
            1 for env_data in environment_results.values() 
            if env_data['statistics'] and env_data['statistics']['avg_oos_pf'] > 1.0
        )
        
        return {
            'environments_tested': environments_tested,
            'successful_environments': successful_environments,
            'success_rate': successful_environments / environments_tested if environments_tested > 0 else 0,
            'overall_adaptability': adaptability['adaptability'],
            'ready_for_implementation': adaptability['adaptability'] in ['HIGH', 'MEDIUM']
        }

def main():
    """メイン実行"""
    print("🚀 市場環境検証システム開始")
    print("   2020-2024年の異なる市場環境での戦略検証")
    
    validator = MarketEnvironmentValidation()
    
    try:
        environment_results, cross_analysis, adaptability = validator.run_market_environment_validation()
        
        if environment_results and cross_analysis and adaptability:
            print(f"\n✅ 市場環境検証完了")
            print(f"   市場適応性: {adaptability['adaptability']}")
            print(f"   推奨事項: {adaptability['recommendation']}")
        else:
            print(f"\n⚠️ 市場環境検証失敗")
            
    except Exception as e:
        print(f"\n❌ エラー発生: {str(e)}")
        return None, None, None
    
    return environment_results, cross_analysis, adaptability

if __name__ == "__main__":
    environment_results, cross_analysis, adaptability = main()