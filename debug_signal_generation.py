#!/usr/bin/env python3
"""
シグナル生成デバッグ
取引数ゼロの根本原因を特定
"""

import json
from datetime import datetime, timedelta
from multi_timeframe_breakout_strategy import MultiTimeframeData, create_enhanced_sample_data

def debug_signal_generation():
    """シグナル生成の詳細デバッグ"""
    
    print("🔍 シグナル生成デバッグ開始")
    print("=" * 60)
    
    # テストデータ
    sample_data = create_enhanced_sample_data()
    mtf_data = MultiTimeframeData(sample_data)
    
    h1_data = mtf_data.get_h1_data()
    h4_data = mtf_data.get_h4_data()
    
    print(f"データ確認:")
    print(f"   H1データ数: {len(h1_data)}")
    print(f"   H4データ数: {len(h4_data)}")
    
    if len(h1_data) > 0:
        print(f"   H1サンプル: {h1_data[0]}")
    if len(h4_data) > 0:
        print(f"   H4サンプル: {h4_data[0]}")
    
    # 基本パラメータ
    base_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,
        'stop_atr': 1.3,
        'min_break_pips': 5
    }
    
    print(f"\nパラメータ:")
    print(f"   H4期間: {base_params['h4_period']}")
    print(f"   H1期間: {base_params['h1_period']}")
    
    # 手動シグナル生成テスト
    print(f"\n🔄 手動シグナル生成テスト")
    print("-" * 40)
    
    signal_count = 0
    buy_signals = 0
    sell_signals = 0
    hold_signals = 0
    error_count = 0
    
    # 100本おきに10回テスト
    for i in range(100, min(600, len(h1_data)), 50):
        try:
            current_time = h1_data[i]['datetime']
            signal = generate_manual_signal(h1_data, h4_data, i, base_params, current_time)
            
            signal_count += 1
            
            if signal and signal.get('action'):
                if signal['action'] == 'BUY':
                    buy_signals += 1
                    print(f"   {current_time.strftime('%Y-%m-%d %H:%M')}: BUY シグナル")
                elif signal['action'] == 'SELL':
                    sell_signals += 1
                    print(f"   {current_time.strftime('%Y-%m-%d %H:%M')}: SELL シグナル")
                else:
                    hold_signals += 1
            else:
                hold_signals += 1
                
        except Exception as e:
            error_count += 1
            print(f"   エラー {i}: {str(e)}")
    
    print(f"\n📊 シグナル生成結果")
    print("-" * 40)
    print(f"   総テスト回数: {signal_count}")
    print(f"   BUYシグナル: {buy_signals}")
    print(f"   SELLシグナル: {sell_signals}")
    print(f"   HOLDシグナル: {hold_signals}")
    print(f"   エラー: {error_count}")
    
    # 取引シグナル率
    trading_signals = buy_signals + sell_signals
    trading_rate = trading_signals / signal_count if signal_count > 0 else 0
    
    print(f"   取引シグナル率: {trading_rate:.1%}")
    
    # 年間推定
    annual_estimate = trading_signals * (365 * 24 / 50)
    print(f"   年間推定取引数: {annual_estimate:.0f}回")
    
    # 価格動きチェック
    print(f"\n📈 価格動き分析")
    print("-" * 40)
    
    if len(h1_data) >= 200:
        recent_h1 = h1_data[100:200]  # 100本分
        
        prices = [bar['close'] for bar in recent_h1]
        price_range = max(prices) - min(prices)
        avg_price = sum(prices) / len(prices)
        
        print(f"   価格レンジ: {price_range:.6f}")
        print(f"   平均価格: {avg_price:.6f}")
        print(f"   レンジ率: {price_range/avg_price:.4%}")
        
        # ブレイクアウト候補
        h1_high = max(bar['high'] for bar in recent_h1[-24:])
        h1_low = min(bar['low'] for bar in recent_h1[-24:])
        current_price = recent_h1[-1]['close']
        
        print(f"   直近H1高値: {h1_high:.6f}")
        print(f"   直近H1安値: {h1_low:.6f}")
        print(f"   現在価格: {current_price:.6f}")
        print(f"   高値まで: {h1_high - current_price:.6f}")
        print(f"   安値まで: {current_price - h1_low:.6f}")
    
    if trading_rate == 0:
        print(f"\n⚠️ 問題診断")
        print("-" * 40)
        print("   1. 価格変動が小さすぎる可能性")
        print("   2. ブレイクアウト判定条件が厳しすぎる可能性")
        print("   3. データ生成に問題がある可能性")
        
        # 条件緩和テスト
        print(f"\n🔧 条件緩和テスト")
        print("-" * 40)
        
        relaxed_params = {
            'h4_period': 12,  # 24→12に縮小
            'h1_period': 12,  # 24→12に縮小
        }
        
        relaxed_signals = 0
        for i in range(100, min(400, len(h1_data)), 50):
            signal = generate_manual_signal(h1_data, h4_data, i, relaxed_params, h1_data[i]['datetime'])
            if signal and signal.get('action') in ['BUY', 'SELL']:
                relaxed_signals += 1
        
        relaxed_rate = relaxed_signals / 6 if 6 > 0 else 0  # 6回テスト
        print(f"   緩和条件シグナル率: {relaxed_rate:.1%}")
        print(f"   緩和条件年間推定: {relaxed_signals * (365 * 24 / 50):.0f}回")
    
    print("\n✅ シグナル生成デバッグ完了")

def generate_manual_signal(h1_data, h4_data, current_index, params, current_time):
    """手動シグナル生成（デバッグ用）"""
    
    if current_index < max(params['h1_period'], params['h4_period']):
        return {'action': 'HOLD', 'reason': 'insufficient_data'}
    
    # 現在価格
    current_bar = h1_data[current_index]
    current_price = current_bar['close']
    
    # H1ブレイクアウト判定
    h1_start = current_index - params['h1_period']
    h1_data_slice = h1_data[h1_start:current_index]
    h1_high = max(bar['high'] for bar in h1_data_slice)
    h1_low = min(bar['low'] for bar in h1_data_slice)
    
    # H4ブレイクアウト判定（H1インデックスをH4にマッピング）
    h4_index = current_index // 4  # 簡易変換
    if h4_index < params['h4_period']:
        h4_high = h1_high  # フォールバック
        h4_low = h1_low
    else:
        h4_start = max(0, h4_index - params['h4_period'])
        h4_data_slice = h4_data[h4_start:h4_index]
        if h4_data_slice:
            h4_high = max(bar['high'] for bar in h4_data_slice)
            h4_low = min(bar['low'] for bar in h4_data_slice)
        else:
            h4_high = h1_high
            h4_low = h1_low
    
    # ブレイクアウト判定（厳密な条件）
    if current_price > h4_high and current_price > h1_high:
        return {
            'action': 'BUY',
            'breakout_strength': (current_price - max(h4_high, h1_high)) / current_price * 10000,
            'h1_high': h1_high,
            'h4_high': h4_high,
            'current_price': current_price,
            'signal_time': current_time.isoformat()
        }
    elif current_price < h4_low and current_price < h1_low:
        return {
            'action': 'SELL',
            'breakout_strength': (min(h4_low, h1_low) - current_price) / current_price * 10000,
            'h1_low': h1_low,
            'h4_low': h4_low,
            'current_price': current_price,
            'signal_time': current_time.isoformat()
        }
    
    return {'action': 'HOLD', 'reason': 'no_breakout'}

if __name__ == "__main__":
    debug_signal_generation()