#!/usr/bin/env python3
"""
Wine環境でのMT5基本テスト - エラー回避版
"""

def test_imports():
    try:
        print("=== Import Test ===")
        import sys
        print(f"Python: {sys.version}")
        
        # MetaTrader5 import テスト（エラー情報収集）
        try:
            import MetaTrader5 as mt5
            print("MT5 import: SUCCESS")
            
            # バージョン情報
            try:
                version = mt5.__version__
                print(f"MT5 version: {version}")
            except Exception as e:
                print(f"Version check error: {e}")
                
            return True
            
        except Exception as e:
            print(f"MT5 import ERROR: {e}")
            print(f"Error type: {type(e).__name__}")
            return False
            
    except Exception as e:
        print(f"Basic import ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("✅ MT5 Import Test: PASSED")
    else:
        print("❌ MT5 Import Test: FAILED")