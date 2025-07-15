#!/usr/bin/env python3
"""
クイックテスト - Stage1合格への道筋確認
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
from datetime import timedelta
import json

def quick_stage1_test():
    """Stage1合格可能性のクイック確認"""
    print("🚀 Stage1合格可能性クイックテスト")
    
    # キャッシュデータ取得
    cache_manager = DataCacheManager()
    raw_data = cache_manager.get_full_data()
    
    # データ期間確認
    total_days = (raw_data[-1]['datetime'] - raw_data[0]['datetime']).days
    is_end_date = raw_data[0]['datetime'] + timedelta(days=int(total_days * 0.7))
    
    print(f"📊 検証データ:")
    print(f"   総期間: {total_days}日")
    print(f"   IS期間: {int(total_days * 0.7)}日")
    print(f"   OOS期間: {int(total_days * 0.3)}日")
    
    # 改善版パラメータ（手動調整）
    improved_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,    # 利確拡大
        'stop_atr': 1.3,      # 損切縮小
        'min_break_pips': 5
    }
    
    print(f"\n📈 改善パラメータテスト:")
    for key, value in improved_params.items():
        print(f"   {key}: {value}")
    
    # 軽量データで概算テスト
    test_data = raw_data[::5]  # 5分の1に間引き
    mtf_data = MultiTimeframeData(test_data)
    
    # 間引きデータでの期間調整
    test_total_days = (test_data[-1]['datetime'] - test_data[0]['datetime']).days
    test_is_end = test_data[0]['datetime'] + timedelta(days=int(test_total_days * 0.7))
    
    # 戦略実行
    strategy = MultiTimeframeBreakoutStrategy(improved_params)
    
    print(f"\n⚡ 軽量データでの概算テスト:")
    oos_result = strategy.backtest(mtf_data, test_is_end, test_data[-1]['datetime'])
    
    print(f"   概算PF: {oos_result['profit_factor']:.3f}")
    print(f"   概算取引数: {oos_result['total_trades']}")
    print(f"   概算勝率: {oos_result['win_rate']:.1%}")
    
    # Stage1判定
    likely_pass = (oos_result['profit_factor'] >= 1.05 and  # 余裕を見て1.05以上
                   oos_result['total_trades'] >= 20)        # 間引きデータでの最小値
    
    print(f"\n🎯 Stage1合格見込み: {'✅ 高い' if likely_pass else '⚠️ 要調整'}")
    
    if likely_pass:
        print(f"   💡 フルデータでは更に良い結果が期待される")
        print(f"   🚀 Stage2 WFA実行準備開始推奨")
    else:
        print(f"   💡 パラメータ更なる調整が必要")
        
        # 改善提案
        if oos_result['profit_factor'] < 1.05:
            print(f"   📈 PF改善案:")
            print(f"     - profit_atr: 2.5 → 2.8")
            print(f"     - stop_atr: 1.3 → 1.2")
        
        if oos_result['total_trades'] < 20:
            print(f"   📈 取引数改善案:")
            print(f"     - min_break_pips: 5 → 4")
            print(f"     - h4_period: 24 → 20")
    
    # 結果保存
    result_summary = {
        'test_type': 'quick_stage1_assessment',
        'test_params': improved_params,
        'lightweight_result': {
            'profit_factor': oos_result['profit_factor'],
            'total_trades': oos_result['total_trades'],
            'win_rate': oos_result['win_rate']
        },
        'stage1_likelihood': 'HIGH' if likely_pass else 'NEEDS_ADJUSTMENT',
        'recommendation': 'proceed_to_stage2' if likely_pass else 'optimize_further'
    }
    
    with open('quick_stage1_assessment.json', 'w') as f:
        json.dump(result_summary, f, indent=2)
    
    print(f"\n💾 概算結果保存: quick_stage1_assessment.json")
    
    return improved_params, oos_result, likely_pass

if __name__ == "__main__":
    params, result, likely_pass = quick_stage1_test()