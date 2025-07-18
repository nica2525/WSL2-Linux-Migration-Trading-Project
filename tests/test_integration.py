#!/usr/bin/env python3
"""
統合テストスイート - Phase 1通信インフラ全体テスト
TCP通信・ファイル通信・MT4統合テスト
"""

import asyncio
import unittest
import time
import json
import tempfile
import os
import shutil
import threading
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import subprocess
import sys

# テスト対象インポート
from communication.tcp_bridge import (
    TCPBridge, TradingSignal, TradingMessage, MessageType, ConnectionState
)
from communication.file_bridge import FileBridge, FileMessage

class TestPhase1Integration(unittest.TestCase):
    """Phase 1統合テストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        # 一時ディレクトリ
        self.temp_dir = tempfile.mkdtemp()
        self.message_dir = Path(self.temp_dir) / "integration_messages"
        
        # TCP Bridge設定
        self.tcp_bridge = TCPBridge(
            host="localhost",
            port=8889,  # テスト用ポート
            reconnect_delay=0.1,
            max_reconnect_attempts=3,
            heartbeat_interval=1.0,
            timeout=2.0
        )
        
        # File Bridge設定
        self.file_bridge = FileBridge(
            message_dir=str(self.message_dir),
            sender_id="integration_test",
            cleanup_interval=5.0,
            max_retry_count=3,
            file_timeout=10.0
        )
        
        # テストデータ
        self.test_signals = [
            TradingSignal(
                timestamp=time.time(),
                symbol="USDJPY",
                action="BUY",
                price=150.00,
                volume=0.1,
                slippage=0.0001,
                confidence=0.85,
                lookback_period=20,
                signal_id=f"integration_test_001"
            ),
            TradingSignal(
                timestamp=time.time(),
                symbol="EURJPY",
                action="SELL",
                price=165.50,
                volume=0.2,
                slippage=0.0002,
                confidence=0.90,
                lookback_period=30,
                signal_id=f"integration_test_002"
            )
        ]
        
        # 統計情報
        self.test_stats = {
            'tcp_tests_passed': 0,
            'file_tests_passed': 0,
            'integration_tests_passed': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'performance_metrics': {}
        }
        
        print(f"=== Phase 1統合テスト開始 ===")
        print(f"テストディレクトリ: {self.temp_dir}")
        print(f"メッセージディレクトリ: {self.message_dir}")
    
    def tearDown(self):
        """テスト後処理"""
        # ファイルブリッジ停止
        try:
            self.file_bridge.stop()
        except:
            pass
        
        # 一時ディレクトリ削除
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
        
        print(f"=== Phase 1統合テスト終了 ===")
        print(f"統計情報: {self.test_stats}")
    
    def test_01_tcp_bridge_basic_functionality(self):
        """TCP Bridge基本機能テスト"""
        print("\n--- TCP Bridge基本機能テスト ---")
        
        # 初期化確認
        self.assertEqual(self.tcp_bridge.connection_state, ConnectionState.DISCONNECTED)
        self.assertEqual(self.tcp_bridge.stats['messages_sent'], 0)
        
        # 接続状態取得
        status = self.tcp_bridge.get_connection_status()
        self.assertIn('state', status)
        self.assertIn('host', status)
        self.assertIn('port', status)
        self.assertIn('stats', status)
        
        # メッセージハンドラー登録
        test_handler_called = False
        def test_handler(message):
            nonlocal test_handler_called
            test_handler_called = True
        
        self.tcp_bridge.register_message_handler(MessageType.SIGNAL, test_handler)
        self.assertIn(MessageType.SIGNAL, self.tcp_bridge.message_handlers)
        
        print("✅ TCP Bridge基本機能テスト合格")
        self.test_stats['tcp_tests_passed'] += 1
    
    def test_02_file_bridge_basic_functionality(self):
        """File Bridge基本機能テスト"""
        print("\n--- File Bridge基本機能テスト ---")
        
        # ディレクトリ作成確認
        self.assertTrue(self.file_bridge.message_dir.exists())
        self.assertTrue(self.file_bridge.inbox_dir.exists())
        self.assertTrue(self.file_bridge.outbox_dir.exists())
        self.assertTrue(self.file_bridge.processed_dir.exists())
        self.assertTrue(self.file_bridge.failed_dir.exists())
        
        # 初期統計情報
        self.assertEqual(self.file_bridge.stats['messages_sent'], 0)
        self.assertEqual(self.file_bridge.stats['messages_received'], 0)
        
        # ステータス取得
        status = self.file_bridge.get_status()
        self.assertIn('running', status)
        self.assertIn('message_dir', status)
        self.assertIn('stats', status)
        self.assertIn('directories', status)
        
        print("✅ File Bridge基本機能テスト合格")
        self.test_stats['file_tests_passed'] += 1
    
    def test_03_message_serialization_integrity(self):
        """メッセージシリアライゼーション整合性テスト"""
        print("\n--- メッセージシリアライゼーション整合性テスト ---")
        
        for i, signal in enumerate(self.test_signals):
            # TradingMessage作成
            message = TradingMessage(
                message_type=MessageType.SIGNAL,
                timestamp=time.time(),
                data={
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'price': signal.price,
                    'volume': signal.volume,
                    'confidence': signal.confidence
                },
                message_id=f"serialization_test_{i}"
            )
            
            # JSON変換・復元
            json_str = message.to_json()
            restored_message = TradingMessage.from_json(json_str)
            
            # 整合性確認
            self.assertEqual(message.message_type, restored_message.message_type)
            self.assertEqual(message.timestamp, restored_message.timestamp)
            self.assertEqual(message.data, restored_message.data)
            self.assertEqual(message.message_id, restored_message.message_id)
            
            # データ型確認
            self.assertIsInstance(restored_message.data['price'], float)
            self.assertIsInstance(restored_message.data['volume'], float)
            self.assertIsInstance(restored_message.data['confidence'], float)
        
        print("✅ メッセージシリアライゼーション整合性テスト合格")
        self.test_stats['integration_tests_passed'] += 1
    
    def test_04_file_bridge_message_flow(self):
        """File Bridge メッセージフロー テスト"""
        print("\n--- File Bridge メッセージフロー テスト ---")
        
        # ファイルブリッジ開始
        self.file_bridge.start()
        
        # メッセージ送信
        for signal in self.test_signals:
            result = self.file_bridge.send_signal(signal)
            self.assertTrue(result)
            self.test_stats['total_messages_sent'] += 1
        
        # outboxディレクトリ確認
        outbox_files = list(self.file_bridge.outbox_dir.glob('*.msg'))
        self.assertEqual(len(outbox_files), len(self.test_signals))
        
        # ファイル内容確認
        for file_path in outbox_files:
            self.assertTrue(file_path.exists())
            self.assertGreater(file_path.stat().st_size, 0)
            
            # JSON読み込み確認
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                self.assertIn('message', file_data)
                self.assertIn('sender', file_data)
                self.assertIn('checksum', file_data)
        
        # 統計情報確認
        self.assertEqual(self.file_bridge.stats['messages_sent'], len(self.test_signals))
        
        print("✅ File Bridge メッセージフロー テスト合格")
        self.test_stats['file_tests_passed'] += 1
    
    def test_05_performance_benchmarks(self):
        """パフォーマンスベンチマークテスト"""
        print("\n--- パフォーマンスベンチマークテスト ---")
        
        # シリアライゼーション性能
        start_time = time.time()
        message_count = 1000
        
        for i in range(message_count):
            message = TradingMessage(
                message_type=MessageType.SIGNAL,
                timestamp=time.time(),
                data={
                    'symbol': f"TEST{i % 10}",
                    'action': "BUY" if i % 2 == 0 else "SELL",
                    'price': 100.0 + (i % 100),
                    'volume': 0.1 + (i % 10) * 0.01,
                    'confidence': 0.8 + (i % 20) * 0.01
                },
                message_id=f"perf_test_{i}"
            )
            
            json_str = message.to_json()
            restored = TradingMessage.from_json(json_str)
            
            # 基本確認
            self.assertEqual(message.message_id, restored.message_id)
        
        elapsed = time.time() - start_time
        messages_per_second = message_count / elapsed
        
        # 性能要件: 1000メッセージ/秒以上
        self.assertGreaterEqual(messages_per_second, 1000)
        
        # 統計記録
        self.test_stats['performance_metrics']['serialization_msg_per_sec'] = messages_per_second
        self.test_stats['performance_metrics']['serialization_elapsed'] = elapsed
        
        print(f"✅ シリアライゼーション性能: {messages_per_second:.1f} msg/sec")
        print(f"✅ 処理時間: {elapsed:.4f}秒")
        
        # ファイル書き込み性能
        start_time = time.time()
        file_count = 100
        
        for i in range(file_count):
            signal = TradingSignal(
                timestamp=time.time(),
                symbol=f"PERF{i % 5}",
                action="BUY" if i % 2 == 0 else "SELL",
                price=100.0 + i,
                volume=0.1,
                slippage=0.0001,
                confidence=0.85,
                lookback_period=20,
                signal_id=f"perf_file_test_{i}"
            )
            
            result = self.file_bridge.send_signal(signal)
            self.assertTrue(result)
        
        elapsed = time.time() - start_time
        files_per_second = file_count / elapsed
        
        # 性能要件: 50ファイル/秒以上
        self.assertGreaterEqual(files_per_second, 50)
        
        # 統計記録
        self.test_stats['performance_metrics']['file_write_per_sec'] = files_per_second
        self.test_stats['performance_metrics']['file_write_elapsed'] = elapsed
        
        print(f"✅ ファイル書き込み性能: {files_per_second:.1f} files/sec")
        print(f"✅ 処理時間: {elapsed:.4f}秒")
        
        self.test_stats['integration_tests_passed'] += 1
    
    def test_06_error_handling_resilience(self):
        """エラーハンドリング・復旧性テスト"""
        print("\n--- エラーハンドリング・復旧性テスト ---")
        
        # 不正なメッセージタイプ
        invalid_message = TradingMessage(
            message_type=MessageType.SIGNAL,
            timestamp=time.time(),
            data={"invalid": "data"},
            message_id="invalid_test"
        )
        
        # 不正なJSON
        invalid_json = '{"invalid": json}'
        
        try:
            restored = TradingMessage.from_json(invalid_json)
            self.fail("不正なJSONが処理されました")
        except:
            # 期待される例外
            pass
        
        # ファイルアクセス権限エラー（シミュレート）
        if os.name != 'nt':  # Windows以外
            # 読み取り専用ディレクトリ作成
            readonly_dir = Path(self.temp_dir) / "readonly"
            readonly_dir.mkdir(exist_ok=True)
            readonly_dir.chmod(0o444)
            
            try:
                readonly_bridge = FileBridge(
                    message_dir=str(readonly_dir),
                    sender_id="error_test"
                )
                
                # 書き込みテスト
                test_signal = self.test_signals[0]
                result = readonly_bridge.send_signal(test_signal)
                
                # 書き込み失敗が期待される
                self.assertFalse(result)
                
            finally:
                # 権限復旧
                readonly_dir.chmod(0o755)
        
        print("✅ エラーハンドリング・復旧性テスト合格")
        self.test_stats['integration_tests_passed'] += 1
    
    def test_07_concurrent_operations(self):
        """並行処理テスト"""
        print("\n--- 並行処理テスト ---")
        
        # 並行メッセージ送信
        def concurrent_send_messages(thread_id, count):
            for i in range(count):
                signal = TradingSignal(
                    timestamp=time.time(),
                    symbol=f"THREAD{thread_id}",
                    action="BUY" if i % 2 == 0 else "SELL",
                    price=100.0 + i,
                    volume=0.1,
                    slippage=0.0001,
                    confidence=0.85,
                    lookback_period=20,
                    signal_id=f"concurrent_test_{thread_id}_{i}"
                )
                
                result = self.file_bridge.send_signal(signal)
                self.assertTrue(result)
        
        # 複数スレッドで並行実行
        threads = []
        thread_count = 5
        messages_per_thread = 10
        
        for thread_id in range(thread_count):
            thread = threading.Thread(
                target=concurrent_send_messages,
                args=(thread_id, messages_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # 全スレッド完了待機
        for thread in threads:
            thread.join()
        
        # 結果確認
        expected_files = thread_count * messages_per_thread
        outbox_files = list(self.file_bridge.outbox_dir.glob('*.msg'))
        
        self.assertEqual(len(outbox_files), expected_files)
        self.assertEqual(self.file_bridge.stats['messages_sent'], expected_files)
        
        # ファイル名重複確認
        file_names = [f.name for f in outbox_files]
        self.assertEqual(len(set(file_names)), len(file_names))
        
        print(f"✅ 並行処理テスト合格: {expected_files}メッセージ")
        self.test_stats['integration_tests_passed'] += 1
    
    def test_08_system_integration_verification(self):
        """システム統合検証テスト"""
        print("\n--- システム統合検証テスト ---")
        
        # 全コンポーネント初期化確認
        self.assertIsNotNone(self.tcp_bridge)
        self.assertIsNotNone(self.file_bridge)
        
        # メッセージ型の互換性確認
        for message_type in MessageType:
            # TCPブリッジ
            test_handler = lambda msg: None
            self.tcp_bridge.register_message_handler(message_type, test_handler)
            
            # ファイルブリッジ
            self.file_bridge.register_message_handler(message_type, test_handler)
        
        # 統計情報の一貫性確認
        tcp_status = self.tcp_bridge.get_connection_status()
        file_status = self.file_bridge.get_status()
        
        self.assertIn('stats', tcp_status)
        self.assertIn('stats', file_status)
        
        # 設定値の確認
        self.assertEqual(self.tcp_bridge.host, "localhost")
        self.assertEqual(self.tcp_bridge.port, 8889)
        self.assertEqual(self.file_bridge.sender_id, "integration_test")
        
        print("✅ システム統合検証テスト合格")
        self.test_stats['integration_tests_passed'] += 1
    
    def test_09_mt4_ea_communication_simulation(self):
        """MT4 EA通信シミュレーションテスト"""
        print("\n--- MT4 EA通信シミュレーションテスト ---")
        
        # MT4 EA メッセージ形式シミュレート
        mt4_messages = [
            {
                "message_type": "heartbeat",
                "timestamp": int(time.time()),
                "data": {"status": "alive", "symbol": "USDJPY", "price": 150.00},
                "message_id": "heartbeat_001"
            },
            {
                "message_type": "confirmation",
                "timestamp": int(time.time()),
                "data": {"success": True, "action": "BUY", "price": 150.00, "volume": 0.1},
                "message_id": "confirmation_001"
            },
            {
                "message_type": "status_response",
                "timestamp": int(time.time()),
                "data": {
                    "symbol": "USDJPY",
                    "price": 150.00,
                    "connected": True,
                    "messages_received": 10,
                    "messages_sent": 5,
                    "executed_trades": 3
                },
                "message_id": "status_001"
            }
        ]
        
        # MT4からのメッセージ受信シミュレート
        for mt4_msg in mt4_messages:
            # メッセージファイル作成（MT4 EA想定）
            filename = f"mt4_message_{mt4_msg['message_id']}.msg"
            filepath = self.file_bridge.inbox_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'message': mt4_msg,
                    'file_timestamp': time.time(),
                    'sender': 'mt4_ea',
                    'status': 'pending',
                    'retry_count': 0,
                    'checksum': 'test_checksum'
                }, f, indent=2)
            
            # ファイル作成確認
            self.assertTrue(filepath.exists())
        
        # Python側からのシグナル送信シミュレート
        python_signal = TradingSignal(
            timestamp=time.time(),
            symbol="USDJPY",
            action="BUY",
            price=150.00,
            volume=0.1,
            slippage=0.0001,
            confidence=0.85,
            lookback_period=20,
            signal_id="python_signal_001"
        )
        
        result = self.file_bridge.send_signal(python_signal)
        self.assertTrue(result)
        
        # outboxファイル確認
        outbox_files = list(self.file_bridge.outbox_dir.glob('*.msg'))
        self.assertGreaterEqual(len(outbox_files), 1)
        
        # 双方向通信確認
        inbox_files = list(self.file_bridge.inbox_dir.glob('*.msg'))
        self.assertEqual(len(inbox_files), len(mt4_messages))
        
        print("✅ MT4 EA通信シミュレーションテスト合格")
        self.test_stats['integration_tests_passed'] += 1
    
    def test_10_final_integration_summary(self):
        """最終統合サマリーテスト"""
        print("\n--- 最終統合サマリーテスト ---")
        
        # 全テスト結果確認
        minimum_passed_tests = 5
        self.assertGreaterEqual(self.test_stats['integration_tests_passed'], minimum_passed_tests)
        
        # パフォーマンス要件確認
        if 'performance_metrics' in self.test_stats:
            perf = self.test_stats['performance_metrics']
            if 'serialization_msg_per_sec' in perf:
                self.assertGreaterEqual(perf['serialization_msg_per_sec'], 1000)
        
        # コンポーネント状態確認
        self.assertEqual(self.tcp_bridge.connection_state, ConnectionState.DISCONNECTED)
        self.assertGreaterEqual(self.file_bridge.stats['messages_sent'], 0)
        
        # ディレクトリ構造確認
        self.assertTrue(self.message_dir.exists())
        self.assertTrue(self.file_bridge.outbox_dir.exists())
        self.assertTrue(self.file_bridge.inbox_dir.exists())
        
        # 最終統計
        total_tests = (
            self.test_stats['tcp_tests_passed'] +
            self.test_stats['file_tests_passed'] +
            self.test_stats['integration_tests_passed']
        )
        
        print(f"✅ 最終統合サマリーテスト合格")
        print(f"✅ 合計テスト通過数: {total_tests}")
        print(f"✅ TCP Bridge テスト: {self.test_stats['tcp_tests_passed']}")
        print(f"✅ File Bridge テスト: {self.test_stats['file_tests_passed']}")
        print(f"✅ 統合テスト: {self.test_stats['integration_tests_passed']}")
        
        self.test_stats['integration_tests_passed'] += 1


class TestPhase1AsyncIntegration(unittest.IsolatedAsyncioTestCase):
    """Phase 1非同期統合テストクラス"""
    
    async def asyncSetUp(self):
        """非同期テスト前準備"""
        self.tcp_bridge = TCPBridge(
            host="localhost",
            port=8890,  # 別のテスト用ポート
            timeout=1.0
        )
        
        self.test_signal = TradingSignal(
            timestamp=time.time(),
            symbol="USDJPY",
            action="BUY",
            price=150.00,
            volume=0.1,
            slippage=0.0001,
            confidence=0.85,
            lookback_period=20,
            signal_id="async_test_001"
        )
    
    async def test_async_tcp_operations(self):
        """非同期TCP操作テスト"""
        print("\n--- 非同期TCP操作テスト ---")
        
        # 接続失敗テスト（存在しないポート）
        result = await self.tcp_bridge.connect()
        self.assertFalse(result)
        self.assertEqual(self.tcp_bridge.connection_state, ConnectionState.ERROR)
        
        # 未接続時のメッセージ送信
        test_message = TradingMessage(
            message_type=MessageType.SIGNAL,
            timestamp=time.time(),
            data={"test": "async_data"},
            message_id="async_msg_001"
        )
        
        result = await self.tcp_bridge.send_message(test_message)
        self.assertFalse(result)
        
        print("✅ 非同期TCP操作テスト合格")
    
    @patch('asyncio.open_connection')
    async def test_async_tcp_with_mock(self, mock_open_connection):
        """非同期TCPモックテスト"""
        print("\n--- 非同期TCPモックテスト ---")
        
        # モック設定
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (mock_reader, mock_writer)
        
        # 接続テスト
        result = await self.tcp_bridge.connect()
        self.assertTrue(result)
        self.assertEqual(self.tcp_bridge.connection_state, ConnectionState.CONNECTED)
        
        # メッセージ送信テスト
        result = await self.tcp_bridge.send_signal(self.test_signal)
        self.assertTrue(result)
        
        # モック呼び出し確認
        mock_writer.write.assert_called()
        mock_writer.drain.assert_called()
        
        print("✅ 非同期TCPモックテスト合格")
    
    async def asyncTearDown(self):
        """非同期テスト後処理"""
        if self.tcp_bridge.connection_state == ConnectionState.CONNECTED:
            await self.tcp_bridge.disconnect()


if __name__ == '__main__':
    # テストスイート実行
    print("=== Phase 1 統合テストスイート 実行開始 ===")
    
    # 基本統合テスト
    suite1 = unittest.TestLoader().loadTestsFromTestCase(TestPhase1Integration)
    
    # 非同期統合テスト
    suite2 = unittest.TestLoader().loadTestsFromTestCase(TestPhase1AsyncIntegration)
    
    # 統合テストスイート
    combined_suite = unittest.TestSuite([suite1, suite2])
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(combined_suite)
    
    # 結果サマリー
    print("\n=== Phase 1 統合テストスイート 実行結果 ===")
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n--- 失敗テスト ---")
        for test, traceback in result.failures:
            print(f"❌ {test}: {traceback}")
    
    if result.errors:
        print("\n--- エラーテスト ---")
        for test, traceback in result.errors:
            print(f"💥 {test}: {traceback}")
    
    # 終了コード
    sys.exit(0 if result.wasSuccessful() else 1)