#!/usr/bin/env python3
"""
共通設定管理モジュール - リファクタリング後
全Phaseで使用する共通設定・ユーティリティ関数

主要機能:
- 設定ファイル統一管理
- 共通ユーティリティ関数
- データベース接続統一
- ログ設定統一
"""

import asyncio
import logging
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DatabaseConfig:
    """データベース設定"""
    path: str
    backup_enabled: bool = True
    cleanup_days: int = 30
    
@dataclass 
class CommunicationConfig:
    """通信設定"""
    tcp_host: str = "localhost"
    tcp_port: int = 9090
    signal_tcp_port: int = 9090
    file_bridge_dir: str = "/mnt/c/MT4_Bridge"
    timeout_ms: int = 5000

@dataclass
class TradingConfig:
    """取引設定"""
    lookback_period: int = 20
    breakout_threshold: float = 2.0
    volume_filter: bool = True
    atr_period: int = 14
    min_volume_ratio: float = 1.5

@dataclass
class SystemConfig:
    """システム全体設定"""
    database: DatabaseConfig
    communication: CommunicationConfig
    trading: TradingConfig
    environment: str = "development"
    log_level: str = "INFO"
    
def load_unified_config(config_path: Optional[str] = None) -> SystemConfig:
    """統一設定ロード"""
    if config_path is None:
        config_path = "config.yaml"
    
    # デフォルト設定
    default_config = {
        'database': {
            'path': './trading_system.db',
            'backup_enabled': True,
            'cleanup_days': 30
        },
        'communication': {
            'tcp_host': 'localhost',
            'tcp_port': 9090,
            'signal_tcp_port': 9090,
            'file_bridge_dir': '/mnt/c/MT4_Bridge',
            'timeout_ms': 5000
        },
        'trading': {
            'lookback_period': 20,
            'breakout_threshold': 2.0,
            'volume_filter': True,
            'atr_period': 14,
            'min_volume_ratio': 1.5
        },
        'environment': 'development',
        'log_level': 'INFO'
    }
    
    # 設定ファイル読み込み
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                
            # デフォルト設定をファイル設定でオーバーライド
            def merge_config(default: dict, override: dict) -> dict:
                result = default.copy()
                for key, value in override.items():
                    if isinstance(value, dict) and key in result:
                        result[key] = merge_config(result[key], value)
                    else:
                        result[key] = value
                return result
                
            config_dict = merge_config(default_config, file_config)
        else:
            config_dict = default_config
            
    except Exception as e:
        logging.warning(f"設定ファイル読み込みエラー: {e}. デフォルト設定使用")
        config_dict = default_config
    
    # 設定オブジェクト作成
    return SystemConfig(
        database=DatabaseConfig(**config_dict['database']),
        communication=CommunicationConfig(**config_dict['communication']),
        trading=TradingConfig(**config_dict['trading']),
        environment=config_dict['environment'],
        log_level=config_dict['log_level']
    )

def setup_unified_logging(config: SystemConfig, module_name: str) -> logging.Logger:
    """統一ログ設定"""
    logger = logging.getLogger(module_name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.log_level))
    
    return logger

async def get_unified_database_connection(config: SystemConfig):
    """統一データベース接続"""
    import aiosqlite
    return await aiosqlite.connect(config.database.path)

def format_timestamp(dt: Optional[datetime] = None) -> str:
    """統一タイムスタンプ形式"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def validate_symbol(symbol: str) -> bool:
    """通貨ペア検証"""
    valid_symbols = [
        'EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'AUDUSD', 'USDCAD',
        'NZDUSD', 'EURJPY', 'GBPJPY', 'CHFJPY', 'AUDJPY', 'CADJPY',
        'EURGBP', 'EURAUD', 'EURCHF', 'EURCAD', 'GBPAUD', 'GBPCHF'
    ]
    return symbol.upper() in valid_symbols

def calculate_pip_value(symbol: str, lot_size: float = 0.1) -> float:
    """pip値計算"""
    pip_values = {
        'USDJPY': 0.01,    # 100単位通貨
        'EURJPY': 0.01,
        'GBPJPY': 0.01,
        'CHFJPY': 0.01,
        'AUDJPY': 0.01,
        'CADJPY': 0.01,
    }
    
    # デフォルトは0.0001（4桁通貨ペア）
    base_pip = pip_values.get(symbol.upper(), 0.0001)
    return base_pip * lot_size * 10000  # 標準ロットサイズ調整

class PerformanceMonitor:
    """統一パフォーマンス監視"""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {}
    
    def start_timing(self, operation: str):
        """計測開始"""
        self.start_time = datetime.now()
        self.metrics[operation] = {'start': self.start_time}
    
    def end_timing(self, operation: str) -> float:
        """計測終了（ミリ秒）"""
        if operation in self.metrics and self.start_time:
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds() * 1000
            self.metrics[operation]['end'] = end_time
            self.metrics[operation]['duration_ms'] = duration
            return duration
        return 0.0
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクス取得"""
        return self.metrics.copy()

# グローバル設定インスタンス
GLOBAL_CONFIG = load_unified_config()
GLOBAL_LOGGER = setup_unified_logging(GLOBAL_CONFIG, 'trading_system')

# 下位互換性のためのレガシー設定
CONFIG = {
    'database_path': GLOBAL_CONFIG.database.path,
    'communication': {
        'tcp_host': GLOBAL_CONFIG.communication.tcp_host,
        'tcp_port': GLOBAL_CONFIG.communication.tcp_port,
        'signal_tcp_port': GLOBAL_CONFIG.communication.signal_tcp_port,
        'file_bridge_dir': GLOBAL_CONFIG.communication.file_bridge_dir,
        'timeout_ms': GLOBAL_CONFIG.communication.timeout_ms
    },
    'trading': {
        'lookback_period': GLOBAL_CONFIG.trading.lookback_period,
        'breakout_threshold': GLOBAL_CONFIG.trading.breakout_threshold,
        'volume_filter': GLOBAL_CONFIG.trading.volume_filter,
        'atr_period': GLOBAL_CONFIG.trading.atr_period,
        'min_volume_ratio': GLOBAL_CONFIG.trading.min_volume_ratio
    },
    'environment': GLOBAL_CONFIG.environment,
    'log_level': GLOBAL_CONFIG.log_level
}

if __name__ == "__main__":
    # 設定テスト
    print("統一設定システムテスト")
    print(f"データベース: {GLOBAL_CONFIG.database.path}")
    print(f"通信ホスト: {GLOBAL_CONFIG.communication.tcp_host}")
    print(f"取引設定: {GLOBAL_CONFIG.trading}")
    print(f"環境: {GLOBAL_CONFIG.environment}")
    
    # パフォーマンス監視テスト
    monitor = PerformanceMonitor()
    monitor.start_timing("test_operation")
    import time
    time.sleep(0.1)
    duration = monitor.end_timing("test_operation")
    print(f"テスト操作時間: {duration:.2f}ms")