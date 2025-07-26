#!/usr/bin/env python3
"""
MT5接続共通ライブラリ
Wine環境でのMT5・RPYC接続管理
"""

import os
import time
import rpyc
import psutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager

from .config_manager import config_manager
from .logger_setup import get_logger
from .error_handler import MT5ConnectionError, RPYCConnectionError


class MT5Connection:
    """MT5接続管理クラス"""
    
    def __init__(self, logger_name: str = "MT5Connection"):
        self.logger = get_logger(logger_name)
        self.mt5_config = config_manager.get_mt5_config()
        self.rpyc_config = self.mt5_config.get('rpyc', {})
        self.wine_config = self.mt5_config.get('wine', {})
        
        self.rpyc_conn = None
        self.mt5_instance = None
    
    def is_mt5_running(self) -> bool:
        """MT5プロセス確認"""
        try:
            process_name = self.mt5_config.get('mt5', {}).get('process_name', 'terminal64.exe')
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"MT5プロセス確認エラー: {e}")
            return False
    
    def start_mt5(self, wait_for_startup: bool = True) -> bool:
        """MT5起動"""
        try:
            if self.is_mt5_running():
                self.logger.info("MT5は既に起動中")
                return True
            
            # Wine環境設定
            env = os.environ.copy()
            env.update({
                'WINEPREFIX': self.wine_config.get('wine_prefix', '/home/trader/.wine'),
                'WINEDEBUG': self.wine_config.get('winedebug', '-all'),
                'LANG': 'C.UTF-8',
                'LC_ALL': 'C.UTF-8'
            })
            
            # MT5起動
            terminal_path = self.mt5_config.get('mt5', {}).get('terminal_path')
            if not terminal_path:
                raise MT5ConnectionError("MT5ターミナルパスが設定されていません")
            
            self.logger.info(f"MT5起動中: {terminal_path}")
            
            # ホームディレクトリから起動（パスエンコーディング問題回避）
            process = subprocess.Popen(
                ['wine', terminal_path],
                env=env,
                cwd=os.path.expanduser('~'),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            if wait_for_startup:
                timeout = self.mt5_config.get('mt5', {}).get('startup_timeout', 30)
                return self._wait_for_mt5_startup(timeout)
            
            return True
            
        except Exception as e:
            self.logger.error(f"MT5起動エラー: {e}")
            raise MT5ConnectionError(f"MT5起動失敗: {e}")
    
    def _wait_for_mt5_startup(self, timeout: int) -> bool:
        """MT5起動待機"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_mt5_running():
                self.logger.info("MT5起動完了")
                time.sleep(2)  # 完全起動まで少し待機
                return True
            
            time.sleep(1)
        
        self.logger.error(f"MT5起動タイムアウト ({timeout}秒)")
        return False
    
    def connect_rpyc(self, retries: int = None) -> bool:
        """RPYC接続"""
        if retries is None:
            retries = self.rpyc_config.get('retry_attempts', 3)
        
        host = self.rpyc_config.get('host', 'localhost')
        port = self.rpyc_config.get('port', 18812)
        timeout = self.rpyc_config.get('connection_timeout', 10)
        retry_delay = self.rpyc_config.get('retry_delay', 5)
        
        for attempt in range(retries):
            try:
                self.logger.info(f"RPYC接続試行 {attempt + 1}/{retries}: {host}:{port}")
                
                self.rpyc_conn = rpyc.connect(
                    host, port,
                    config={'sync_request_timeout': timeout}
                )
                
                # 接続テスト
                self.mt5_instance = self.rpyc_conn.root
                test_result = self.mt5_instance.ping()
                
                self.logger.info(f"RPYC接続成功: {test_result}")
                return True
                
            except Exception as e:
                self.logger.warning(f"RPYC接続失敗 {attempt + 1}/{retries}: {e}")
                
                if attempt < retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise RPYCConnectionError(f"RPYC接続失敗（全{retries}回試行）: {e}")
        
        return False
    
    def disconnect_rpyc(self):
        """RPYC切断"""
        if self.rpyc_conn:
            try:
                self.rpyc_conn.close()
                self.logger.info("RPYC切断完了")
            except Exception as e:
                self.logger.warning(f"RPYC切断エラー: {e}")
            finally:
                self.rpyc_conn = None
                self.mt5_instance = None
    
    def get_mt5_instance(self):
        """MT5インスタンス取得"""
        if not self.mt5_instance:
            raise RPYCConnectionError("RPYC未接続")
        return self.mt5_instance
    
    def check_connection(self) -> bool:
        """接続状態確認"""
        try:
            if not self.rpyc_conn or not self.mt5_instance:
                return False
            
            # ping テスト
            result = self.mt5_instance.ping()
            return "pong" in str(result).lower()
            
        except Exception as e:
            self.logger.warning(f"接続確認エラー: {e}")
            return False
    
    def ensure_connection(self) -> bool:
        """接続保証（自動復旧）"""
        try:
            # 既存接続確認
            if self.check_connection():
                return True
            
            self.logger.info("接続復旧を開始")
            
            # RPYC再接続
            self.disconnect_rpyc()
            
            # MT5確認・起動
            if not self.is_mt5_running():
                if not self.start_mt5():
                    return False
            
            # RPYC再接続
            return self.connect_rpyc()
            
        except Exception as e:
            self.logger.error(f"接続復旧エラー: {e}")
            return False
    
    @contextmanager
    def connection_context(self):
        """接続コンテキストマネージャー"""
        try:
            if not self.ensure_connection():
                raise MT5ConnectionError("MT5接続確立失敗")
            
            yield self.get_mt5_instance()
            
        except Exception as e:
            self.logger.error(f"接続コンテキストエラー: {e}")
            raise
        finally:
            # 接続は維持（他の処理で使用される可能性）
            pass
    
    def get_connection_status(self) -> Dict[str, Any]:
        """接続状態取得"""
        return {
            'mt5_running': self.is_mt5_running(),
            'rpyc_connected': self.check_connection(),
            'connection_config': {
                'host': self.rpyc_config.get('host'),
                'port': self.rpyc_config.get('port')
            }
        }


def get_mt5_connection(logger_name: str = "MT5Connection") -> MT5Connection:
    """MT5接続取得（簡易版）"""
    return MT5Connection(logger_name)


@contextmanager
def mt5_context(logger_name: str = "MT5Context"):
    """MT5接続コンテキスト（簡易版）"""
    connection = get_mt5_connection(logger_name)
    
    try:
        with connection.connection_context() as mt5:
            yield mt5
    finally:
        connection.disconnect_rpyc()


if __name__ == "__main__":
    # テスト実行
    try:
        connection = get_mt5_connection("TestConnection")
        
        print("=== MT5接続テスト ===")
        print(f"MT5プロセス確認: {connection.is_mt5_running()}")
        
        if connection.ensure_connection():
            status = connection.get_connection_status()
            print(f"接続状態: {status}")
            
            # 接続コンテキストテスト
            with connection.connection_context() as mt5:
                result = mt5.ping()
                print(f"pingテスト: {result}")
        
        print("MT5接続ライブラリテスト完了")
        
    except Exception as e:
        print(f"テストエラー: {e}")
    finally:
        if 'connection' in locals():
            connection.disconnect_rpyc()