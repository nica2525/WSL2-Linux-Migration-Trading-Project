#!/usr/bin/env python3
"""
Phase 4.5: Existing Automation Compatibility System
kiro設計tasks.md:159-165準拠 - 既存自動化システムとの互換性確保

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 6.1, 6.2, 6.3, 6.4, 6.5 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import logging
import aiosqlite
import time
import subprocess
import os
import signal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import sys
from pathlib import Path
import threading
import shutil

# psutil はオプショナル
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, CONFIG
from database_manager import DatabaseManager
from position_management import PositionTracker
from risk_management import RiskManager
from emergency_protection import EmergencyProtectionSystem
from system_state_manager import SystemStateManager
from health_monitor import HealthMonitor
from performance_reporter import PerformanceReporter

# ログ設定
logger = logging.getLogger(__name__)

class AutomationStatus(Enum):
    """自動化状態"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"

class ComponentType(Enum):
    """コンポーネント種別"""
    CORE_SYSTEM = "CORE_SYSTEM"
    CRON_JOB = "CRON_JOB"
    WORKER_PROCESS = "WORKER_PROCESS"
    MONITOR_SERVICE = "MONITOR_SERVICE"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"

class CompatibilityLevel(Enum):
    """互換性レベル"""
    FULL_COMPATIBLE = "FULL_COMPATIBLE"
    PARTIAL_COMPATIBLE = "PARTIAL_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"

@dataclass
class AutomationComponent:
    """自動化コンポーネント"""
    component_id: str
    name: str
    component_type: ComponentType
    status: AutomationStatus
    pid: Optional[int]
    command: str
    schedule: Optional[str]
    working_directory: str
    log_file: str
    last_seen: datetime
    start_time: Optional[datetime]
    restart_count: int
    health_check_endpoint: Optional[str]
    dependencies: List[str]
    compatibility_level: CompatibilityLevel

@dataclass
class HotSwapOperation:
    """ホットスワップ操作"""
    operation_id: str
    target_component: str
    operation_type: str  # START, STOP, RESTART, REPLACE
    old_version: Optional[str]
    new_version: Optional[str]
    start_time: datetime
    completion_time: Optional[datetime]
    success: bool
    rollback_available: bool
    error_message: Optional[str]

class AutomationCompatibilityManager:
    """
    既存自動化互換性システム - kiro設計tasks.md:159-165準拠
    cron統合・19ワーカー並列処理・運用時間窓・ホットスワップ機能
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # 設定読み込み
        self.config = CONFIG
        
        # 自動化設定
        self.automation_config = self.config.get('automation', {})
        self.operating_hours = self.automation_config.get('operating_hours', {'start': 9, 'end': 22})
        self.max_workers = self.automation_config.get('max_workers', 19)
        self.cron_schedule_file = self.automation_config.get('cron_file', '/tmp/trading_cron_schedule')
        
        # コンポーネント管理
        self.registered_components = {}
        self.worker_processes = {}
        self.active_workers = 0
        
        # 互換性チェック
        self.compatibility_cache = {}
        self.last_compatibility_check = None
        
        # ホットスワップ管理
        self.hotswap_operations = {}
        self.hotswap_lock = asyncio.Lock()
        
        # 監視設定
        self.monitoring_enabled = True
        self.monitor_interval_seconds = 60
        self.monitor_task = None
        
        # ログディレクトリ
        self.logs_dir = Path(self.automation_config.get('logs_directory', './logs'))
        self.logs_dir.mkdir(exist_ok=True)
        
        logger.info("Automation Compatibility Manager initialized")
    
    async def initialize(self):
        """自動化互換性マネージャー初期化"""
        logger.info("Initializing Automation Compatibility Manager...")
        
        try:
            # 互換性管理テーブル初期化
            await self._initialize_compatibility_tables()
            
            # 既存自動化システム検出
            await self._discover_existing_automation()
            
            # cron統合検証
            await self._verify_cron_integration()
            
            # 運用時間窓検証
            await self._verify_operating_hours()
            
            # 19ワーカー並列処理初期化
            await self._initialize_worker_pool()
            
            # 監視開始
            await self._start_monitoring()
            
            logger.info("Automation Compatibility Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Automation Compatibility Manager initialization error: {e}")
            raise
    
    async def _initialize_compatibility_tables(self):
        """互換性管理テーブル初期化"""
        try:
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                # 自動化コンポーネント登録テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS automation_components (
                        component_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        component_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        pid INTEGER,
                        command TEXT NOT NULL,
                        schedule TEXT,
                        working_directory TEXT NOT NULL,
                        log_file TEXT NOT NULL,
                        last_seen TEXT NOT NULL,
                        start_time TEXT,
                        restart_count INTEGER DEFAULT 0,
                        health_check_endpoint TEXT,
                        dependencies TEXT,
                        compatibility_level TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # ホットスワップ操作履歴テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS hotswap_operations (
                        operation_id TEXT PRIMARY KEY,
                        target_component TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        old_version TEXT,
                        new_version TEXT,
                        start_time TEXT NOT NULL,
                        completion_time TEXT,
                        success BOOLEAN NOT NULL,
                        rollback_available BOOLEAN DEFAULT FALSE,
                        error_message TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 互換性チェック履歴テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS compatibility_checks (
                        check_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        component_id TEXT NOT NULL,
                        compatibility_level TEXT NOT NULL,
                        issues_found TEXT,
                        recommendations TEXT,
                        check_duration_ms REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await conn.commit()
                logger.info("Compatibility management tables initialized")
                
        except Exception as e:
            logger.error(f"Compatibility tables initialization error: {e}")
            raise
    
    async def _discover_existing_automation(self):
        """既存自動化システム検出 - kiro要件6.1準拠"""
        try:
            discovered_components = []
            
            # 1. cron自動化システム検出
            cron_components = await self._discover_cron_jobs()
            discovered_components.extend(cron_components)
            
            # 2. 実行中プロセス検出
            process_components = await self._discover_running_processes()
            discovered_components.extend(process_components)
            
            # 3. システムサービス検出
            service_components = await self._discover_system_services()
            discovered_components.extend(service_components)
            
            # 4. 検出されたコンポーネント登録
            for component in discovered_components:
                await self._register_component(component)
            
            logger.info(f"Discovered {len(discovered_components)} automation components")
            
        except Exception as e:
            logger.error(f"Existing automation discovery error: {e}")
    
    async def _discover_cron_jobs(self) -> List[AutomationComponent]:
        """cron自動化システム検出"""
        try:
            components = []
            
            # crontab -l でcronジョブ取得
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            
            if result.returncode == 0:
                cron_lines = result.stdout.strip().split('\n')
                
                for i, line in enumerate(cron_lines):
                    if line.strip() and not line.startswith('#'):
                        # cron式とコマンドを分離
                        parts = line.strip().split(' ', 5)
                        if len(parts) >= 6:
                            schedule = ' '.join(parts[:5])
                            command = parts[5]
                            
                            # 取引システム関連のcronジョブを識別
                            if any(keyword in command for keyword in ['trading', 'git_auto_save', 'system_monitor']):
                                component = AutomationComponent(
                                    component_id=f"cron_{i}",
                                    name=f"Cron Job: {command[:50]}...",
                                    component_type=ComponentType.CRON_JOB,
                                    status=AutomationStatus.ACTIVE,
                                    pid=None,
                                    command=command,
                                    schedule=schedule,
                                    working_directory=os.getcwd(),
                                    log_file=self._extract_log_file_from_command(command),
                                    last_seen=datetime.now(),
                                    start_time=None,
                                    restart_count=0,
                                    health_check_endpoint=None,
                                    dependencies=[],
                                    compatibility_level=CompatibilityLevel.FULL_COMPATIBLE
                                )
                                components.append(component)
            
            return components
            
        except Exception as e:
            logger.error(f"Cron jobs discovery error: {e}")
            return []
    
    async def _discover_running_processes(self) -> List[AutomationComponent]:
        """実行中プロセス検出"""
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available - process discovery limited")
            return []
        
        try:
            components = []
            
            # psutil で実行中プロセス取得
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cwd']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else pinfo['name']
                    
                    # 取引システム関連プロセス識別
                    if any(keyword in cmdline.lower() for keyword in [
                        'trading', 'signal_generator', 'position_management', 'risk_management'
                    ]):
                        component = AutomationComponent(
                            component_id=f"proc_{pinfo['pid']}",
                            name=f"Process: {pinfo['name']}",
                            component_type=ComponentType.WORKER_PROCESS,
                            status=AutomationStatus.ACTIVE,
                            pid=pinfo['pid'],
                            command=cmdline,
                            schedule=None,
                            working_directory=pinfo['cwd'] or os.getcwd(),
                            log_file=f"./logs/process_{pinfo['pid']}.log",
                            last_seen=datetime.now(),
                            start_time=datetime.fromtimestamp(pinfo['create_time']),
                            restart_count=0,
                            health_check_endpoint=None,
                            dependencies=[],
                            compatibility_level=CompatibilityLevel.UNKNOWN
                        )
                        components.append(component)
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return components
            
        except Exception as e:
            logger.error(f"Running processes discovery error: {e}")
            return []
    
    async def _discover_system_services(self) -> List[AutomationComponent]:
        """システムサービス検出"""
        try:
            components = []
            
            # systemctl でサービス状態確認（WSL2では限定的）
            try:
                result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=active'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'trading' in line.lower():
                            parts = line.split()
                            if len(parts) > 0:
                                service_name = parts[0]
                                component = AutomationComponent(
                                    component_id=f"service_{service_name}",
                                    name=f"Service: {service_name}",
                                    component_type=ComponentType.MONITOR_SERVICE,
                                    status=AutomationStatus.ACTIVE,
                                    pid=None,
                                    command=f"systemctl status {service_name}",
                                    schedule=None,
                                    working_directory="/",
                                    log_file=f"/var/log/{service_name}.log",
                                    last_seen=datetime.now(),
                                    start_time=None,
                                    restart_count=0,
                                    health_check_endpoint=None,
                                    dependencies=[],
                                    compatibility_level=CompatibilityLevel.PARTIAL_COMPATIBLE
                                )
                                components.append(component)
            
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.info("systemctl not available (WSL2 environment)")
            
            return components
            
        except Exception as e:
            logger.error(f"System services discovery error: {e}")
            return []
    
    def _extract_log_file_from_command(self, command: str) -> str:
        """コマンドからログファイルパス抽出"""
        # >> filename.log パターンを検索
        if '>>' in command:
            parts = command.split('>>')
            if len(parts) > 1:
                log_file = parts[1].strip().split()[0]
                return log_file
        
        # デフォルトログファイル
        return "./logs/automation.log"
    
    async def _register_component(self, component: AutomationComponent):
        """コンポーネント登録"""
        try:
            self.registered_components[component.component_id] = component
            
            # データベース保存
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO automation_components (
                        component_id, name, component_type, status, pid, command,
                        schedule, working_directory, log_file, last_seen, start_time,
                        restart_count, health_check_endpoint, dependencies,
                        compatibility_level, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    component.component_id, component.name, component.component_type.value,
                    component.status.value, component.pid, component.command,
                    component.schedule, component.working_directory, component.log_file,
                    component.last_seen.isoformat(),
                    component.start_time.isoformat() if component.start_time else None,
                    component.restart_count, component.health_check_endpoint,
                    json.dumps(component.dependencies), component.compatibility_level.value,
                    datetime.now().isoformat()
                ))
                await conn.commit()
            
            logger.debug(f"Component registered: {component.component_id}")
            
        except Exception as e:
            logger.error(f"Component registration error: {e}")
    
    async def _verify_cron_integration(self):
        """cron統合検証 - kiro要件6.1準拠"""
        try:
            logger.info("Verifying cron integration...")
            
            # 重要なcronジョブ確認
            essential_cron_jobs = [
                'cron_git_auto_save.py',  # Git自動保存
                'cron_system_monitor.py'  # システム監視
            ]
            
            missing_jobs = []
            for job_script in essential_cron_jobs:
                found = False
                for component_id, component in self.registered_components.items():
                    if (component.component_type == ComponentType.CRON_JOB and 
                        job_script in component.command):
                        found = True
                        break
                
                if not found:
                    missing_jobs.append(job_script)
            
            if missing_jobs:
                logger.warning(f"Missing essential cron jobs: {missing_jobs}")
            else:
                logger.info("All essential cron jobs are active")
            
        except Exception as e:
            logger.error(f"Cron integration verification error: {e}")
    
    async def _verify_operating_hours(self):
        """運用時間窓検証 - kiro要件6.3準拠"""
        try:
            current_hour = datetime.now().hour
            start_hour = self.operating_hours['start']
            end_hour = self.operating_hours['end']
            
            if start_hour <= current_hour <= end_hour:
                logger.info(f"Within operating hours: {current_hour}:00 ({start_hour}-{end_hour})")
                return True
            else:
                logger.info(f"Outside operating hours: {current_hour}:00 (scheduled: {start_hour}-{end_hour})")
                return False
                
        except Exception as e:
            logger.error(f"Operating hours verification error: {e}")
            return False
    
    async def _initialize_worker_pool(self):
        """19ワーカー並列処理初期化 - kiro要件6.2準拠"""
        try:
            logger.info(f"Initializing worker pool (max: {self.max_workers})...")
            
            # 既存ワーカープロセス確認
            current_workers = 0
            for component_id, component in self.registered_components.items():
                if (component.component_type == ComponentType.WORKER_PROCESS and 
                    component.status == AutomationStatus.ACTIVE):
                    current_workers += 1
            
            self.active_workers = current_workers
            
            logger.info(f"Current active workers: {self.active_workers}/{self.max_workers}")
            
            # 必要に応じて追加ワーカー起動
            if self.active_workers < self.max_workers:
                available_slots = self.max_workers - self.active_workers
                logger.info(f"Available worker slots: {available_slots}")
            
        except Exception as e:
            logger.error(f"Worker pool initialization error: {e}")
    
    async def start_worker(self, worker_id: str, command: str, working_dir: str = None) -> bool:
        """ワーカープロセス開始"""
        try:
            if self.active_workers >= self.max_workers:
                logger.warning(f"Worker pool full ({self.max_workers}), cannot start {worker_id}")
                return False
            
            if worker_id in self.worker_processes:
                logger.warning(f"Worker {worker_id} already running")
                return False
            
            # プロセス開始
            process = subprocess.Popen(
                command.split(),
                cwd=working_dir or os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.worker_processes[worker_id] = process
            self.active_workers += 1
            
            # コンポーネント登録
            component = AutomationComponent(
                component_id=f"worker_{worker_id}",
                name=f"Worker: {worker_id}",
                component_type=ComponentType.WORKER_PROCESS,
                status=AutomationStatus.ACTIVE,
                pid=process.pid,
                command=command,
                schedule=None,
                working_directory=working_dir or os.getcwd(),
                log_file=f"./logs/worker_{worker_id}.log",
                last_seen=datetime.now(),
                start_time=datetime.now(),
                restart_count=0,
                health_check_endpoint=None,
                dependencies=[],
                compatibility_level=CompatibilityLevel.FULL_COMPATIBLE
            )
            
            await self._register_component(component)
            
            logger.info(f"Worker started: {worker_id} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Worker start error: {e}")
            return False
    
    async def stop_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """ワーカープロセス停止"""
        try:
            if worker_id not in self.worker_processes:
                logger.warning(f"Worker {worker_id} not found")
                return False
            
            process = self.worker_processes[worker_id]
            
            if graceful:
                # 優雅な停止
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:
                # 強制停止
                process.kill()
            
            del self.worker_processes[worker_id]
            self.active_workers -= 1
            
            # コンポーネント状態更新
            component_id = f"worker_{worker_id}"
            if component_id in self.registered_components:
                self.registered_components[component_id].status = AutomationStatus.INACTIVE
                await self._register_component(self.registered_components[component_id])
            
            logger.info(f"Worker stopped: {worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Worker stop error: {e}")
            return False
    
    async def hotswap_component(self, component_id: str, new_version_path: str, 
                               rollback_on_failure: bool = True) -> HotSwapOperation:
        """ホットスワップ機能 - kiro要件6.4準拠"""
        async with self.hotswap_lock:
            operation_id = f"hotswap_{int(time.time())}"
            
            try:
                logger.info(f"Starting hotswap operation: {operation_id} for {component_id}")
                
                if component_id not in self.registered_components:
                    raise ValueError(f"Component {component_id} not registered")
                
                component = self.registered_components[component_id]
                old_version = component.command
                
                operation = HotSwapOperation(
                    operation_id=operation_id,
                    target_component=component_id,
                    operation_type="REPLACE",
                    old_version=old_version,
                    new_version=new_version_path,
                    start_time=datetime.now(),
                    completion_time=None,
                    success=False,
                    rollback_available=rollback_on_failure,
                    error_message=None
                )
                
                # 1. 新バージョンのバックアップ作成
                backup_path = f"{new_version_path}.backup_{int(time.time())}"
                if os.path.exists(component.command):
                    shutil.copy2(component.command, backup_path)
                
                # 2. 現在のプロセス停止（該当する場合）
                if component.component_type == ComponentType.WORKER_PROCESS and component.pid:
                    try:
                        os.kill(component.pid, signal.SIGTERM)
                        time.sleep(2)  # 優雅な停止を待機
                    except ProcessLookupError:
                        pass  # プロセスが既に停止している
                
                # 3. 新バージョンのデプロイ
                shutil.copy2(new_version_path, component.command)
                os.chmod(component.command, 0o755)  # 実行権限付与
                
                # 4. 新バージョンでプロセス再開
                if component.component_type == ComponentType.WORKER_PROCESS:
                    process = subprocess.Popen(
                        component.command.split(),
                        cwd=component.working_directory,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    component.pid = process.pid
                    component.restart_count += 1
                
                # 5. 健全性チェック
                await asyncio.sleep(5)  # 起動待機
                health_ok = await self._verify_component_health(component_id)
                
                if health_ok:
                    operation.success = True
                    operation.completion_time = datetime.now()
                    logger.info(f"Hotswap completed successfully: {operation_id}")
                    
                    # バックアップファイル削除
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                else:
                    # 失敗時のロールバック
                    if rollback_on_failure and os.path.exists(backup_path):
                        shutil.copy2(backup_path, component.command)
                        logger.warning(f"Hotswap failed, rolled back: {operation_id}")
                        operation.error_message = "Health check failed after deployment"
                    else:
                        operation.error_message = "Health check failed, no rollback"
                
                # コンポーネント状態更新
                component.last_seen = datetime.now()
                await self._register_component(component)
                
                # 操作履歴保存
                self.hotswap_operations[operation_id] = operation
                await self._save_hotswap_operation(operation)
                
                return operation
                
            except Exception as e:
                logger.error(f"Hotswap operation error: {e}")
                operation.error_message = str(e)
                operation.completion_time = datetime.now()
                await self._save_hotswap_operation(operation)
                return operation
    
    async def _verify_component_health(self, component_id: str) -> bool:
        """コンポーネント健全性確認"""
        try:
            if component_id not in self.registered_components:
                return False
            
            component = self.registered_components[component_id]
            
            # プロセス存在確認
            if component.pid:
                try:
                    os.kill(component.pid, 0)  # プロセス存在確認
                    return True
                except ProcessLookupError:
                    return False
            
            # cronジョブの場合は常にTrue（スケジュール実行のため）
            if component.component_type == ComponentType.CRON_JOB:
                return True
            
            # その他のケース
            return component.status == AutomationStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Component health verification error: {e}")
            return False
    
    async def _save_hotswap_operation(self, operation: HotSwapOperation):
        """ホットスワップ操作履歴保存"""
        try:
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                await conn.execute('''
                    INSERT INTO hotswap_operations (
                        operation_id, target_component, operation_type, old_version,
                        new_version, start_time, completion_time, success,
                        rollback_available, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    operation.operation_id, operation.target_component, operation.operation_type,
                    operation.old_version, operation.new_version, operation.start_time.isoformat(),
                    operation.completion_time.isoformat() if operation.completion_time else None,
                    operation.success, operation.rollback_available, operation.error_message
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Hotswap operation save error: {e}")
    
    async def _start_monitoring(self):
        """監視開始"""
        try:
            if self.monitoring_enabled:
                self.monitor_task = asyncio.create_task(self._monitor_automation_system())
                logger.info("Automation system monitoring started")
            
        except Exception as e:
            logger.error(f"Monitoring start error: {e}")
    
    async def _monitor_automation_system(self):
        """自動化システム監視"""
        while self.monitoring_enabled:
            try:
                # 各コンポーネントの健全性チェック
                for component_id in list(self.registered_components.keys()):
                    health_ok = await self._verify_component_health(component_id)
                    
                    if not health_ok:
                        logger.warning(f"Component health issue detected: {component_id}")
                        
                        # 必要に応じて自動復旧
                        component = self.registered_components[component_id]
                        if component.component_type == ComponentType.WORKER_PROCESS:
                            logger.info(f"Attempting auto-recovery for: {component_id}")
                            await self._attempt_component_recovery(component_id)
                
                # ワーカープール状態チェック
                if self.active_workers < self.max_workers:
                    logger.debug(f"Worker pool status: {self.active_workers}/{self.max_workers}")
                
                await asyncio.sleep(self.monitor_interval_seconds)
                
            except Exception as e:
                logger.error(f"Automation monitoring error: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def _attempt_component_recovery(self, component_id: str):
        """コンポーネント自動復旧"""
        try:
            if component_id not in self.registered_components:
                return False
            
            component = self.registered_components[component_id]
            
            if component.component_type == ComponentType.WORKER_PROCESS:
                # ワーカープロセス再起動
                logger.info(f"Restarting worker process: {component_id}")
                
                # 既存プロセス強制停止
                if component.pid:
                    try:
                        os.kill(component.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                
                # 新プロセス開始
                process = subprocess.Popen(
                    component.command.split(),
                    cwd=component.working_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                component.pid = process.pid
                component.restart_count += 1
                component.status = AutomationStatus.ACTIVE
                component.last_seen = datetime.now()
                
                await self._register_component(component)
                
                logger.info(f"Component recovery completed: {component_id} (new PID: {process.pid})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Component recovery error: {e}")
            return False
    
    async def get_automation_status(self) -> Dict[str, Any]:
        """自動化システム状態取得"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'operating_hours': self.operating_hours,
                'within_operating_hours': await self._verify_operating_hours(),
                'max_workers': self.max_workers,
                'active_workers': self.active_workers,
                'registered_components': len(self.registered_components),
                'components_by_type': {},
                'components_by_status': {},
                'recent_hotswap_operations': []
            }
            
            # コンポーネント種別統計
            for component in self.registered_components.values():
                comp_type = component.component_type.value
                status['components_by_type'][comp_type] = status['components_by_type'].get(comp_type, 0) + 1
                
                comp_status = component.status.value
                status['components_by_status'][comp_status] = status['components_by_status'].get(comp_status, 0) + 1
            
            # 最近のホットスワップ操作
            recent_ops = sorted(self.hotswap_operations.values(), 
                              key=lambda x: x.start_time, reverse=True)[:5]
            status['recent_hotswap_operations'] = [
                {
                    'operation_id': op.operation_id,
                    'target_component': op.target_component,
                    'operation_type': op.operation_type,
                    'success': op.success,
                    'start_time': op.start_time.isoformat()
                }
                for op in recent_ops
            ]
            
            return status
            
        except Exception as e:
            logger.error(f"Automation status retrieval error: {e}")
            return {}
    
    async def stop(self):
        """自動化互換性マネージャー停止"""
        logger.info("Stopping Automation Compatibility Manager...")
        
        try:
            # 監視停止
            self.monitoring_enabled = False
            if self.monitor_task:
                self.monitor_task.cancel()
            
            # ワーカープロセス停止
            for worker_id in list(self.worker_processes.keys()):
                await self.stop_worker(worker_id, graceful=True)
            
            logger.info("Automation Compatibility Manager stopped successfully")
            
        except Exception as e:
            logger.error(f"Automation Compatibility Manager stop error: {e}")

# テスト関数
async def test_automation_compatibility():
    """自動化互換性テスト"""
    print("🧪 Automation Compatibility Test Starting...")
    
    # 依存システム初期化（モック）
    from database_manager import DatabaseManager
    
    db_manager = DatabaseManager("./test_automation.db")
    await db_manager.initialize()
    
    # 自動化互換性マネージャー初期化
    compat_manager = AutomationCompatibilityManager(db_manager)
    await compat_manager.initialize()
    
    try:
        # 自動化システム状態取得テスト
        status = await compat_manager.get_automation_status()
        print(f"✅ Automation status: {status['registered_components']} components")
        
        # ワーカー開始テスト
        success = await compat_manager.start_worker("test_worker", "echo 'test worker'")
        print(f"✅ Worker start test: {'SUCCESS' if success else 'FAILED'}")
        
        # ワーカー停止テスト
        if success:
            success = await compat_manager.stop_worker("test_worker")
            print(f"✅ Worker stop test: {'SUCCESS' if success else 'FAILED'}")
        
        print("✅ Automation Compatibility Test Completed")
        
    finally:
        await compat_manager.stop()
        await db_manager.stop()

if __name__ == "__main__":
    asyncio.run(test_automation_compatibility())