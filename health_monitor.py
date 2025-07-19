#!/usr/bin/env python3
"""
Phase 4.3: Comprehensive Monitoring System
kiro設計tasks.md:143-149準拠 - 包括的監視システム・HealthMonitor・ダッシュボード

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 2.1, 2.2, 2.4 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import logging
import aiosqlite
import time
import psutil
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import sys
from pathlib import Path
import threading
import queue
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, CONFIG
from position_management import PositionTracker
from risk_management import RiskManager
from emergency_protection import EmergencyProtectionSystem
from database_manager import DatabaseManager
from system_state_manager import SystemStateManager

# ログ設定
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """健全性状態"""
    EXCELLENT = "EXCELLENT"    # 95%+
    GOOD = "GOOD"             # 80-94%
    FAIR = "FAIR"             # 60-79%
    POOR = "POOR"             # 40-59%
    CRITICAL = "CRITICAL"     # <40%

class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ComponentType(Enum):
    """コンポーネント種別"""
    CORE_SERVICE = "CORE_SERVICE"
    COMMUNICATION = "COMMUNICATION"
    DATABASE = "DATABASE"
    MONITORING = "MONITORING"
    EMERGENCY = "EMERGENCY"

@dataclass
class HealthMetric:
    """健全性指標"""
    metric_name: str
    current_value: float
    threshold_warning: float
    threshold_critical: float
    unit: str
    timestamp: datetime
    trend: str  # IMPROVING, STABLE, DEGRADING

@dataclass
class SystemAlert:
    """システムアラート"""
    alert_id: str
    timestamp: datetime
    component: str
    alert_level: AlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    auto_resolved: bool
    resolution_time: Optional[datetime]

@dataclass
class ComponentHealth:
    """コンポーネント健全性"""
    component_name: str
    component_type: ComponentType
    health_status: HealthStatus
    health_score: float
    last_check: datetime
    metrics: List[HealthMetric]
    active_alerts: List[SystemAlert]
    uptime_seconds: float
    error_count_24h: int

class DashboardServer:
    """リアルタイム監視ダッシュボードサーバー"""
    
    def __init__(self, health_monitor, port: int = 8080):
        self.health_monitor = health_monitor
        self.port = port
        self.server = None
        self.server_thread = None
        self.is_running = False
    
    def start(self):
        """ダッシュボードサーバー開始"""
        try:
            self.server = HTTPServer(('localhost', self.port), self._create_request_handler())
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.is_running = True
            logger.info(f"Dashboard server started on http://localhost:{self.port}")
            
        except Exception as e:
            logger.error(f"Dashboard server start error: {e}")
    
    def stop(self):
        """ダッシュボードサーバー停止"""
        if self.server:
            self.server.shutdown()
            self.is_running = False
            logger.info("Dashboard server stopped")
    
    def _create_request_handler(self):
        """リクエストハンドラー作成"""
        health_monitor = self.health_monitor
        
        class DashboardHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == '/':
                        self._serve_dashboard()
                    elif self.path == '/api/health':
                        self._serve_health_api()
                    elif self.path == '/api/metrics':
                        self._serve_metrics_api()
                    elif self.path == '/api/alerts':
                        self._serve_alerts_api()
                    else:
                        self._serve_404()
                        
                except Exception as e:
                    logger.error(f"Dashboard request error: {e}")
                    self._serve_500()
            
            def _serve_dashboard(self):
                """ダッシュボードHTML提供"""
                html_content = self._generate_dashboard_html()
                self._send_response(200, html_content, 'text/html')
            
            def _serve_health_api(self):
                """健全性API提供"""
                health_data = asyncio.run(health_monitor.get_system_health_summary())
                self._send_response(200, json.dumps(health_data, default=str), 'application/json')
            
            def _serve_metrics_api(self):
                """指標API提供"""
                metrics_data = asyncio.run(health_monitor.get_current_metrics())
                self._send_response(200, json.dumps(metrics_data, default=str), 'application/json')
            
            def _serve_alerts_api(self):
                """アラートAPI提供"""
                alerts_data = asyncio.run(health_monitor.get_active_alerts())
                self._send_response(200, json.dumps(alerts_data, default=str), 'application/json')
            
            def _serve_404(self):
                self._send_response(404, "Not Found", 'text/plain')
            
            def _serve_500(self):
                self._send_response(500, "Internal Server Error", 'text/plain')
            
            def _send_response(self, status_code: int, content: str, content_type: str):
                self.send_response(status_code)
                self.send_header('Content-type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode())
            
            def _generate_dashboard_html(self) -> str:
                """ダッシュボードHTML生成"""
                return """
<!DOCTYPE html>
<html>
<head>
    <title>Trading System Health Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .status-card { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .status-excellent { border-left: 5px solid #27ae60; }
        .status-good { border-left: 5px solid #f39c12; }
        .status-fair { border-left: 5px solid #e67e22; }
        .status-poor { border-left: 5px solid #e74c3c; }
        .status-critical { border-left: 5px solid #c0392b; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        .alert { padding: 10px; margin: 5px 0; border-radius: 3px; }
        .alert-info { background: #d1ecf1; border: 1px solid #bee5eb; }
        .alert-warning { background: #fff3cd; border: 1px solid #ffeaa7; }
        .alert-error { background: #f8d7da; border: 1px solid #f5c6cb; }
        .alert-critical { background: #f8d7da; border: 1px solid #f5c6cb; font-weight: bold; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 3px; cursor: pointer; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Trading System Health Monitor</h1>
            <p>Real-time monitoring and health dashboard</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>
        
        <div id="health-status">
            <h2>System Components Health</h2>
            <div id="components-grid" class="status-grid">
                Loading...
            </div>
        </div>
        
        <div id="active-alerts">
            <h2>🚨 Active Alerts</h2>
            <div id="alerts-container">
                Loading...
            </div>
        </div>
        
        <div id="metrics-summary">
            <h2>📊 Key Metrics</h2>
            <div id="metrics-container">
                Loading...
            </div>
        </div>
    </div>

    <script>
        async function loadHealthData() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                updateComponentsGrid(data.components || {});
            } catch (error) {
                console.error('Failed to load health data:', error);
            }
        }
        
        async function loadAlertsData() {
            try {
                const response = await fetch('/api/alerts');
                const data = await response.json();
                updateAlertsContainer(data);
            } catch (error) {
                console.error('Failed to load alerts data:', error);
            }
        }
        
        async function loadMetricsData() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                updateMetricsContainer(data);
            } catch (error) {
                console.error('Failed to load metrics data:', error);
            }
        }
        
        function updateComponentsGrid(components) {
            const grid = document.getElementById('components-grid');
            grid.innerHTML = '';
            
            for (const [name, component] of Object.entries(components)) {
                const card = document.createElement('div');
                card.className = `status-card status-${component.health_status.toLowerCase()}`;
                card.innerHTML = `
                    <h3>${name}</h3>
                    <div class="metric">
                        <span>Status:</span>
                        <span>${component.health_status}</span>
                    </div>
                    <div class="metric">
                        <span>Score:</span>
                        <span>${(component.health_score * 100).toFixed(1)}%</span>
                    </div>
                    <div class="metric">
                        <span>Uptime:</span>
                        <span>${formatUptime(component.uptime_seconds)}</span>
                    </div>
                    <div class="metric">
                        <span>Errors (24h):</span>
                        <span>${component.error_count_24h}</span>
                    </div>
                `;
                grid.appendChild(card);
            }
        }
        
        function updateAlertsContainer(alerts) {
            const container = document.getElementById('alerts-container');
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<p style="color: #27ae60;">✅ No active alerts</p>';
                return;
            }
            
            container.innerHTML = '';
            alerts.forEach(alert => {
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${alert.alert_level.toLowerCase()}`;
                alertDiv.innerHTML = `
                    <strong>${alert.component}</strong> - ${alert.message}
                    <div class="timestamp">${new Date(alert.timestamp).toLocaleString()}</div>
                `;
                container.appendChild(alertDiv);
            });
        }
        
        function updateMetricsContainer(metrics) {
            const container = document.getElementById('metrics-container');
            container.innerHTML = '';
            
            for (const [category, categoryMetrics] of Object.entries(metrics)) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'status-card';
                categoryDiv.innerHTML = `<h3>${category}</h3>`;
                
                for (const [metricName, value] of Object.entries(categoryMetrics)) {
                    const metricDiv = document.createElement('div');
                    metricDiv.className = 'metric';
                    metricDiv.innerHTML = `
                        <span>${metricName}:</span>
                        <span>${formatMetricValue(value)}</span>
                    `;
                    categoryDiv.appendChild(metricDiv);
                }
                
                container.appendChild(categoryDiv);
            }
        }
        
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
        
        function formatMetricValue(value) {
            if (typeof value === 'number') {
                return value.toFixed(2);
            }
            return value;
        }
        
        // 初期ロード
        loadHealthData();
        loadAlertsData();
        loadMetricsData();
        
        // 自動更新（30秒間隔）
        setInterval(() => {
            loadHealthData();
            loadAlertsData();
            loadMetricsData();
        }, 30000);
    </script>
</body>
</html>
                """
            
            def log_message(self, format, *args):
                # ログ出力を抑制
                pass
        
        return DashboardHandler

class HealthMonitor:
    """
    包括的健全性監視システム - kiro設計tasks.md:143-149準拠
    コンポーネント健全性チェック・可用性監視・パフォーマンス指標収集・アラート機能
    """
    
    def __init__(self, position_tracker: PositionTracker, risk_manager: RiskManager,
                 emergency_system: EmergencyProtectionSystem, db_manager: DatabaseManager,
                 state_manager: SystemStateManager):
        self.position_tracker = position_tracker
        self.risk_manager = risk_manager
        self.emergency_system = emergency_system
        self.db_manager = db_manager
        self.state_manager = state_manager
        
        # 設定読み込み
        self.config = CONFIG
        self.monitoring_config = self.config.get('monitoring', {})
        
        # 監視設定
        self.check_interval_seconds = self.monitoring_config.get('check_interval', 30)
        self.alert_thresholds = self.monitoring_config.get('alert_thresholds', {
            'cpu_usage_warning': 70.0,
            'cpu_usage_critical': 90.0,
            'memory_usage_warning': 80.0,
            'memory_usage_critical': 95.0,
            'disk_usage_warning': 85.0,
            'disk_usage_critical': 95.0,
            'error_rate_warning': 5.0,
            'error_rate_critical': 10.0,
            'latency_warning': 100.0,
            'latency_critical': 500.0
        })
        
        # 監視状態
        self.is_running = False
        self.monitoring_task = None
        self.alert_queue = asyncio.Queue()
        self.active_alerts: Dict[str, SystemAlert] = {}
        self.component_health: Dict[str, ComponentHealth] = {}
        self.metrics_history: Dict[str, List[HealthMetric]] = {}
        self.alert_callbacks: List[Callable] = []
        
        # ダッシュボード
        self.dashboard_server = DashboardServer(self, port=self.monitoring_config.get('dashboard_port', 8080))
        
        # パフォーマンス追跡
        self.start_time = time.time()
        self.error_counts: Dict[str, int] = {}
        self.latency_samples: List[float] = []
        
        logger.info("Health Monitor initialized")
    
    async def initialize(self):
        """健全性監視システム初期化"""
        logger.info("Initializing Health Monitor...")
        
        try:
            # 監視データベーステーブル初期化
            await self._initialize_monitoring_tables()
            
            # コンポーネント登録
            await self._register_components()
            
            # 監視タスク開始
            await self._start_monitoring_tasks()
            
            # ダッシュボード開始
            self.dashboard_server.start()
            
            self.is_running = True
            logger.info("Health Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Health Monitor initialization error: {e}")
            raise
    
    async def _initialize_monitoring_tables(self):
        """監視データベーステーブル初期化"""
        try:
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                # 健全性メトリクステーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS health_metrics (
                        metric_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        component_name TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        threshold_warning REAL,
                        threshold_critical REAL,
                        unit TEXT,
                        trend TEXT DEFAULT 'STABLE',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # システムアラートテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_alerts (
                        alert_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        component TEXT NOT NULL,
                        alert_level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        metric_name TEXT,
                        current_value REAL,
                        threshold_value REAL,
                        auto_resolved BOOLEAN DEFAULT 0,
                        resolution_time TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 可用性履歴テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS availability_history (
                        availability_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        component_name TEXT NOT NULL,
                        is_available BOOLEAN NOT NULL,
                        response_time_ms REAL,
                        error_message TEXT,
                        check_duration_ms REAL NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await conn.commit()
                logger.info("Monitoring tables initialized")
                
        except Exception as e:
            logger.error(f"Monitoring tables initialization error: {e}")
            raise
    
    async def _register_components(self):
        """監視対象コンポーネント登録"""
        try:
            components = {
                'position_tracker': ComponentType.CORE_SERVICE,
                'risk_manager': ComponentType.CORE_SERVICE,
                'emergency_system': ComponentType.EMERGENCY,
                'database_manager': ComponentType.DATABASE,
                'state_manager': ComponentType.MONITORING,
                'tcp_bridge': ComponentType.COMMUNICATION,
                'file_bridge': ComponentType.COMMUNICATION
            }
            
            for component_name, component_type in components.items():
                self.component_health[component_name] = ComponentHealth(
                    component_name=component_name,
                    component_type=component_type,
                    health_status=HealthStatus.GOOD,
                    health_score=1.0,
                    last_check=datetime.now(),
                    metrics=[],
                    active_alerts=[],
                    uptime_seconds=0.0,
                    error_count_24h=0
                )
            
            logger.info(f"Registered {len(components)} components for monitoring")
            
        except Exception as e:
            logger.error(f"Component registration error: {e}")
    
    async def _start_monitoring_tasks(self):
        """監視タスク開始"""
        try:
            # メイン監視ループ
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # アラート処理タスク
            asyncio.create_task(self._alert_processor())
            
            logger.info("Monitoring tasks started")
            
        except Exception as e:
            logger.error(f"Monitoring tasks start error: {e}")
    
    async def _monitoring_loop(self):
        """メイン監視ループ"""
        while self.is_running:
            try:
                # システムレベル監視
                await self._check_system_resources()
                
                # コンポーネント監視
                await self._check_component_health()
                
                # パフォーマンス監視
                await self._check_performance_metrics()
                
                # アラート評価
                await self._evaluate_alerts()
                
                # 可用性記録
                await self._record_availability()
                
                await asyncio.sleep(self.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    async def _check_system_resources(self):
        """システムリソース監視"""
        try:
            timestamp = datetime.now()
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            await self._record_metric("system", "cpu_usage_percent", cpu_percent, 
                                    self.alert_thresholds['cpu_usage_warning'],
                                    self.alert_thresholds['cpu_usage_critical'], "%", timestamp)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            await self._record_metric("system", "memory_usage_percent", memory_percent,
                                    self.alert_thresholds['memory_usage_warning'],
                                    self.alert_thresholds['memory_usage_critical'], "%", timestamp)
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            await self._record_metric("system", "disk_usage_percent", disk_percent,
                                    self.alert_thresholds['disk_usage_warning'],
                                    self.alert_thresholds['disk_usage_critical'], "%", timestamp)
            
            # ネットワーク統計
            network = psutil.net_io_counters()
            await self._record_metric("system", "network_bytes_sent", float(network.bytes_sent), 
                                    None, None, "bytes", timestamp)
            await self._record_metric("system", "network_bytes_recv", float(network.bytes_recv),
                                    None, None, "bytes", timestamp)
            
        except Exception as e:
            logger.error(f"System resources check error: {e}")
    
    async def _check_component_health(self):
        """コンポーネント健全性チェック"""
        try:
            timestamp = datetime.now()
            
            # Position Tracker
            if hasattr(self.position_tracker, 'is_running'):
                is_running = self.position_tracker.is_running
                await self._update_component_availability("position_tracker", is_running, timestamp)
                
                if is_running:
                    stats = self.position_tracker.get_statistics()
                    await self._record_metric("position_tracker", "active_positions", 
                                            float(stats.get('active_positions', 0)), None, None, "count", timestamp)
                    await self._record_metric("position_tracker", "total_pnl", 
                                            stats.get('total_pnl', 0.0), None, None, "USD", timestamp)
            
            # Risk Manager
            if hasattr(self.risk_manager, 'is_running'):
                is_running = self.risk_manager.is_running
                await self._update_component_availability("risk_manager", is_running, timestamp)
                
                if is_running:
                    risk_stats = self.risk_manager.get_risk_statistics()
                    await self._record_metric("risk_manager", "current_drawdown",
                                            risk_stats.get('current_drawdown', 0.0), 20.0, 30.0, "%", timestamp)
            
            # Emergency System
            if hasattr(self.emergency_system, 'is_running'):
                is_running = self.emergency_system.is_running
                await self._update_component_availability("emergency_system", is_running, timestamp)
                
                if is_running:
                    protection_status = self.emergency_system.get_protection_status()
                    emergency_count = protection_status.get('emergency_events_count', 0)
                    await self._record_metric("emergency_system", "emergency_events_count",
                                            float(emergency_count), 5.0, 10.0, "count", timestamp)
            
            # Database Manager
            if hasattr(self.db_manager, 'db_path'):
                db_available = Path(self.db_manager.db_path).exists()
                await self._update_component_availability("database_manager", db_available, timestamp)
                
                if db_available:
                    db_stats = await self.db_manager.get_system_statistics()
                    await self._record_metric("database_manager", "database_size_mb",
                                            db_stats.get('database_size_mb', 0.0), 500.0, 1000.0, "MB", timestamp)
            
        except Exception as e:
            logger.error(f"Component health check error: {e}")
    
    async def _check_performance_metrics(self):
        """パフォーマンス指標監視"""
        try:
            timestamp = datetime.now()
            
            # レイテンシ監視
            if self.latency_samples:
                avg_latency = sum(self.latency_samples) / len(self.latency_samples)
                max_latency = max(self.latency_samples)
                await self._record_metric("performance", "average_latency_ms", avg_latency,
                                        self.alert_thresholds['latency_warning'],
                                        self.alert_thresholds['latency_critical'], "ms", timestamp)
                await self._record_metric("performance", "max_latency_ms", max_latency,
                                        None, None, "ms", timestamp)
                
                # サンプルクリア
                self.latency_samples = self.latency_samples[-100:]  # 最新100件保持
            
            # エラー率監視
            total_errors = sum(self.error_counts.values())
            error_rate = (total_errors / max(1, self.check_interval_seconds)) * 100
            await self._record_metric("performance", "error_rate_percent", error_rate,
                                    self.alert_thresholds['error_rate_warning'],
                                    self.alert_thresholds['error_rate_critical'], "%", timestamp)
            
            # エラー数リセット
            self.error_counts = {}
            
        except Exception as e:
            logger.error(f"Performance metrics check error: {e}")
    
    async def _record_metric(self, component: str, metric_name: str, value: float,
                           warning_threshold: Optional[float], critical_threshold: Optional[float],
                           unit: str, timestamp: datetime):
        """メトリクス記録"""
        try:
            metric_id = f"{component}_{metric_name}_{int(timestamp.timestamp())}"
            
            # トレンド計算
            trend = self._calculate_metric_trend(component, metric_name, value)
            
            # メトリクスオブジェクト作成
            metric = HealthMetric(
                metric_name=f"{component}.{metric_name}",
                current_value=value,
                threshold_warning=warning_threshold or 0.0,
                threshold_critical=critical_threshold or 0.0,
                unit=unit,
                timestamp=timestamp,
                trend=trend
            )
            
            # 履歴に追加
            if component not in self.metrics_history:
                self.metrics_history[component] = []
            self.metrics_history[component].append(metric)
            
            # 履歴サイズ制限
            if len(self.metrics_history[component]) > 1000:
                self.metrics_history[component] = self.metrics_history[component][-1000:]
            
            # データベース記録
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                await conn.execute('''
                    INSERT INTO health_metrics (
                        metric_id, timestamp, component_name, metric_name,
                        metric_value, threshold_warning, threshold_critical,
                        unit, trend
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metric_id, timestamp.isoformat(), component, metric_name,
                    value, warning_threshold, critical_threshold, unit, trend
                ))
                await conn.commit()
            
        except Exception as e:
            logger.error(f"Metric recording error: {e}")
    
    def _calculate_metric_trend(self, component: str, metric_name: str, current_value: float) -> str:
        """メトリクストレンド計算"""
        try:
            if component in self.metrics_history:
                recent_metrics = [m for m in self.metrics_history[component] 
                                if m.metric_name.endswith(metric_name)][-5:]  # 最新5件
                
                if len(recent_metrics) >= 3:
                    values = [m.current_value for m in recent_metrics]
                    avg_old = sum(values[:2]) / 2
                    avg_new = sum(values[-2:]) / 2
                    
                    if avg_new > avg_old * 1.1:
                        return "IMPROVING" if metric_name.endswith("score") else "DEGRADING"
                    elif avg_new < avg_old * 0.9:
                        return "DEGRADING" if metric_name.endswith("score") else "IMPROVING"
            
            return "STABLE"
            
        except Exception:
            return "STABLE"
    
    async def _update_component_availability(self, component_name: str, is_available: bool, timestamp: datetime):
        """コンポーネント可用性更新"""
        try:
            # 可用性記録
            availability_id = f"{component_name}_availability_{int(timestamp.timestamp())}"
            
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                await conn.execute('''
                    INSERT INTO availability_history (
                        availability_id, timestamp, component_name, is_available,
                        check_duration_ms
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    availability_id, timestamp.isoformat(), component_name,
                    is_available, 50.0  # 簡略実装
                ))
                await conn.commit()
            
            # コンポーネント健全性更新
            if component_name in self.component_health:
                component = self.component_health[component_name]
                component.last_check = timestamp
                
                if is_available:
                    component.uptime_seconds = time.time() - self.start_time
                    component.health_score = min(1.0, component.health_score + 0.1)
                else:
                    component.health_score = max(0.0, component.health_score - 0.3)
                
                # 健全性状態更新
                if component.health_score >= 0.95:
                    component.health_status = HealthStatus.EXCELLENT
                elif component.health_score >= 0.8:
                    component.health_status = HealthStatus.GOOD
                elif component.health_score >= 0.6:
                    component.health_status = HealthStatus.FAIR
                elif component.health_score >= 0.4:
                    component.health_status = HealthStatus.POOR
                else:
                    component.health_status = HealthStatus.CRITICAL
            
        except Exception as e:
            logger.error(f"Component availability update error: {e}")
    
    async def _evaluate_alerts(self):
        """アラート評価・生成"""
        try:
            timestamp = datetime.now()
            
            # 各コンポーネントの最新メトリクスをチェック
            for component_name, metrics_list in self.metrics_history.items():
                if not metrics_list:
                    continue
                
                latest_metrics = metrics_list[-1:]  # 最新のメトリクス
                
                for metric in latest_metrics:
                    # クリティカルアラート
                    if (metric.threshold_critical > 0 and 
                        metric.current_value >= metric.threshold_critical):
                        await self._create_alert(
                            component_name, AlertLevel.CRITICAL, 
                            f"Critical threshold exceeded: {metric.metric_name} = {metric.current_value:.2f}{metric.unit}",
                            metric.metric_name, metric.current_value, metric.threshold_critical
                        )
                    
                    # 警告アラート
                    elif (metric.threshold_warning > 0 and 
                          metric.current_value >= metric.threshold_warning):
                        await self._create_alert(
                            component_name, AlertLevel.WARNING,
                            f"Warning threshold exceeded: {metric.metric_name} = {metric.current_value:.2f}{metric.unit}",
                            metric.metric_name, metric.current_value, metric.threshold_warning
                        )
            
            # 古いアラートの自動解決
            await self._auto_resolve_alerts()
            
        except Exception as e:
            logger.error(f"Alert evaluation error: {e}")
    
    async def _create_alert(self, component: str, level: AlertLevel, message: str,
                          metric_name: str, current_value: float, threshold_value: float):
        """アラート作成"""
        try:
            alert_id = f"alert_{component}_{metric_name}_{int(time.time())}"
            
            alert = SystemAlert(
                alert_id=alert_id,
                timestamp=datetime.now(),
                component=component,
                alert_level=level,
                message=message,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                auto_resolved=False,
                resolution_time=None
            )
            
            # 重複チェック
            existing_key = f"{component}_{metric_name}_{level.value}"
            if existing_key not in self.active_alerts:
                self.active_alerts[existing_key] = alert
                
                # アラートキューに追加
                await self.alert_queue.put(alert)
                
                # データベース記録
                await self._save_alert_to_db(alert)
                
                logger.warning(f"Alert created: {alert.component} - {alert.message}")
                
        except Exception as e:
            logger.error(f"Alert creation error: {e}")
    
    async def _auto_resolve_alerts(self):
        """古いアラート自動解決"""
        try:
            current_time = datetime.now()
            resolved_alerts = []
            
            for key, alert in self.active_alerts.items():
                # 15分以上経過したアラートを自動解決
                if (current_time - alert.timestamp).total_seconds() > 900:
                    alert.auto_resolved = True
                    alert.resolution_time = current_time
                    resolved_alerts.append(key)
                    
                    # データベース更新
                    async with aiosqlite.connect(self.db_manager.db_path) as conn:
                        await conn.execute('''
                            UPDATE system_alerts 
                            SET auto_resolved = 1, resolution_time = ?
                            WHERE alert_id = ?
                        ''', (current_time.isoformat(), alert.alert_id))
                        await conn.commit()
            
            # 解決済みアラート削除
            for key in resolved_alerts:
                del self.active_alerts[key]
            
        except Exception as e:
            logger.error(f"Auto resolve alerts error: {e}")
    
    async def _save_alert_to_db(self, alert: SystemAlert):
        """アラートデータベース保存"""
        try:
            async with aiosqlite.connect(self.db_manager.db_path) as conn:
                await conn.execute('''
                    INSERT INTO system_alerts (
                        alert_id, timestamp, component, alert_level, message,
                        metric_name, current_value, threshold_value, auto_resolved
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert.alert_id, alert.timestamp.isoformat(), alert.component,
                    alert.alert_level.value, alert.message, alert.metric_name,
                    alert.current_value, alert.threshold_value, alert.auto_resolved
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Alert database save error: {e}")
    
    async def _alert_processor(self):
        """アラート処理タスク"""
        while self.is_running:
            try:
                alert = await self.alert_queue.get()
                
                # アラートコールバック実行
                for callback in self.alert_callbacks:
                    try:
                        await callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
                
                # クリティカルアラートの場合は緊急システムに通知
                if alert.alert_level == AlertLevel.CRITICAL:
                    logger.critical(f"CRITICAL ALERT: {alert.component} - {alert.message}")
                    # 必要に応じて緊急停止トリガー
                
            except Exception as e:
                logger.error(f"Alert processor error: {e}")
                await asyncio.sleep(1)
    
    async def _record_availability(self):
        """可用性記録"""
        try:
            # 簡略実装 - 全コンポーネントの可用性スコア計算
            total_score = 0.0
            component_count = len(self.component_health)
            
            for component in self.component_health.values():
                total_score += component.health_score
            
            availability_score = total_score / max(1, component_count)
            
            await self._record_metric("system", "availability_score", availability_score,
                                    0.8, 0.6, "score", datetime.now())
            
        except Exception as e:
            logger.error(f"Availability recording error: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """アラートコールバック追加"""
        self.alert_callbacks.append(callback)
    
    def record_latency(self, latency_ms: float):
        """レイテンシ記録"""
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > 1000:
            self.latency_samples = self.latency_samples[-1000:]
    
    def record_error(self, component: str):
        """エラー記録"""
        if component not in self.error_counts:
            self.error_counts[component] = 0
        self.error_counts[component] += 1
    
    async def get_system_health_summary(self) -> Dict[str, Any]:
        """システム健全性サマリー取得"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': self._calculate_overall_status(),
                'components': {name: {
                    'health_status': comp.health_status.value,
                    'health_score': comp.health_score,
                    'uptime_seconds': comp.uptime_seconds,
                    'error_count_24h': comp.error_count_24h,
                    'last_check': comp.last_check.isoformat()
                } for name, comp in self.component_health.items()},
                'active_alerts_count': len(self.active_alerts),
                'monitoring_uptime_seconds': time.time() - self.start_time
            }
            
        except Exception as e:
            logger.error(f"System health summary error: {e}")
            return {}
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """現在のメトリクス取得"""
        try:
            metrics_summary = {}
            
            for component, metrics_list in self.metrics_history.items():
                if metrics_list:
                    latest_metrics = metrics_list[-5:]  # 最新5件
                    component_metrics = {}
                    
                    for metric in latest_metrics:
                        metric_key = metric.metric_name.split('.')[-1]
                        component_metrics[metric_key] = metric.current_value
                    
                    metrics_summary[component] = component_metrics
            
            return metrics_summary
            
        except Exception as e:
            logger.error(f"Current metrics error: {e}")
            return {}
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """アクティブアラート取得"""
        try:
            return [asdict(alert) for alert in self.active_alerts.values()]
            
        except Exception as e:
            logger.error(f"Active alerts error: {e}")
            return []
    
    def _calculate_overall_status(self) -> str:
        """全体状態計算"""
        if not self.component_health:
            return "UNKNOWN"
        
        critical_count = sum(1 for comp in self.component_health.values() 
                           if comp.health_status == HealthStatus.CRITICAL)
        poor_count = sum(1 for comp in self.component_health.values() 
                        if comp.health_status == HealthStatus.POOR)
        
        if critical_count > 0:
            return "CRITICAL"
        elif poor_count > len(self.component_health) * 0.3:
            return "DEGRADED"
        else:
            return "HEALTHY"
    
    async def stop(self):
        """健全性監視システム停止"""
        logger.info("Stopping Health Monitor...")
        
        try:
            self.is_running = False
            
            # 監視タスク停止
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            # ダッシュボード停止
            self.dashboard_server.stop()
            
            logger.info("Health Monitor stopped successfully")
            
        except Exception as e:
            logger.error(f"Health Monitor stop error: {e}")

# テスト関数
async def test_health_monitor():
    """健全性監視システムテスト"""
    print("🧪 Health Monitor Test Starting...")
    
    # 依存システム初期化（モック）
    from position_management import PositionTracker
    from risk_management import RiskManager, RiskParameters
    from emergency_protection import EmergencyProtectionSystem
    from database_manager import DatabaseManager
    from system_state_manager import SystemStateManager
    
    db_manager = DatabaseManager("./test_health_monitor.db")
    await db_manager.initialize()
    
    position_tracker = PositionTracker()
    await position_tracker.initialize()
    
    risk_manager = RiskManager(position_tracker, RiskParameters())
    await risk_manager.initialize()
    
    emergency_system = EmergencyProtectionSystem(position_tracker, risk_manager)
    await emergency_system.initialize()
    
    state_manager = SystemStateManager(position_tracker, risk_manager, emergency_system, db_manager)
    await state_manager.initialize()
    
    # 健全性監視初期化
    health_monitor = HealthMonitor(position_tracker, risk_manager, emergency_system, db_manager, state_manager)
    await health_monitor.initialize()
    
    try:
        # 監視テスト
        print("🔍 Running health checks...")
        await asyncio.sleep(5)  # 数秒間監視実行
        
        # 健全性サマリー取得
        health_summary = await health_monitor.get_system_health_summary()
        print(f"✅ Health summary: {health_summary['overall_status']}")
        
        # メトリクス取得
        metrics = await health_monitor.get_current_metrics()
        print(f"✅ Metrics collected: {len(metrics)} components")
        
        # アラート取得
        alerts = await health_monitor.get_active_alerts()
        print(f"✅ Active alerts: {len(alerts)}")
        
        print("✅ Health Monitor Test Completed")
        print(f"💻 Dashboard available at: http://localhost:8080")
        
    finally:
        await health_monitor.stop()
        await state_manager.stop()
        await emergency_system.stop()
        await risk_manager.stop()
        await position_tracker.stop()
        await db_manager.stop()

if __name__ == "__main__":
    asyncio.run(test_health_monitor())