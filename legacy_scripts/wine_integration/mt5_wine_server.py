#!/usr/bin/env python3
"""
MT5 Wine RPYCサーバー
Wine環境のMetaTrader5をLinuxから制御するためのサーバー
"""

import MetaTrader5 as mt5
import rpyc
from rpyc.utils.server import ThreadedServer
import sys

class MT5Service(rpyc.Service):
    """MT5 RPYC サービス"""
    
    def on_connect(self, conn):
        print("Linux client connected")
        
    def on_disconnect(self, conn):
        print("Linux client disconnected")
    
    def exposed_initialize(self, login=None, password=None, server=None, timeout=5000):
        """MT5初期化"""
        try:
            if login and password and server:
                result = mt5.initialize(login=int(login), password=password, server=server, timeout=timeout)
            else:
                result = mt5.initialize()
            
            if result:
                print("MT5 initialized successfully")
                return True
            else:
                print(f"MT5 initialization failed: {mt5.last_error()}")
                return False
        except Exception as e:
            print(f"MT5 initialization error: {e}")
            return False
    
    def exposed_shutdown(self):
        """MT5終了"""
        mt5.shutdown()
        return True
    
    def exposed_account_info(self):
        """アカウント情報取得"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None
            
            # NamedTupleをdictに変換
            return account_info._asdict()
        except Exception as e:
            print(f"Account info error: {e}")
            return None
    
    def exposed_positions_get(self, symbol=None, group=None, ticket=None):
        """ポジション情報取得"""
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            elif group:
                positions = mt5.positions_get(group=group)
            elif ticket:
                positions = mt5.positions_get(ticket=ticket)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            # NamedTupleのタプルをdictのリストに変換
            return [pos._asdict() for pos in positions]
        except Exception as e:
            print(f"Positions get error: {e}")
            return []
    
    def exposed_history_deals_get(self, date_from, date_to, group=None):
        """取引履歴取得"""
        try:
            if group:
                deals = mt5.history_deals_get(date_from, date_to, group=group)
            else:
                deals = mt5.history_deals_get(date_from, date_to)
            
            if deals is None:
                return []
            
            return [deal._asdict() for deal in deals]
        except Exception as e:
            print(f"History deals get error: {e}")
            return []
    
    def exposed_terminal_info(self):
        """ターミナル情報取得"""
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                return None
            
            return terminal_info._asdict()
        except Exception as e:
            print(f"Terminal info error: {e}")
            return None
    
    def exposed_version(self):
        """MT5バージョン情報"""
        try:
            return mt5.version()
        except Exception as e:
            print(f"Version error: {e}")
            return None
    
    def exposed_last_error(self):
        """最後のエラー情報"""
        try:
            return mt5.last_error()
        except Exception as e:
            print(f"Last error check failed: {e}")
            return (0, "Unknown error")

def main():
    print("MT5 Wine RPYC Server starting...")
    print(f"Python version: {sys.version}")
    print(f"MT5 version: {mt5.version()}")
    
    # サーバー起動
    server = ThreadedServer(
        MT5Service,
        port=18812,
        protocol_config={'allow_public_attrs': True}
    )
    
    print("MT5 RPYC Server started on port 18812")
    print("Waiting for Linux client connections...")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        mt5.shutdown()

if __name__ == "__main__":
    main()