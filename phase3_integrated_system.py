#!/usr/bin/env python3
"""
Phase 3: Integrated Position Management & Risk Control System
kiro設計tasks.md:83-115準拠 - 統合ポジション管理・リスク制御システム

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 4.1, 4.2, 4.3, 4.4, 4.5 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

# Phase2システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import RealtimeSignalSystem, TradingSignal, MarketData

# Phase3システム統合
from position_management import PositionTracker, Position, PositionStatus, PositionType
from risk_management import RiskManager, RiskParameters, RiskAssessment, RiskAction
from emergency_protection import EmergencyProtectionSystem, EmergencyTrigger

# ログ設定
logger = logging.getLogger(__name__)

class IntegratedTradingSystem:
    """
    Phase3統合取引システム - kiro設計準拠
    ポジション管理・リスク制御・緊急保護の統合運用
    """
    
    def __init__(self, risk_params: Optional[RiskParameters] = None):
        # Phase2: リアルタイムシグナル生成システム
        self.signal_system = RealtimeSignalSystem()
        
        # Phase3.1: ポジション追跡システム
        self.position_tracker = PositionTracker()
        
        # Phase3.2: リスク管理エンジン
        self.risk_manager = RiskManager(self.position_tracker, risk_params)
        
        # Phase3.3: 緊急保護システム
        self.emergency_system = EmergencyProtectionSystem(self.position_tracker, self.risk_manager)
        
        # システム状態
        self.is_running = False
        self.system_start_time = None
        
        # 統計情報
        self.system_stats = {
            'signals_processed': 0,
            'trades_executed': 0,
            'trades_blocked': 0,
            'emergency_stops': 0,
            'uptime_seconds': 0
        }
        
        logger.info("Integrated Trading System initialized")
    
    async def initialize(self):
        """統合システム初期化 - kiro要件準拠"""
        logger.info("Initializing Integrated Trading System...")
        
        try:
            # Phase2初期化
            logger.info("Initializing Phase2 (Signal Generation)...")
            # signal_systemは自動初期化されるため、追加初期化は不要
            
            # Phase3.1初期化
            logger.info("Initializing Phase3.1 (Position Tracking)...")
            await self.position_tracker.initialize()
            
            # Phase3.2初期化
            logger.info("Initializing Phase3.2 (Risk Management)...")
            await self.risk_manager.initialize()
            
            # Phase3.3初期化
            logger.info("Initializing Phase3.3 (Emergency Protection)...")
            await self.emergency_system.initialize()
            
            # システム間連携設定
            await self._setup_system_integration()
            
            self.is_running = True
            self.system_start_time = datetime.now()
            
            logger.info("Integrated Trading System initialized successfully")
            
        except Exception as e:
            logger.error(f"System initialization error: {e}")
            raise
    
    async def _setup_system_integration(self):
        """システム間連携設定"""
        try:
            # Phase2 → Phase3連携: シグナル受信時のリスク評価・実行
            self.signal_system.signal_generator.signal_queue = asyncio.Queue()
            
            # 市場データ更新をポジション追跡に転送
            self.signal_system.market_feed.subscribe(self._on_market_data_received)
            
            logger.info("System integration configured")
            
        except Exception as e:
            logger.error(f"System integration setup error: {e}")
    
    async def _on_market_data_received(self, market_data: MarketData):
        """市場データ受信処理"""
        try:
            # ポジション価格更新
            await self.position_tracker.update_position_price(
                market_data.symbol, 
                market_data.close
            )
            
        except Exception as e:
            logger.error(f"Market data processing error: {e}")
    
    async def start(self):
        """統合システム開始"""
        logger.info("Starting Integrated Trading System...")
        
        if not self.is_running:
            await self.initialize()
        
        # メイン処理ループ開始
        await asyncio.gather(
            self._signal_processing_loop(),
            self._system_monitoring_loop(),
            return_exceptions=True
        )
    
    async def _signal_processing_loop(self):
        """シグナル処理メインループ"""
        logger.info("Signal processing loop started")
        
        while self.is_running:
            try:
                # Phase2からシグナル取得
                signal = await self.signal_system.signal_generator.get_next_signal()
                
                if signal:
                    await self._process_trading_signal(signal)
                
                await asyncio.sleep(0.01)  # 10ms
                
            except Exception as e:
                logger.error(f"Signal processing loop error: {e}")
                await asyncio.sleep(1)
    
    async def _process_trading_signal(self, signal: TradingSignal):
        """取引シグナル処理 - kiro要件4.1-4.5準拠"""
        try:
            self.system_stats['signals_processed'] += 1
            
            # 1. リスク評価（要件4.1-4.3）
            risk_assessment = await self.risk_manager.assess_trading_risk(
                symbol=signal.symbol,
                position_type=signal.action,
                quantity=signal.quantity,
                entry_price=signal.price or 0.0
            )
            
            logger.info(f"Risk assessment: {risk_assessment.risk_level.value} - {risk_assessment.risk_action.value}")
            
            # 2. リスクアクション判定
            if risk_assessment.risk_action == RiskAction.ALLOW:
                # 取引実行
                await self._execute_trade(signal, risk_assessment)
                
            elif risk_assessment.risk_action == RiskAction.REDUCE_SIZE:
                # ポジションサイズ削減実行
                await self._execute_reduced_trade(signal, risk_assessment)
                
            elif risk_assessment.risk_action == RiskAction.STOP_TRADING:
                # 取引停止
                self.system_stats['trades_blocked'] += 1
                logger.warning(f"Trade blocked due to risk: {signal.symbol} {signal.action}")
                
            elif risk_assessment.risk_action == RiskAction.CLOSE_ALL:
                # 全ポジション決済
                await self._close_all_positions("Risk limit exceeded")
                
            elif risk_assessment.risk_action == RiskAction.EMERGENCY_SHUTDOWN:
                # 緊急停止
                await self.emergency_system.trigger_emergency_shutdown(
                    EmergencyTrigger.EXCESSIVE_LOSS,
                    "Critical risk level reached"
                )
            
        except Exception as e:
            logger.error(f"Trading signal processing error: {e}")
    
    async def _execute_trade(self, signal: TradingSignal, risk_assessment: RiskAssessment):
        """通常取引実行"""
        try:
            # 最適ポジションサイズ計算（要件4.1）
            optimal_size = await self.risk_manager.calculate_optimal_position_size(
                symbol=signal.symbol,
                entry_price=signal.price,
                stop_loss=signal.stop_loss,
                account_balance=risk_assessment.account_balance
            )
            
            # ポジション開設
            position = await self.position_tracker.open_position(
                symbol=signal.symbol,
                position_type=signal.action,
                entry_price=signal.price,
                quantity=optimal_size,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy_params=signal.strategy_params
            )
            
            self.system_stats['trades_executed'] += 1
            logger.info(f"Trade executed: {position.position_id} (size: {optimal_size:.3f})")
            
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
    
    async def _execute_reduced_trade(self, signal: TradingSignal, risk_assessment: RiskAssessment):
        """削減サイズ取引実行"""
        try:
            # 通常サイズの50%で実行
            reduced_quantity = signal.quantity * 0.5
            
            position = await self.position_tracker.open_position(
                symbol=signal.symbol,
                position_type=signal.action,
                entry_price=signal.price,
                quantity=reduced_quantity,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy_params=signal.strategy_params
            )
            
            self.system_stats['trades_executed'] += 1
            logger.info(f"Reduced trade executed: {position.position_id} (size: {reduced_quantity:.3f})")
            
        except Exception as e:
            logger.error(f"Reduced trade execution error: {e}")
    
    async def _close_all_positions(self, reason: str):
        """全ポジション決済"""
        try:
            active_positions = self.position_tracker.get_active_positions()
            
            for position in active_positions:
                if position.status == PositionStatus.OPEN:
                    await self.position_tracker.close_position(
                        position.position_id,
                        position.current_price or position.entry_price
                    )
            
            logger.info(f"All positions closed: {reason}")
            
        except Exception as e:
            logger.error(f"Close all positions error: {e}")
    
    async def _system_monitoring_loop(self):
        """システム監視ループ"""
        logger.info("System monitoring loop started")
        
        while self.is_running:
            try:
                # 稼働時間更新
                if self.system_start_time:
                    uptime = (datetime.now() - self.system_start_time).total_seconds()
                    self.system_stats['uptime_seconds'] = uptime
                
                # システム状態ログ出力（5分間隔）
                if int(time.time()) % 300 == 0:  # 5分ごと
                    await self._log_system_status()
                
                await asyncio.sleep(10)  # 10秒間隔
                
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _log_system_status(self):
        """システム状態ログ出力"""
        try:
            # 各システムの統計取得
            position_stats = self.position_tracker.get_statistics()
            risk_stats = self.risk_manager.get_risk_statistics()
            protection_status = self.emergency_system.get_protection_status()
            
            status_summary = {
                'system': self.system_stats,
                'positions': position_stats,
                'risk': risk_stats,
                'protection': protection_status['status']
            }
            
            logger.info(f"System Status: {json.dumps(status_summary, indent=2)}")
            
        except Exception as e:
            logger.error(f"System status logging error: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """統合システム状態取得"""
        try:
            return {
                'system': {
                    'is_running': self.is_running,
                    'start_time': self.system_start_time.isoformat() if self.system_start_time else None,
                    'stats': self.system_stats
                },
                'positions': self.position_tracker.get_statistics(),
                'risk': self.risk_manager.get_risk_statistics(),
                'protection': self.emergency_system.get_protection_status()
            }
        except Exception as e:
            logger.error(f"System status retrieval error: {e}")
            return {'error': str(e)}
    
    async def manual_emergency_stop(self, reason: str = "Manual intervention"):
        """手動緊急停止"""
        try:
            await self.emergency_system.trigger_emergency_shutdown(
                EmergencyTrigger.MANUAL_OVERRIDE,
                reason
            )
            logger.info(f"Manual emergency stop executed: {reason}")
        except Exception as e:
            logger.error(f"Manual emergency stop error: {e}")
    
    async def stop(self):
        """統合システム停止"""
        logger.info("Stopping Integrated Trading System...")
        
        self.is_running = False
        
        try:
            # 各システム順次停止
            await self.emergency_system.stop()
            await self.risk_manager.stop()
            await self.position_tracker.stop()
            # signal_systemは自動停止
            
            logger.info("Integrated Trading System stopped successfully")
            
        except Exception as e:
            logger.error(f"System stop error: {e}")

# メイン実行関数
async def main():
    """統合システムメイン実行"""
    # リスクパラメータ設定
    risk_params = RiskParameters(
        max_daily_loss=500.0,
        max_drawdown_percent=5.0,
        max_position_size=0.5,
        risk_per_trade_percent=1.0
    )
    
    # 統合システム初期化
    system = IntegratedTradingSystem(risk_params)
    
    try:
        logger.info("🚀 Starting Phase3 Integrated Trading System...")
        await system.start()
        
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        await system.stop()

if __name__ == "__main__":
    # ログレベル設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())