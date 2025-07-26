"""
共通ライブラリパッケージ
MT5取引システム用統一ライブラリ
"""

# バージョン情報
__version__ = "1.0.0"
__author__ = "Trading Development Project"

# 主要クラス・関数のインポート
from .config_manager import (
    ConfigManager,
    config_manager,
    get_config,
    get_value
)

from .logger_setup import (
    LoggerSetup,
    get_logger,
    get_mt5_logger,
    get_trading_logger,
    LogContext
)

try:
    from .mt5_connection import (
        MT5Connection,
        get_mt5_connection,
        mt5_context
    )
    MT5_CONNECTION_AVAILABLE = True
except ImportError as e:
    MT5_CONNECTION_AVAILABLE = False
    print(f"MT5接続モジュール読み込みエラー: {e}")

from .error_handler import (
    # エラークラス
    MT5Error,
    MT5ConnectionError,
    RPYCConnectionError,
    EAError,
    ConfigurationError,
    FileOperationError,
    RetryableError,
    
    # エラーハンドラー
    ErrorHandler,
    error_handler,
    MT5ErrorHandler,
    
    # デコレータ・関数
    retry_on_failure,
    safe_execute,
    error_context
)

# モジュール一覧
__all__ = [
    # config_manager
    'ConfigManager',
    'config_manager', 
    'get_config',
    'get_value',
    
    # logger_setup
    'LoggerSetup',
    'get_logger',
    'get_mt5_logger', 
    'get_trading_logger',
    'LogContext',
    
    # mt5_connection (if available)
    'MT5Connection',
    'get_mt5_connection',
    'mt5_context',
    
    # error_handler
    'MT5Error',
    'MT5ConnectionError',
    'RPYCConnectionError', 
    'EAError',
    'ConfigurationError',
    'FileOperationError',
    'RetryableError',
    'ErrorHandler',
    'error_handler',
    'MT5ErrorHandler',
    'retry_on_failure',
    'safe_execute',
    'error_context'
]


def initialize_system():
    """システム初期化"""
    try:
        # ログシステム初期化
        LoggerSetup.initialize()
        
        # 設定検証
        required_configs = [
            "mt5_config",
            "ea_config", 
            "trading_config",
            "system_config"
        ]
        
        logger = get_logger("SystemInitializer")
        logger.info("システム初期化開始")
        
        for config_name in required_configs:
            try:
                config = get_config(config_name)
                logger.info(f"設定読み込み完了: {config_name}")
            except Exception as e:
                logger.error(f"設定読み込みエラー: {config_name} - {e}")
                raise ConfigurationError(f"設定初期化失敗: {config_name}")
        
        logger.info("システム初期化完了")
        return True
        
    except Exception as e:
        print(f"システム初期化エラー: {e}")
        raise


def get_system_status():
    """システム状態取得"""
    try:
        import time
        logger = get_logger("SystemStatus")
        
        # 設定状態
        config_status = {}
        for config_name in ["mt5_config", "ea_config", "trading_config", "system_config"]:
            try:
                get_config(config_name)
                config_status[config_name] = "OK"
            except Exception as e:
                config_status[config_name] = f"ERROR: {e}"
        
        # MT5接続状態（利用可能な場合のみ）
        connection_status = {}
        if MT5_CONNECTION_AVAILABLE:
            try:
                connection = get_mt5_connection("StatusCheck")
                connection_status = connection.get_connection_status()
            except Exception as e:
                connection_status = {"error": str(e)}
        else:
            connection_status = {"status": "MT5接続モジュール未利用"}
        
        status = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "connection": connection_status,
            "configs": config_status,
            "library_version": __version__,
            "modules_available": {
                "mt5_connection": MT5_CONNECTION_AVAILABLE
            }
        }
        
        logger.info(f"システム状態確認完了: {status}")
        return status
        
    except Exception as e:
        logger.error(f"システム状態確認エラー: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # ライブラリテスト
    import time
    
    print(f"=== 共通ライブラリテスト (v{__version__}) ===")
    
    try:
        # システム初期化
        initialize_system()
        
        # システム状態確認
        status = get_system_status()
        print(f"システム状態: {status}")
        
        print("共通ライブラリテスト完了")
        
    except Exception as e:
        print(f"ライブラリテストエラー: {e}")