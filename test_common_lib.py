#!/usr/bin/env python3
"""
共通ライブラリ統合テスト
全ライブラリの動作確認
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_manager():
    """設定管理ライブラリテスト"""
    print("=== 設定管理ライブラリテスト ===")
    
    try:
        from lib.config_manager import ConfigManager, get_config, get_value
        
        cm = ConfigManager()
        
        # 基本テスト
        mt5_config = cm.get_mt5_config()
        print(f"✓ MT5設定読み込み: {len(mt5_config)} keys")
        
        ea_config = cm.get_ea_config()
        print(f"✓ EA設定読み込み: {len(ea_config)} keys")
        
        # 特定値テスト
        terminal_path = cm.get_mt5_terminal_path()
        print(f"✓ MT5パス取得: {terminal_path}")
        
        rpyc_port = cm.get_value("mt5_config", "rpyc.port", 0)
        print(f"✓ RPYCポート取得: {rpyc_port}")
        
        print("設定管理ライブラリテスト完了\n")
        return True
        
    except Exception as e:
        print(f"❌ 設定管理ライブラリエラー: {e}\n")
        return False


def test_logger_setup():
    """ログ設定ライブラリテスト"""
    print("=== ログ設定ライブラリテスト ===")
    
    try:
        from lib.logger_setup import LoggerSetup, get_logger, LogContext
        
        # 基本ログテスト
        logger = get_logger("TestLogger")
        logger.info("ログテスト開始")
        logger.warning("警告テスト")
        logger.error("エラーテスト")
        print("✓ 基本ログ出力")
        
        # 専用ログテスト
        mt5_logger = LoggerSetup.get_mt5_logger()
        mt5_logger.info("MT5ログテスト")
        print("✓ MT5専用ログ")
        
        # コンテキストテスト
        with LogContext(logger, "テスト操作"):
            logger.info("コンテキスト内処理")
        print("✓ ログコンテキスト")
        
        print("ログ設定ライブラリテスト完了\n")
        return True
        
    except Exception as e:
        print(f"❌ ログ設定ライブラリエラー: {e}\n")
        return False


def test_error_handler():
    """エラーハンドリングライブラリテスト"""
    print("=== エラーハンドリングライブラリテスト ===")
    
    try:
        from lib.error_handler import (
            ErrorHandler, retry_on_failure, safe_execute, 
            error_context, MT5Error, ConfigurationError
        )
        
        handler = ErrorHandler("TestHandler")
        
        # 安全実行テスト
        def error_function():
            raise ValueError("テストエラー")
        
        result = handler.safe_execute(error_function, default_return="デフォルト値")
        print(f"✓ 安全実行: {result}")
        
        # エラーコンテキストテスト
        with handler.error_context("テスト操作"):
            pass
        print("✓ エラーコンテキスト")
        
        # カスタムエラーテスト
        try:
            raise MT5Error("テストMT5エラー")
        except MT5Error as e:
            print(f"✓ カスタムエラー: {type(e).__name__}")
        
        print("エラーハンドリングライブラリテスト完了\n")
        return True
        
    except Exception as e:
        print(f"❌ エラーハンドリングライブラリエラー: {e}\n")
        return False


def test_mt5_connection():
    """MT5接続ライブラリテスト（依存関係なし）"""
    print("=== MT5接続ライブラリテスト ===")
    
    try:
        from lib.mt5_connection import MT5Connection
        
        connection = MT5Connection("TestConnection")
        
        # 基本設定確認
        config = connection.mt5_config
        print(f"✓ MT5設定読み込み: {len(config)} keys")
        
        # プロセス確認（psutilなしでも動作）
        is_running = connection.is_mt5_running()
        print(f"✓ プロセス確認: {is_running}")
        
        # 接続状態取得
        status = connection.get_connection_status()
        print(f"✓ 接続状態: {status}")
        
        print("MT5接続ライブラリテスト完了\n")
        return True
        
    except Exception as e:
        print(f"❌ MT5接続ライブラリエラー: {e}\n")
        return False


def test_integration():
    """統合テスト"""
    print("=== 統合テスト ===")
    
    try:
        # 複数ライブラリ連携テスト
        from lib.config_manager import get_config
        from lib.logger_setup import get_logger
        from lib.error_handler import error_context
        
        logger = get_logger("IntegrationTest")
        
        with error_context("統合テスト", critical=False):
            # 設定読み込み
            mt5_config = get_config("mt5_config")
            ea_config = get_config("ea_config")
            
            logger.info(f"統合テスト完了: MT5設定{len(mt5_config)}項目, EA設定{len(ea_config)}項目")
        
        print("✓ ライブラリ間連携")
        print("統合テスト完了\n")
        return True
        
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}\n")
        return False


def main():
    """メイン統合テスト"""
    print("🔍 共通ライブラリ統合テスト開始\n")
    
    tests = [
        ("設定管理", test_config_manager),
        ("ログ設定", test_logger_setup),
        ("エラーハンドリング", test_error_handler),
        ("MT5接続", test_mt5_connection),
        ("統合", test_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name}テスト実行エラー: {e}")
            results[test_name] = False
    
    # 結果サマリー
    print("=" * 50)
    print("📊 テスト結果サマリー")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<15}: {status}")
        if result:
            passed += 1
    
    print(f"\n成功: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 全テスト成功！共通ライブラリは正常に動作しています")
        return True
    else:
        print(f"\n⚠️  {total-passed}個のテストが失敗しました")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)