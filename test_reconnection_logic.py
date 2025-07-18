#!/usr/bin/env python3
"""
再接続ロジック強化テスト - 改善4検証
Gemini査読対応: 3回試行・指数バックオフ実装テスト
"""

import asyncio
import unittest
import time
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import MarketDataFeed, SignalTransmissionSystem

class TestReconnectionLogic(unittest.IsolatedAsyncioTestCase):
    """再接続ロジック強化テスト"""
    
    @patch('realtime_signal_generator.CONFIG', {
        'communication': {
            'reconnect_attempts': 3,
            'reconnect_timeout': 1.0,  # テスト用短縮
            'data_tcp_host': 'localhost',
            'data_tcp_port': 9091
        }
    })
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_exponential_backoff_reconnection(self, mock_file_bridge, mock_tcp_bridge):
        """指数バックオフ再接続テスト"""
        # TCP接続失敗・成功シナリオ
        mock_tcp_instance = mock_tcp_bridge.return_value
        
        # 1回目・2回目失敗、3回目成功
        connection_error = ConnectionError("Connection refused")
        mock_tcp_instance.connect = AsyncMock(side_effect=[connection_error, connection_error, True])
        
        feed = MarketDataFeed()
        
        # 再接続実行・時間測定
        start_time = time.time()
        result = await feed._connect_tcp()
        end_time = time.time()
        
        # 成功確認
        self.assertTrue(result)
        
        # 呼び出し回数確認
        self.assertEqual(mock_tcp_instance.connect.call_count, 3)
        
        # 指数バックオフ時間確認（1s + 2s = 約3秒）
        elapsed_time = end_time - start_time
        self.assertGreater(elapsed_time, 2.8)  # 最低2.8秒
        self.assertLess(elapsed_time, 6.0)     # 最大6.0秒（マージン増加）
        
    @patch('realtime_signal_generator.CONFIG', {
        'communication': {
            'reconnect_attempts': 3,
            'reconnect_timeout': 0.1,  # テスト用短縮
            'signal_tcp_host': 'localhost',
            'signal_tcp_port': 9090
        }
    })
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_max_retry_attempts(self, mock_file_bridge, mock_tcp_bridge):
        """最大試行回数テスト"""
        # 全て失敗
        mock_tcp_instance = mock_tcp_bridge.return_value
        connection_error = ConnectionError("Connection refused")
        mock_tcp_instance.connect = AsyncMock(side_effect=[connection_error, connection_error, connection_error])
        
        transmission = SignalTransmissionSystem()
        
        # 再接続実行
        result = await transmission._connect_tcp()
        
        # 失敗確認
        self.assertFalse(result)
        
        # 3回試行確認
        self.assertEqual(mock_tcp_instance.connect.call_count, 3)
        
    @patch('realtime_signal_generator.CONFIG', {
        'communication': {
            'reconnect_attempts': 2,
            'reconnect_timeout': 0.5,
            'data_tcp_host': 'localhost',
            'data_tcp_port': 9091
        }
    })
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_immediate_success(self, mock_file_bridge, mock_tcp_bridge):
        """即座成功テスト"""
        # 1回目で成功
        mock_tcp_instance = mock_tcp_bridge.return_value
        mock_tcp_instance.connect = AsyncMock(return_value=True)
        
        feed = MarketDataFeed()
        
        # 再接続実行・時間測定
        start_time = time.time()
        result = await feed._connect_tcp()
        end_time = time.time()
        
        # 成功確認
        self.assertTrue(result)
        
        # 1回のみ呼び出し確認
        self.assertEqual(mock_tcp_instance.connect.call_count, 1)
        
        # 待機時間なし確認（0.1秒以下）
        elapsed_time = end_time - start_time
        self.assertLess(elapsed_time, 0.1)
        
    @patch('realtime_signal_generator.CONFIG', {
        'communication': {
            'reconnect_attempts': 3,
            'reconnect_timeout': 0.1,
            'signal_tcp_host': 'localhost',
            'signal_tcp_port': 9090
        }
    })
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_connection_exception_handling(self, mock_file_bridge, mock_tcp_bridge):
        """接続例外処理テスト"""
        # 例外発生後成功
        mock_tcp_instance = mock_tcp_bridge.return_value
        mock_tcp_instance.connect = AsyncMock(side_effect=[
            ConnectionError("Connection refused"),
            OSError("Network unreachable"),
            True
        ])
        
        transmission = SignalTransmissionSystem()
        
        # 再接続実行
        result = await transmission._connect_tcp()
        
        # 成功確認
        self.assertTrue(result)
        
        # 3回試行確認
        self.assertEqual(mock_tcp_instance.connect.call_count, 3)

class TestHealthCheckReconnection(unittest.IsolatedAsyncioTestCase):
    """健全性チェック再接続テスト"""
    
    @patch('realtime_signal_generator.CONFIG', {
        'communication': {
            'reconnect_attempts': 2,
            'reconnect_timeout': 0.1,
            'data_tcp_host': 'localhost',
            'data_tcp_port': 9091
        }
    })
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_health_check_reconnection(self, mock_file_bridge, mock_tcp_bridge):
        """健全性チェック再接続テスト"""
        mock_tcp_instance = mock_tcp_bridge.return_value
        mock_tcp_instance.is_connected.return_value = False
        mock_tcp_instance.connect = AsyncMock(return_value=True)
        
        feed = MarketDataFeed()
        
        # 健全性チェック実行
        await feed._perform_health_check()
        
        # 再接続試行確認
        mock_tcp_instance.connect.assert_called_once()

class TestSignalTransmissionReconnection(unittest.IsolatedAsyncioTestCase):
    """シグナル送信再接続テスト"""
    
    @patch('realtime_signal_generator.CONFIG', {
        'communication': {
            'reconnect_attempts': 2,
            'reconnect_timeout': 0.1,
            'signal_tcp_host': 'localhost',
            'signal_tcp_port': 9090
        }
    })
    @patch('realtime_signal_generator.TCPBridge')
    @patch('realtime_signal_generator.FileBridge')
    async def test_transmission_failure_reconnection(self, mock_file_bridge, mock_tcp_bridge):
        """送信失敗時再接続テスト"""
        mock_tcp_instance = mock_tcp_bridge.return_value
        mock_tcp_instance.is_connected.return_value = True
        
        # 1回目送信失敗、再接続後成功
        mock_tcp_instance.send_data = AsyncMock(side_effect=[
            ConnectionError("Connection lost"),
            True  # 再接続後成功
        ])
        mock_tcp_instance.connect = AsyncMock(return_value=True)
        
        mock_file_instance = mock_file_bridge.return_value
        
        transmission = SignalTransmissionSystem()
        
        # テストデータ（正しいTradingSignal形式）
        from realtime_signal_generator import TradingSignal
        from datetime import datetime
        
        signal = TradingSignal(
            timestamp=datetime.now(),
            symbol='EURUSD',
            action='BUY',
            quantity=0.1,
            price=1.1000
        )
        
        # 送信実行
        result = await transmission._transmit_signal(signal)
        
        # 成功確認（再接続後成功）
        self.assertTrue(result)
        
        # 再接続確認
        mock_tcp_instance.connect.assert_called_once()
        
        # 2回送信試行確認
        self.assertEqual(mock_tcp_instance.send_data.call_count, 2)

def run_reconnection_tests():
    """再接続ロジックテスト実行"""
    print("再接続ロジック強化テスト開始...")
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラス追加
    suite.addTests(loader.loadTestsFromTestCase(TestReconnectionLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthCheckReconnection))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalTransmissionReconnection))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n再接続ロジックテスト完了")
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_reconnection_tests()
    sys.exit(0 if success else 1)