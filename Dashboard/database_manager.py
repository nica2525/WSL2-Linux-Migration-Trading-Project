#!/usr/bin/env python3
"""
Phase 2統計機能追加 - SQLiteデータベース統合
取引履歴保存・統計データキャッシュ・データ永続化層
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

class DatabaseManager:
    """SQLiteデータベース管理・統計データ永続化"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/trading_data.db"
        self.logger = logging.getLogger(__name__)
        self._ensure_database()
    
    def _ensure_database(self):
        """データベース・テーブル初期化"""
        with self.get_connection() as conn:
            # 口座履歴テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS account_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    balance REAL NOT NULL,
                    equity REAL NOT NULL,
                    profit REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ポジション履歴テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS position_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticket INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    profit REAL NOT NULL,
                    open_price REAL,
                    current_price REAL,
                    open_time TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 統計キャッシュテーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_type TEXT NOT NULL,
                    period TEXT NOT NULL,
                    value REAL NOT NULL,
                    data_json TEXT,
                    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stat_type, period)
                )
            """)
            
            # パフォーマンス指標テーブル
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    gross_profit REAL DEFAULT 0,
                    gross_loss REAL DEFAULT 0,
                    net_profit REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)
            
            # インデックス作成
            conn.execute("CREATE INDEX IF NOT EXISTS idx_account_timestamp ON account_history(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_position_timestamp ON position_history(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_position_ticket ON position_history(ticket)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_date ON performance_metrics(date)")
            
            conn.commit()
            self.logger.info("データベース初期化完了")
    
    @contextmanager
    def get_connection(self):
        """データベース接続コンテキストマネージャー"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"データベースエラー: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def store_mt5_data(self, data: Dict[str, Any]) -> bool:
        """MT5データを永続化"""
        try:
            with self.get_connection() as conn:
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                # 口座データ保存
                account = data.get('account', {})
                if account:
                    conn.execute("""
                        INSERT INTO account_history (timestamp, balance, equity, profit)
                        VALUES (?, ?, ?, ?)
                    """, (
                        timestamp,
                        account.get('balance', 0),
                        account.get('equity', 0),
                        account.get('profit', 0)
                    ))
                
                # ポジションデータ保存
                positions = data.get('positions', [])
                for position in positions:
                    conn.execute("""
                        INSERT INTO position_history (
                            timestamp, ticket, symbol, type, volume, profit,
                            open_price, current_price, open_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp,
                        position.get('ticket', 0),
                        position.get('symbol', ''),
                        position.get('type', ''),
                        position.get('volume', 0),
                        position.get('profit', 0),
                        position.get('open_price'),
                        position.get('current_price'),
                        position.get('open_time')
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"MT5データ保存エラー: {e}")
            return False
    
    def get_account_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """口座履歴取得"""
        try:
            with self.get_connection() as conn:
                cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                cursor = conn.execute("""
                    SELECT timestamp, balance, equity, profit, created_at
                    FROM account_history
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (cutoff_time,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"口座履歴取得エラー: {e}")
            return []
    
    def get_position_history(self, hours: int = 24, symbol: str = None) -> List[Dict[str, Any]]:
        """ポジション履歴取得"""
        try:
            with self.get_connection() as conn:
                cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                query = """
                    SELECT timestamp, ticket, symbol, type, volume, profit,
                           open_price, current_price, open_time, created_at
                    FROM position_history
                    WHERE timestamp > ?
                """
                params = [cutoff_time]
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"ポジション履歴取得エラー: {e}")
            return []
    
    def calculate_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """日別統計計算"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                # その日の全ポジション取得
                cursor = conn.execute("""
                    SELECT profit, type FROM position_history
                    WHERE DATE(timestamp) = ?
                """, (date,))
                
                positions = cursor.fetchall()
                
                if not positions:
                    return self._empty_stats()
                
                # 統計計算
                profits = [row['profit'] for row in positions]
                winning_trades = [p for p in profits if p > 0]
                losing_trades = [p for p in profits if p < 0]
                
                total_trades = len(profits)
                win_count = len(winning_trades)
                loss_count = len(losing_trades)
                
                gross_profit = sum(winning_trades) if winning_trades else 0
                gross_loss = sum(losing_trades) if losing_trades else 0
                net_profit = gross_profit + gross_loss
                
                win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
                profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
                
                # 最大ドローダウン計算（簡易版）
                max_drawdown = self._calculate_max_drawdown(profits)
                
                stats = {
                    'date': date,
                    'total_trades': total_trades,
                    'winning_trades': win_count,
                    'losing_trades': loss_count,
                    'gross_profit': gross_profit,
                    'gross_loss': gross_loss,
                    'net_profit': net_profit,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'max_drawdown': max_drawdown,
                    'avg_win': gross_profit / win_count if win_count > 0 else 0,
                    'avg_loss': gross_loss / loss_count if loss_count > 0 else 0
                }
                
                # データベースに保存（UPSERT）
                conn.execute("""
                    INSERT OR REPLACE INTO performance_metrics (
                        date, total_trades, winning_trades, losing_trades,
                        gross_profit, gross_loss, net_profit, max_drawdown,
                        win_rate, profit_factor
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date, total_trades, win_count, loss_count,
                    gross_profit, gross_loss, net_profit, max_drawdown,
                    win_rate, profit_factor
                ))
                
                conn.commit()
                return stats
                
        except Exception as e:
            self.logger.error(f"日別統計計算エラー: {e}")
            return self._empty_stats()
    
    def _calculate_max_drawdown(self, profits: List[float]) -> float:
        """最大ドローダウン計算"""
        if not profits:
            return 0.0
        
        cumulative = 0
        peak = 0
        max_dd = 0
        
        for profit in profits:
            cumulative += profit
            if cumulative > peak:
                peak = cumulative
            
            drawdown = peak - cumulative
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _empty_stats(self) -> Dict[str, Any]:
        """空の統計データ"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'net_profit': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0
        }
    
    def get_period_stats(self, days: int = 7) -> Dict[str, Any]:
        """期間統計取得"""
        try:
            with self.get_connection() as conn:
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
                cursor = conn.execute("""
                    SELECT * FROM performance_metrics
                    WHERE date >= ?
                    ORDER BY date DESC
                """, (start_date,))
                
                daily_stats = [dict(row) for row in cursor.fetchall()]
                
                if not daily_stats:
                    return self._empty_period_stats()
                
                # 期間集計
                total_trades = sum(s['total_trades'] for s in daily_stats)
                total_winning = sum(s['winning_trades'] for s in daily_stats)
                total_losing = sum(s['losing_trades'] for s in daily_stats)
                total_gross_profit = sum(s['gross_profit'] for s in daily_stats)
                total_gross_loss = sum(s['gross_loss'] for s in daily_stats)
                total_net_profit = sum(s['net_profit'] for s in daily_stats)
                max_dd = max(s['max_drawdown'] for s in daily_stats)
                
                period_win_rate = (total_winning / total_trades) * 100 if total_trades > 0 else 0
                period_pf = abs(total_gross_profit / total_gross_loss) if total_gross_loss != 0 else 0
                
                return {
                    'period_days': days,
                    'start_date': start_date,
                    'end_date': datetime.now().strftime('%Y-%m-%d'),
                    'total_trades': total_trades,
                    'winning_trades': total_winning,
                    'losing_trades': total_losing,
                    'gross_profit': total_gross_profit,
                    'gross_loss': total_gross_loss,
                    'net_profit': total_net_profit,
                    'win_rate': period_win_rate,
                    'profit_factor': period_pf,
                    'max_drawdown': max_dd,
                    'daily_avg_profit': total_net_profit / len(daily_stats),
                    'daily_stats': daily_stats
                }
                
        except Exception as e:
            self.logger.error(f"期間統計取得エラー: {e}")
            return self._empty_period_stats()
    
    def _empty_period_stats(self) -> Dict[str, Any]:
        """空の期間統計"""
        return {
            'period_days': 0,
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'net_profit': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'daily_avg_profit': 0,
            'daily_stats': []
        }
    
    def cache_statistics(self, stat_type: str, period: str, value: float, data: Dict[str, Any] = None):
        """統計キャッシュ保存"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO statistics_cache (stat_type, period, value, data_json)
                    VALUES (?, ?, ?, ?)
                """, (stat_type, period, value, json.dumps(data) if data else None))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"統計キャッシュエラー: {e}")
    
    def get_cached_statistics(self, stat_type: str, period: str) -> Optional[Tuple[float, Dict[str, Any]]]:
        """キャッシュされた統計取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT value, data_json, calculated_at FROM statistics_cache
                    WHERE stat_type = ? AND period = ?
                """, (stat_type, period))
                
                row = cursor.fetchone()
                if row:
                    data = json.loads(row['data_json']) if row['data_json'] else {}
                    return row['value'], data
                
                return None
                
        except Exception as e:
            self.logger.error(f"統計キャッシュ取得エラー: {e}")
            return None
    
    def cleanup_old_data(self, days: int = 30):
        """古いデータクリーンアップ"""
        try:
            with self.get_connection() as conn:
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # 古い口座履歴削除
                conn.execute("DELETE FROM account_history WHERE created_at < ?", (cutoff_date,))
                
                # 古いポジション履歴削除
                conn.execute("DELETE FROM position_history WHERE created_at < ?", (cutoff_date,))
                
                # 古い統計キャッシュ削除
                conn.execute("DELETE FROM statistics_cache WHERE calculated_at < ?", (cutoff_date,))
                
                conn.commit()
                self.logger.info(f"{days}日以前のデータをクリーンアップ完了")
                
        except Exception as e:
            self.logger.error(f"データクリーンアップエラー: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """データベース統計取得"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # テーブル行数取得
                for table in ['account_history', 'position_history', 'performance_metrics', 'statistics_cache']:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()['count']
                
                # データベースファイルサイズ
                db_path = Path(self.db_path)
                stats['db_size_mb'] = db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0
                
                # 最新データ日時
                cursor = conn.execute("SELECT MAX(timestamp) as latest FROM account_history")
                row = cursor.fetchone()
                stats['latest_data'] = row['latest'] if row['latest'] else None
                
                return stats
                
        except Exception as e:
            self.logger.error(f"データベース統計エラー: {e}")
            return {}

# 使用例・テスト関数
def test_database():
    """データベース動作テスト"""
    db = DatabaseManager()
    
    # テストデータ保存
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "account": {
            "balance": 3000000.0,
            "equity": 2990000.0,
            "profit": -10000.0
        },
        "positions": [
            {
                "ticket": 123456,
                "symbol": "EURUSD",
                "type": "buy",
                "volume": 0.01,
                "profit": -50.0,
                "open_price": 1.0850,
                "current_price": 1.0840,
                "open_time": datetime.now().isoformat()
            }
        ]
    }
    
    success = db.store_mt5_data(test_data)
    print(f"データ保存: {success}")
    
    # 履歴取得テスト
    account_history = db.get_account_history(hours=1)
    print(f"口座履歴: {len(account_history)}件")
    
    position_history = db.get_position_history(hours=1)
    print(f"ポジション履歴: {len(position_history)}件")
    
    # 統計計算テスト
    daily_stats = db.calculate_daily_stats()
    print(f"日別統計: {daily_stats}")
    
    # データベース統計
    db_stats = db.get_database_stats()
    print(f"DB統計: {db_stats}")

if __name__ == "__main__":
    test_database()