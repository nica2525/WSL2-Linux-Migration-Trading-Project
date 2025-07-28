#!/usr/bin/env python3
"""
MT5自動取引有効化システム
EA運用に必要な設定を確認・ガイド提供
"""

import rpyc
import time
from datetime import datetime

class MT5TradingEnabler:
    """MT5自動取引有効化クラス"""
    
    def __init__(self):
        self.conn = None
        self.mt5 = None
        
    def connect_to_server(self):
        """RPYCサーバー接続"""
        try:
            print("🔗 Connecting to MT5 RPYC server...")
            self.conn = rpyc.connect('localhost', 18812, config={'sync_request_timeout': 30})
            self.mt5 = self.conn.root
            print("✅ RPYC server connection successful")
            return True
        except Exception as e:
            print(f"❌ RPYC connection failed: {e}")
            return False
    
    def check_trading_permissions(self):
        """取引許可設定確認"""
        try:
            print("\n📋 Checking Trading Permissions...")
            
            if not self.mt5.initialize():
                print("❌ MT5 initialization failed")
                return False
            
            terminal_info = self.mt5.terminal_info()
            account_info = self.mt5.account_info()
            
            if terminal_info:
                print(f"\n🖥️ Terminal Status:")
                print(f"   Connected: {terminal_info.get('connected', False)}")
                print(f"   Trade Allowed: {terminal_info.get('trade_allowed', False)}")
                print(f"   DLL Allowed: {terminal_info.get('dlls_allowed', False)}")
                print(f"   Expert Enabled: {terminal_info.get('expert_enabled', False)}")
                print(f"   Trade Expert: {terminal_info.get('trade_expert', False)}")
                
            if account_info:
                print(f"\n💰 Account Status:")
                account_dict = dict(account_info)
                print(f"   Login: {account_dict.get('login', 'Unknown')}")
                print(f"   Trade Allowed: {account_dict.get('trade_allowed', False)}")
                print(f"   Trade Expert: {account_dict.get('trade_expert', False)}")
                print(f"   Balance: {account_dict.get('balance', 0)} {account_dict.get('currency', '')}")
                
                return terminal_info, account_info
            
            return terminal_info, None
            
        except Exception as e:
            print(f"❌ Permission check failed: {e}")
            return None, None
    
    def provide_manual_setup_guide(self):
        """手動設定ガイド提供"""
        print("\n" + "=" * 60)
        print("🛠️ MANUAL SETUP REQUIRED")
        print("=" * 60)
        print()
        print("MT5で以下の設定を手動で有効化してください：")
        print()
        print("📋 必須設定項目:")
        print("   1. Tools → Options → Expert Advisors")
        print("      ☐ Allow automated trading")
        print("      ☐ Allow DLL imports") 
        print("      ☐ Confirm DLL function calls: OFF")
        print()
        print("   2. ツールバーのAutoTrading ボタン")
        print("      ☐ AutoTrading を有効化（緑色にする）")
        print()
        print("   3. ポップアップ抑制設定:")
        print("      ☐ Tools → Options → Trading")
        print("      ☐ 'Confirm manual trading operations': OFF")
        print()
        print("   4. 言語設定（オプション）:")
        print("      ☐ View → Languages → Japanese")
        print("      ☐ 設定後MT5再起動")
        print()
        print("🎯 設定完了後、再度接続テストを実行してください")
        print("=" * 60)
    
    def wait_for_user_confirmation(self):
        """ユーザー設定完了待機"""
        print("\n⏳ Waiting for manual configuration...")
        print("設定完了後、このテストを再実行してください")
        
        # 10秒間隔で設定状況を確認
        for i in range(12):  # 2分間
            try:
                print(f"\n📡 Checking settings... ({i+1}/12)")
                terminal_info, account_info = self.check_trading_permissions()
                
                if terminal_info and terminal_info.get('trade_allowed', False):
                    print("🎉 Trade allowed detected!")
                    return True
                    
                if i < 11:
                    print("⏳ Waiting 10 seconds...")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"⚠️ Check failed: {e}")
                
        return False
    
    def run_setup_process(self):
        """セットアップ処理実行"""
        print("🚀 Starting MT5 Trading Enabler")
        print("=" * 50)
        
        if not self.connect_to_server():
            return False
        
        try:
            # 現在の設定確認
            terminal_info, account_info = self.check_trading_permissions()
            
            if terminal_info and terminal_info.get('trade_allowed', False):
                print("\n🎉 Trading is already enabled!")
                print("✅ System ready for EA deployment")
                return True
            else:
                # 手動設定ガイド提供
                self.provide_manual_setup_guide()
                
                # ユーザー設定完了待機
                return self.wait_for_user_confirmation()
                
        finally:
            if self.conn:
                self.conn.close()
                print("\n🔒 Connection closed")

def main():
    enabler = MT5TradingEnabler()
    success = enabler.run_setup_process()
    
    if success:
        print("\n🏆 Trading setup successful!")
        print("🚀 Ready for EA development and deployment!")
    else:
        print("\n⚠️ Manual setup required")
        print("📋 Please complete the configuration steps above")

if __name__ == "__main__":
    main()