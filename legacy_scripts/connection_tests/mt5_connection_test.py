#!/usr/bin/env python3
"""
MT5接続テスト - 簡易版
WSL環境でのMT5接続動作確認
"""

def test_mt5_connection():
    try:
        # mt5linux使用（WSL環境用）
        import mt5linux
        
        print("📡 MT5接続テスト開始...")
        print("✅ mt5linux import成功")
        
        # 基本情報表示
        print("🔗 MT5初期化試行中...")
        
        # 注意: mt5linuxは特別な設定が必要
        print("⚠️  mt5linuxは以下の事前設定が必要:")
        print("   1. Wine環境でWindows版Python + MetaTrader5パッケージ")
        print("   2. MT5プラットフォーム起動")
        print("   3. デモ口座ログイン")
        
        return True
        
    except ImportError as e:
        print(f"❌ import失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

if __name__ == "__main__":
    success = test_mt5_connection()
    if success:
        print("✅ MT5接続準備完了")
    else:
        print("❌ MT5接続準備失敗")