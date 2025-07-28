#!/usr/bin/env python3
"""
MT5接続簡易テスト - サーバー通信確認のみ
"""

import rpyc
import time

def test_server_connection():
    """サーバー接続テスト"""
    try:
        print("=== MT5 RPYC Connection Test ===")
        
        # RPYCサーバーに接続
        print("Connecting to RPYC server...")
        conn = rpyc.connect('localhost', 18812)
        mt5_service = conn.root
        
        print("✅ RPYC connection successful")
        
        # バージョン情報取得（MT5ターミナル不要）
        try:
            version = mt5_service.version()
            print(f"✅ MT5 service version: {version}")
        except Exception as e:
            print(f"Version check: {e}")
        
        # 最後のエラー確認
        try:
            last_error = mt5_service.last_error()
            print(f"Last error: {last_error}")
        except Exception as e:
            print(f"Error check failed: {e}")
        
        # 接続終了
        conn.close()
        print("✅ Test completed - RPYC communication working")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_server_connection()
    if success:
        print("\n🎉 Phase 4 - RPYC Server Communication: SUCCESS")
        print("Next: MT5ターミナル起動後にフル機能テスト")
    else:
        print("\n❌ Phase 4 - RPYC Server Communication: FAILED")