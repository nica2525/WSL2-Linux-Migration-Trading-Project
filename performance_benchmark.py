#!/usr/bin/env python3
"""
Phase2 性能ベンチマークテスト
kiro要件準拠: レイテンシ・スループット測定
"""

import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import (
    MarketDataFeed, SignalGenerator, MarketData, RealtimeSignalSystem
)

class PerformanceBenchmark:
    """性能ベンチマーク"""
    
    def __init__(self):
        self.results = {}
        
    async def benchmark_signal_generation_latency(self) -> float:
        """シグナル生成レイテンシベンチマーク"""
        print("📊 シグナル生成レイテンシベンチマーク開始...")
        
        feed = MarketDataFeed()
        generator = SignalGenerator(feed)
        
        # 履歴データ準備
        base_time = datetime.now()
        for i in range(25):
            data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol='EURUSD',
                open=1.1000 + i * 0.0001,
                high=1.1010 + i * 0.0001,
                low=1.0990 + i * 0.0001,
                close=1.1005 + i * 0.0001,
                volume=1000
            )
            with feed.buffer_lock:
                feed.data_buffer.append(data)
        
        # ブレイクアウトデータ準備
        breakout_data = MarketData(
            timestamp=base_time + timedelta(minutes=26),
            symbol='EURUSD',
            open=1.1050,
            high=1.1100,  # 強いブレイクアウト
            low=1.0995,
            close=1.1095,
            volume=1500
        )
        
        # レイテンシ測定（100回実行）
        latencies = []
        for i in range(100):
            start_time = asyncio.get_event_loop().time()
            signal = await generator._detect_breakout_signal(breakout_data)
            end_time = asyncio.get_event_loop().time()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        # 統計計算
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95パーセンタイル
        
        self.results['signal_generation'] = {
            'average_ms': avg_latency,
            'max_ms': max_latency,
            'min_ms': min_latency,
            'p95_ms': p95_latency,
            'requirement_met': avg_latency < 100
        }
        
        print(f"  平均レイテンシ: {avg_latency:.2f}ms")
        print(f"  最大レイテンシ: {max_latency:.2f}ms")
        print(f"  95パーセンタイル: {p95_latency:.2f}ms")
        print(f"  要件達成 (<100ms): {'✅' if avg_latency < 100 else '❌'}")
        
        return avg_latency
    
    async def benchmark_data_processing_throughput(self) -> float:
        """データ処理スループットベンチマーク"""
        print("\n📊 データ処理スループットベンチマーク開始...")
        
        feed = MarketDataFeed()
        
        # 1000データの処理時間測定
        data_count = 1000
        start_time = time.time()
        
        for i in range(data_count):
            test_data = {
                'timestamp': (datetime.now() + timedelta(milliseconds=i)).isoformat(),
                'symbol': 'EURUSD',
                'open': 1.1000,
                'high': 1.1010,
                'low': 1.0990,
                'close': 1.1005,
                'volume': 1000
            }
            await feed._process_market_data(test_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        throughput = data_count / processing_time
        
        self.results['data_processing'] = {
            'data_count': data_count,
            'processing_time_s': processing_time,
            'throughput_per_sec': throughput,
            'requirement_met': throughput >= 1000
        }
        
        print(f"  処理データ数: {data_count}")
        print(f"  処理時間: {processing_time:.3f}s")
        print(f"  スループット: {throughput:.1f} データ/秒")
        print(f"  要件達成 (≥1000/秒): {'✅' if throughput >= 1000 else '❌'}")
        
        return throughput
    
    async def benchmark_memory_usage(self) -> dict:
        """メモリ使用量ベンチマーク（簡易版）"""
        print("\n📊 メモリ使用量ベンチマーク開始...")
        
        # システム初期化
        system = RealtimeSignalSystem()
        
        # バッファサイズテスト
        feed = system.market_feed
        initial_buffer_size = len(feed.data_buffer)
        
        # 大量データ処理シミュレーション
        for i in range(10000):
            test_data = {
                'timestamp': (datetime.now() + timedelta(milliseconds=i)).isoformat(),
                'symbol': 'EURUSD',
                'open': 1.1000,
                'high': 1.1010,
                'low': 1.0990,
                'close': 1.1005,
                'volume': 1000
            }
            await feed._process_market_data(test_data)
        
        final_buffer_size = len(feed.data_buffer)
        
        self.results['memory_usage'] = {
            'initial_buffer_size': initial_buffer_size,
            'final_buffer_size': final_buffer_size,
            'data_processed': 10000,
            'buffer_managed': final_buffer_size <= 10000  # バッファ制限確認
        }
        
        print(f"  初期バッファサイズ: {initial_buffer_size}")
        print(f"  最終バッファサイズ: {final_buffer_size}")
        print(f"  処理データ数: 10000")
        print(f"  バッファ管理: {'✅ 制限内' if final_buffer_size <= 10000 else '❌ 制限超過'}")
        
        return self.results['memory_usage']
    
    async def benchmark_concurrent_processing(self) -> dict:
        """並行処理性能ベンチマーク"""
        print("\n📊 並行処理性能ベンチマーク開始...")
        
        async def process_symbol_data(symbol: str, count: int):
            """シンボル別データ処理"""
            feed = MarketDataFeed()
            start_time = time.time()
            
            for i in range(count):
                test_data = {
                    'timestamp': (datetime.now() + timedelta(milliseconds=i)).isoformat(),
                    'symbol': symbol,
                    'open': 1.1000,
                    'high': 1.1010,
                    'low': 1.0990,
                    'close': 1.1005,
                    'volume': 1000
                }
                await feed._process_market_data(test_data)
            
            end_time = time.time()
            return end_time - start_time
        
        # 5シンボル同時処理
        symbols = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCAD', 'AUDUSD']
        data_per_symbol = 200
        
        start_time = time.time()
        tasks = [process_symbol_data(symbol, data_per_symbol) for symbol in symbols]
        processing_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        total_data = len(symbols) * data_per_symbol
        concurrent_throughput = total_data / total_time
        
        self.results['concurrent_processing'] = {
            'symbols': len(symbols),
            'data_per_symbol': data_per_symbol,
            'total_data': total_data,
            'total_time_s': total_time,
            'concurrent_throughput': concurrent_throughput,
            'processing_times': dict(zip(symbols, processing_times))
        }
        
        print(f"  シンボル数: {len(symbols)}")
        print(f"  総データ数: {total_data}")
        print(f"  総処理時間: {total_time:.3f}s")
        print(f"  並行スループット: {concurrent_throughput:.1f} データ/秒")
        
        return self.results['concurrent_processing']
    
    def generate_performance_report(self):
        """性能レポート生成"""
        print("\n" + "="*60)
        print("📋 Phase2 性能ベンチマーク結果サマリー")
        print("="*60)
        
        # 要件達成確認
        requirements_met = []
        
        if 'signal_generation' in self.results:
            sg = self.results['signal_generation']
            requirements_met.append(('シグナル生成レイテンシ', sg['requirement_met'], f"{sg['average_ms']:.2f}ms < 100ms"))
        
        if 'data_processing' in self.results:
            dp = self.results['data_processing']
            requirements_met.append(('データ処理スループット', dp['requirement_met'], f"{dp['throughput_per_sec']:.0f}/s ≥ 1000/s"))
        
        print("\n🎯 要件達成状況:")
        for requirement, met, detail in requirements_met:
            status = "✅ PASS" if met else "❌ FAIL"
            print(f"  {requirement}: {status} ({detail})")
        
        # 全体評価
        all_met = all(met for _, met, _ in requirements_met)
        print(f"\n🏆 総合評価: {'✅ 全要件達成' if all_met else '❌ 要件未達成あり'}")
        
        return all_met

async def run_performance_benchmark():
    """性能ベンチマーク実行"""
    print("🚀 Phase2 性能ベンチマーク開始")
    print("="*60)
    
    benchmark = PerformanceBenchmark()
    
    try:
        # 各ベンチマーク実行
        await benchmark.benchmark_signal_generation_latency()
        await benchmark.benchmark_data_processing_throughput()
        await benchmark.benchmark_memory_usage()
        await benchmark.benchmark_concurrent_processing()
        
        # レポート生成
        all_requirements_met = benchmark.generate_performance_report()
        
        return all_requirements_met
        
    except Exception as e:
        print(f"❌ ベンチマーク実行エラー: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_performance_benchmark())
    sys.exit(0 if success else 1)