#!/usr/bin/env python3
"""
Phase 4.1: Database Schema Extension
kiro設計tasks.md:127-133準拠 - 取引操作のためのデータベーススキーマ拡張

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 5.1, 5.4 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import logging
import aiosqlite
import time
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import sys
from pathlib import Path

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, CONFIG
from position_management import Position, PositionStatus, PositionType
from risk_management import RiskAssessment, RiskLevel, RiskAction

# ログ設定
logger = logging.getLogger(__name__)

class MigrationStatus(Enum):
    """データベース移行状態"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"

class DataIntegrityLevel(Enum):
    """データ整合性レベル"""
    STRICT = "STRICT"
    MODERATE = "MODERATE"
    RELAXED = "RELAXED"

@dataclass
class TradingSignalRecord:
    """取引シグナル記録"""
    signal_id: str
    timestamp: datetime
    symbol: str
    action: str
    quantity: float
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    quality_score: float
    confidence_level: float
    strategy_params: Dict[str, Any]
    source_system: str
    processing_time_ms: float
    market_conditions: Dict[str, Any]
    signal_status: str  # GENERATED, SENT, EXECUTED, REJECTED, EXPIRED

@dataclass
class TradeExecutionRecord:
    """取引実行記録"""
    execution_id: str
    signal_id: str
    position_id: Optional[str]
    timestamp: datetime
    symbol: str
    action: str
    requested_quantity: float
    executed_quantity: float
    requested_price: float
    executed_price: float
    execution_time_ms: float
    slippage: float
    commission: float
    execution_status: str  # PENDING, EXECUTED, PARTIAL, FAILED, CANCELLED
    failure_reason: Optional[str]
    mt4_ticket: Optional[int]
    risk_assessment_id: Optional[str]

@dataclass
class DatabaseMigration:
    """データベース移行記録"""
    migration_id: str
    version_from: str
    version_to: str
    description: str
    sql_script: str
    created_at: datetime
    executed_at: Optional[datetime]
    status: MigrationStatus
    execution_time_seconds: Optional[float]
    rollback_script: Optional[str]
    error_message: Optional[str]

class DatabaseManager:
    """
    データベース管理システム - kiro設計tasks.md:127-133準拠
    取引シグナル・実行・ポジション統合管理・スキーマ移行・データ整合性
    """
    
    def __init__(self, db_path: str = None):
        # 設定読み込み
        self.config = CONFIG
        self.db_path = db_path or self.config.get('database', {}).get('path', './trading_system.db')
        
        # データベース設定
        self.current_schema_version = "4.1.0"
        self.integrity_level = DataIntegrityLevel.STRICT
        self.auto_backup_enabled = True
        self.backup_retention_days = 30
        
        # 接続プール設定
        self.max_connections = 10
        self.connection_timeout = 30
        self._connection_pool = []
        self._pool_lock = asyncio.Lock()
        
        # 移行管理
        self.migrations_applied = set()
        self.migration_lock = asyncio.Lock()
        
        # バックアップ設定
        self.backup_dir = Path(self.db_path).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Database Manager initialized: {self.db_path}")
    
    async def initialize(self):
        """データベースマネージャー初期化"""
        logger.info("Initializing Database Manager...")
        
        try:
            # 基本テーブル作成
            await self._create_core_tables()
            
            # 移行システム初期化
            await self._initialize_migration_system()
            
            # Phase4拡張テーブル作成
            await self._create_phase4_tables()
            
            # データ整合性制約追加
            await self._create_integrity_constraints()
            
            # バックアップシステム初期化
            await self._initialize_backup_system()
            
            logger.info("Database Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Database Manager initialization error: {e}")
            raise
    
    async def _create_core_tables(self):
        """既存システム統合のための基本テーブル作成"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # システム情報テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_info (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # バージョン情報設定
                await conn.execute('''
                    INSERT OR REPLACE INTO system_info (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', ('schema_version', self.current_schema_version, datetime.now().isoformat()))
                
                await conn.commit()
                logger.info("Core tables created successfully")
                
        except Exception as e:
            logger.error(f"Core tables creation error: {e}")
            raise
    
    async def _initialize_migration_system(self):
        """データベース移行システム初期化"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # 移行履歴テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS database_migrations (
                        migration_id TEXT PRIMARY KEY,
                        version_from TEXT NOT NULL,
                        version_to TEXT NOT NULL,
                        description TEXT NOT NULL,
                        sql_script TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        executed_at TEXT,
                        status TEXT NOT NULL,
                        execution_time_seconds REAL,
                        rollback_script TEXT,
                        error_message TEXT,
                        checksum TEXT NOT NULL
                    )
                ''')
                
                await conn.commit()
                logger.info("Migration system initialized")
                
        except Exception as e:
            logger.error(f"Migration system initialization error: {e}")
            raise
    
    async def _create_phase4_tables(self):
        """Phase4拡張テーブル作成 - kiro要件5.1準拠"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # 取引シグナルテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        signal_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        action TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        quality_score REAL NOT NULL,
                        confidence_level REAL NOT NULL,
                        strategy_params TEXT,
                        source_system TEXT NOT NULL,
                        processing_time_ms REAL NOT NULL,
                        market_conditions TEXT,
                        signal_status TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 取引実行テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS trade_executions (
                        execution_id TEXT PRIMARY KEY,
                        signal_id TEXT NOT NULL,
                        position_id TEXT,
                        timestamp TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        action TEXT NOT NULL,
                        requested_quantity REAL NOT NULL,
                        executed_quantity REAL NOT NULL,
                        requested_price REAL NOT NULL,
                        executed_price REAL NOT NULL,
                        execution_time_ms REAL NOT NULL,
                        slippage REAL DEFAULT 0.0,
                        commission REAL DEFAULT 0.0,
                        execution_status TEXT NOT NULL,
                        failure_reason TEXT,
                        mt4_ticket INTEGER,
                        risk_assessment_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES trading_signals (signal_id),
                        FOREIGN KEY (position_id) REFERENCES positions (position_id)
                    )
                ''')
                
                # リスク評価テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS risk_assessments (
                        assessment_id TEXT PRIMARY KEY,
                        signal_id TEXT,
                        timestamp TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        risk_action TEXT NOT NULL,
                        risk_score REAL NOT NULL,
                        account_balance REAL NOT NULL,
                        daily_pnl REAL NOT NULL,
                        current_drawdown REAL NOT NULL,
                        volatility_score REAL NOT NULL,
                        exposure_ratio REAL NOT NULL,
                        reasons TEXT,
                        recommendations TEXT,
                        assessment_time_ms REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES trading_signals (signal_id)
                    )
                ''')
                
                # システム状態スナップショットテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        system_version TEXT NOT NULL,
                        component_states TEXT NOT NULL,
                        performance_metrics TEXT NOT NULL,
                        active_positions_count INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        account_balance REAL DEFAULT 0.0,
                        risk_level TEXT,
                        system_health_score REAL DEFAULT 0.0,
                        snapshot_size_bytes INTEGER DEFAULT 0,
                        compression_ratio REAL DEFAULT 1.0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await conn.commit()
                logger.info("Phase4 extended tables created successfully")
                
        except Exception as e:
            logger.error(f"Phase4 tables creation error: {e}")
            raise
    
    async def _create_integrity_constraints(self):
        """データ整合性制約と検証ルール作成 - kiro要件5.1準拠"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # インデックス作成（パフォーマンス向上）
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol)",
                    "CREATE INDEX IF NOT EXISTS idx_trading_signals_status ON trading_signals(signal_status)",
                    "CREATE INDEX IF NOT EXISTS idx_trade_executions_timestamp ON trade_executions(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_trade_executions_symbol ON trade_executions(symbol)",
                    "CREATE INDEX IF NOT EXISTS idx_trade_executions_status ON trade_executions(execution_status)",
                    "CREATE INDEX IF NOT EXISTS idx_risk_assessments_timestamp ON risk_assessments(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_risk_assessments_level ON risk_assessments(risk_level)",
                    "CREATE INDEX IF NOT EXISTS idx_system_snapshots_timestamp ON system_snapshots(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
                    "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)"
                ]
                
                for index_sql in indexes:
                    await conn.execute(index_sql)
                
                await conn.commit()
                logger.info("Database integrity constraints created")
                
        except Exception as e:
            logger.error(f"Integrity constraints creation error: {e}")
    
    async def _initialize_backup_system(self):
        """バックアップシステム初期化 - kiro要件5.4準拠"""
        try:
            # バックアップスケジュールテーブル
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS backup_schedule (
                        backup_id TEXT PRIMARY KEY,
                        backup_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size_bytes INTEGER NOT NULL,
                        checksum TEXT NOT NULL,
                        compression_ratio REAL DEFAULT 1.0,
                        backup_status TEXT NOT NULL,
                        retention_until TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await conn.commit()
            
            # 初回バックアップ作成
            await self._create_backup("initialization")
            
            logger.info("Backup system initialized")
            
        except Exception as e:
            logger.error(f"Backup system initialization error: {e}")
    
    async def save_trading_signal(self, signal: TradingSignalRecord) -> bool:
        """取引シグナル保存"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO trading_signals (
                        signal_id, timestamp, symbol, action, quantity, price,
                        stop_loss, take_profit, quality_score, confidence_level,
                        strategy_params, source_system, processing_time_ms,
                        market_conditions, signal_status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal.signal_id, signal.timestamp.isoformat(), signal.symbol,
                    signal.action, signal.quantity, signal.price, signal.stop_loss,
                    signal.take_profit, signal.quality_score, signal.confidence_level,
                    json.dumps(signal.strategy_params), signal.source_system,
                    signal.processing_time_ms, json.dumps(signal.market_conditions),
                    signal.signal_status, datetime.now().isoformat()
                ))
                await conn.commit()
                
                logger.debug(f"Trading signal saved: {signal.signal_id}")
                return True
                
        except Exception as e:
            logger.error(f"Trading signal save error: {e}")
            return False
    
    async def save_trade_execution(self, execution: TradeExecutionRecord) -> bool:
        """取引実行記録保存"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO trade_executions (
                        execution_id, signal_id, position_id, timestamp, symbol,
                        action, requested_quantity, executed_quantity, requested_price,
                        executed_price, execution_time_ms, slippage, commission,
                        execution_status, failure_reason, mt4_ticket, risk_assessment_id,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    execution.execution_id, execution.signal_id, execution.position_id,
                    execution.timestamp.isoformat(), execution.symbol, execution.action,
                    execution.requested_quantity, execution.executed_quantity,
                    execution.requested_price, execution.executed_price,
                    execution.execution_time_ms, execution.slippage, execution.commission,
                    execution.execution_status, execution.failure_reason,
                    execution.mt4_ticket, execution.risk_assessment_id,
                    datetime.now().isoformat()
                ))
                await conn.commit()
                
                logger.debug(f"Trade execution saved: {execution.execution_id}")
                return True
                
        except Exception as e:
            logger.error(f"Trade execution save error: {e}")
            return False
    
    async def save_risk_assessment(self, assessment: RiskAssessment, signal_id: str = None) -> bool:
        """リスク評価保存"""
        try:
            assessment_id = f"risk_{int(time.time() * 1000)}"
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO risk_assessments (
                        assessment_id, signal_id, timestamp, risk_level, risk_action,
                        risk_score, account_balance, daily_pnl, current_drawdown,
                        volatility_score, exposure_ratio, reasons, recommendations,
                        assessment_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    assessment_id, signal_id, datetime.now().isoformat(),
                    assessment.risk_level.value, assessment.risk_action.value,
                    assessment.risk_score, assessment.account_balance,
                    assessment.daily_pnl, assessment.current_drawdown,
                    assessment.volatility_score, assessment.exposure_ratio,
                    json.dumps(assessment.reasons), json.dumps(assessment.recommendations),
                    assessment.assessment_time_ms
                ))
                await conn.commit()
                
                logger.debug(f"Risk assessment saved: {assessment_id}")
                return True
                
        except Exception as e:
            logger.error(f"Risk assessment save error: {e}")
            return False
    
    async def get_trading_history(self, symbol: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """取引履歴取得 - kiro要件5.1準拠"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as conn:
                if symbol:
                    cursor = await conn.execute('''
                        SELECT ts.*, te.*, ra.risk_level, ra.risk_score
                        FROM trading_signals ts
                        LEFT JOIN trade_executions te ON ts.signal_id = te.signal_id
                        LEFT JOIN risk_assessments ra ON ts.signal_id = ra.signal_id
                        WHERE ts.symbol = ? AND ts.timestamp >= ?
                        ORDER BY ts.timestamp DESC
                    ''', (symbol, since_date))
                else:
                    cursor = await conn.execute('''
                        SELECT ts.*, te.*, ra.risk_level, ra.risk_score
                        FROM trading_signals ts
                        LEFT JOIN trade_executions te ON ts.signal_id = te.signal_id
                        LEFT JOIN risk_assessments ra ON ts.signal_id = ra.signal_id
                        WHERE ts.timestamp >= ?
                        ORDER BY ts.timestamp DESC
                    ''', (since_date,))
                
                rows = await cursor.fetchall()
                
                # 列名取得
                columns = [description[0] for description in cursor.description]
                
                # 辞書形式に変換
                history = []
                for row in rows:
                    record = dict(zip(columns, row))
                    history.append(record)
                
                logger.info(f"Retrieved {len(history)} trading history records")
                return history
                
        except Exception as e:
            logger.error(f"Trading history retrieval error: {e}")
            return []
    
    async def _create_backup(self, backup_type: str) -> bool:
        """データベースバックアップ作成 - kiro要件5.4準拠"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"trading_system_{backup_type}_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # バックアップ作成
            async with aiosqlite.connect(self.db_path) as source:
                async with aiosqlite.connect(str(backup_path)) as backup:
                    await source.backup(backup)
            
            # チェックサム計算
            file_size = backup_path.stat().st_size
            with open(backup_path, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            # バックアップ記録保存
            backup_id = f"backup_{timestamp}"
            retention_date = (datetime.now() + timedelta(days=self.backup_retention_days)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO backup_schedule (
                        backup_id, backup_type, timestamp, file_path, file_size_bytes,
                        checksum, backup_status, retention_until
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    backup_id, backup_type, datetime.now().isoformat(),
                    str(backup_path), file_size, checksum, "COMPLETED", retention_date
                ))
                await conn.commit()
            
            logger.info(f"Database backup created: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Database backup creation error: {e}")
            return False
    
    async def verify_data_integrity(self) -> Dict[str, Any]:
        """データ整合性検証 - kiro要件5.1準拠"""
        try:
            integrity_report = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'HEALTHY',
                'checks_performed': [],
                'issues_found': [],
                'recommendations': []
            }
            
            async with aiosqlite.connect(self.db_path) as conn:
                # 1. 外部キー整合性チェック
                cursor = await conn.execute('''
                    SELECT COUNT(*) as orphaned_executions
                    FROM trade_executions te
                    LEFT JOIN trading_signals ts ON te.signal_id = ts.signal_id
                    WHERE ts.signal_id IS NULL
                ''')
                orphaned_count = (await cursor.fetchone())[0]
                
                integrity_report['checks_performed'].append('foreign_key_integrity')
                if orphaned_count > 0:
                    integrity_report['issues_found'].append(f"Orphaned executions: {orphaned_count}")
                    integrity_report['overall_status'] = 'DEGRADED'
                
                # 2. データ完整性チェック
                cursor = await conn.execute('''
                    SELECT COUNT(*) as null_prices
                    FROM trading_signals
                    WHERE price IS NULL AND signal_status = 'EXECUTED'
                ''')
                null_prices = (await cursor.fetchone())[0]
                
                integrity_report['checks_performed'].append('data_completeness')
                if null_prices > 0:
                    integrity_report['issues_found'].append(f"Executed signals with null prices: {null_prices}")
                
                # 3. タイムスタンプ整合性チェック
                cursor = await conn.execute('''
                    SELECT COUNT(*) as future_timestamps
                    FROM trading_signals
                    WHERE datetime(timestamp) > datetime('now')
                ''')
                future_timestamps = (await cursor.fetchone())[0]
                
                integrity_report['checks_performed'].append('timestamp_validity')
                if future_timestamps > 0:
                    integrity_report['issues_found'].append(f"Future timestamps: {future_timestamps}")
                
                # 推奨事項生成
                if len(integrity_report['issues_found']) == 0:
                    integrity_report['recommendations'].append("Data integrity is excellent")
                else:
                    integrity_report['recommendations'].append("Consider running data cleanup procedures")
                    integrity_report['overall_status'] = 'NEEDS_ATTENTION'
            
            logger.info(f"Data integrity check completed: {integrity_report['overall_status']}")
            return integrity_report
            
        except Exception as e:
            logger.error(f"Data integrity verification error: {e}")
            return {'overall_status': 'ERROR', 'error': str(e)}
    
    async def cleanup_old_data(self, retention_days: int = 180) -> Dict[str, int]:
        """古いデータクリーンアップ - kiro要件5.1準拠"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            cleanup_results = {}
            
            async with aiosqlite.connect(self.db_path) as conn:
                # 古いシグナル削除
                cursor = await conn.execute('''
                    DELETE FROM trading_signals
                    WHERE timestamp < ? AND signal_status IN ('EXPIRED', 'REJECTED')
                ''', (cutoff_date,))
                cleanup_results['signals_deleted'] = cursor.rowcount
                
                # 古いスナップショット削除（最新30日分は保持）
                snapshot_cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                cursor = await conn.execute('''
                    DELETE FROM system_snapshots
                    WHERE timestamp < ?
                ''', (snapshot_cutoff,))
                cleanup_results['snapshots_deleted'] = cursor.rowcount
                
                # 古いバックアップファイル削除
                cursor = await conn.execute('''
                    SELECT file_path FROM backup_schedule
                    WHERE retention_until < ?
                ''', (datetime.now().isoformat(),))
                
                old_backups = await cursor.fetchall()
                deleted_backups = 0
                for (file_path,) in old_backups:
                    try:
                        Path(file_path).unlink(missing_ok=True)
                        deleted_backups += 1
                    except Exception:
                        pass
                
                # バックアップ記録削除
                cursor = await conn.execute('''
                    DELETE FROM backup_schedule
                    WHERE retention_until < ?
                ''', (datetime.now().isoformat(),))
                
                cleanup_results['backups_deleted'] = deleted_backups
                
                await conn.commit()
            
            logger.info(f"Data cleanup completed: {cleanup_results}")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Data cleanup error: {e}")
            return {}
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """システム統計情報取得"""
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'database_size_mb': 0,
                'total_signals': 0,
                'total_executions': 0,
                'total_positions': 0,
                'data_integrity_score': 0.0
            }
            
            # データベースサイズ
            db_size = Path(self.db_path).stat().st_size / (1024 * 1024)
            stats['database_size_mb'] = round(db_size, 2)
            
            async with aiosqlite.connect(self.db_path) as conn:
                # シグナル数
                cursor = await conn.execute('SELECT COUNT(*) FROM trading_signals')
                stats['total_signals'] = (await cursor.fetchone())[0]
                
                # 実行数
                cursor = await conn.execute('SELECT COUNT(*) FROM trade_executions')
                stats['total_executions'] = (await cursor.fetchone())[0]
                
                # ポジション数
                cursor = await conn.execute('SELECT COUNT(*) FROM positions')
                stats['total_positions'] = (await cursor.fetchone())[0]
            
            # データ整合性スコア
            integrity_result = await self.verify_data_integrity()
            if integrity_result['overall_status'] == 'HEALTHY':
                stats['data_integrity_score'] = 1.0
            elif integrity_result['overall_status'] == 'DEGRADED':
                stats['data_integrity_score'] = 0.7
            else:
                stats['data_integrity_score'] = 0.3
            
            return stats
            
        except Exception as e:
            logger.error(f"System statistics error: {e}")
            return {}
    
    async def stop(self):
        """データベースマネージャー停止"""
        logger.info("Stopping Database Manager...")
        
        try:
            # 最終バックアップ作成
            await self._create_backup("shutdown")
            
            # データクリーンアップ
            await self.cleanup_old_data()
            
            logger.info("Database Manager stopped successfully")
            
        except Exception as e:
            logger.error(f"Database Manager stop error: {e}")

# テスト関数
async def test_database_manager():
    """データベースマネージャーテスト"""
    print("🧪 Database Manager Test Starting...")
    
    db_manager = DatabaseManager("./test_trading_system.db")
    await db_manager.initialize()
    
    try:
        # テストシグナル作成
        test_signal = TradingSignalRecord(
            signal_id="TEST_SIGNAL_001",
            timestamp=datetime.now(),
            symbol="EURUSD",
            action="BUY",
            quantity=0.1,
            price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            quality_score=0.85,
            confidence_level=0.75,
            strategy_params={"breakout_threshold": 2.0},
            source_system="Phase2_SignalGenerator",
            processing_time_ms=15.5,
            market_conditions={"volatility": "normal"},
            signal_status="GENERATED"
        )
        
        # シグナル保存テスト
        success = await db_manager.save_trading_signal(test_signal)
        print(f"✅ Signal save test: {'SUCCESS' if success else 'FAILED'}")
        
        # データ整合性テスト
        integrity = await db_manager.verify_data_integrity()
        print(f"✅ Data integrity test: {integrity['overall_status']}")
        
        # 統計情報テスト
        stats = await db_manager.get_system_statistics()
        print(f"✅ System statistics: {stats}")
        
        print("✅ Database Manager Test Completed")
        
    finally:
        await db_manager.stop()

if __name__ == "__main__":
    asyncio.run(test_database_manager())