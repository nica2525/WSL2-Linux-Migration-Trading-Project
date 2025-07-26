#!/usr/bin/env python3
"""
MT5 Linux クライアント
Wine環境のMT5サーバーに接続してデータを取得
"""

import rpyc
import time
from datetime import datetime, timedelta
import json

class MT5LinuxClient:
    """MT5 Linux クライアント"""
    
    def __init__(self, host='localhost', port=18812):
        self.host = host
        self.port = port
        self.conn = None
        self.mt5 = None
    
    def connect(self):
        """RPYCサーバーに接続"""
        try:
            print(f"Connecting to MT5 server at {self.host}:{self.port}...")
            self.conn = rpyc.connect(self.host, self.port)
            self.mt5 = self.conn.root
            print("✅ Connected to MT5 server successfully")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """サーバーから切断"""
        if self.conn:
            self.conn.close()
            print("Disconnected from MT5 server")
    
    def initialize_mt5(self, login=None, password=None, server=None):
        """MT5初期化"""
        try:
            if not self.mt5:
                print("❌ Not connected to server")
                return False
            
            result = self.mt5.initialize(login, password, server)
            if result:
                print("✅ MT5 initialized successfully")
                return True
            else:
                print("❌ MT5 initialization failed")
                return False
        except Exception as e:
            print(f"❌ MT5 initialization error: {e}")
            return False
    
    def get_account_info(self):
        """アカウント情報取得"""
        try:
            account_info = self.mt5.account_info()
            if account_info:
                print("✅ Account info retrieved successfully")
                return account_info
            else:
                print("❌ Failed to get account info")
                return None
        except Exception as e:
            print(f"❌ Account info error: {e}")
            return None
    
    def get_positions(self, symbol=None):
        """ポジション取得"""
        try:
            positions = self.mt5.positions_get(symbol=symbol)
            if positions is not None:
                print(f"✅ Retrieved {len(positions)} positions")
                return positions
            else:
                print("❌ Failed to get positions")
                return []
        except Exception as e:
            print(f"❌ Positions error: {e}")
            return []
    
    def get_terminal_info(self):
        """ターミナル情報取得"""
        try:
            terminal_info = self.mt5.terminal_info()
            if terminal_info:
                print("✅ Terminal info retrieved successfully")
                return terminal_info
            else:
                print("❌ Failed to get terminal info")
                return None
        except Exception as e:
            print(f"❌ Terminal info error: {e}")
            return None
    
    def get_version(self):
        """バージョン情報取得"""
        try:
            version = self.mt5.version()
            if version:
                print(f"✅ MT5 version: {version}")
                return version
            else:
                print("❌ Failed to get version")
                return None
        except Exception as e:
            print(f"❌ Version error: {e}")
            return None
    
    def test_basic_connection(self):
        """基本接続テスト"""
        print("=== MT5 Linux Client Test ===")
        
        # 接続テスト
        if not self.connect():
            return False
        
        # バージョン確認
        version = self.get_version()
        if not version:
            return False
        
        # MT5初期化（デモ口座の場合はパラメータなし）
        if not self.initialize_mt5():
            return False
        
        # ターミナル情報確認
        terminal_info = self.get_terminal_info()
        if terminal_info:
            print(f"Company: {terminal_info.get('company', 'Unknown')}")
            print(f"Connected: {terminal_info.get('connected', False)}")
        
        # アカウント情報確認
        account_info = self.get_account_info()
        if account_info:
            print(f"Balance: {account_info.get('balance', 0)}")
            print(f"Equity: {account_info.get('equity', 0)}")
            print(f"Currency: {account_info.get('currency', 'Unknown')}")
        
        # ポジション確認
        positions = self.get_positions()
        print(f"Active positions: {len(positions)}")
        
        # 切断
        self.disconnect()
        
        print("✅ MT5 Linux Client Test completed successfully")
        return True

def main():
    """メイン実行"""
    client = MT5LinuxClient()
    success = client.test_basic_connection()
    
    if success:
        print("\n🎉 MT5 Linux Client is working properly!")
    else:
        print("\n❌ MT5 Linux Client test failed")

if __name__ == "__main__":
    main()