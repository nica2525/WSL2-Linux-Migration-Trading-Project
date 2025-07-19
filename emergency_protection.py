#!/usr/bin/env python3
"""
Phase 3.3: Emergency Protection System
kiro設計tasks.md:109-115準拠 - 緊急保護システム

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 4.4, 4.5 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import time
import logging
import aiosqlite
import signal
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import sys
from pathlib import Path

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, calculate_time_diff_seconds, CONFIG
from position_management import Position, PositionTracker, PositionStatus, PositionType
from risk_management import RiskManager, RiskLevel, RiskAction

# ログ設定
logger = logging.getLogger(__name__)

class EmergencyTrigger(Enum):
    """緊急保護トリガー"""
    SYSTEM_FAILURE = "SYSTEM_FAILURE"
    NETWORK_DISCONNECTION = "NETWORK_DISCONNECTION"
    EXCESSIVE_LOSS = "EXCESSIVE_LOSS"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    EXTERNAL_SIGNAL = "EXTERNAL_SIGNAL"
    RESOURCE_DEPLETION = "RESOURCE_DEPLETION"

class ProtectionStatus(Enum):
    """保護システム状態"""
    ACTIVE = "ACTIVE"
    STANDBY = "STANDBY"
    EMERGENCY = "EMERGENCY"
    DISABLED = "DISABLED"
    MAINTENANCE = "MAINTENANCE"

@dataclass
class EmergencyEvent:
    """緊急イベント情報"""
    trigger: EmergencyTrigger
    severity: str
    description: str
    timestamp: datetime
    system_state: Dict[str, Any]
    positions_affected: int
    action_taken: str
    recovery_time: Optional[float] = None
    manual_intervention_required: bool = False

class NetworkMonitor:
    """
    ネットワーク接続監視 - kiro要件4.4準拠
    接続断時保護ストップ維持
    """
    
    def __init__(self, tcp_bridges: List[Any], check_interval: int = 10):
        self.tcp_bridges = tcp_bridges
        self.check_interval = check_interval
        self.is_monitoring = False
        self.connection_states = {}
        self.last_check_time = time.time()
        self.disconnection_callbacks: List[Callable] = []
        
        logger.info("Network Monitor initialized")
    
    async def start_monitoring(self):
        """ネットワーク監視開始"""
        self.is_monitoring = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("Network monitoring started")
    
    async def _monitoring_loop(self):
        """監視メインループ"""
        while self.is_monitoring:
            try:
                await self._check_connections()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Network monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _check_connections(self):
        """接続状態チェック"""
        try:
            current_time = time.time()
            disconnected_bridges = []
            
            for bridge in self.tcp_bridges:
                bridge_id = getattr(bridge, 'host', 'unknown') + ':' + str(getattr(bridge, 'port', 0))
                
                try:
                    # 接続状態確認
                    is_connected = bridge.is_connected() if hasattr(bridge, 'is_connected') else False
                    
                    # 前回状態と比較
                    was_connected = self.connection_states.get(bridge_id, True)
                    
                    if was_connected and not is_connected:
                        # 接続断検知
                        disconnected_bridges.append(bridge_id)
                        logger.warning(f"Connection lost: {bridge_id}")
                    elif not was_connected and is_connected:
                        # 再接続検知
                        logger.info(f"Connection restored: {bridge_id}")
                    
                    self.connection_states[bridge_id] = is_connected
                    
                except Exception as e:
                    logger.error(f"Connection check error for {bridge_id}: {e}")
                    self.connection_states[bridge_id] = False
            
            # 切断時コールバック実行
            if disconnected_bridges:
                for callback in self.disconnection_callbacks:
                    try:
                        await callback(disconnected_bridges)
                    except Exception as e:
                        logger.error(f"Disconnection callback error: {e}")
        
        except Exception as e:
            logger.error(f"Connection check error: {e}")
    
    def register_disconnection_callback(self, callback: Callable):
        """切断時コールバック登録"""
        self.disconnection_callbacks.append(callback)
    
    def get_connection_status(self) -> Dict[str, bool]:
        """接続状態取得"""
        return self.connection_states.copy()
    
    def stop_monitoring(self):
        """監視停止"""
        self.is_monitoring = False
        logger.info("Network monitoring stopped")

class EmergencyProtectionSystem:
    """
    緊急保護システム - kiro設計tasks.md:109-115準拠
    システム障害時緊急シャットダウン・自動決済・手動オーバーライド
    """
    
    def __init__(self, position_tracker: PositionTracker, risk_manager: RiskManager):
        self.position_tracker = position_tracker
        self.risk_manager = risk_manager
        self.status = ProtectionStatus.STANDBY
        self.is_running = False
        
        # 設定読み込み
        self.config = CONFIG
        self._load_emergency_config()
        
        # ネットワーク監視
        tcp_bridges = [
            self.position_tracker.tcp_bridge,
            self.risk_manager.position_tracker.tcp_bridge if hasattr(self.risk_manager, 'position_tracker') else None
        ]
        tcp_bridges = [b for b in tcp_bridges if b is not None]
        self.network_monitor = NetworkMonitor(tcp_bridges)
        
        # 緊急イベント履歴
        self.emergency_history: List[EmergencyEvent] = []
        
        # シグナルハンドラー設定
        self._setup_signal_handlers()
        
        # 手動オーバーライド機能
        self.manual_override_enabled = True
        self.override_file_path = Path(self.config.get('emergency', {}).get('override_file', './emergency_override.json'))
        
        # データベース
        self.db_path = self.config.get('database', {}).get('path', './emergency_protection.db')
        
        # 保護設定
        self.protection_config = {
            'max_emergency_close_time': 30,      # 緊急決済最大時間（秒）
            'connection_timeout_threshold': 60,  # 接続タイムアウト閾値（秒）
            'system_health_check_interval': 15,  # システムヘルスチェック間隔（秒）
            'stop_maintenance_interval': 5,      # 保護ストップ維持間隔（秒）
        }
        
        logger.info("Emergency Protection System initialized")
    
    def _load_emergency_config(self):
        """緊急保護設定読み込み"""
        try:
            emergency_config = self.config.get('emergency_protection', {})
            if emergency_config:
                for key, value in emergency_config.items():
                    if key in self.protection_config:
                        self.protection_config[key] = value
                        logger.info(f"Emergency config updated: {key} = {value}")
        except Exception as e:
            logger.error(f"Emergency config loading error: {e}")
    
    def _setup_signal_handlers(self):
        """システムシグナルハンドラー設定"""
        try:
            # SIGTERM, SIGINT処理
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # Windows環境でのSIGBREAK処理
            if hasattr(signal, 'SIGBREAK'):
                signal.signal(signal.SIGBREAK, self._signal_handler)
                
            logger.info("Signal handlers configured")
        except Exception as e:
            logger.error(f"Signal handler setup error: {e}")
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        logger.critical(f"System signal received: {signum}")
        # 非同期タスクとして緊急停止実行
        asyncio.create_task(self.trigger_emergency_shutdown(
            EmergencyTrigger.EXTERNAL_SIGNAL,
            f"System signal {signum} received"
        ))
    
    async def initialize(self):
        """緊急保護システム初期化"""
        logger.info("Initializing Emergency Protection System...")
        
        # データベース初期化
        await self._init_database()
        
        # ネットワーク監視開始
        await self.network_monitor.start_monitoring()
        self.network_monitor.register_disconnection_callback(self._handle_network_disconnection)
        
        # システム監視開始
        self.is_running = True
        self.status = ProtectionStatus.ACTIVE
        asyncio.create_task(self._protection_monitoring_loop())
        asyncio.create_task(self._manual_override_monitor())
        
        logger.info("Emergency Protection System initialized successfully")
    
    async def _init_database(self):
        """緊急保護データベース初期化"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # 緊急イベントテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS emergency_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT,
                        system_state TEXT,
                        positions_affected INTEGER DEFAULT 0,
                        action_taken TEXT,
                        recovery_time REAL,
                        manual_intervention_required BOOLEAN DEFAULT 0
                    )
                ''')
                
                # システム状態スナップショットテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        protection_status TEXT NOT NULL,
                        active_positions INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        network_status TEXT,
                        risk_level TEXT,
                        trading_enabled BOOLEAN DEFAULT 1
                    )
                ''')
                
                await conn.commit()
            
            logger.info("Emergency protection database initialized")
            
        except Exception as e:
            logger.error(f"Emergency database initialization error: {e}")
    
    async def _protection_monitoring_loop(self):
        """保護システム監視ループ"""
        while self.is_running:
            try:
                # システムヘルスチェック
                await self._perform_system_health_check()
                
                # 保護ストップ維持（要件4.4）
                await self._maintain_protection_stops()
                
                # システム状態スナップショット保存
                await self._save_system_snapshot()
                
                await asyncio.sleep(self.protection_config['system_health_check_interval'])
                
            except Exception as e:
                logger.error(f"Protection monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_system_health_check(self):
        """システムヘルスチェック実行"""
        try:
            # 各コンポーネントの稼働状態確認
            issues = []
            
            # ポジション追跡システム
            if not self.position_tracker.is_running:
                issues.append("Position tracker not running")
            
            # リスク管理システム
            if not self.risk_manager.is_running:
                issues.append("Risk manager not running")
            
            # ネットワーク接続状態
            connection_status = self.network_monitor.get_connection_status()
            if not any(connection_status.values()):
                issues.append("All network connections lost")
            
            # 重大な問題が検出された場合
            if issues:
                await self.trigger_emergency_shutdown(
                    EmergencyTrigger.SYSTEM_FAILURE,
                    f"System health check failed: {', '.join(issues)}"
                )
        
        except Exception as e:
            logger.error(f"System health check error: {e}")
    
    async def _maintain_protection_stops(self):
        """保護ストップ維持 - kiro要件4.4準拠"""
        try:
            # アクティブポジションの保護ストップ確認
            active_positions = self.position_tracker.get_active_positions()
            
            for position in active_positions:
                if position.status == PositionStatus.OPEN and position.stop_loss:
                    # ストップロス監視
                    if position.current_price:
                        should_trigger_stop = False
                        
                        if position.position_type == PositionType.BUY:
                            should_trigger_stop = position.current_price <= position.stop_loss
                        else:  # SELL
                            should_trigger_stop = position.current_price >= position.stop_loss
                        
                        if should_trigger_stop:
                            logger.warning(f"Protection stop triggered for {position.position_id}")
                            await self.position_tracker.close_position(
                                position.position_id,
                                position.current_price,
                                commission=0.0
                            )
        
        except Exception as e:
            logger.error(f"Protection stop maintenance error: {e}")
    
    async def _handle_network_disconnection(self, disconnected_bridges: List[str]):
        """ネットワーク切断処理 - kiro要件4.4準拠"""
        try:
            logger.critical(f"Network disconnection detected: {disconnected_bridges}")
            
            # 接続断時の保護措置
            await self.trigger_emergency_shutdown(
                EmergencyTrigger.NETWORK_DISCONNECTION,
                f"Network connections lost: {', '.join(disconnected_bridges)}"
            )
        
        except Exception as e:
            logger.error(f"Network disconnection handling error: {e}")
    
    async def _manual_override_monitor(self):
        """手動オーバーライド監視"""
        while self.is_running:
            try:
                if self.manual_override_enabled and self.override_file_path.exists():
                    # オーバーライドファイル読み込み
                    with open(self.override_file_path, 'r') as f:
                        override_data = json.load(f)
                    
                    # オーバーライドコマンド実行
                    await self._execute_manual_override(override_data)
                    
                    # ファイル削除（実行済み）
                    self.override_file_path.unlink()
                
                await asyncio.sleep(2)  # 2秒間隔でチェック
                
            except json.JSONDecodeError:
                logger.error("Invalid override file format")
                self.override_file_path.unlink()
            except Exception as e:
                logger.error(f"Manual override monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _execute_manual_override(self, override_data: Dict[str, Any]):
        """手動オーバーライド実行"""
        try:
            command = override_data.get('command')
            
            if command == 'EMERGENCY_STOP':
                await self.trigger_emergency_shutdown(
                    EmergencyTrigger.MANUAL_OVERRIDE,
                    override_data.get('reason', 'Manual emergency stop')
                )
            elif command == 'CLOSE_ALL_POSITIONS':
                await self._emergency_close_all_positions()
            elif command == 'DISABLE_TRADING':
                self.risk_manager.trading_enabled = False
                logger.info("Trading disabled by manual override")
            elif command == 'ENABLE_TRADING':
                self.risk_manager.trading_enabled = True
                logger.info("Trading enabled by manual override")
            
            logger.info(f"Manual override executed: {command}")
            
        except Exception as e:
            logger.error(f"Manual override execution error: {e}")
    
    async def trigger_emergency_shutdown(self, trigger: EmergencyTrigger, reason: str):
        """緊急シャットダウン発動 - kiro要件4.5準拠"""
        try:
            start_time = time.time()
            logger.critical(f"EMERGENCY SHUTDOWN TRIGGERED: {trigger.value} - {reason}")
            
            # ステータス更新
            self.status = ProtectionStatus.EMERGENCY
            
            # システム状態収集
            system_state = await self._collect_system_state()
            
            # 全ポジション緊急決済（30秒以内）
            active_positions = self.position_tracker.get_active_positions()
            close_success = await self._emergency_close_all_positions()
            
            # 取引無効化
            self.risk_manager.trading_enabled = False
            
            # リカバリー時間計算
            recovery_time = time.time() - start_time
            
            # 緊急イベント記録
            emergency_event = EmergencyEvent(
                trigger=trigger,
                severity="CRITICAL",
                description=reason,
                timestamp=datetime.now(),
                system_state=system_state,
                positions_affected=len(active_positions),
                action_taken="Emergency shutdown and position closure",
                recovery_time=recovery_time,
                manual_intervention_required=not close_success
            )
            
            self.emergency_history.append(emergency_event)
            await self._save_emergency_event(emergency_event)
            
            logger.critical(f"Emergency shutdown completed in {recovery_time:.2f}s")
            
            if not close_success:
                logger.critical("MANUAL INTERVENTION REQUIRED - Some positions may not have closed")
            
        except Exception as e:
            logger.error(f"Emergency shutdown error: {e}")
    
    async def _emergency_close_all_positions(self) -> bool:
        """全ポジション緊急決済"""
        try:
            active_positions = self.position_tracker.get_active_positions()
            if not active_positions:
                return True
            
            close_tasks = []
            for position in active_positions:
                if position.status == PositionStatus.OPEN:
                    task = asyncio.create_task(
                        self.position_tracker.close_position(
                            position.position_id,
                            position.current_price or position.entry_price,
                            commission=0.0
                        )
                    )
                    close_tasks.append(task)
            
            # タイムアウト付き決済実行
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=self.protection_config['max_emergency_close_time']
                )
                
                # 結果確認
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                total_count = len(close_tasks)
                
                logger.info(f"Emergency closure: {success_count}/{total_count} positions closed")
                return success_count == total_count
                
            except asyncio.TimeoutError:
                logger.error("Emergency closure timeout exceeded")
                return False
        
        except Exception as e:
            logger.error(f"Emergency close error: {e}")
            return False
    
    async def _collect_system_state(self) -> Dict[str, Any]:
        """システム状態収集"""
        try:
            position_stats = self.position_tracker.get_statistics()
            risk_stats = self.risk_manager.get_risk_statistics()
            network_status = self.network_monitor.get_connection_status()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'positions': position_stats,
                'risk': risk_stats,
                'network': network_status,
                'protection_status': self.status.value
            }
        except Exception as e:
            logger.error(f"System state collection error: {e}")
            return {'error': str(e)}
    
    async def _save_emergency_event(self, event: EmergencyEvent):
        """緊急イベントデータベース保存"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO emergency_events (
                        timestamp, trigger_type, severity, description,
                        system_state, positions_affected, action_taken,
                        recovery_time, manual_intervention_required
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.timestamp.isoformat(),
                    event.trigger.value,
                    event.severity,
                    event.description,
                    json.dumps(event.system_state),
                    event.positions_affected,
                    event.action_taken,
                    event.recovery_time,
                    event.manual_intervention_required
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Emergency event save error: {e}")
    
    async def _save_system_snapshot(self):
        """システム状態スナップショット保存"""
        try:
            position_stats = self.position_tracker.get_statistics()
            network_status = self.network_monitor.get_connection_status()
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO system_snapshots (
                        timestamp, protection_status, active_positions,
                        total_pnl, network_status, trading_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    self.status.value,
                    position_stats.get('active_positions', 0),
                    position_stats.get('total_pnl', 0.0),
                    json.dumps(network_status),
                    self.risk_manager.trading_enabled
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"System snapshot save error: {e}")
    
    def create_manual_override_file(self, command: str, reason: str = ""):
        """手動オーバーライドファイル作成"""
        try:
            override_data = {
                'command': command,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.override_file_path, 'w') as f:
                json.dump(override_data, f, indent=2)
            
            logger.info(f"Manual override file created: {command}")
            
        except Exception as e:
            logger.error(f"Manual override file creation error: {e}")
    
    def get_emergency_history(self) -> List[EmergencyEvent]:
        """緊急イベント履歴取得"""
        return self.emergency_history.copy()
    
    def get_protection_status(self) -> Dict[str, Any]:
        """保護システム状態取得"""
        return {
            'status': self.status.value,
            'is_running': self.is_running,
            'manual_override_enabled': self.manual_override_enabled,
            'network_status': self.network_monitor.get_connection_status(),
            'emergency_events_count': len(self.emergency_history),
            'config': self.protection_config.copy()
        }
    
    async def stop(self):
        """緊急保護システム停止"""
        logger.info("Stopping Emergency Protection System...")
        
        self.is_running = False
        self.status = ProtectionStatus.DISABLED
        self.network_monitor.stop_monitoring()
        
        # 最終システムスナップショット保存
        await self._save_system_snapshot()
        
        logger.info("Emergency Protection System stopped")

# テスト関数
async def test_emergency_protection():
    """緊急保護システムテスト"""
    print("🧪 Emergency Protection System Test Starting...")
    
    # 依存システム初期化
    from position_management import PositionTracker
    from risk_management import RiskManager
    
    position_tracker = PositionTracker()
    await position_tracker.initialize()
    
    risk_manager = RiskManager(position_tracker)
    await risk_manager.initialize()
    
    # 緊急保護システム初期化
    emergency_system = EmergencyProtectionSystem(position_tracker, risk_manager)
    await emergency_system.initialize()
    
    try:
        # テストポジション作成
        await position_tracker.open_position(
            symbol="EURUSD",
            position_type="BUY",
            entry_price=1.1000,
            quantity=0.1
        )
        
        # 手動オーバーライドテスト
        emergency_system.create_manual_override_file("DISABLE_TRADING", "Test override")
        await asyncio.sleep(3)  # オーバーライド処理待機
        
        # 保護状態確認
        status = emergency_system.get_protection_status()
        print(f"📊 Protection Status: {status}")
        
        # 緊急停止テスト（コメントアウト）
        # await emergency_system.trigger_emergency_shutdown(
        #     EmergencyTrigger.MANUAL_OVERRIDE,
        #     "Test emergency shutdown"
        # )
        
        print("✅ Emergency Protection System Test Completed")
        
    finally:
        await emergency_system.stop()
        await risk_manager.stop()
        await position_tracker.stop()

if __name__ == "__main__":
    asyncio.run(test_emergency_protection())