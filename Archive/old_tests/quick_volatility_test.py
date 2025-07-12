#!/usr/bin/env python3
"""
ATRボラティリティフィルター効果の軽量テスト
"""

import json
from datetime import datetime, timedelta
from enhanced_breakout_strategy import EnhancedBreakoutStrategy
from multi_timeframe_breakout_strategy import MultiTimeframeData

def create_test_data():
    """軽量テストデータ生成"""
    import random
    
    # 1000本のH1データ生成
    data = []
    base_date = datetime(2019, 1, 1)
    price = 1.1000
    
    for i in range(1000):
        # 時間増分（1時間ずつ）
        hours_to_add = i
        current_time = base_date + timedelta(hours=hours_to_add)
        
        # 価格変動
        change = random.uniform(-0.0020, 0.0020)
        price += change
        
        # ATR計算用の変動幅
        high_low_range = random.uniform(0.0005, 0.0030)
        
        bar = {
            'datetime': current_time,
            'open': price,
            'high': price + high_low_range * 0.6,
            'low': price - high_low_range * 0.4,
            'close': price,
            'volume': random.randint(800, 1200)
        }
        
        data.append(bar)
    
    return data

def test_volatility_filter_simple():
    """簡易ATRフィルターテスト"""
    
    print("🔍 ATRボラティリティフィルター簡易テスト開始")
    print("=" * 50)
    
    # テストデータ生成
    print("📊 テストデータ生成中...")
    sample_data = create_test_data()
    mtf_data = MultiTimeframeData(sample_data)
    
    print(f"✅ データ生成完了: {len(sample_data)}本")
    
    # 基本パラメータ
    base_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,
        'stop_atr': 1.3,
        'min_break_pips': 5
    }
    
    # 強化戦略初期化
    strategy = EnhancedBreakoutStrategy(base_params)
    
    print("\n🔄 フィルター機能テスト")
    print("-" * 30)
    
    # シグナル生成テスト
    test_signals = []
    filtered_signals = []
    
    for i in range(100, 900, 50):  # 100本目から50本おきに16回テスト
        current_time = sample_data[i]['datetime']
        
        # 簡易シグナル生成
        signal = strategy._get_simple_signal(mtf_data, current_time)
        
        if signal:
            test_signals.append(signal)
            
            if signal['action'] != 'HOLD':
                filtered_signals.append(signal)
                
                print(f"時刻 {current_time.strftime('%Y-%m-%d %H:%M')}: {signal['action']}")
                if 'volatility_level' in signal:
                    print(f"   ボラティリティレベル: {signal['volatility_level']}")
                if 'breakout_strength' in signal:
                    print(f"   ブレイクアウト強度: {signal['breakout_strength']:.3f}")
                if 'filter_reason' in signal:
                    print(f"   フィルター理由: {signal['filter_reason']}")
                print()
    
    # 結果分析
    print("📊 テスト結果")
    print("-" * 30)
    
    total_signals = len(test_signals)
    trading_signals = len(filtered_signals)
    filter_rate = (total_signals - trading_signals) / total_signals if total_signals > 0 else 0
    
    print(f"総シグナル: {total_signals}")
    print(f"取引シグナル: {trading_signals}")
    print(f"フィルタリング率: {filter_rate:.1%}")
    
    # ボラティリティレベル分析
    volatility_levels = {}
    for signal in filtered_signals:
        if 'volatility_level' in signal:
            level = signal['volatility_level']
            volatility_levels[level] = volatility_levels.get(level, 0) + 1
    
    if volatility_levels:
        print("\nボラティリティレベル分布:")
        for level, count in volatility_levels.items():
            print(f"   {level}: {count}回")
    
    # ATRフィルター機能テスト
    print("\n🔍 ATRフィルター詳細テスト")
    print("-" * 30)
    
    h1_data = mtf_data.get_h1_data()
    if len(h1_data) > 100:
        atr_analysis = strategy._calculate_atr_volatility_filter(h1_data)
        
        print(f"現在ATR: {atr_analysis['current_atr']:.6f}")
        print(f"ATRパーセンタイル: {atr_analysis['atr_percentile']:.1f}%")
        print(f"ボラティリティレベル: {atr_analysis['volatility_level']}")
        print(f"トレンド強度: {atr_analysis['trend_strength']:.3f}")
        print(f"ボリューム係数: {atr_analysis['volume_factor']:.3f}")
    
    # 結果保存
    test_results = {
        'test_type': 'atr_volatility_filter_simple',
        'timestamp': datetime.now().isoformat(),
        'total_signals': total_signals,
        'trading_signals': trading_signals,
        'filter_rate': filter_rate,
        'volatility_levels': volatility_levels,
        'atr_analysis': atr_analysis if 'atr_analysis' in locals() else None
    }
    
    filename = f"atr_filter_simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📝 結果保存: {filename}")
    print("✅ ATRボラティリティフィルターテスト完了")
    
    return True

if __name__ == "__main__":
    test_volatility_filter_simple()