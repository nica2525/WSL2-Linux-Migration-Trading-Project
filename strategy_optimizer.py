#!/usr/bin/env python3
"""
マルチタイムフレーム戦略パラメータ最適化
Stage1基準達成のためのパラメータ調整
"""

from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, create_enhanced_sample_data, MultiTimeframeData
from datetime import datetime, timedelta
import itertools

class StrategyOptimizer:
    """戦略パラメータ最適化クラス"""
    
    def __init__(self, mtf_data):
        self.mtf_data = mtf_data
        
    def optimize_parameters(self, is_start_date, is_end_date, max_trials=12):
        """
        パラメータ最適化実行
        
        Args:
            is_start_date: IS期間開始日
            is_end_date: IS期間終了日  
            max_trials: 最大試行回数
            
        Returns:
            tuple: (最適パラメータ, 最適結果)
        """
        print(f"🔍 パラメータ最適化開始（最大{max_trials}試行）")
        
        # パラメータ範囲の定義（最小限）
        param_ranges = {
            'h4_period': [20, 28],               # H4期間
            'profit_atr': [1.8, 2.5],           # 利確ATR倍数
            'stop_atr': [1.0, 1.5],             # 損切ATR倍数
            'min_break_pips': [3, 7]            # 最小ブレイク幅
        }
        
        # 固定パラメータ
        fixed_params = {
            'atr_period': 14,
            'h1_period': 24
        }
        
        # パラメータ組み合わせ生成
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        # 試行回数制限
        if len(combinations) > max_trials:
            import random
            combinations = random.sample(combinations, max_trials)
        
        best_params = None
        best_score = -999
        best_result = None
        
        print(f"   実行組み合わせ数: {len(combinations)}")
        
        for i, param_combo in enumerate(combinations, 1):
            # パラメータ辞書作成
            params = fixed_params.copy()
            for name, value in zip(param_names, param_combo):
                params[name] = value
            
            # 戦略実行
            strategy = MultiTimeframeBreakoutStrategy(params)
            result = strategy.backtest(self.mtf_data, is_start_date, is_end_date)
            
            # スコア計算（プロフィットファクター + 取引数ボーナス）
            pf_score = result['profit_factor']
            trade_bonus = min(1.0, result['total_trades'] / 200) * 0.1  # 取引数ボーナス
            score = pf_score + trade_bonus
            
            print(f"   試行{i:2d}: PF={result['profit_factor']:.3f}, 取引={result['total_trades']:3d}, スコア={score:.3f}")
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
                best_result = result.copy()
        
        print(f"\n🏆 最適化完了")
        print(f"   最高スコア: {best_score:.3f}")
        print(f"   最適PF: {best_result['profit_factor']:.3f}")
        print(f"   最適取引数: {best_result['total_trades']}")
        print(f"   最適パラメータ: {best_params}")
        
        return best_params, best_result

def main():
    """最適化実行メイン関数"""
    print("🚀 マルチタイムフレーム戦略パラメータ最適化実行")
    
    # サンプルデータ生成
    print("📊 サンプルデータ生成中...")
    raw_data = create_enhanced_sample_data()
    mtf_data = MultiTimeframeData(raw_data)
    
    # IS期間の設定（70%）
    total_days = (raw_data[-1]['datetime'] - raw_data[0]['datetime']).days
    is_end_date = raw_data[0]['datetime'] + timedelta(days=int(total_days * 0.7))
    
    print(f"   IS期間: {raw_data[0]['datetime'].strftime('%Y-%m-%d')} to {is_end_date.strftime('%Y-%m-%d')}")
    
    # パラメータ最適化実行
    optimizer = StrategyOptimizer(mtf_data)
    best_params, best_is_result = optimizer.optimize_parameters(
        raw_data[0]['datetime'], 
        is_end_date, 
        max_trials=12
    )
    
    # 最適パラメータでOOS検証
    print(f"\n📈 最適パラメータでのOOS検証")
    optimized_strategy = MultiTimeframeBreakoutStrategy(best_params)
    oos_result = optimized_strategy.backtest(mtf_data, is_end_date, raw_data[-1]['datetime'])
    
    print(f"   OOS結果:")
    print(f"   - PF: {oos_result['profit_factor']:.3f}")
    print(f"   - 取引数: {oos_result['total_trades']}")
    print(f"   - 勝率: {oos_result['win_rate']:.1%}")
    print(f"   - 最大DD: {oos_result['max_drawdown']:.4f}")
    
    # Stage1再判定
    stage1_pass = (oos_result['profit_factor'] >= 1.1 and 
                   oos_result['total_trades'] >= 100)
    
    print(f"\n🎯 Stage1再判定: {'✅ 合格' if stage1_pass else '❌ 不合格'}")
    
    if stage1_pass:
        print(f"   Stage2（WFA検証）への移行準備完了")
        
        # 最適パラメータの保存
        import json
        optimized_config = {
            'strategy_name': 'multi_timeframe_breakout',
            'optimization_date': datetime.now().isoformat(),
            'best_parameters': best_params,
            'is_performance': {
                'profit_factor': best_is_result['profit_factor'],
                'total_trades': best_is_result['total_trades'],
                'win_rate': best_is_result['win_rate']
            },
            'oos_performance': {
                'profit_factor': oos_result['profit_factor'],
                'total_trades': oos_result['total_trades'],
                'win_rate': oos_result['win_rate'],
                'max_drawdown': oos_result['max_drawdown']
            },
            'stage1_passed': stage1_pass
        }
        
        with open('optimized_strategy_config.json', 'w') as f:
            json.dump(optimized_config, f, indent=2)
        
        print(f"   最適化設定を optimized_strategy_config.json に保存")
        
    else:
        print(f"   更なる戦略改良が必要")
        print(f"   考慮事項:")
        if oos_result['profit_factor'] < 1.1:
            print(f"   - エッジ（優位性）の強化が必要")
        if oos_result['total_trades'] < 100:
            print(f"   - 取引頻度の向上が必要")
    
    return best_params, best_is_result, oos_result, stage1_pass

if __name__ == "__main__":
    best_params, is_result, oos_result, passed = main()