#!/usr/bin/env python3
"""
Phase2統合テスト - kiro設計計画準拠
実装担当: Claude (設計: kiro)
参照: .kiro/specs/breakout-trading-system/tasks.md
"""

import asyncio
import unittest
import tempfile
import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# テスト対象システム
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import (
    RealtimeSignalSystem, MarketDataFeed, SignalGenerator, 
    SignalTransmissionSystem, MarketData, TradingSignal
)

class TestPhase2Integration(unittest.TestCase):
    """Phase2統合テスト"""
    
    def setUp(self):
        """テスト初期化"""
        self.test_config = {
            'data_buffer_size': 100,
            'signal_quality_threshold': 0.5,
            'max_signals_per_minute': 10,
            'health_check_interval': 5
        }
        
    def test_market_data_validation(self):
        """市場データ検証テスト - tasks.md:64"""
        feed = MarketDataFeed()
        
        # 正常データ
        valid_data = {
            'timestamp': '2025-07-18T22:00:00',
            'symbol': 'EURUSD',
            'open': 1.1000,
            'high': 1.1050,
            'low': 1.0950,
            'close': 1.1025,
            'volume': 1000
        }
        self.assertTrue(feed._validate_data(valid_data))
        
        # 異常データ
        invalid_data = {
            'timestamp': '2025-07-18T22:00:00',
            'symbol': 'EURUSD',
            'open': 1.1000,
            'high': 1.0900,  # high < open (異常)
            'low': 1.0950,
            'close': 1.1025
        }
        self.assertFalse(feed._validate_data(invalid_data))
        
    def test_signal_quality_evaluation(self):
        """シグナル品質評価テスト - tasks.md:72"""
        feed = MarketDataFeed()
        generator = SignalGenerator(feed)
        
        # テストデータ準備
        market_data = MarketData(
            timestamp=datetime.now(),
            symbol='EURUSD',
            open=1.1000,
            high=1.1050,
            low=1.0950,
            close=1.1025,
            volume=2000
        )
        
        signal = TradingSignal(
            timestamp=datetime.now(),
            symbol='EURUSD',
            action='BUY',
            quantity=0.1,
            price=1.1025,
            stop_loss=1.0950,
            take_profit=1.1175
        )
        
        # 品質評価実行
        quality = generator._evaluate_signal_quality(signal, market_data)
        self.assertGreaterEqual(quality, 0.0)
        self.assertLessEqual(quality, 1.0)
        
    def test_wfa_parameter_loading(self):
        """WFA最適化パラメータ読み込みテスト - tasks.md:69"""
        generator = SignalGenerator(MarketDataFeed())
        
        # デフォルトパラメータ確認
        required_params = ['lookback_period', 'breakout_threshold', 'atr_period']
        for param in required_params:
            self.assertIn(param, generator.wfa_params)
            
    def test_signal_database_operations(self):
        """シグナルデータベース操作テスト - tasks.md:79"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            # テスト用データベース設定
            import realtime_signal_generator
            original_db_path = realtime_signal_generator.CONFIG['database_path']
            realtime_signal_generator.CONFIG['database_path'] = tmp_db.name
            
            try:
                # 送信システム初期化
                transmission = SignalTransmissionSystem()
                
                # データベーステーブル存在確認
                conn = sqlite3.connect(tmp_db.name)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
                result = cursor.fetchone()
                self.assertIsNotNone(result)
                conn.close()
                
            finally:
                # 設定復元
                realtime_signal_generator.CONFIG['database_path'] = original_db_path

class TestPhase2AsyncIntegration(unittest.IsolatedAsyncioTestCase):
    """Phase2非同期統合テスト"""
    
    async def test_market_data_processing_flow(self):
        """市場データ処理フローテスト - tasks.md:60-65"""
        feed = MarketDataFeed()
        
        # モックデータ準備
        test_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'EURUSD',
            'open': 1.1000,
            'high': 1.1050,
            'low': 1.0950,
            'close': 1.1025,
            'volume': 1000
        }
        
        # データ処理実行
        await feed._process_market_data(test_data)
        
        # バッファ確認
        with feed.buffer_lock:
            self.assertEqual(len(feed.data_buffer), 1)
            stored_data = feed.data_buffer[0]
            self.assertEqual(stored_data.symbol, 'EURUSD')
            self.assertEqual(stored_data.close, 1.1025)
    
    async def test_signal_generation_latency(self):
        """シグナル生成レイテンシテスト - 要件1.2: <100ms"""
        feed = MarketDataFeed()
        generator = SignalGenerator(feed)
        
        # テストデータ準備（ブレイクアウト条件）
        base_time = datetime.now()
        test_data = []
        
        # 20期間の履歴データ
        for i in range(20):
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
        
        # ブレイクアウト条件のデータ
        breakout_data = MarketData(
            timestamp=base_time + timedelta(minutes=21),
            symbol='EURUSD',
            open=1.1050,
            high=1.1080,  # 明確なブレイクアウト
            low=1.1045,
            close=1.1075,
            volume=2000
        )
        
        # レイテンシ測定
        start_time = asyncio.get_event_loop().time()
        signal = await generator._detect_breakout_signal(breakout_data)
        end_time = asyncio.get_event_loop().time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # 100ms以下確認
        self.assertLess(latency_ms, 100, f"Signal generation latency {latency_ms:.2f}ms exceeds 100ms requirement")
        
        # シグナル生成確認
        if signal:
            self.assertEqual(signal.action, 'BUY')
            self.assertEqual(signal.symbol, 'EURUSD')
    
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_signal_transmission_fallback(self, mock_file_bridge, mock_tcp_bridge):
        """シグナル送信フォールバック機能テスト - tasks.md:76-81"""
        # TCP失敗、ファイル成功のシナリオ
        mock_tcp_instance = mock_tcp_bridge.return_value
        mock_tcp_instance.is_connected.return_value = False
        mock_tcp_instance.send_data = AsyncMock(return_value=False)
        
        mock_file_instance = mock_file_bridge.return_value
        mock_file_instance.send_message = AsyncMock(return_value=True)
        
        # 送信システム初期化
        transmission = SignalTransmissionSystem()
        
        # テストシグナル
        signal = TradingSignal(
            timestamp=datetime.now(),
            symbol='EURUSD',
            action='BUY',
            quantity=0.1,
            price=1.1025
        )
        
        # 送信実行
        result = await transmission._transmit_signal(signal)
        
        # フォールバック確認
        self.assertTrue(result)
        mock_file_instance.send_message.assert_called_once()
    
    async def test_rate_limiting(self):
        """レート制限テスト - CONFIG['max_signals_per_minute']"""
        transmission = SignalTransmissionSystem()
        
        # レート制限内確認
        transmission.sent_signals_count = 5
        self.assertTrue(transmission._check_rate_limit())
        
        # レート制限超過確認
        transmission.sent_signals_count = 150
        self.assertFalse(transmission._check_rate_limit())

class TestPhase2PerformanceRequirements(unittest.IsolatedAsyncioTestCase):
    """Phase2性能要件テスト - kiro要件準拠"""
    
    async def test_data_throughput_requirement(self):
        """データ処理スループット要件テスト - 1000ティック/秒対応"""
        feed = MarketDataFeed()
        
        # 1000ティック/秒シミュレーション（1秒間で1000データ）
        start_time = asyncio.get_event_loop().time()
        
        for i in range(100):  # 100データで簡易テスト
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
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # 100データを1秒以内で処理（1000ティック/秒の1/10）
        self.assertLess(processing_time, 0.1, f"Data processing too slow: {processing_time:.3f}s for 100 ticks")
    
    async def test_signal_detection_latency(self):
        """シグナル検出レイテンシ要件テスト - <50ms"""
        feed = MarketDataFeed()
        generator = SignalGenerator(feed)
        
        # 履歴データ準備
        for i in range(25):
            data = MarketData(
                timestamp=datetime.now() + timedelta(minutes=i),
                symbol='EURUSD',
                open=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
                volume=1000
            )
            with feed.buffer_lock:
                feed.data_buffer.append(data)
        
        # シグナル検出レイテンシ測定
        test_data = MarketData(
            timestamp=datetime.now() + timedelta(minutes=26),
            symbol='EURUSD',
            open=1.1000,
            high=1.1100,  # 強いブレイクアウト
            low=1.0995,
            close=1.1095,
            volume=1500
        )
        
        start_time = asyncio.get_event_loop().time()
        signal = await generator._detect_breakout_signal(test_data)
        end_time = asyncio.get_event_loop().time()
        
        latency_ms = (end_time - start_time) * 1000
        self.assertLess(latency_ms, 50, f"Signal detection latency {latency_ms:.2f}ms exceeds 50ms requirement")

def run_integration_tests():
    """統合テスト実行"""
    print("Phase2統合テスト開始...")
    
    # 同期テスト実行
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase2Integration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 非同期テスト実行（簡単なテストのみ）
    print("\n非同期テスト実行...")
    
    # 基本的なモジュールインポートテスト
    try:
        from realtime_signal_generator import RealtimeSignalSystem
        print("✅ RealtimeSignalSystem モジュールインポート成功")
    except Exception as e:
        print(f"❌ モジュールインポートエラー: {e}")
        return False
    
    print(f"Phase2統合テスト完了")
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)