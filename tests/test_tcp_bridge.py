#!/usr/bin/env python3
"""
TCP通信ブリッジ単体テスト
"""

import asyncio
import unittest
import time
import json
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

# テスト対象インポート
from communication.tcp_bridge import (
    TCPBridge, TradingSignal, TradingMessage, MessageType, ConnectionState
)

class TestTCPBridge(unittest.TestCase):
    """TCP通信ブリッジテストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        self.bridge = TCPBridge(
            host="localhost",
            port=8888,
            reconnect_delay=0.1,
            max_reconnect_attempts=2,
            heartbeat_interval=1.0,
            timeout=1.0
        )
        
        # テストシグナル
        self.test_signal = TradingSignal(
            timestamp=time.time(),
            symbol="USDJPY",
            action="BUY",
            price=150.00,
            volume=0.1,
            slippage=0.0001,
            confidence=0.85,
            lookback_period=20,
            signal_id="test_001"
        )
    
    def test_trading_signal_creation(self):
        """取引シグナル作成テスト"""
        signal = self.test_signal
        
        self.assertEqual(signal.symbol, "USDJPY")
        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.price, 150.00)
        self.assertEqual(signal.volume, 0.1)
        self.assertEqual(signal.signal_id, "test_001")
    
    def test_trading_message_serialization(self):
        """メッセージシリアライゼーションテスト"""
        message = TradingMessage(
            message_type=MessageType.SIGNAL,
            timestamp=time.time(),
            data={"test": "data"},
            message_id="test_msg_001"
        )
        
        # JSON変換
        json_str = message.to_json()
        self.assertIsInstance(json_str, str)
        
        # JSON解析
        parsed = json.loads(json_str)
        self.assertEqual(parsed['message_type'], MessageType.SIGNAL.value)
        self.assertEqual(parsed['data']['test'], "data")
        self.assertEqual(parsed['message_id'], "test_msg_001")
        
        # 復元
        restored = TradingMessage.from_json(json_str)
        self.assertEqual(restored.message_type, MessageType.SIGNAL)
        self.assertEqual(restored.data['test'], "data")
        self.assertEqual(restored.message_id, "test_msg_001")
    
    def test_bridge_initialization(self):
        """ブリッジ初期化テスト"""
        bridge = TCPBridge(host="testhost", port=9999)
        
        self.assertEqual(bridge.host, "testhost")
        self.assertEqual(bridge.port, 9999)
        self.assertEqual(bridge.connection_state, ConnectionState.DISCONNECTED)
        self.assertEqual(bridge.stats['messages_sent'], 0)
        self.assertEqual(bridge.stats['messages_received'], 0)
    
    def test_connection_status(self):
        """接続状態取得テスト"""
        status = self.bridge.get_connection_status()
        
        self.assertIn('state', status)
        self.assertIn('host', status)
        self.assertIn('port', status)
        self.assertIn('stats', status)
        
        self.assertEqual(status['state'], ConnectionState.DISCONNECTED.value)
        self.assertEqual(status['host'], "localhost")
        self.assertEqual(status['port'], 8888)
    
    def test_message_handler_registration(self):
        """メッセージハンドラー登録テスト"""
        def test_handler(message):
            pass
        
        # ハンドラー登録前
        self.assertNotIn(MessageType.SIGNAL, self.bridge.message_handlers)
        
        # ハンドラー登録
        self.bridge.register_message_handler(MessageType.SIGNAL, test_handler)
        
        # ハンドラー登録後
        self.assertIn(MessageType.SIGNAL, self.bridge.message_handlers)
        self.assertEqual(self.bridge.message_handlers[MessageType.SIGNAL], test_handler)

class TestTCPBridgeAsync(unittest.IsolatedAsyncioTestCase):
    """TCP通信ブリッジ非同期テストクラス"""
    
    async def asyncSetUp(self):
        """非同期テスト前準備"""
        self.bridge = TCPBridge(
            host="localhost",
            port=8888,
            reconnect_delay=0.1,
            max_reconnect_attempts=2,
            heartbeat_interval=1.0,
            timeout=1.0
        )
        
        # テストシグナル
        self.test_signal = TradingSignal(
            timestamp=time.time(),
            symbol="USDJPY",
            action="BUY",
            price=150.00,
            volume=0.1,
            slippage=0.0001,
            confidence=0.85,
            lookback_period=20,
            signal_id="test_001"
        )
    
    async def test_connection_failure(self):
        """接続失敗テスト"""
        # 存在しないポートへの接続
        bridge = TCPBridge(host="localhost", port=9999, timeout=0.1)
        
        result = await bridge.connect()
        self.assertFalse(result)
        self.assertEqual(bridge.connection_state, ConnectionState.ERROR)
        self.assertEqual(bridge.stats['connection_attempts'], 1)
        self.assertEqual(bridge.stats['successful_connections'], 0)
        self.assertEqual(bridge.stats['connection_errors'], 1)
    
    @patch('asyncio.open_connection')
    async def test_connection_success(self, mock_open_connection):
        """接続成功テスト（モック使用）"""
        # モック設定
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (mock_reader, mock_writer)
        
        # 接続テスト
        result = await self.bridge.connect()
        
        self.assertTrue(result)
        self.assertEqual(self.bridge.connection_state, ConnectionState.CONNECTED)
        self.assertEqual(self.bridge.stats['successful_connections'], 1)
        self.assertIsNotNone(self.bridge.reader)
        self.assertIsNotNone(self.bridge.writer)
    
    async def test_send_message_without_connection(self):
        """未接続時メッセージ送信テスト"""
        message = TradingMessage(
            message_type=MessageType.SIGNAL,
            timestamp=time.time(),
            data={"test": "data"},
            message_id="test_msg_001"
        )
        
        result = await self.bridge.send_message(message)
        
        self.assertFalse(result)
        self.assertEqual(self.bridge.stats['messages_sent'], 0)
    
    @patch('asyncio.open_connection')
    async def test_send_message_with_connection(self, mock_open_connection):
        """接続時メッセージ送信テスト（モック使用）"""
        # モック設定
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (mock_reader, mock_writer)
        
        # 接続
        await self.bridge.connect()
        
        # メッセージ送信
        message = TradingMessage(
            message_type=MessageType.SIGNAL,
            timestamp=time.time(),
            data={"test": "data"},
            message_id="test_msg_001"
        )
        
        result = await self.bridge.send_message(message)
        
        self.assertTrue(result)
        self.assertEqual(self.bridge.stats['messages_sent'], 1)
        mock_writer.write.assert_called_once()
        mock_writer.drain.assert_called_once()
    
    @patch('asyncio.open_connection')
    async def test_send_signal(self, mock_open_connection):
        """シグナル送信テスト（モック使用）"""
        # モック設定
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (mock_reader, mock_writer)
        
        # 接続
        await self.bridge.connect()
        
        # シグナル送信
        result = await self.bridge.send_signal(self.test_signal)
        
        self.assertTrue(result)
        self.assertEqual(self.bridge.stats['messages_sent'], 1)
        mock_writer.write.assert_called_once()
        mock_writer.drain.assert_called_once()
    
    async def test_wait_for_confirmation_timeout(self):
        """確認応答タイムアウトテスト"""
        result = await self.bridge.wait_for_confirmation("test_msg_001", timeout=0.1)
        
        self.assertFalse(result)
        self.assertNotIn("test_msg_001", self.bridge.pending_confirmations)
    
    async def test_wait_for_confirmation_success(self):
        """確認応答成功テスト"""
        # 確認応答を別タスクで送信
        async def send_confirmation():
            await asyncio.sleep(0.1)
            message = TradingMessage(
                message_type=MessageType.CONFIRMATION,
                timestamp=time.time(),
                data={"message_id": "test_msg_001"},
                message_id="conf_001"
            )
            await self.bridge._handle_message(message)
        
        # 確認応答待機と送信を並行実行
        confirmation_task = asyncio.create_task(send_confirmation())
        result = await self.bridge.wait_for_confirmation("test_msg_001", timeout=1.0)
        
        await confirmation_task
        
        self.assertTrue(result)
        self.assertNotIn("test_msg_001", self.bridge.pending_confirmations)
    
    async def test_heartbeat_handling(self):
        """ハートビート処理テスト"""
        initial_time = self.bridge.last_heartbeat_received
        
        # ハートビートメッセージ処理
        heartbeat_message = TradingMessage(
            message_type=MessageType.HEARTBEAT,
            timestamp=time.time(),
            data={"status": "alive"},
            message_id="heartbeat_001"
        )
        
        await self.bridge._handle_message(heartbeat_message)
        
        # ハートビート受信時間が更新されることを確認
        self.assertGreater(self.bridge.last_heartbeat_received, initial_time)
    
    async def test_custom_message_handler(self):
        """カスタムメッセージハンドラーテスト"""
        handler_called = False
        received_message = None
        
        async def custom_handler(message):
            nonlocal handler_called, received_message
            handler_called = True
            received_message = message
        
        # ハンドラー登録
        self.bridge.register_message_handler(MessageType.STATUS_REQUEST, custom_handler)
        
        # メッセージ処理
        test_message = TradingMessage(
            message_type=MessageType.STATUS_REQUEST,
            timestamp=time.time(),
            data={"request": "status"},
            message_id="status_001"
        )
        
        await self.bridge._handle_message(test_message)
        
        # ハンドラーが呼ばれたことを確認
        self.assertTrue(handler_called)
        self.assertEqual(received_message.message_id, "status_001")
    
    async def asyncTearDown(self):
        """非同期テスト後処理"""
        if self.bridge.connection_state == ConnectionState.CONNECTED:
            await self.bridge.disconnect()

class TestTCPBridgeIntegration(unittest.TestCase):
    """TCP通信ブリッジ統合テスト"""
    
    def test_performance_requirements(self):
        """パフォーマンス要件テスト"""
        # メッセージシリアライゼーション性能
        start_time = time.time()
        
        for i in range(1000):
            message = TradingMessage(
                message_type=MessageType.SIGNAL,
                timestamp=time.time(),
                data={"test": f"data_{i}"},
                message_id=f"test_msg_{i}"
            )
            json_str = message.to_json()
            restored = TradingMessage.from_json(json_str)
        
        elapsed = time.time() - start_time
        
        # 1000メッセージの処理が1秒以内
        self.assertLess(elapsed, 1.0)
        print(f"1000メッセージ処理時間: {elapsed:.3f}秒")
    
    def test_concurrent_message_creation(self):
        """並行メッセージ作成テスト"""
        import threading
        
        messages = []
        
        def create_messages():
            for i in range(100):
                message = TradingMessage(
                    message_type=MessageType.SIGNAL,
                    timestamp=time.time(),
                    data={"thread_data": f"data_{i}"},
                    message_id=f"thread_msg_{i}"
                )
                messages.append(message)
        
        # 複数スレッドで並行実行
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_messages)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 全メッセージが作成されたことを確認
        self.assertEqual(len(messages), 500)
        
        # メッセージIDの重複がないことを確認
        message_ids = [msg.message_id for msg in messages]
        self.assertEqual(len(set(message_ids)), 500)

if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)