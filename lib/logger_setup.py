#!/usr/bin/env python3
"""
統一ログ設定ライブラリ
全スクリプト共通のログ設定管理
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from .config_manager import config_manager
except ImportError:
    # 単体テスト用
    from config_manager import config_manager


class LoggerSetup:
    """統一ログ設定クラス"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls, project_root: Optional[str] = None):
        """ログシステム初期化"""
        if cls._initialized:
            return
        
        try:
            # 設定読み込み
            log_config = config_manager.get_log_config()
            
            # ログディレクトリ作成
            if project_root:
                log_dir = Path(project_root) / log_config.get('log_dir', 'MT5/Logs')
            else:
                log_dir = config_manager.project_root / log_config.get('log_dir', 'MT5/Logs')
            
            log_dir.mkdir(parents=True, exist_ok=True)
            
            cls._initialized = True
            
        except Exception as e:
            # フォールバック設定
            print(f"ログ設定初期化エラー（デフォルト設定使用）: {e}")
            cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """統一ログ取得"""
        cls.initialize()
        
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # 重複ハンドラー防止
        if logger.handlers:
            logger.handlers.clear()
        
        try:
            # 設定読み込み
            log_config = config_manager.get_log_config()
            
            # ログレベル設定
            level_str = log_config.get('level', 'INFO').upper()
            level = getattr(logging, level_str, logging.INFO)
            logger.setLevel(level)
            
            # フォーマッター作成
            formatter = logging.Formatter(
                log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            
            # コンソールハンドラー
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # ファイルハンドラー（指定された場合）
            if log_file:
                log_dir = config_manager.project_root / log_config.get('log_dir', 'MT5/Logs')
                log_path = log_dir / log_file
                
                # ローテーティングファイルハンドラー
                file_handler = logging.handlers.RotatingFileHandler(
                    log_path,
                    maxBytes=log_config.get('max_size', 5242880),  # 5MB
                    backupCount=log_config.get('backup_count', 5),
                    encoding=log_config.get('encoding', 'utf-8')
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
        
        except Exception as e:
            # フォールバック設定
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.warning(f"ログ設定エラー（基本設定使用）: {e}")
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def get_mt5_logger(cls) -> logging.Logger:
        """MT5用ログ取得"""
        return cls.get_logger("MT5", "mt5_auto_start.log")
    
    @classmethod
    def get_trading_logger(cls) -> logging.Logger:
        """取引監視用ログ取得"""
        return cls.get_logger("Trading", "trading_monitor.log")
    
    @classmethod
    def get_version_control_logger(cls) -> logging.Logger:
        """バージョン管理用ログ取得"""
        return cls.get_logger("VersionControl", "ea_version_control.log")
    
    @classmethod
    def get_sync_logger(cls) -> logging.Logger:
        """同期用ログ取得"""
        return cls.get_logger("Sync", "ea_sync.log")
    
    @classmethod
    def get_script_logger(cls, script_name: str) -> logging.Logger:
        """スクリプト専用ログ取得"""
        log_file = f"{script_name}.log"
        return cls.get_logger(script_name, log_file)


def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """ログ取得（簡易版）"""
    return LoggerSetup.get_logger(name, log_file)


def get_mt5_logger() -> logging.Logger:
    """MT5ログ取得（簡易版）"""
    return LoggerSetup.get_mt5_logger()


def get_trading_logger() -> logging.Logger:
    """取引ログ取得（簡易版）"""
    return LoggerSetup.get_trading_logger()


class LogContext:
    """ログコンテキストマネージャー"""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
    
    def __enter__(self):
        self.logger.info(f"開始: {self.operation}")
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(f"エラー終了: {self.operation} - {exc_val}")
        else:
            self.logger.info(f"正常終了: {self.operation}")


if __name__ == "__main__":
    # テスト実行
    try:
        logger = get_logger("TestLogger", "test.log")
        
        logger.info("ログテスト開始")
        logger.warning("警告テスト")
        logger.error("エラーテスト")
        
        # コンテキストマネージャーテスト
        with LogContext(logger, "テスト操作"):
            logger.info("操作実行中")
        
        print("ログ設定ライブラリテスト完了")
        
    except Exception as e:
        print(f"テストエラー: {e}")