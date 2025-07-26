#!/usr/bin/env python3
"""
MT5取引監視システム
- JamesORB EAの取引を監視
- 取引発生時に記録・通知
- 統計情報の収集
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
import MetaTrader5 as mt5

# ログ設定
LOG_DIR = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/Trading"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f'monitor_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)

# 取引記録ファイル
TRADE_RECORD_FILE = os.path.join(LOG_DIR, "trades.json")

class MT5TradingMonitor:
    def __init__(self):
        self.ea_magic = 12345  # JamesORB EAのマジックナンバー（要確認）
        self.symbol = "EURUSD"
        self.last_position_count = 0
        self.trades = self.load_trades()
        
    def load_trades(self):
        """既存の取引記録を読み込み"""
        if os.path.exists(TRADE_RECORD_FILE):
            try:
                with open(TRADE_RECORD_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_trades(self):
        """取引記録を保存"""
        with open(TRADE_RECORD_FILE, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def connect_mt5(self):
        """MT5に接続"""
        if not mt5.initialize():
            logging.error(f"MT5接続失敗: {mt5.last_error()}")
            return False
        logging.info("MT5接続成功")
        return True
    
    def monitor_positions(self):
        """ポジションを監視"""
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            logging.error("ポジション取得エラー")
            return
        
        current_count = len(positions)
        
        # 新規ポジション検出
        if current_count > self.last_position_count:
            logging.info(f"🔔 新規ポジション検出！ ({current_count}個)")
            
            for pos in positions:
                # JamesORB EAのポジションか確認
                if hasattr(pos, 'magic') and pos.magic == self.ea_magic:
                    self.record_new_position(pos)
        
        # ポジション決済検出
        elif current_count < self.last_position_count:
            logging.info(f"💰 ポジション決済検出！ (残り{current_count}個)")
            self.check_closed_positions()
        
        self.last_position_count = current_count
    
    def record_new_position(self, position):
        """新規ポジションを記録"""
        trade_info = {
            "ticket": position.ticket,
            "symbol": position.symbol,
            "type": "BUY" if position.type == 0 else "SELL",
            "volume": position.volume,
            "open_price": position.price_open,
            "open_time": datetime.fromtimestamp(position.time).isoformat(),
            "sl": position.sl,
            "tp": position.tp,
            "status": "OPEN",
            "profit": 0
        }
        
        self.trades.append(trade_info)
        self.save_trades()
        
        logging.info(f"新規取引記録: {trade_info['type']} {trade_info['volume']}ロット @ {trade_info['open_price']}")
    
    def check_closed_positions(self):
        """決済されたポジションを確認"""
        # 履歴から最新の決済取引を取得
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        deals = mt5.history_deals_get(yesterday, today)
        if deals:
            for deal in deals:
                if deal.symbol == self.symbol and hasattr(deal, 'magic') and deal.magic == self.ea_magic:
                    self.update_closed_position(deal)
    
    def update_closed_position(self, deal):
        """決済情報を更新"""
        for trade in self.trades:
            if trade.get("ticket") == deal.position_id and trade["status"] == "OPEN":
                trade["status"] = "CLOSED"
                trade["close_price"] = deal.price
                trade["close_time"] = datetime.fromtimestamp(deal.time).isoformat()
                trade["profit"] = deal.profit
                
                self.save_trades()
                logging.info(f"取引決済: チケット{trade['ticket']} 利益: ${trade['profit']:.2f}")
                break
    
    def generate_summary(self):
        """取引サマリーを生成"""
        if not self.trades:
            return "取引履歴なし"
        
        total_trades = len(self.trades)
        closed_trades = [t for t in self.trades if t["status"] == "CLOSED"]
        open_trades = [t for t in self.trades if t["status"] == "OPEN"]
        
        if closed_trades:
            total_profit = sum(t["profit"] for t in closed_trades)
            win_trades = [t for t in closed_trades if t["profit"] > 0]
            win_rate = len(win_trades) / len(closed_trades) * 100
        else:
            total_profit = 0
            win_rate = 0
        
        summary = f"""
=== JamesORB EA 取引サマリー ===
総取引数: {total_trades}
オープン中: {len(open_trades)}
決済済み: {len(closed_trades)}
総利益: ${total_profit:.2f}
勝率: {win_rate:.1f}%
監視時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================
"""
        return summary
    
    def run_monitor(self, interval=60):
        """監視を実行"""
        logging.info("=== MT5取引監視開始 ===")
        
        if not self.connect_mt5():
            return
        
        try:
            while True:
                self.monitor_positions()
                
                # 定期的にサマリー出力
                if datetime.now().minute % 15 == 0:
                    summary = self.generate_summary()
                    logging.info(summary)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logging.info("監視を終了します")
        finally:
            mt5.shutdown()

def main():
    """メイン処理"""
    monitor = MT5TradingMonitor()
    
    # 単発チェックモード（cron用）
    if os.environ.get('CRON_MODE'):
        if monitor.connect_mt5():
            monitor.monitor_positions()
            summary = monitor.generate_summary()
            print(summary)
            mt5.shutdown()
    else:
        # 継続監視モード
        monitor.run_monitor()

if __name__ == "__main__":
    main()