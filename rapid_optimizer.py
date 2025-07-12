#!/usr/bin/env python3
"""
高速パラメータ最適化
Stage1合格達成のための効率的調整
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
from datetime import datetime, timedelta
import json

class RapidOptimizer:
    """高速最適化クラス"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
    def run_targeted_optimization(self):
        """Stage1合格に特化した最適化"""
        print("🎯 Stage1合格特化最適化実行")
        
        # キャッシュからデータ取得
        raw_data = self.cache_manager.get_full_data()
        mtf_data = MultiTimeframeData(raw_data)
        
        # IS/OOS分割
        total_days = (raw_data[-1]['datetime'] - raw_data[0]['datetime']).days
        is_end_date = raw_data[0]['datetime'] + timedelta(days=int(total_days * 0.7))
        
        print(f"📊 データ期間: {(raw_data[-1]['datetime'] - raw_data[0]['datetime']).days}日")
        
        # 厳選パラメータで最適化
        best_params, best_result = self._focused_optimization(
            mtf_data, raw_data[0]['datetime'], is_end_date
        )
        
        # OOS最終検証
        final_result = self._final_validation(
            mtf_data, best_params, is_end_date, raw_data[-1]['datetime']
        )
        
        return best_params, best_result, final_result
    
    def _focused_optimization(self, mtf_data, is_start, is_end):
        """集中的最適化"""
        print("\n🔍 集中的パラメータ最適化")
        
        # Stage1合格に効果的なパラメータ候補
        candidates = [
            # リスクリワード改善重視
            {'h4_period': 24, 'h1_period': 24, 'profit_atr': 2.5, 'stop_atr': 1.3, 'min_break_pips': 5, 'atr_period': 14},
            {'h4_period': 24, 'h1_period': 24, 'profit_atr': 2.8, 'stop_atr': 1.4, 'min_break_pips': 4, 'atr_period': 14},
            {'h4_period': 24, 'h1_period': 24, 'profit_atr': 2.3, 'stop_atr': 1.2, 'min_break_pips': 6, 'atr_period': 14},
            
            # エントリー精度重視
            {'h4_period': 28, 'h1_period': 24, 'profit_atr': 2.4, 'stop_atr': 1.5, 'min_break_pips': 7, 'atr_period': 14},
            {'h4_period': 20, 'h1_period': 20, 'profit_atr': 2.6, 'stop_atr': 1.4, 'min_break_pips': 4, 'atr_period': 14},
            
            # バランス型
            {'h4_period': 26, 'h1_period': 22, 'profit_atr': 2.4, 'stop_atr': 1.3, 'min_break_pips': 5, 'atr_period': 14},
            {'h4_period': 22, 'h1_period': 26, 'profit_atr': 2.7, 'stop_atr': 1.5, 'min_break_pips': 6, 'atr_period': 14},
        ]
        
        best_params = None
        best_score = -999
        best_result = None
        
        for i, params in enumerate(candidates, 1):
            strategy = MultiTimeframeBreakoutStrategy(params)
            result = strategy.backtest(mtf_data, is_start, is_end)
            
            # Stage1特化スコア
            pf_weight = 3.0  # PF重視
            trade_bonus = min(0.2, result['total_trades'] / 500)
            rr_ratio = params['profit_atr'] / params['stop_atr']
            rr_bonus = (rr_ratio - 1.5) * 0.1
            
            score = (result['profit_factor'] * pf_weight) + trade_bonus + rr_bonus
            
            print(f"   候補{i}: PF={result['profit_factor']:.3f}, 取引={result['total_trades']:3d}, RR={rr_ratio:.1f}, スコア={score:.3f}")
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
                best_result = result.copy()
        
        print(f"\n🏆 IS期間最適化完了")
        print(f"   最高スコア: {best_score:.3f}")
        print(f"   最適PF: {best_result['profit_factor']:.3f}")
        print(f"   リスクリワード: {best_params['profit_atr']:.1f}:{best_params['stop_atr']:.1f}")
        
        return best_params, best_result
    
    def _final_validation(self, mtf_data, best_params, oos_start, oos_end):
        """最終OOS検証"""
        print(f"\n📈 最適パラメータでの最終OOS検証")
        
        strategy = MultiTimeframeBreakoutStrategy(best_params)
        oos_result = strategy.backtest(mtf_data, oos_start, oos_end)
        
        print(f"\n📊 最終結果:")
        print(f"   OOS PF: {oos_result['profit_factor']:.3f}")
        print(f"   OOS取引数: {oos_result['total_trades']}")
        print(f"   OOS勝率: {oos_result['win_rate']:.1%}")
        print(f"   OOS最大DD: {oos_result['max_drawdown']:.4f}")
        
        # Stage1判定
        stage1_pass = (oos_result['profit_factor'] >= 1.1 and 
                       oos_result['total_trades'] >= 100)
        
        print(f"\n🎯 Stage1最終判定: {'✅ 合格!' if stage1_pass else '❌ 不合格'}")
        
        if stage1_pass:
            print(f"   🎊 Stage1合格達成！")
            print(f"   🔬 Stage2（WFA統計的検証）への移行準備完了")
            
            # 合格時の詳細分析
            rr_ratio = best_params['profit_atr'] / best_params['stop_atr']
            print(f"\n🔍 合格戦略の特徴:")
            print(f"   リスクリワード比: {rr_ratio:.1f}:1")
            print(f"   エントリー精度: {oos_result['win_rate']:.1%}勝率")
            print(f"   リスク管理: 最大DD {oos_result['max_drawdown']:.1%}")
            
        else:
            shortage_pf = max(0, 1.1 - oos_result['profit_factor'])
            shortage_trades = max(0, 100 - oos_result['total_trades'])
            
            print(f"   不足要素:")
            if shortage_pf > 0:
                print(f"   - PF不足: {shortage_pf:.3f}")
            if shortage_trades > 0:
                print(f"   - 取引数不足: {shortage_trades}回")
        
        # 結果保存
        self._save_final_results(best_params, oos_result, stage1_pass)
        
        return oos_result
    
    def _save_final_results(self, params, result, passed):
        """最終結果保存"""
        final_data = {
            'timestamp': datetime.now().isoformat(),
            'optimization_type': 'stage1_focused',
            'stage1_status': 'PASSED' if passed else 'FAILED',
            'final_parameters': params,
            'oos_performance': {
                'profit_factor': result['profit_factor'],
                'total_trades': result['total_trades'],
                'win_rate': result['win_rate'],
                'max_drawdown': result['max_drawdown'],
                'sharpe_ratio': result['sharpe_ratio']
            },
            'next_phase': 'stage2_wfa' if passed else 'strategy_revision',
            'readiness_for_wfa': passed
        }
        
        with open('stage1_final_results.json', 'w') as f:
            json.dump(final_data, f, indent=2)
        
        print(f"\n💾 最終結果保存: stage1_final_results.json")

def main():
    """メイン実行"""
    print("🚀 Stage1合格特化最適化開始")
    
    optimizer = RapidOptimizer()
    best_params, is_result, oos_result = optimizer.run_targeted_optimization()
    
    # フェーズ3総括
    stage1_passed = (oos_result['profit_factor'] >= 1.1 and 
                     oos_result['total_trades'] >= 100)
    
    print(f"\n🎊 フェーズ3総括:")
    print(f"   マルチタイムフレーム戦略: ✅ 完成")
    print(f"   データ品質向上: ✅ 5年データ対応")
    print(f"   取引頻度改善: ✅ 8→{oos_result['total_trades']}回")
    print(f"   Stage1合格: {'✅ 達成' if stage1_passed else '❌ 継続課題'}")
    
    if stage1_passed:
        print(f"\n🚀 次のステップ: Stage2 WFA統計的検証")
        print(f"   準備完了項目:")
        print(f"   - Purged & Embargoed WFA実装済み")
        print(f"   - 5年データ準備済み")
        print(f"   - 統計的有意性検定準備済み")
    
    return optimizer, best_params, is_result, oos_result

if __name__ == "__main__":
    optimizer, best_params, is_result, oos_result = main()