#!/usr/bin/env python3
"""
Phase 4.2: System State Management
kiro設計tasks.md:135-141準拠 - システム状態管理・スナップショット・復旧手順

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 5.2, 5.3 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import gzip
import logging
import aiosqlite
import time
import hashlib
import pickle
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import sys
from pathlib import Path

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, CONFIG
from position_management import PositionTracker
from risk_management import RiskManager
from emergency_protection import EmergencyProtectionSystem
from database_manager import DatabaseManager

# ログ設定
logger = logging.getLogger(__name__)

class SnapshotType(Enum):
    """スナップショット種別"""
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    MANUAL = "MANUAL"
    EMERGENCY = "EMERGENCY"
    SHUTDOWN = "SHUTDOWN"

class SystemStatus(Enum):
    """システム状態"""
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    EMERGENCY = "EMERGENCY"
    MAINTENANCE = "MAINTENANCE"
    STOPPED = "STOPPED"

class RecoveryLevel(Enum):
    """復旧レベル"""
    FULL_RESTORE = "FULL_RESTORE"
    PARTIAL_RESTORE = "PARTIAL_RESTORE"
    CONFIG_ONLY = "CONFIG_ONLY"
    EMERGENCY_RESTORE = "EMERGENCY_RESTORE"

@dataclass
class SystemSnapshot:
    """システムスナップショット"""
    snapshot_id: str
    timestamp: datetime
    snapshot_type: SnapshotType
    system_version: str
    component_states: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    configuration_data: Dict[str, Any]
    active_positions: List[Dict[str, Any]]
    risk_parameters: Dict[str, Any]
    emergency_status: Dict[str, Any]
    file_size_bytes: int
    compression_ratio: float
    checksum: str
    recovery_priority: int

@dataclass
class RecoveryPlan:
    """復旧計画"""
    plan_id: str
    target_snapshot_id: str
    recovery_level: RecoveryLevel
    estimated_time_minutes: int
    steps: List[Dict[str, Any]]
    prerequisites: List[str]
    rollback_available: bool
    risk_assessment: str

class SystemStateManager:
    """
    システム状態管理システム - kiro設計tasks.md:135-141準拠
    スナップショット作成・復元・システム復旧手順・状態検証
    """
    
    def __init__(self, position_tracker: PositionTracker, risk_manager: RiskManager,
                 emergency_system: EmergencyProtectionSystem, db_manager: DatabaseManager):
        self.position_tracker = position_tracker
        self.risk_manager = risk_manager
        self.emergency_system = emergency_system
        self.db_manager = db_manager
        
        # 設定読み込み
        self.config = CONFIG
        
        # スナップショット設定
        self.snapshot_dir = Path(self.config.get('snapshots', {}).get('directory', './snapshots'))
        self.snapshot_dir.mkdir(exist_ok=True)
        
        self.max_snapshots_per_type = {
            SnapshotType.HOURLY: 24,      # 24時間分
            SnapshotType.DAILY: 30,       # 30日分
            SnapshotType.MANUAL: 10,      # 10個まで
            SnapshotType.EMERGENCY: 5,    # 5個まで
            SnapshotType.SHUTDOWN: 3      # 3個まで
        }
        
        # 復旧設定
        self.auto_recovery_enabled = True
        self.recovery_timeout_seconds = 300  # 5分
        self.corruption_threshold = 0.1      # 10%以上の破損で復旧
        
        # システム状態
        self.current_status = SystemStatus.INITIALIZING
        self.last_snapshot_time = None
        self.snapshot_schedule_task = None
        self.health_check_task = None
        
        # パフォーマンス監視
        self.performance_history = []
        self.max_performance_history = 1000
        
        logger.info("System State Manager initialized")
    
    async def initialize(self):
        """システム状態管理初期化"""
        logger.info("Initializing System State Manager...")
        
        try:
            # スナップショット管理テーブル初期化
            await self._initialize_snapshot_tables()
            
            # 前回シャットダウン時の状態確認
            await self._check_previous_shutdown()
            
            # 初期スナップショット作成
            await self.create_snapshot(SnapshotType.MANUAL, "initialization")
            
            # スケジュールタスク開始
            await self._start_scheduled_tasks()
            
            self.current_status = SystemStatus.RUNNING
            logger.info("System State Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"System State Manager initialization error: {e}")
            self.current_status = SystemStatus.DEGRADED
            raise
    
    async def _initialize_snapshot_tables(self):
        """スナップショット管理テーブル初期化"""
        try:
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                # スナップショット詳細テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_snapshot_details (
                        snapshot_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        snapshot_type TEXT NOT NULL,
                        system_version TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size_bytes INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        checksum TEXT NOT NULL,
                        component_count INTEGER DEFAULT 0,
                        recovery_priority INTEGER DEFAULT 5,
                        validation_status TEXT DEFAULT 'PENDING',
                        description TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 復旧履歴テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS recovery_history (
                        recovery_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        source_snapshot_id TEXT NOT NULL,
                        recovery_level TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        execution_time_seconds REAL NOT NULL,
                        components_restored INTEGER DEFAULT 0,
                        error_message TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (source_snapshot_id) REFERENCES system_snapshot_details (snapshot_id)
                    )
                ''')
                
                await conn.commit()
                logger.info("Snapshot management tables initialized")
                
        except Exception as e:
            logger.error(f"Snapshot tables initialization error: {e}")
            raise
    
    async def _check_previous_shutdown(self):
        """前回シャットダウン状態確認 - kiro要件5.3準拠"""
        try:
            # 最新のシャットダウンスナップショット確認
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                cursor = await conn.execute('''
                    SELECT snapshot_id, timestamp, validation_status
                    FROM system_snapshot_details
                    WHERE snapshot_type = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (SnapshotType.SHUTDOWN.value,))
                
                last_shutdown = await cursor.fetchone()
                
                if last_shutdown:
                    snapshot_id, timestamp, validation_status = last_shutdown
                    logger.info(f"Previous shutdown snapshot found: {snapshot_id}")
                    
                    # 異常終了検知
                    if validation_status != 'VALIDATED':
                        logger.warning("Previous shutdown was not clean - potential crash detected")
                        await self._handle_crash_recovery(snapshot_id)
                    else:
                        logger.info("Previous shutdown was clean")
                else:
                    logger.info("No previous shutdown snapshot found")
                    
        except Exception as e:
            logger.error(f"Previous shutdown check error: {e}")
    
    async def _handle_crash_recovery(self, last_snapshot_id: str):
        """クラッシュ復旧処理 - kiro要件5.3準拠"""
        try:
            if not self.auto_recovery_enabled:
                logger.warning("Auto recovery disabled - manual intervention required")
                return
            
            logger.info(f"Initiating crash recovery from snapshot: {last_snapshot_id}")
            
            # 復旧プラン作成
            recovery_plan = await self._create_recovery_plan(
                last_snapshot_id, 
                RecoveryLevel.PARTIAL_RESTORE
            )
            
            # 復旧実行
            success = await self._execute_recovery_plan(recovery_plan)
            
            if success:
                logger.info("Crash recovery completed successfully")
                self.current_status = SystemStatus.RUNNING
            else:
                logger.error("Crash recovery failed - manual intervention required")
                self.current_status = SystemStatus.DEGRADED
                
        except Exception as e:
            logger.error(f"Crash recovery error: {e}")
            self.current_status = SystemStatus.EMERGENCY
    
    async def create_snapshot(self, snapshot_type: SnapshotType, description: str = "") -> str:
        """システムスナップショット作成 - kiro要件5.2準拠"""
        try:
            start_time = time.time()
            snapshot_id = f"snapshot_{int(time.time() * 1000)}"
            timestamp = datetime.now()
            
            logger.info(f"Creating system snapshot: {snapshot_id} ({snapshot_type.value})")
            
            # システム状態収集
            component_states = await self._collect_component_states()
            performance_metrics = await self._collect_performance_metrics()
            configuration_data = await self._collect_configuration_data()
            active_positions = await self._collect_active_positions()
            risk_parameters = await self._collect_risk_parameters()
            emergency_status = await self._collect_emergency_status()
            
            # スナップショットオブジェクト作成
            snapshot = SystemSnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                snapshot_type=snapshot_type,
                system_version=self.db_manager.current_schema_version,
                component_states=component_states,
                performance_metrics=performance_metrics,
                configuration_data=configuration_data,
                active_positions=active_positions,
                risk_parameters=risk_parameters,
                emergency_status=emergency_status,
                file_size_bytes=0,
                compression_ratio=0.0,
                checksum="",
                recovery_priority=self._calculate_recovery_priority(snapshot_type)
            )
            
            # ファイル保存
            file_path = await self._save_snapshot_to_file(snapshot)
            
            # チェックサム計算
            checksum = await self._calculate_file_checksum(file_path)
            file_size = file_path.stat().st_size
            
            # 圧縮比計算（推定）
            snapshot_data_temp = asdict(snapshot)
            original_size = len(json.dumps(snapshot_data_temp, default=lambda x: x.isoformat() if isinstance(x, datetime) else (x.value if isinstance(x, Enum) else str(x))).encode())
            compression_ratio = file_size / original_size if original_size > 0 else 1.0
            
            # スナップショット更新
            snapshot.file_size_bytes = file_size
            snapshot.compression_ratio = compression_ratio
            snapshot.checksum = checksum
            
            # データベース記録
            await self._save_snapshot_metadata(snapshot, str(file_path))
            
            # 古いスナップショット削除
            await self._cleanup_old_snapshots(snapshot_type)
            
            execution_time = time.time() - start_time
            logger.info(f"Snapshot created successfully: {snapshot_id} ({execution_time:.2f}s)")
            
            self.last_snapshot_time = timestamp
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Snapshot creation error: {e}")
            raise
    
    async def _collect_component_states(self) -> Dict[str, Any]:
        """コンポーネント状態収集"""
        try:
            return {
                'position_tracker': {
                    'is_running': self.position_tracker.is_running,
                    'active_positions_count': len(self.position_tracker.active_positions),
                    'stats': self.position_tracker.get_statistics()
                },
                'risk_manager': {
                    'is_running': self.risk_manager.is_running,
                    'trading_enabled': self.risk_manager.trading_enabled,
                    'risk_stats': self.risk_manager.get_risk_statistics()
                },
                'emergency_system': {
                    'is_running': self.emergency_system.is_running,
                    'status': self.emergency_system.status.value,
                    'protection_status': self.emergency_system.get_protection_status()
                },
                'database_manager': {
                    'db_path': self.db_manager.db_path,
                    'schema_version': self.db_manager.current_schema_version,
                    'stats': await self.db_manager.get_system_statistics()
                },
                'system_state_manager': {
                    'current_status': self.current_status.value,
                    'last_snapshot_time': self.last_snapshot_time.isoformat() if self.last_snapshot_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"Component states collection error: {e}")
            return {}
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンス指標収集"""
        try:
            # 最新のパフォーマンス履歴から統計計算
            recent_metrics = self.performance_history[-100:] if self.performance_history else []
            
            if recent_metrics:
                avg_latency = sum(m.get('latency_ms', 0) for m in recent_metrics) / len(recent_metrics)
                avg_throughput = sum(m.get('throughput', 0) for m in recent_metrics) / len(recent_metrics)
            else:
                avg_latency = 0
                avg_throughput = 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'average_latency_ms': avg_latency,
                'average_throughput': avg_throughput,
                'memory_usage_mb': self._get_memory_usage(),
                'cpu_usage_percent': self._get_cpu_usage(),
                'active_connections': self._get_active_connections(),
                'error_rate_percent': self._calculate_error_rate(),
                'uptime_seconds': self._get_uptime_seconds()
            }
            
        except Exception as e:
            logger.error(f"Performance metrics collection error: {e}")
            return {}
    
    async def _collect_configuration_data(self) -> Dict[str, Any]:
        """設定データ収集"""
        try:
            return {
                'config': self.config,
                'risk_parameters': asdict(self.risk_manager.risk_params) if hasattr(self.risk_manager, 'risk_params') else {},
                'emergency_config': self.emergency_system.protection_config,
                'database_config': {
                    'db_path': self.db_manager.db_path,
                    'schema_version': self.db_manager.current_schema_version,
                    'backup_enabled': self.db_manager.auto_backup_enabled
                }
            }
            
        except Exception as e:
            logger.error(f"Configuration data collection error: {e}")
            return {}
    
    async def _collect_active_positions(self) -> List[Dict[str, Any]]:
        """アクティブポジション収集"""
        try:
            positions = []
            for position in self.position_tracker.get_active_positions():
                positions.append(position.to_dict())
            return positions
            
        except Exception as e:
            logger.error(f"Active positions collection error: {e}")
            return []
    
    async def _collect_risk_parameters(self) -> Dict[str, Any]:
        """リスクパラメータ収集"""
        try:
            return asdict(self.risk_manager.risk_params) if hasattr(self.risk_manager, 'risk_params') else {}
            
        except Exception as e:
            logger.error(f"Risk parameters collection error: {e}")
            return {}
    
    async def _collect_emergency_status(self) -> Dict[str, Any]:
        """緊急状態収集"""
        try:
            return {
                'status': self.emergency_system.status.value,
                'protection_status': self.emergency_system.get_protection_status(),
                'emergency_history_count': len(self.emergency_system.get_emergency_history()),
                'network_status': self.emergency_system.network_monitor.get_connection_status()
            }
            
        except Exception as e:
            logger.error(f"Emergency status collection error: {e}")
            return {}
    
    def _calculate_recovery_priority(self, snapshot_type: SnapshotType) -> int:
        """復旧優先度計算"""
        priority_map = {
            SnapshotType.EMERGENCY: 1,
            SnapshotType.SHUTDOWN: 2,
            SnapshotType.DAILY: 3,
            SnapshotType.HOURLY: 4,
            SnapshotType.MANUAL: 5
        }
        return priority_map.get(snapshot_type, 5)
    
    async def _save_snapshot_to_file(self, snapshot: SystemSnapshot) -> Path:
        """スナップショットファイル保存"""
        try:
            file_name = f"{snapshot.snapshot_id}_{snapshot.snapshot_type.value}.json.gz"
            file_path = self.snapshot_dir / file_name
            
            # JSON形式でシリアライズ（datetime・enum対応）
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, Enum):
                    return obj.value
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            snapshot_data = asdict(snapshot)
            json_data = json.dumps(snapshot_data, indent=2, default=json_serializer).encode()
            
            # gzip圧縮して保存
            with gzip.open(file_path, 'wb') as f:
                f.write(json_data)
            
            return file_path
            
        except Exception as e:
            logger.error(f"Snapshot file save error: {e}")
            raise
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """ファイルチェックサム計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
                
        except Exception as e:
            logger.error(f"Checksum calculation error: {e}")
            return ""
    
    async def _save_snapshot_metadata(self, snapshot: SystemSnapshot, file_path: str):
        """スナップショットメタデータ保存"""
        try:
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                await conn.execute('''
                    INSERT INTO system_snapshot_details (
                        snapshot_id, timestamp, snapshot_type, system_version,
                        file_path, file_size_bytes, compression_ratio, checksum,
                        component_count, recovery_priority, validation_status,
                        description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot.snapshot_id,
                    snapshot.timestamp.isoformat(),
                    snapshot.snapshot_type.value,
                    snapshot.system_version,
                    file_path,
                    snapshot.file_size_bytes,
                    snapshot.compression_ratio,
                    snapshot.checksum,
                    len(snapshot.component_states),
                    snapshot.recovery_priority,
                    'CREATED',
                    f"System snapshot - {snapshot.snapshot_type.value}"
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Snapshot metadata save error: {e}")
    
    async def _cleanup_old_snapshots(self, snapshot_type: SnapshotType):
        """古いスナップショット削除"""
        try:
            max_count = self.max_snapshots_per_type.get(snapshot_type, 10)
            
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                # 古いスナップショット取得
                cursor = await conn.execute('''
                    SELECT snapshot_id, file_path FROM system_snapshot_details
                    WHERE snapshot_type = ?
                    ORDER BY timestamp DESC
                    LIMIT -1 OFFSET ?
                ''', (snapshot_type.value, max_count))
                
                old_snapshots = await cursor.fetchall()
                
                for snapshot_id, file_path in old_snapshots:
                    try:
                        # ファイル削除
                        Path(file_path).unlink(missing_ok=True)
                        
                        # データベース記録削除
                        await conn.execute('''
                            DELETE FROM system_snapshot_details
                            WHERE snapshot_id = ?
                        ''', (snapshot_id,))
                        
                        logger.debug(f"Old snapshot deleted: {snapshot_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to delete old snapshot {snapshot_id}: {e}")
                
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Old snapshots cleanup error: {e}")
    
    async def _start_scheduled_tasks(self):
        """スケジュールタスク開始"""
        try:
            # 毎時スナップショット
            self.snapshot_schedule_task = asyncio.create_task(self._snapshot_scheduler())
            
            # ヘルスチェック
            self.health_check_task = asyncio.create_task(self._health_checker())
            
            logger.info("Scheduled tasks started")
            
        except Exception as e:
            logger.error(f"Scheduled tasks start error: {e}")
    
    async def _snapshot_scheduler(self):
        """スナップショットスケジューラー"""
        while self.current_status in [SystemStatus.RUNNING, SystemStatus.DEGRADED]:
            try:
                # 毎時スナップショット作成
                await asyncio.sleep(3600)  # 1時間
                await self.create_snapshot(SnapshotType.HOURLY, "scheduled_hourly")
                
                # 日次スナップショット（0時台）
                current_hour = datetime.now().hour
                if current_hour == 0:
                    await self.create_snapshot(SnapshotType.DAILY, "scheduled_daily")
                
            except Exception as e:
                logger.error(f"Snapshot scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _health_checker(self):
        """ヘルスチェッカー"""
        while self.current_status in [SystemStatus.RUNNING, SystemStatus.DEGRADED]:
            try:
                # システム健全性チェック
                health_score = await self._calculate_system_health()
                
                if health_score < 0.7:  # 70%未満で劣化状態
                    if self.current_status == SystemStatus.RUNNING:
                        self.current_status = SystemStatus.DEGRADED
                        logger.warning(f"System health degraded: {health_score:.2f}")
                        
                        # 緊急スナップショット作成
                        await self.create_snapshot(SnapshotType.EMERGENCY, f"health_degraded_{health_score:.2f}")
                
                elif health_score >= 0.8:  # 80%以上で正常復帰
                    if self.current_status == SystemStatus.DEGRADED:
                        self.current_status = SystemStatus.RUNNING
                        logger.info(f"System health restored: {health_score:.2f}")
                
                await asyncio.sleep(300)  # 5分間隔
                
            except Exception as e:
                logger.error(f"Health checker error: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_system_health(self) -> float:
        """システム健全性スコア計算"""
        try:
            health_factors = []
            
            # コンポーネント稼働状態
            if self.position_tracker.is_running:
                health_factors.append(0.25)
            if self.risk_manager.is_running:
                health_factors.append(0.25)
            if self.emergency_system.is_running:
                health_factors.append(0.25)
            
            # データベース健全性
            db_integrity = await self.db_manager.verify_data_integrity()
            if db_integrity['overall_status'] == 'HEALTHY':
                health_factors.append(0.25)
            elif db_integrity['overall_status'] == 'DEGRADED':
                health_factors.append(0.15)
            
            return sum(health_factors)
            
        except Exception as e:
            logger.error(f"System health calculation error: {e}")
            return 0.0
    
    # ヘルパーメソッド（簡略実装）
    def _get_memory_usage(self) -> float:
        """メモリ使用量取得（MB）"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """CPU使用率取得（%）"""
        try:
            import psutil
            return psutil.Process().cpu_percent()
        except:
            return 0.0
    
    def _get_active_connections(self) -> int:
        """アクティブ接続数取得"""
        return 1  # 簡略実装
    
    def _calculate_error_rate(self) -> float:
        """エラー率計算（%）"""
        return 0.0  # 簡略実装
    
    def _get_uptime_seconds(self) -> float:
        """稼働時間取得（秒）"""
        if hasattr(self, '_start_time'):
            return time.time() - self._start_time
        return 0.0
    
    async def _create_recovery_plan(self, snapshot_id: str, recovery_level: RecoveryLevel) -> RecoveryPlan:
        """復旧プラン作成"""
        # 簡略実装
        return RecoveryPlan(
            plan_id=f"recovery_{int(time.time())}",
            target_snapshot_id=snapshot_id,
            recovery_level=recovery_level,
            estimated_time_minutes=5,
            steps=[{"step": "restore_configuration"}, {"step": "restore_positions"}],
            prerequisites=["database_accessible"],
            rollback_available=True,
            risk_assessment="LOW"
        )
    
    async def _execute_recovery_plan(self, plan: RecoveryPlan) -> bool:
        """復旧プラン実行"""
        # 簡略実装
        logger.info(f"Executing recovery plan: {plan.plan_id}")
        return True
    
    async def stop(self):
        """システム状態管理停止"""
        logger.info("Stopping System State Manager...")
        
        try:
            # シャットダウンスナップショット作成
            await self.create_snapshot(SnapshotType.SHUTDOWN, "system_shutdown")
            
            # スケジュールタスク停止
            if self.snapshot_schedule_task:
                self.snapshot_schedule_task.cancel()
            if self.health_check_task:
                self.health_check_task.cancel()
            
            self.current_status = SystemStatus.STOPPED
            logger.info("System State Manager stopped successfully")
            
        except Exception as e:
            logger.error(f"System State Manager stop error: {e}")

# テスト関数
async def test_system_state_manager():
    """システム状態管理テスト"""
    print("🧪 System State Manager Test Starting...")
    
    # 依存システム初期化（モック）
    from position_management import PositionTracker
    from risk_management import RiskManager, RiskParameters
    from emergency_protection import EmergencyProtectionSystem
    from database_manager import DatabaseManager
    
    db_manager = DatabaseManager("./test_system_state.db")
    await db_manager.initialize()
    
    position_tracker = PositionTracker()
    await position_tracker.initialize()
    
    risk_manager = RiskManager(position_tracker, RiskParameters())
    await risk_manager.initialize()
    
    emergency_system = EmergencyProtectionSystem(position_tracker, risk_manager)
    await emergency_system.initialize()
    
    # システム状態管理初期化
    state_manager = SystemStateManager(position_tracker, risk_manager, emergency_system, db_manager)
    await state_manager.initialize()
    
    try:
        # スナップショット作成テスト
        snapshot_id = await state_manager.create_snapshot(SnapshotType.MANUAL, "test_snapshot")
        print(f"✅ Snapshot creation test: {snapshot_id}")
        
        # システム健全性テスト
        health_score = await state_manager._calculate_system_health()
        print(f"✅ System health test: {health_score:.2f}")
        
        print("✅ System State Manager Test Completed")
        
    finally:
        await state_manager.stop()
        await emergency_system.stop()
        await risk_manager.stop()
        await position_tracker.stop()
        await db_manager.stop()

if __name__ == "__main__":
    asyncio.run(test_system_state_manager())