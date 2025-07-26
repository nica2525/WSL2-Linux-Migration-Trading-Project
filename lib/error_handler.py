#!/usr/bin/env python3
"""
統一エラーハンドリングライブラリ
共通エラークラスとリトライ機構
"""

import time
import functools
from typing import Callable, Any, Optional, Type, Tuple, Union
from contextlib import contextmanager

try:
    from .config_manager import config_manager
    from .logger_setup import get_logger
except ImportError:
    # 単体テスト用
    from config_manager import config_manager
    from logger_setup import get_logger


# 共通エラークラス
class MT5Error(Exception):
    """MT5関連エラー基底クラス"""
    pass


class MT5ConnectionError(MT5Error):
    """MT5接続エラー"""
    pass


class RPYCConnectionError(MT5Error):
    """RPYC接続エラー"""
    pass


class EAError(MT5Error):
    """EA関連エラー"""
    pass


class ConfigurationError(Exception):
    """設定エラー"""
    pass


class FileOperationError(Exception):
    """ファイル操作エラー"""
    pass


class RetryableError(Exception):
    """リトライ可能エラー"""
    pass


class ErrorHandler:
    """統一エラーハンドリングクラス"""
    
    def __init__(self, logger_name: str = "ErrorHandler"):
        self.logger = get_logger(logger_name)
        self.error_config = config_manager.get_value("system_config", "error_handling", {})
    
    def retry_on_failure(
        self,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        backoff_factor: float = 1.0
    ):
        """リトライデコレータ"""
        if max_retries is None:
            max_retries = self.error_config.get('max_retries', 3)
        if retry_delay is None:
            retry_delay = self.error_config.get('retry_delay', 5)
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt < max_retries:
                            wait_time = retry_delay * (backoff_factor ** attempt)
                            self.logger.warning(
                                f"{func.__name__} 失敗 ({attempt + 1}/{max_retries + 1}): {e}. "
                                f"{wait_time}秒後にリトライ"
                            )
                            time.sleep(wait_time)
                        else:
                            self.logger.error(
                                f"{func.__name__} 全リトライ失敗: {e}"
                            )
                
                raise last_exception
            
            return wrapper
        return decorator
    
    def safe_execute(
        self,
        func: Callable,
        *args,
        default_return: Any = None,
        log_errors: bool = True,
        **kwargs
    ) -> Any:
        """安全実行（例外を捕捉してデフォルト値返却）"""
        try:
            return func(*args, **kwargs)
        
        except Exception as e:
            if log_errors:
                self.logger.error(f"{func.__name__} 実行エラー: {e}")
            return default_return
    
    def handle_critical_error(self, error: Exception, context: str = ""):
        """重大エラー処理"""
        error_message = f"重大エラー{f' ({context})' if context else ''}: {error}"
        
        self.logger.critical(error_message)
        
        # 重大エラー通知チェック
        if self.error_config.get('error_notifications', False):
            critical_errors = self.error_config.get('critical_errors', [])
            
            for critical_pattern in critical_errors:
                if critical_pattern.lower() in str(error).lower():
                    self._send_error_notification(error_message)
                    break
    
    def _send_error_notification(self, message: str):
        """エラー通知送信（将来拡張用）"""
        # TODO: メール通知、Slack通知等の実装
        self.logger.info(f"エラー通知: {message}")
    
    @contextmanager
    def error_context(self, operation: str, critical: bool = False):
        """エラーコンテキストマネージャー"""
        try:
            self.logger.info(f"開始: {operation}")
            yield
            self.logger.info(f"正常完了: {operation}")
        
        except Exception as e:
            error_message = f"エラー: {operation} - {e}"
            
            if critical:
                self.handle_critical_error(e, operation)
            else:
                self.logger.error(error_message)
            
            raise
    
    def validate_config(self, config: dict, required_keys: list) -> bool:
        """設定妥当性確認"""
        missing_keys = []
        
        for key in required_keys:
            if '.' in key:
                # ネストしたキー確認
                keys = key.split('.')
                current = config
                
                try:
                    for k in keys:
                        current = current[k]
                except (KeyError, TypeError):
                    missing_keys.append(key)
            else:
                if key not in config:
                    missing_keys.append(key)
        
        if missing_keys:
            raise ConfigurationError(f"必須設定が不足: {missing_keys}")
        
        return True


# グローバルエラーハンドラー
error_handler = ErrorHandler()


def retry_on_failure(
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    backoff_factor: float = 1.0
):
    """リトライデコレータ（簡易版）"""
    return error_handler.retry_on_failure(max_retries, retry_delay, exceptions, backoff_factor)


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """安全実行（簡易版）"""
    return error_handler.safe_execute(func, *args, **kwargs)


@contextmanager
def error_context(operation: str, critical: bool = False):
    """エラーコンテキスト（簡易版）"""
    with error_handler.error_context(operation, critical):
        yield


class MT5ErrorHandler(ErrorHandler):
    """MT5専用エラーハンドラー"""
    
    def __init__(self):
        super().__init__("MT5ErrorHandler")
    
    @retry_on_failure(exceptions=(MT5ConnectionError, RPYCConnectionError))
    def ensure_mt5_connection(self, connection_func: Callable) -> Any:
        """MT5接続保証"""
        return connection_func()
    
    def handle_ea_error(self, error: Exception, ea_name: str):
        """EA専用エラー処理"""
        self.handle_critical_error(error, f"EA: {ea_name}")


if __name__ == "__main__":
    # テスト実行
    try:
        handler = ErrorHandler("TestHandler")
        
        print("=== エラーハンドリングテスト ===")
        
        # リトライテスト
        @handler.retry_on_failure(max_retries=2, retry_delay=1)
        def test_retry_function():
            import random
            if random.random() < 0.7:  # 70%の確率で失敗
                raise Exception("ランダムエラー")
            return "成功"
        
        # 安全実行テスト
        def test_error_function():
            raise ValueError("テストエラー")
        
        result = handler.safe_execute(test_error_function, default_return="デフォルト値")
        print(f"安全実行結果: {result}")
        
        # エラーコンテキストテスト
        with handler.error_context("テスト操作"):
            print("エラーコンテキスト内処理")
        
        print("エラーハンドリングライブラリテスト完了")
        
    except Exception as e:
        print(f"テストエラー: {e}")