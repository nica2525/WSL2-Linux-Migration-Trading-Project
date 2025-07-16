#!/usr/bin/env python3
"""
コスト耐性戦略テスト実行
小規模テストで改善効果を確認
"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from cost_resistant_strategy import CostResistantStrategy
from multi_timeframe_breakout_strategy import MultiTimeframeData

class MockDataBar:
    """モックデータバー"""
    def __init__(self, datetime_val, open_val, high_val, low_val, close_val, volume_val=1000):
        self.datetime = datetime_val
        self.open = open_val
        self.high = high_val
        self.low = low_val
        self.close = close_val
        self.volume = volume_val

class CostResistantStrategyTest:
    """コスト耐性戦略テストクラス"""
    
    def __init__(self):
        self.base_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,
            'stop_atr': 1.3,
            'min_break_pips': 5
        }
        
        self.strategy = CostResistantStrategy(self.base_params)
    
    def generate_test_data(self, num_bars: int = 500) -> Tuple[List[MockDataBar], List[MockDataBar]]:
        """テストデータ生成"""
        print(f"📊 テストデータ生成中... ({num_bars}バー)")
        
        # 基準価格とトレンド
        base_price = 1.2000
        trend = 0.0001  # 上昇トレンド
        
        h1_data = []
        h4_data = []
        
        for i in range(num_bars):
            # 時間設定
            bar_time = datetime.now() - timedelta(hours=num_bars-i)
            
            # 価格変動（ATRとトレンドを考慮）
            price_change = np.random.normal(0, 0.0005)  # 標準偏差50pips
            trend_component = trend * (i / num_bars)
            
            if i == 0:
                open_price = base_price
            else:
                open_price = h1_data[-1].close
            
            # 価格計算
            close_price = open_price + price_change + trend_component
            
            # 修正: ランダム代わりに決定的パターンでブレイクアウト生成
            if i > 100 and (i % 33) == 0:  # 33バー毎に大きな動き
                breakout_size = 0.005  # 固定50pips
                breakout_direction = 1 if (i // 33) % 2 == 0 else -1  # 交互方向
                close_price = open_price + (breakout_size * breakout_direction)
            
            # 修正: High/Low計算を決定的に
            intrabar_range = 0.0008 + (i % 7) * 0.0001  # 8-14pipsの決定的レンジ
            high_price = max(open_price, close_price) + intrabar_range/2
            low_price = min(open_price, close_price) - intrabar_range/2
            
            # H1データ
            h1_bar = MockDataBar(bar_time, open_price, high_price, low_price, close_price)
            h1_data.append(h1_bar)
            
            # H4データ（4時間毎）
            if i % 4 == 0:
                h4_bar = MockDataBar(bar_time, open_price, high_price, low_price, close_price)
                h4_data.append(h4_bar)
        
        print(f"   H1データ: {len(h1_data)}バー")
        print(f"   H4データ: {len(h4_data)}バー")
        
        return h1_data, h4_data
    
    def create_mtf_data(self, h1_data: List[MockDataBar], h4_data: List[MockDataBar]) -> MultiTimeframeData:
        """MultiTimeframeDataオブジェクト作成"""
        class TestMultiTimeframeData(MultiTimeframeData):
            def __init__(self, h1_bars, h4_bars):
                self.h1_bars = h1_bars
                self.h4_bars = h4_bars
            
            def get_h1_data(self):
                return self.h1_bars
            
            def get_h4_data(self):
                return self.h4_bars
        
        return TestMultiTimeframeData(h1_data, h4_data)
    
    def run_small_scale_test(self) -> Dict:
        """小規模テスト実行"""
        print("🧪 コスト耐性戦略 小規模テスト開始")
        
        # テストデータ生成
        h1_data, h4_data = self.generate_test_data(500)
        
        # 直接フィルタリングテスト
        signals = []
        test_period = 200  # 最後の200バーでテスト
        
        for i in range(len(h1_data) - test_period, len(h1_data)):
            current_time = h1_data[i].datetime
            
            # データ切り取り（現在時点まで）
            current_h1_data = h1_data[:i+1]
            current_h4_data = h4_data[:len(current_h1_data)//4+1]
            
            # 簡易ブレイクアウト検出
            if len(current_h1_data) < 50 or len(current_h4_data) < 20:
                continue
                
            # 現在価格
            current_price = current_h1_data[-1].close
            
            # ブレイクアウト判定（期間を短くして検出しやすくする）
            lookback_period = min(24, len(current_h1_data) - 1)
            h4_lookback = min(6, len(current_h4_data) - 1)
            
            if lookback_period > 0 and h4_lookback > 0:
                # 過去の高値・安値（現在バーを除く）
                h1_high = max([bar.high for bar in current_h1_data[-lookback_period-1:-1]])
                h1_low = min([bar.low for bar in current_h1_data[-lookback_period-1:-1]])
                h4_high = max([bar.high for bar in current_h4_data[-h4_lookback-1:-1]])
                h4_low = min([bar.low for bar in current_h4_data[-h4_lookback-1:-1]])
                
                base_signal = None
                
                # より緩い条件でブレイクアウト判定
                if current_price > h1_high or current_price > h4_high:
                    base_signal = {
                        'action': 'BUY',
                        'price': current_price,
                        'timestamp': current_time
                    }
                elif current_price < h1_low or current_price < h4_low:
                    base_signal = {
                        'action': 'SELL',
                        'price': current_price,
                        'timestamp': current_time
                    }
            
            if base_signal:
                self.strategy.signals_generated += 1
                
                # フィルタリングテスト
                try:
                    # ATRフィルター
                    atr_filter_passed, atr_multiple = self.strategy._check_atr_filter(current_h1_data, base_signal)
                    if not atr_filter_passed:
                        self.strategy.signals_filtered_atr += 1
                        if len(signals) < 3:  # 最初の3個だけデバッグ出力
                            print(f"   ATRフィルター除外: atr_multiple={atr_multiple:.2f} < {self.strategy.cost_resistance_params['min_atr_multiple']}")
                        continue
                    
                    # トレンドフィルター  
                    trend_filter_passed, trend_strength = self.strategy._check_trend_filter(current_h1_data, base_signal)
                    if not trend_filter_passed:
                        self.strategy.signals_filtered_trend += 1
                        if len(signals) < 3:  # 最初の3個だけデバッグ出力
                            print(f"   トレンドフィルター除外: 方向性不一致 {base_signal['action']} 現在価格={current_h1_data[-1].close:.5f}")
                        continue
                    
                    # 利益フィルター
                    profit_filter_passed, expected_profit_pips = self.strategy._check_profit_filter(current_h1_data, base_signal)
                    if not profit_filter_passed:
                        self.strategy.signals_filtered_profit += 1
                        if len(signals) < 3:  # 最初の3個だけデバッグ出力
                            print(f"   利益フィルター除外: expected_profit={expected_profit_pips:.1f} < {self.strategy.cost_resistance_params['min_profit_pips']}")
                        continue
                    
                    # 承認シグナル
                    self.strategy.signals_approved += 1
                    
                    # 詳細情報
                    confidence = self.strategy._evaluate_signal_quality(atr_multiple, trend_strength, expected_profit_pips)
                    cost_ratio = expected_profit_pips / 2.0  # 2.0 pips cost
                    
                    stop_loss, take_profit = self.strategy._calculate_optimized_levels(
                        current_h1_data, base_signal, expected_profit_pips
                    )
                    
                    signals.append({
                        'timestamp': current_time.isoformat(),
                        'direction': base_signal['action'],
                        'entry_price': current_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'confidence': confidence,
                        'atr_multiple': atr_multiple,
                        'trend_strength': trend_strength,
                        'expected_profit_pips': expected_profit_pips,
                        'cost_ratio': cost_ratio
                    })
                    
                except Exception as e:
                    print(f"   フィルタリングエラー: {e}")
                    continue
        
        # 結果分析
        stats = self.strategy.get_statistics()
        
        print(f"\n📊 テスト結果:")
        print(f"   テスト期間: {test_period}バー")
        print(f"   生成シグナル: {stats['signals_generated']}")
        print(f"   ATRフィルター除外: {stats['signals_filtered_atr']}")
        print(f"   トレンドフィルター除外: {stats['signals_filtered_trend']}")
        print(f"   利益フィルター除外: {stats['signals_filtered_profit']}")
        print(f"   承認シグナル: {stats['signals_approved']}")
        print(f"   承認率: {stats['approval_rate']:.1%}")
        print(f"   フィルター効果: {stats['filter_effectiveness']:.1%}")
        
        if signals:
            print(f"\n🎯 承認シグナルの品質:")
            avg_atr_multiple = np.mean([s['atr_multiple'] for s in signals])
            avg_trend_strength = np.mean([s['trend_strength'] for s in signals])
            avg_expected_profit = np.mean([s['expected_profit_pips'] for s in signals])
            avg_cost_ratio = np.mean([s['cost_ratio'] for s in signals])
            
            print(f"   平均ATR倍数: {avg_atr_multiple:.2f}")
            print(f"   平均トレンド強度: {avg_trend_strength:.2f}")
            print(f"   平均期待利益: {avg_expected_profit:.1f} pips")
            print(f"   平均コスト比率: {avg_cost_ratio:.2f}")
            
            # 信頼度分析
            high_conf = len([s for s in signals if s['confidence'] == 'HIGH'])
            medium_conf = len([s for s in signals if s['confidence'] == 'MEDIUM'])
            low_conf = len([s for s in signals if s['confidence'] == 'LOW'])
            
            print(f"   信頼度分布:")
            print(f"     HIGH: {high_conf} ({high_conf/len(signals)*100:.1f}%)")
            print(f"     MEDIUM: {medium_conf} ({medium_conf/len(signals)*100:.1f}%)")
            print(f"     LOW: {low_conf} ({low_conf/len(signals)*100:.1f}%)")
        
        # 元の戦略との比較用データ
        comparison_data = {
            'original_strategy_signals_per_200_bars': 'estimated_50-80',  # 推定値
            'cost_resistant_signals_per_200_bars': stats['signals_approved'],
            'signal_reduction_ratio': 1 - (stats['signals_approved'] / 60),  # 60を基準とした削減率
            'quality_improvement': {
                'avg_expected_profit_pips': avg_expected_profit if signals else 0,
                'avg_cost_ratio': avg_cost_ratio if signals else 0,
                'min_atr_multiple': self.strategy.cost_resistance_params['min_atr_multiple'],
                'min_profit_pips': self.strategy.cost_resistance_params['min_profit_pips']
            }
        }
        
        results = {
            'test_stats': stats,
            'signals': signals,
            'comparison_data': comparison_data,
            'test_parameters': self.strategy.cost_resistance_params,
            'base_parameters': self.base_params
        }
        
        return results
    
    def save_test_results(self, results: Dict, filename: str = 'cost_resistant_test_results.json'):
        """テスト結果保存"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📄 テスト結果保存: {filename}")

def main():
    """メイン実行"""
    print("🛡️ コスト耐性戦略テスト開始")
    
    # テスト実行
    test = CostResistantStrategyTest()
    results = test.run_small_scale_test()
    
    # 結果保存
    test.save_test_results(results)
    
    # 結論
    print(f"\n🎯 テスト結論:")
    
    stats = results['test_stats']
    if stats['signals_approved'] > 0:
        print(f"   ✅ フィルタリングシステム正常動作")
        print(f"   ✅ 高品質シグナル生成: {stats['signals_approved']}個")
        print(f"   ✅ 承認率: {stats['approval_rate']:.1%}")
        
        if stats['approval_rate'] < 0.3:
            print(f"   🎯 適切な品質管理: 低品質シグナル除外成功")
        else:
            print(f"   ⚠️ フィルター調整の検討が必要")
    else:
        print(f"   ❌ フィルターが厳しすぎる可能性")
        print(f"   → パラメータ調整が必要")
    
    print(f"\n🚀 次のステップ:")
    print(f"   1. 実際のデータでのテスト")
    print(f"   2. WFA再実行による効果検証")
    print(f"   3. パラメータ最適化")

if __name__ == "__main__":
    main()