"""
Phase 3-A: Real Data Integration Manager
実データ統合システム - MT5リアルタイムデータの収集・永続化
"""

import sqlite3
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
# MT5インポート（Wine環境対応）
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    import mt5_mock as mt5
    MT5_AVAILABLE = False
from flask_socketio import emit
# import numpy as np  # テスト時は無効化

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('RealDataIntegration')


class RealDataIntegrationManager:
    """実データ統合マネージャー"""
    
    def __init__(self, socketio=None):
        self.db_path = 'dashboard.db'
        self.socketio = socketio
        self.lock = threading.Lock()
        self.last_update = {}
        self.is_running = False
        self.tasks = {}
        
        # MT5接続状態
        self.mt5_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        # データベース接続プール
        self.db_connections = {}
        
    def initialize(self):
        """実データ収集の初期化"""
        try:
            # MT5接続確認
            if not self._connect_mt5():
                logger.error("MT5接続に失敗しました")
                return False
            
            # データベース初期化確認
            self._verify_database_schema()
            
            # バックグラウンドタスク開始
            self.start_background_tasks()
            
            logger.info("実データ統合システムが正常に初期化されました")
            return True
            
        except Exception as e:
            logger.error(f"初期化エラー: {e}")
            return False
    
    def _connect_mt5(self):
        """MT5への接続・再接続"""
        for attempt in range(self.max_reconnect_attempts):
            try:
                if mt5.initialize():
                    self.mt5_connected = True
                    self.reconnect_attempts = 0
                    logger.info("MT5に正常に接続しました")
                    return True
                time.sleep(5)
            except Exception as e:
                logger.warning(f"MT5接続試行 {attempt + 1}/{self.max_reconnect_attempts} 失敗: {e}")
        
        self.mt5_connected = False
        return False
    
    def _get_db_connection(self):
        """スレッドセーフなデータベース接続取得"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.db_connections:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.db_connections[thread_id] = conn
            
        return self.db_connections[thread_id]
    
    def _verify_database_schema(self):
        """データベーススキーマの検証"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # 必要なテーブルの存在確認
        required_tables = [
            'account_history', 'position_details', 
            'statistics_cache', 'system_monitoring'
        ]
        
        for table in required_tables:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not cursor.fetchone():
                logger.error(f"必要なテーブル '{table}' が存在しません")
                raise Exception(f"Missing required table: {table}")
        
        logger.info("データベーススキーマ検証完了")
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        self.is_running = True
        
        # 口座情報更新タスク（5秒間隔）
        self._start_task('account_update', 5.0, self.update_account_data)
        
        # ポジション情報更新タスク（3秒間隔）
        self._start_task('position_update', 3.0, self.update_position_data)
        
        # 統計計算タスク（60秒間隔）
        self._start_task('statistics_calc', 60.0, self.calculate_statistics)
        
        # システム監視タスク（30秒間隔）
        self._start_task('system_monitor', 30.0, self.monitor_system_health)
        
        logger.info("すべてのバックグラウンドタスクを開始しました")
    
    def _start_task(self, task_name: str, interval: float, func):
        """個別タスクの開始"""
        def run_task():
            while self.is_running:
                try:
                    func()
                except Exception as e:
                    logger.error(f"{task_name} タスクエラー: {e}")
                time.sleep(interval)
        
        task_thread = threading.Thread(target=run_task, daemon=True)
        task_thread.start()
        self.tasks[task_name] = task_thread
    
    def update_account_data(self):
        """口座データの実時間更新"""
        if not self.mt5_connected:
            if not self._connect_mt5():
                return
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                self._log_error("口座情報取得失敗")
                return
            
            # データベースに保存
            with self.lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO account_history (
                        balance, equity, margin, free_margin, margin_level, profit,
                        server_time, trade_allowed, trade_expert, margin_so_mode,
                        margin_so_call, margin_so_so, currency_digits, fifo_close
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_info.balance,
                    account_info.equity,
                    account_info.margin,
                    account_info.margin_free,
                    account_info.margin_level,
                    account_info.profit,
                    datetime.fromtimestamp(account_info.server_time) if hasattr(account_info, 'server_time') else datetime.now(),
                    account_info.trade_allowed if hasattr(account_info, 'trade_allowed') else True,
                    account_info.trade_expert if hasattr(account_info, 'trade_expert') else True,
                    account_info.margin_so_mode if hasattr(account_info, 'margin_so_mode') else 0,
                    account_info.margin_so_call if hasattr(account_info, 'margin_so_call') else 0,
                    account_info.margin_so_so if hasattr(account_info, 'margin_so_so') else 0,
                    account_info.currency_digits if hasattr(account_info, 'currency_digits') else 2,
                    account_info.fifo_close if hasattr(account_info, 'fifo_close') else False
                ))
                conn.commit()
            
            # WebSocket経由でクライアントに通知
            if self.socketio:
                self.socketio.emit('account_update', {
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'margin_level': account_info.margin_level,
                    'profit': account_info.profit,
                    'timestamp': datetime.now().isoformat()
                })
            
            self.last_update['account'] = datetime.now()
            
        except Exception as e:
            self._log_error(f"口座データ更新エラー: {e}")
    
    def update_position_data(self):
        """ポジションデータの実時間更新"""
        if not self.mt5_connected:
            if not self._connect_mt5():
                return
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                positions = []
            
            position_list = []
            
            for position in positions:
                # データベースに保存または更新
                with self.lock:
                    conn = self._get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO position_details (
                            ticket, symbol, type, volume, price_open, price_current,
                            sl, tp, profit, swap, commission, magic, comment,
                            identifier, reason, external_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        position.ticket,
                        position.symbol,
                        position.type,
                        position.volume,
                        position.price_open,
                        position.price_current,
                        position.sl,
                        position.tp,
                        position.profit,
                        position.swap,
                        position.commission if hasattr(position, 'commission') else 0,
                        position.magic,
                        position.comment,
                        position.identifier if hasattr(position, 'identifier') else 0,
                        position.reason if hasattr(position, 'reason') else 0,
                        position.external_id if hasattr(position, 'external_id') else None
                    ))
                    conn.commit()
                
                # WebSocket用データ準備
                position_list.append({
                    'ticket': position.ticket,
                    'symbol': position.symbol,
                    'type': 'BUY' if position.type == 0 else 'SELL',
                    'volume': position.volume,
                    'open_price': position.price_open,
                    'current_price': position.price_current,
                    'profit': position.profit,
                    'swap': position.swap,
                    'sl': position.sl,
                    'tp': position.tp
                })
            
            # WebSocket経由でクライアントに通知
            if self.socketio:
                self.socketio.emit('positions_update', {
                    'positions': position_list,
                    'count': len(position_list),
                    'timestamp': datetime.now().isoformat()
                })
            
            self.last_update['positions'] = datetime.now()
            
        except Exception as e:
            self._log_error(f"ポジションデータ更新エラー: {e}")
    
    def calculate_statistics(self):
        """統計データの定期計算・キャッシュ"""
        try:
            # 日次統計計算
            daily_stats = self._calculate_period_statistics('daily', 1)
            self._cache_statistics('daily', daily_stats)
            
            # 週次統計計算
            weekly_stats = self._calculate_period_statistics('weekly', 7)
            self._cache_statistics('weekly', weekly_stats)
            
            # 月次統計計算
            monthly_stats = self._calculate_period_statistics('monthly', 30)
            self._cache_statistics('monthly', monthly_stats)
            
            # WebSocket経由で統計更新通知
            if self.socketio:
                self.socketio.emit('statistics_update', {
                    'daily': daily_stats,
                    'weekly': weekly_stats,
                    'monthly': monthly_stats,
                    'timestamp': datetime.now().isoformat()
                })
            
            self.last_update['statistics'] = datetime.now()
            
        except Exception as e:
            self._log_error(f"統計計算エラー: {e}")
    
    def _calculate_period_statistics(self, period_type: str, days: int) -> Dict:
        """期間別統計計算"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # 期間内の取引データ取得
        cursor.execute("""
            SELECT profit, swap, commission 
            FROM position_details 
            WHERE timestamp BETWEEN ? AND ? AND profit != 0
            ORDER BY timestamp
        """, (start_date, end_date))
        
        trades = cursor.fetchall()
        
        if not trades:
            return self._empty_statistics()
        
        # 純利益計算（profit + swap - commission）
        net_profits = [
            trade['profit'] + trade['swap'] - abs(trade['commission']) 
            for trade in trades
        ]
        
        winning_trades = [p for p in net_profits if p > 0]
        losing_trades = [p for p in net_profits if p < 0]
        
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        net_profit = sum(net_profits)
        
        # 高度統計指標計算
        statistics = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) * 100 if trades else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': net_profit,
            'profit_factor': gross_profit / gross_loss if gross_loss > 0 else 0,
            'expected_payoff': net_profit / len(trades) if trades else 0,
            'sharpe_ratio': self._calculate_sharpe_ratio(net_profits),
            'max_drawdown': self._calculate_max_drawdown(net_profits),
            'consecutive_stats': self._calculate_consecutive_stats(net_profits)
        }
        
        return statistics
    
    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """シャープレシオ計算"""
        if len(returns) < 2:
            return 0
        
        # 標準ライブラリで統計計算
        mean_return = sum(returns) / len(returns)
        variance = sum((x - mean_return) ** 2 for x in returns) / (len(returns) - 1)
        std_return = variance ** 0.5
        
        if std_return == 0:
            return 0
        
        # 年率換算（252営業日）
        sharpe = (mean_return / std_return) * (252 ** 0.5)
        return round(sharpe, 3)
    
    def _calculate_max_drawdown(self, profits: List[float]) -> float:
        """最大ドローダウン計算"""
        if not profits:
            return 0
        
        cumulative = []
        running_sum = 0
        
        for profit in profits:
            running_sum += profit
            cumulative.append(running_sum)
        
        peak = cumulative[0]
        max_dd = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_dd:
                max_dd = drawdown
        
        return round(max_dd, 2)
    
    def _calculate_consecutive_stats(self, profits: List[float]) -> Dict:
        """連勝・連敗統計"""
        if not profits:
            return {'max_consecutive_wins': 0, 'max_consecutive_losses': 0}
        
        max_wins = current_wins = 0
        max_losses = current_losses = 0
        
        for profit in profits:
            if profit > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif profit < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return {
            'max_consecutive_wins': max_wins,
            'max_consecutive_losses': max_losses
        }
    
    def _cache_statistics(self, period_type: str, stats: Dict):
        """統計結果のキャッシュ保存"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        calculation_date = datetime.now().date()
        
        cursor.execute("""
            INSERT OR REPLACE INTO statistics_cache (
                calculation_date, period_type, total_trades, winning_trades,
                losing_trades, gross_profit, gross_loss, profit_factor,
                expected_payoff, sharpe_ratio, maximal_drawdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            calculation_date,
            period_type,
            stats['total_trades'],
            stats['winning_trades'],
            stats['losing_trades'],
            stats['gross_profit'],
            stats['gross_loss'],
            stats['profit_factor'],
            stats['expected_payoff'],
            stats['sharpe_ratio'],
            stats['max_drawdown']
        ))
        
        conn.commit()
    
    def monitor_system_health(self):
        """システムヘルス監視"""
        try:
            # MT5接続状態
            mt5_status = 'connected' if self.mt5_connected else 'disconnected'
            self._log_metric('mt5_connection', 'status', 1 if self.mt5_connected else 0, mt5_status)
            
            # データベースサイズ
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM account_history")
            account_records = cursor.fetchone()['count']
            self._log_metric('database', 'account_records', account_records)
            
            # 最終更新時刻チェック
            for component, last_time in self.last_update.items():
                if last_time:
                    seconds_since_update = (datetime.now() - last_time).total_seconds()
                    status = 'normal' if seconds_since_update < 300 else 'warning'
                    self._log_metric(component, 'last_update_seconds', seconds_since_update, status)
            
        except Exception as e:
            self._log_error(f"システム監視エラー: {e}")
    
    def _log_metric(self, component: str, metric_name: str, metric_value: float, status: str = 'normal'):
        """メトリクスのログ記録"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_monitoring (
                component, metric_name, metric_value, status
            ) VALUES (?, ?, ?, ?)
        """, (component, metric_name, metric_value, status))
        
        conn.commit()
    
    def _log_error(self, message: str):
        """エラーログ記録"""
        logger.error(message)
        self._log_metric('system', 'error', 1, 'critical')
    
    def _empty_statistics(self) -> Dict:
        """空の統計結果"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'expected_payoff': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'consecutive_stats': {
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            }
        }
    
    def stop(self):
        """バックグラウンドタスクの停止"""
        self.is_running = False
        logger.info("実データ統合システムを停止しています...")
        
        # MT5接続解除
        if self.mt5_connected:
            mt5.shutdown()
        
        # データベース接続クローズ
        for conn in self.db_connections.values():
            conn.close()
        
        logger.info("実データ統合システムが停止しました")


# テスト実行用
if __name__ == "__main__":
    manager = RealDataIntegrationManager()
    
    if manager.initialize():
        print("実データ統合システムが開始されました。Ctrl+Cで停止します。")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop()
            print("\n実データ統合システムを停止しました。")
    else:
        print("実データ統合システムの初期化に失敗しました。")