#!/usr/bin/env python3
"""
Phase3簡易テスト - 基本機能確認
"""

import asyncio
import tempfile
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

# Phase3システム
from position_management import Position, PositionStatus, PositionType
from risk_management import RiskParameters, RiskManager
from emergency_protection import EmergencyTrigger

async def test_position_pnl():
    """P&L計算テスト"""
    print("🧪 P&L計算テスト...")
    
    # BUYポジション作成
    position = Position(
        position_id="TEST_001",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        quantity=0.1,
        entry_time=datetime.now(),
        current_price=1.1000
    )
    
    # 未実現損益計算（利益）
    unrealized_pnl = position.calculate_unrealized_pnl(1.1050)
    expected = 0.005 * 0.1 * 100000  # 50.0
    
    print(f"  未実現損益: {unrealized_pnl:.2f} (期待値: {expected:.2f})")
    assert abs(unrealized_pnl - expected) < 0.1, f"P&L計算エラー: {unrealized_pnl} != {expected}"
    
    # 実現損益計算
    position.exit_price = 1.1050
    position.status = PositionStatus.CLOSED
    realized_pnl = position.calculate_realized_pnl()
    
    print(f"  実現損益: {realized_pnl:.2f}")
    assert abs(realized_pnl - expected) < 0.1, f"実現損益計算エラー: {realized_pnl} != {expected}"
    
    print("✅ P&L計算テスト成功")

async def test_risk_parameters():
    """リスクパラメータテスト"""
    print("🧪 リスクパラメータテスト...")
    
    # リスクパラメータ作成
    risk_params = RiskParameters(
        max_daily_loss=1000.0,
        max_drawdown_percent=10.0,
        risk_per_trade_percent=2.0
    )
    
    print(f"  最大日次損失: {risk_params.max_daily_loss}")
    print(f"  最大ドローダウン: {risk_params.max_drawdown_percent}%")
    print(f"  取引リスク率: {risk_params.risk_per_trade_percent}%")
    
    assert risk_params.max_daily_loss == 1000.0
    assert risk_params.max_drawdown_percent == 10.0
    
    print("✅ リスクパラメータテスト成功")

async def test_emergency_trigger():
    """緊急トリガーテスト"""
    print("🧪 緊急トリガーテスト...")
    
    # 緊急トリガーenumテスト
    triggers = [
        EmergencyTrigger.SYSTEM_FAILURE,
        EmergencyTrigger.NETWORK_DISCONNECTION,
        EmergencyTrigger.EXCESSIVE_LOSS,
        EmergencyTrigger.MANUAL_OVERRIDE
    ]
    
    for trigger in triggers:
        print(f"  トリガー: {trigger.value}")
        assert isinstance(trigger.value, str)
    
    print("✅ 緊急トリガーテスト成功")

async def test_system_integration():
    """システム統合基本テスト"""
    print("🧪 システム統合基本テスト...")
    
    try:
        # モジュールインポートテスト
        from position_management import PositionTracker
        from risk_management import RiskManager
        from emergency_protection import EmergencyProtectionSystem
        from phase3_integrated_system import IntegratedTradingSystem
        
        print("  ✅ 全モジュールインポート成功")
        
        # 基本クラス作成テスト
        risk_params = RiskParameters()
        
        # 統合システム作成テスト（初期化はスキップ）
        integrated_system = IntegratedTradingSystem(risk_params)
        
        print("  ✅ 統合システムインスタンス作成成功")
        print("✅ システム統合基本テスト成功")
        
    except Exception as e:
        print(f"❌ システム統合テストエラー: {e}")
        raise

async def run_simple_tests():
    """簡易テスト実行"""
    print("🚀 Phase3簡易テスト開始")
    print("="*50)
    
    try:
        await test_position_pnl()
        await test_risk_parameters()
        await test_emergency_trigger()
        await test_system_integration()
        
        print("="*50)
        print("🎉 Phase3簡易テスト全成功!")
        return True
        
    except Exception as e:
        print("="*50)
        print(f"❌ テスト失敗: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_simple_tests())
    sys.exit(0 if success else 1)