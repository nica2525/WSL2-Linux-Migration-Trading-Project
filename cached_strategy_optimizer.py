#!/usr/bin/env python3
"""
キャッシュ活用戦略最適化
品質優先5年データでのパラメータ最適化
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
from datetime import datetime, timedelta
import itertools
import json

class CachedStrategyOptimizer:
    """キャッシュ活用戦略最適化クラス"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
    def run_full_optimization(self):
        """フル最適化実行"""
        print("🚀 品質優先フル最適化実行開始")
        
        # キャッシュからフルデータ取得
        raw_data = self.cache_manager.get_full_data()
        mtf_data = MultiTimeframeData(raw_data)
        
        print(f"📊 データ構築完了:")
        print(f"   M5: {len(raw_data)}バー")
        print(f"   H1: {len(mtf_data.h1_data)}バー")
        print(f"   H4: {len(mtf_data.h4_data)}バー")
        print(f"   期間: {raw_data[0]['datetime'].strftime('%Y-%m-%d')} to {raw_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        
        # IS/OOS分割（70/30）
        total_days = (raw_data[-1]['datetime'] - raw_data[0]['datetime']).days
        is_end_date = raw_data[0]['datetime'] + timedelta(days=int(total_days * 0.7))
        
        print(f"📈 データ分割:")
        print(f"   IS期間: {raw_data[0]['datetime'].strftime('%Y-%m-%d')} to {is_end_date.strftime('%Y-%m-%d')}")
        print(f"   OOS期間: {is_end_date.strftime('%Y-%m-%d')} to {raw_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        
        # パラメータ最適化実行
        best_params, best_is_result = self._optimize_parameters(
            mtf_data, 
            raw_data[0]['datetime'], 
            is_end_date
        )
        
        # 最適パラメータでOOS検証
        print(f"\n📊 最適パラメータでのOOS検証")
        optimized_strategy = MultiTimeframeBreakoutStrategy(best_params)
        oos_result = optimized_strategy.backtest(mtf_data, is_end_date, raw_data[-1]['datetime'])
        
        # 結果表示と判定
        self._display_results(best_params, best_is_result, oos_result)
        
        # 設定保存
        self._save_results(best_params, best_is_result, oos_result)
        
        return best_params, best_is_result, oos_result
    
    def _optimize_parameters(self, mtf_data, is_start_date, is_end_date):
        """パラメータ最適化実行"""
        print(f"\n🔍 パラメータ最適化実行")
        
        # パラメータ範囲（厳選版）
        param_ranges = {
            'profit_atr': [2.2, 2.5, 2.8],      # 利確ATR倍数（拡大重視）
            'stop_atr': [1.2, 1.5],             # 損切ATR倍数
            'min_break_pips': [4, 6]            # 最小ブレイク幅
        }
        
        # 固定パラメータ（追加）
        param_ranges['h4_period'] = [24]         # H4期間固定
        param_ranges['h1_period'] = [24]         # H1期間固定
        
        fixed_params = {'atr_period': 14}
        
        # 組み合わせ生成
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        print(f"   組み合わせ数: {len(combinations)}")
        
        best_params = None
        best_score = -999
        best_result = None
        
        for i, param_combo in enumerate(combinations, 1):
            # パラメータ設定
            params = fixed_params.copy()
            for name, value in zip(param_names, param_combo):
                params[name] = value
            
            # 戦略実行
            strategy = MultiTimeframeBreakoutStrategy(params)
            result = strategy.backtest(mtf_data, is_start_date, is_end_date)
            
            # スコア計算（Stage1基準重視）
            pf_score = result['profit_factor']
            trade_bonus = min(1.0, result['total_trades'] / 300) * 0.15
            rr_bonus = (params['profit_atr'] / params['stop_atr'] - 1.0) * 0.05  # リスクリワード
            
            score = pf_score + trade_bonus + rr_bonus
            
            print(f"   試行{i:2d}: PF={result['profit_factor']:.3f}, 取引={result['total_trades']:3d}, スコア={score:.3f}")
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
                best_result = result.copy()
        
        print(f"\n🏆 最適化完了")
        print(f"   最高スコア: {best_score:.3f}")
        print(f"   最適IS PF: {best_result['profit_factor']:.3f}")
        print(f"   最適取引数: {best_result['total_trades']}")
        
        return best_params, best_result
    
    def _display_results(self, best_params, is_result, oos_result):
        """結果表示"""
        print(f"\n📊 最終結果サマリー")
        
        print(f"\n🎯 最適パラメータ:")
        for key, value in best_params.items():
            print(f"   {key}: {value}")
        
        print(f"\n📈 パフォーマンス結果:")
        print(f"   IS  - PF: {is_result['profit_factor']:.3f}, 取引: {is_result['total_trades']}, 勝率: {is_result['win_rate']:.1%}")
        print(f"   OOS - PF: {oos_result['profit_factor']:.3f}, 取引: {oos_result['total_trades']}, 勝率: {oos_result['win_rate']:.1%}")
        print(f"   OOS最大DD: {oos_result['max_drawdown']:.4f}")
        
        # Stage1判定
        stage1_pass = (oos_result['profit_factor'] >= 1.1 and 
                       oos_result['total_trades'] >= 100)
        
        print(f"\n🎯 Stage1判定: {'✅ 合格!' if stage1_pass else '❌ 不合格'}")
        
        if stage1_pass:
            print(f"   🎊 Stage1合格達成！")
            print(f"   📈 Stage2（WFA検証）への移行準備完了")
            print(f"   🔬 統計的有意性検定を実行可能")
        else:
            print(f"   改善が必要な項目:")
            if oos_result['profit_factor'] < 1.1:
                print(f"   - PF改善: {oos_result['profit_factor']:.3f} → 1.1+ (差:{1.1 - oos_result['profit_factor']:.3f})")
            if oos_result['total_trades'] < 100:
                print(f"   - 取引数: {oos_result['total_trades']} → 100+")
    
    def _save_results(self, best_params, is_result, oos_result):
        """結果保存"""
        stage1_pass = (oos_result['profit_factor'] >= 1.1 and 
                       oos_result['total_trades'] >= 100)
        
        results = {
            'optimization_date': datetime.now().isoformat(),
            'strategy_name': 'multi_timeframe_breakout_optimized',
            'data_quality': '5_year_full_data',
            'best_parameters': best_params,
            'is_performance': {
                'profit_factor': is_result['profit_factor'],
                'total_trades': is_result['total_trades'],
                'win_rate': is_result['win_rate'],
                'max_drawdown': is_result['max_drawdown'],
                'sharpe_ratio': is_result['sharpe_ratio']
            },
            'oos_performance': {
                'profit_factor': oos_result['profit_factor'],
                'total_trades': oos_result['total_trades'],
                'win_rate': oos_result['win_rate'],
                'max_drawdown': oos_result['max_drawdown'],
                'sharpe_ratio': oos_result['sharpe_ratio']
            },
            'stage1_results': {
                'passed': stage1_pass,
                'pf_requirement': oos_result['profit_factor'] >= 1.1,
                'trade_requirement': oos_result['total_trades'] >= 100,
                'ready_for_stage2': stage1_pass
            }
        }
        
        filename = 'phase3_stage1_optimization_results.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 結果保存完了: {filename}")

def main():
    """メイン実行"""
    optimizer = CachedStrategyOptimizer()
    
    # キャッシュ情報表示
    cache_info = optimizer.cache_manager.get_cache_info()
    print(f"💾 データキャッシュ情報:")
    print(f"   サイズ: {cache_info['file_size_mb']:.1f}MB")
    print(f"   更新: {cache_info['modified']}")
    
    # フル最適化実行
    best_params, is_result, oos_result = optimizer.run_full_optimization()
    
    return optimizer, best_params, is_result, oos_result

if __name__ == "__main__":
    optimizer, best_params, is_result, oos_result = main()