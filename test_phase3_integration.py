#!/usr/bin/env python3
"""
Phase3統合テスト - kiro設計準拠
実装担当: Claude (設計: kiro)
"""

import asyncio
import unittest
import tempfile
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# テスト対象システム
sys.path.append(str(Path(__file__).parent))

# Phase3システム
from position_management import PositionTracker, Position, PositionStatus, PositionType
from risk_management import RiskManager, RiskParameters, RiskLevel, RiskAction
from emergency_protection import EmergencyProtectionSystem, EmergencyTrigger
from phase3_integrated_system import IntegratedTradingSystem

class TestPhase3PositionManagement(unittest.IsolatedAsyncioTestCase):
    """ポジション管理システムテスト"""
    
    async def test_position_pnl_calculation(self):
        """P&L計算テスト - kiro要件4.1"""
        # BUYポジションテスト
        position = Position(
            position_id="TEST_001",
            symbol="EURUSD",
            position_type=PositionType.BUY,
            entry_price=1.1000,
            quantity=0.1,
            entry_time=datetime.now()
        )
        
        # 未実現損益テスト（利益）
        unrealized_pnl = position.calculate_unrealized_pnl(1.1050)
        self.assertAlmostEqual(unrealized_pnl, 50.0, places=1)  # 0.005 * 10,000 = 50
        
        # 実現損益テスト
        position.exit_price = 1.1050
        position.status = PositionStatus.CLOSED
        realized_pnl = position.calculate_realized_pnl()
        self.assertAlmostEqual(realized_pnl, 50.0, places=1)
        
        print(f"✅ P&L Calculation Test: Unrealized={unrealized_pnl:.2f}, Realized={realized_pnl:.2f}")
    
    async def test_position_synchronization(self):
        """ポジション同期テスト - kiro要件4.1"""
        tracker = PositionTracker()
        
        # モック通信ブリッジ設定
        tracker.tcp_bridge = AsyncMock()
        tracker.tcp_bridge.is_connected.return_value = True
        tracker.tcp_bridge.send_data = AsyncMock(return_value=True)
        
        await tracker.initialize()
        
        try:
            # ポジション開設テスト
            position = await tracker.open_position(
                symbol="EURUSD",
                position_type="BUY",
                entry_price=1.1000,
                quantity=0.1
            )
            
            self.assertIsNotNone(position)
            self.assertEqual(position.symbol, "EURUSD")
            self.assertEqual(len(tracker.active_positions), 1)
            
            # MT4送信確認
            tracker.tcp_bridge.send_data.assert_called()
            
            print(f"✅ Position Synchronization Test: Position created and synced")
            
        finally:
            await tracker.stop()

class TestPhase3RiskManagement(unittest.IsolatedAsyncioTestCase):
    """リスク管理システムテスト"""
    
    async def test_risk_assessment_daily_loss(self):
        """日次損失制限テスト - kiro要件4.2"""
        tracker = PositionTracker()
        await tracker.initialize()
        
        # 損失ポジション作成
        await tracker.open_position("EURUSD", "BUY", 1.1000, 0.1)
        tracker.stats['total_pnl'] = -1500.0  # 制限超過
        
        risk_params = RiskParameters(max_daily_loss=1000.0)
        risk_manager = RiskManager(tracker, risk_params)
        await risk_manager.initialize()
        
        try:
            # リスク評価実行
            assessment = await risk_manager.assess_trading_risk(
                symbol="EURUSD",
                position_type="BUY",
                quantity=0.1,
                entry_price=1.1000
            )
            
            # 取引停止確認
            self.assertEqual(assessment.risk_action, RiskAction.STOP_TRADING)
            self.assertEqual(assessment.risk_level, RiskLevel.CRITICAL)
            
            print(f"✅ Daily Loss Limit Test: {assessment.risk_action.value}")
            
        finally:
            await risk_manager.stop()
            await tracker.stop()
    
    async def test_position_sizing_calculation(self):
        """ポジションサイズ計算テスト - kiro要件4.1"""
        tracker = PositionTracker()
        await tracker.initialize()
        
        risk_params = RiskParameters(risk_per_trade_percent=2.0)
        risk_manager = RiskManager(tracker, risk_params)
        await risk_manager.initialize()
        
        try:
            # 最適ポジションサイズ計算
            optimal_size = await risk_manager.calculate_optimal_position_size(
                symbol="EURUSD",
                entry_price=1.1000,
                stop_loss=1.0950,  # 50pips
                account_balance=10000.0
            )
            
            # 2%リスクで50pips = 0.04lotが期待値
            self.assertGreater(optimal_size, 0.0)
            self.assertLess(optimal_size, 1.0)
            
            print(f"✅ Position Sizing Test: Optimal size = {optimal_size:.3f}")
            
        finally:
            await risk_manager.stop()
            await tracker.stop()
    
    async def test_volatility_reduction(self):
        """ボラティリティ対応テスト - kiro要件4.3"""
        tracker = PositionTracker()
        await tracker.initialize()
        
        # 高ボラティリティ設定
        risk_params = RiskParameters(
            high_volatility_threshold=0.01,  # 低い閾値で強制発動
            volatility_position_reduction=0.5
        )
        risk_manager = RiskManager(tracker, risk_params)
        await risk_manager.initialize()
        
        # テストポジション作成
        position = await tracker.open_position("EURUSD", "BUY", 1.1000, 1.0)
        position.status = PositionStatus.OPEN
        position.current_price = 1.1000
        
        try:
            # 高ボラティリティ処理実行
            await risk_manager._handle_high_volatility(position)
            
            # ポジション決済確認
            self.assertEqual(len(tracker.active_positions), 0)
            
            print(f"✅ Volatility Reduction Test: Position reduced due to high volatility")
            
        finally:
            await risk_manager.stop()
            await tracker.stop()

class TestPhase3EmergencyProtection(unittest.IsolatedAsyncioTestCase):
    """緊急保護システムテスト"""
    
    async def test_emergency_shutdown_timing(self):
        """緊急停止時間テスト - kiro要件4.5"""
        tracker = PositionTracker()
        await tracker.initialize()
        
        risk_manager = RiskManager(tracker)
        await risk_manager.initialize()
        
        emergency_system = EmergencyProtectionSystem(tracker, risk_manager)
        await emergency_system.initialize()
        
        # テストポジション作成
        await tracker.open_position("EURUSD", "BUY", 1.1000, 0.1)
        
        try:
            # 緊急停止実行・時間測定
            start_time = time.time()
            await emergency_system.trigger_emergency_shutdown(
                EmergencyTrigger.MANUAL_OVERRIDE,
                "Test emergency shutdown"
            )
            end_time = time.time()
            
            # 30秒以内確認
            shutdown_time = end_time - start_time
            self.assertLess(shutdown_time, 30.0)
            
            # 全ポジション決済確認
            self.assertEqual(len(tracker.active_positions), 0)
            
            print(f"✅ Emergency Shutdown Test: Completed in {shutdown_time:.2f}s")
            
        finally:
            await emergency_system.stop()
            await risk_manager.stop()
            await tracker.stop()
    
    async def test_network_disconnection_handling(self):
        """ネットワーク切断処理テスト - kiro要件4.4"""
        tracker = PositionTracker()
        await tracker.initialize()
        
        risk_manager = RiskManager(tracker)
        await risk_manager.initialize()
        
        emergency_system = EmergencyProtectionSystem(tracker, risk_manager)
        
        # 通信ブリッジモック設定
        tracker.tcp_bridge.is_connected = MagicMock(return_value=False)
        
        await emergency_system.initialize()
        
        try:
            # ネットワーク切断イベント発生
            await emergency_system._handle_network_disconnection(["localhost:9090"])
            
            # 緊急停止確認
            self.assertEqual(emergency_system.status.value, "EMERGENCY")
            
            print(f"✅ Network Disconnection Test: Emergency triggered")
            
        finally:
            await emergency_system.stop()
            await risk_manager.stop()
            await tracker.stop()

class TestPhase3IntegratedSystem(unittest.IsolatedAsyncioTestCase):
    """統合システムテスト"""
    
    async def test_signal_to_position_workflow(self):
        """シグナル→ポジション実行フローテスト"""
        # 統合システム初期化（簡略版）
        from realtime_signal_generator import TradingSignal
        
        # 依存システム初期化
        tracker = PositionTracker()
        await tracker.initialize()
        
        risk_manager = RiskManager(tracker)
        await risk_manager.initialize()
        
        emergency_system = EmergencyProtectionSystem(tracker, risk_manager)
        await emergency_system.initialize()
        
        # 通信モック設定
        tracker.tcp_bridge = AsyncMock()
        tracker.tcp_bridge.is_connected.return_value = True
        tracker.tcp_bridge.send_data = AsyncMock(return_value=True)
        
        try:
            # テストシグナル作成
            signal = TradingSignal(
                timestamp=datetime.now(),
                symbol="EURUSD",
                action="BUY",
                quantity=0.1,
                price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1100
            )
            
            # 1. リスク評価
            risk_assessment = await risk_manager.assess_trading_risk(
                symbol=signal.symbol,
                position_type=signal.action,
                quantity=signal.quantity,
                entry_price=signal.price
            )
            
            # 2. 取引実行（リスクOKの場合）
            if risk_assessment.risk_action == RiskAction.ALLOW:
                position = await tracker.open_position(
                    symbol=signal.symbol,
                    position_type=signal.action,
                    entry_price=signal.price,
                    quantity=signal.quantity,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit
                )
                
                self.assertIsNotNone(position)
                self.assertEqual(len(tracker.active_positions), 1)
            
            print(f"✅ Signal-to-Position Workflow Test: {risk_assessment.risk_action.value}")
            
        finally:
            await emergency_system.stop()
            await risk_manager.stop()
            await tracker.stop()
    
    async def test_system_statistics_integration(self):
        """システム統計統合テスト"""
        tracker = PositionTracker()
        await tracker.initialize()
        
        # テストポジション・統計作成
        await tracker.open_position("EURUSD", "BUY", 1.1000, 0.1)
        await tracker.close_position(
            list(tracker.active_positions.keys())[0],
            1.1050  # 利益決済
        )
        
        try:
            # 統計取得・検証
            stats = tracker.get_statistics()
            
            self.assertGreater(stats['total_positions'], 0)
            self.assertGreaterEqual(stats['total_pnl'], 0)  # 利益
            
            print(f"✅ System Statistics Test: {stats}")
            
        finally:
            await tracker.stop()

def run_phase3_integration_tests():
    """Phase3統合テスト実行"""
    print("🧪 Phase3統合テスト開始...")
    
    # テストスイート作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラス追加
    suite.addTests(loader.loadTestsFromTestCase(TestPhase3PositionManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase3RiskManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase3EmergencyProtection))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase3IntegratedSystem))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\nPhase3統合テスト完了")
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_phase3_integration_tests()
    sys.exit(0 if success else 1)