#!/usr/bin/env python3
"""
MT5取引監視システム（改善版）
- JamesORB EAの取引を監視
- 取引発生時に記録・通知
- 統計情報の収集
- Wine環境対応
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import threading
import fcntl

# Wine環境でのMetaTrader5インポート処理
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    # Wine環境の場合はRPYCクライアントを使用
    try:
        import rpyc
    except ImportError:
        rpyc = None

# ログ設定
LOG_DIR = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/Trading"
os.makedirs(LOG_DIR, exist_ok=True)

# ロガー設定（ログローテーション対応）
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ログファイルハンドラー（5MB x 5ファイル）
log_file = os.path.join(LOG_DIR, 'monitor.log')
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# コンソールハンドラー
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 取引記録ファイル
TRADE_RECORD_FILE = os.path.join(LOG_DIR, "trades.json")
TRADE_RECORD_LOCK = os.path.join(LOG_DIR, ".trades.lock")

class MT5TradingMonitor:
    def __init__(self):
        # EAマジックナンバー（JamesORB EA用）
        self.ea_magic = self._get_ea_magic()
        self.symbol = "EURUSD"
        self.last_position_count = 0
        self.trades = self.load_trades()
        self.mt5_connection = None
        self.use_rpyc = False
        
    def _get_ea_magic(self):
        """EAのマジックナンバーを取得（設定ファイルから読み込み可能）"""
        # TODO: 実際のJamesORB EAのマジックナンバーを確認して設定
        # 現在は仮の値
        return 12345
    
    def load_trades(self):
        """既存の取引記録を読み込み（ファイルロック対応）"""
        if not os.path.exists(TRADE_RECORD_FILE):
            return []
            
        try:
            # ファイルロックを使用して安全に読み込み
            with open(TRADE_RECORD_FILE, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except json.JSONDecodeError as e:
            logger.error(f"JSON読み込みエラー: {e}")
            # バックアップを作成
            backup_file = f"{TRADE_RECORD_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(TRADE_RECORD_FILE, backup_file)
            logger.info(f"破損ファイルをバックアップ: {backup_file}")
            return []
        except Exception as e:
            logger.error(f"取引記録読み込みエラー: {e}")
            return []
    
    def save_trades(self):
        """取引記録を保存（ファイルロック・アトミック書き込み）"""
        temp_file = f"{TRADE_RECORD_FILE}.tmp"
        
        try:
            # 一時ファイルに書き込み
            with open(temp_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(self.trades, f, indent=2, ensure_ascii=False)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # アトミックに置換
            os.replace(temp_file, TRADE_RECORD_FILE)
            
        except Exception as e:
            logger.error(f"取引記録保存エラー: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def connect_mt5(self):
        """MT5に接続（Wine環境対応）"""
        global MT5_AVAILABLE
        
        # 直接接続を試行
        if MT5_AVAILABLE:
            try:
                if not mt5.initialize():
                    error = mt5.last_error()
                    logger.error(f"MT5接続失敗: {error}")
                    return False
                logger.info("MT5接続成功（直接接続）")
                return True
            except Exception as e:
                logger.warning(f"直接接続失敗、RPYCを試行: {e}")
                MT5_AVAILABLE = False
        
        # Wine環境の場合、RPYC接続を試行
        if rpyc:
            try:
                self.mt5_connection = rpyc.connect("localhost", 18812)
                self.use_rpyc = True
                logger.info("MT5接続成功（RPYC経由）")
                return True
            except Exception as e:
                logger.error(f"RPYC接続失敗: {e}")
                return False
        
        logger.error("MT5接続方法が利用できません")
        return False
    
    def get_positions(self):
        """ポジション情報を取得（接続方法に応じて切り替え）"""
        try:
            if self.use_rpyc:
                positions_data = self.mt5_connection.root.positions_get(symbol=self.symbol)
                # RPYCの場合、辞書形式で返される
                return [type('Position', (), pos) for pos in positions_data] if positions_data else []
            else:
                return mt5.positions_get(symbol=self.symbol) or []
        except Exception as e:
            logger.error(f"ポジション取得エラー: {e}")
            return []
    
    def get_history_deals(self, date_from, date_to):
        """取引履歴を取得"""
        try:
            if self.use_rpyc:
                deals_data = self.mt5_connection.root.history_deals_get(date_from, date_to)
                return [type('Deal', (), deal) for deal in deals_data] if deals_data else []
            else:
                return mt5.history_deals_get(date_from, date_to) or []
        except Exception as e:
            logger.error(f"履歴取得エラー: {e}")
            return []
    
    def monitor_positions(self):
        """ポジションを監視"""
        positions = self.get_positions()
        
        # シンボルでフィルタリング
        symbol_positions = [p for p in positions if getattr(p, 'symbol', '') == self.symbol]
        current_count = len(symbol_positions)
        
        # 新規ポジション検出
        if current_count > self.last_position_count:
            logger.info(f"🔔 新規ポジション検出！ ({current_count}個)")
            
            # 既存チケット番号のセット
            existing_tickets = {t['ticket'] for t in self.trades if t['status'] == 'OPEN'}
            
            for pos in symbol_positions:
                # 新規かつJamesORB EAのポジションか確認
                ticket = getattr(pos, 'ticket', None)
                magic = getattr(pos, 'magic', None)
                
                if ticket and ticket not in existing_tickets and magic == self.ea_magic:
                    self.record_new_position(pos)
        
        # ポジション決済検出
        elif current_count < self.last_position_count:
            logger.info(f"💰 ポジション決済検出！ (残り{current_count}個)")
            self.check_closed_positions()
        
        self.last_position_count = current_count
    
    def record_new_position(self, position):
        """新規ポジションを記録"""
        try:
            trade_info = {
                "ticket": getattr(position, 'ticket', 0),
                "symbol": getattr(position, 'symbol', ''),
                "type": "BUY" if getattr(position, 'type', -1) == 0 else "SELL",
                "volume": getattr(position, 'volume', 0),
                "open_price": getattr(position, 'price_open', 0),
                "open_time": datetime.fromtimestamp(getattr(position, 'time', 0)).isoformat(),
                "sl": getattr(position, 'sl', 0),
                "tp": getattr(position, 'tp', 0),
                "status": "OPEN",
                "profit": 0,
                "magic": getattr(position, 'magic', 0)
            }
            
            # 重複チェック
            if not any(t['ticket'] == trade_info['ticket'] for t in self.trades):
                self.trades.append(trade_info)
                self.save_trades()
                logger.info(f"新規取引記録: {trade_info['type']} {trade_info['volume']}ロット @ {trade_info['open_price']}")
            
        except Exception as e:
            logger.error(f"ポジション記録エラー: {e}")
    
    def check_closed_positions(self):
        """決済されたポジションを確認"""
        # 過去2日間の履歴を確認
        today = datetime.now()
        two_days_ago = today - timedelta(days=2)
        
        deals = self.get_history_deals(two_days_ago, today)
        
        for deal in deals:
            symbol = getattr(deal, 'symbol', '')
            magic = getattr(deal, 'magic', None)
            
            if symbol == self.symbol and magic == self.ea_magic:
                self.update_closed_position(deal)
    
    def update_closed_position(self, deal):
        """決済情報を更新"""
        position_id = getattr(deal, 'position_id', None)
        if not position_id:
            return
            
        for trade in self.trades:
            if trade.get("ticket") == position_id and trade["status"] == "OPEN":
                trade["status"] = "CLOSED"
                trade["close_price"] = getattr(deal, 'price', 0)
                trade["close_time"] = datetime.fromtimestamp(getattr(deal, 'time', 0)).isoformat()
                trade["profit"] = getattr(deal, 'profit', 0)
                trade["commission"] = getattr(deal, 'commission', 0)
                trade["swap"] = getattr(deal, 'swap', 0)
                
                self.save_trades()
                logger.info(f"取引決済: チケット{trade['ticket']} 利益: ${trade['profit']:.2f}")
                break
    
    def generate_summary(self):
        """取引サマリーを生成"""
        if not self.trades:
            return "取引履歴なし"
        
        total_trades = len(self.trades)
        closed_trades = [t for t in self.trades if t["status"] == "CLOSED"]
        open_trades = [t for t in self.trades if t["status"] == "OPEN"]
        
        if closed_trades:
            total_profit = sum(t.get("profit", 0) for t in closed_trades)
            total_commission = sum(t.get("commission", 0) for t in closed_trades)
            total_swap = sum(t.get("swap", 0) for t in closed_trades)
            net_profit = total_profit + total_commission + total_swap
            
            win_trades = [t for t in closed_trades if t.get("profit", 0) > 0]
            win_rate = len(win_trades) / len(closed_trades) * 100 if closed_trades else 0
        else:
            total_profit = net_profit = 0
            win_rate = 0
        
        summary = f"""
=== JamesORB EA 取引サマリー ===
総取引数: {total_trades}
オープン中: {len(open_trades)}
決済済み: {len(closed_trades)}
総利益: ${total_profit:.2f}
純利益: ${net_profit:.2f}
勝率: {win_rate:.1f}%
監視時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================
"""
        return summary
    
    def run_monitor(self, interval=60):
        """監視を実行"""
        logger.info("=== MT5取引監視開始 ===")
        
        if not self.connect_mt5():
            return
        
        error_count = 0
        max_errors = 5
        
        try:
            while True:
                try:
                    self.monitor_positions()
                    error_count = 0  # 成功したらリセット
                    
                    # 定期的にサマリー出力（15分毎）
                    if datetime.now().minute % 15 == 0:
                        summary = self.generate_summary()
                        logger.info(summary)
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"監視エラー ({error_count}/{max_errors}): {e}")
                    
                    if error_count >= max_errors:
                        logger.error("エラー回数上限に達しました。再接続を試みます。")
                        self.disconnect_mt5()
                        time.sleep(30)
                        if not self.connect_mt5():
                            logger.error("再接続失敗。監視を終了します。")
                            break
                        error_count = 0
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("監視を終了します")
        finally:
            self.disconnect_mt5()
    
    def disconnect_mt5(self):
        """MT5接続を切断"""
        try:
            if self.use_rpyc and self.mt5_connection:
                self.mt5_connection.close()
            elif MT5_AVAILABLE:
                mt5.shutdown()
            logger.info("MT5接続を切断しました")
        except Exception as e:
            logger.error(f"切断エラー: {e}")

def main():
    """メイン処理"""
    monitor = MT5TradingMonitor()
    
    # 単発チェックモード（cron用）
    if os.environ.get('CRON_MODE'):
        if monitor.connect_mt5():
            try:
                monitor.monitor_positions()
                summary = monitor.generate_summary()
                print(summary)
            finally:
                monitor.disconnect_mt5()
    else:
        # 継続監視モード
        monitor.run_monitor()

if __name__ == "__main__":
    main()