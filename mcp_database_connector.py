#!/usr/bin/env python3
"""
MCP データベース連携システム
VectorBT結果をMCPデータベースに保存・照会する機能
"""

import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import os

class MCPDatabaseConnector:
    """MCPデータベース連携クラス"""
    
    def __init__(self, db_path="mcp_trading_results.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # VectorBT結果テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vectorbt_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                fold_id INTEGER,
                cost_scenario TEXT,
                lookback_period INTEGER,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                total_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                raw_data TEXT
            )
        ''')
        
        # パフォーマンス比較テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_comparison (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                system_type TEXT,
                avg_return REAL,
                avg_sharpe REAL,
                execution_time REAL,
                memory_usage REAL,
                total_scenarios INTEGER,
                raw_data TEXT
            )
        ''')
        
        # 品質チェック結果テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                check_type TEXT,
                file_path TEXT,
                line_number INTEGER,
                issue_description TEXT,
                confidence_score REAL,
                fix_applied BOOLEAN DEFAULT FALSE,
                raw_data TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ データベース初期化完了: {self.db_path}")
    
    def save_vectorbt_results(self, results: List[Dict], session_id: str = None) -> bool:
        """VectorBT結果をデータベースに保存"""
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for result in results:
                cursor.execute('''
                    INSERT INTO vectorbt_results (
                        session_id, fold_id, cost_scenario, lookback_period,
                        total_return, sharpe_ratio, max_drawdown, total_trades,
                        win_rate, profit_factor, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    result.get('fold_id'),
                    result.get('cost_scenario'),
                    result.get('lookback_period'),
                    result.get('total_return'),
                    result.get('sharpe_ratio'),
                    result.get('max_drawdown'),
                    result.get('total_trades'),
                    result.get('win_rate'),
                    result.get('profit_factor'),
                    json.dumps(result)
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ VectorBT結果保存完了: {len(results)}件 (Session: {session_id})")
            return True
            
        except Exception as e:
            print(f"❌ VectorBT結果保存エラー: {e}")
            return False
    
    def save_performance_comparison(self, comparison: Dict, session_id: str = None) -> bool:
        """パフォーマンス比較結果を保存"""
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # VectorBT結果保存
            vbt_summary = comparison.get('vectorbt_summary', {})
            cursor.execute('''
                INSERT INTO performance_comparison (
                    session_id, system_type, avg_return, avg_sharpe,
                    execution_time, memory_usage, total_scenarios, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                'VectorBT',
                vbt_summary.get('avg_return'),
                vbt_summary.get('avg_sharpe'),
                0,  # execution_time - 後で実装
                0,  # memory_usage - 後で実装
                vbt_summary.get('total_scenarios'),
                json.dumps(comparison)
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ パフォーマンス比較保存完了 (Session: {session_id})")
            return True
            
        except Exception as e:
            print(f"❌ パフォーマンス比較保存エラー: {e}")
            return False
    
    def save_quality_issues(self, issues: List[Dict], session_id: str = None) -> bool:
        """品質チェック結果を保存"""
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for issue in issues:
                cursor.execute('''
                    INSERT INTO quality_checks (
                        session_id, check_type, file_path, line_number,
                        issue_description, confidence_score, fix_applied, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    issue.get('type'),
                    issue.get('file'),
                    issue.get('line'),
                    issue.get('description'),
                    issue.get('confidence', 0.0),
                    issue.get('fixed', False),
                    json.dumps(issue)
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 品質チェック結果保存完了: {len(issues)}件 (Session: {session_id})")
            return True
            
        except Exception as e:
            print(f"❌ 品質チェック結果保存エラー: {e}")
            return False
    
    def query_best_results(self, limit: int = 10) -> List[Dict]:
        """最優秀結果を照会"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM vectorbt_results 
                WHERE sharpe_ratio IS NOT NULL 
                ORDER BY sharpe_ratio DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            # 結果を辞書形式に変換
            columns = [
                'id', 'session_id', 'timestamp', 'fold_id', 'cost_scenario',
                'lookback_period', 'total_return', 'sharpe_ratio', 'max_drawdown',
                'total_trades', 'win_rate', 'profit_factor', 'raw_data'
            ]
            
            formatted_results = []
            for row in results:
                result = dict(zip(columns, row))
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ 最優秀結果照会エラー: {e}")
            return []
    
    def query_session_results(self, session_id: str) -> Dict:
        """セッション別結果照会"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # VectorBT結果
            vbt_df = pd.read_sql_query('''
                SELECT * FROM vectorbt_results 
                WHERE session_id = ?
            ''', conn, params=(session_id,))
            
            # パフォーマンス比較
            perf_df = pd.read_sql_query('''
                SELECT * FROM performance_comparison 
                WHERE session_id = ?
            ''', conn, params=(session_id,))
            
            # 品質チェック
            quality_df = pd.read_sql_query('''
                SELECT * FROM quality_checks 
                WHERE session_id = ?
            ''', conn, params=(session_id,))
            
            conn.close()
            
            return {
                'vectorbt_results': vbt_df,
                'performance_comparison': perf_df,
                'quality_checks': quality_df,
                'session_id': session_id
            }
            
        except Exception as e:
            print(f"❌ セッション結果照会エラー: {e}")
            return {}
    
    def get_database_stats(self) -> Dict:
        """データベース統計情報取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # VectorBT結果統計
            cursor.execute('SELECT COUNT(*) FROM vectorbt_results')
            stats['vectorbt_count'] = cursor.fetchone()[0]
            
            # パフォーマンス比較統計
            cursor.execute('SELECT COUNT(*) FROM performance_comparison')
            stats['performance_count'] = cursor.fetchone()[0]
            
            # 品質チェック統計
            cursor.execute('SELECT COUNT(*) FROM quality_checks')
            stats['quality_count'] = cursor.fetchone()[0]
            
            # セッション数
            cursor.execute('SELECT COUNT(DISTINCT session_id) FROM vectorbt_results')
            stats['total_sessions'] = cursor.fetchone()[0]
            
            # 最新セッション
            cursor.execute('SELECT session_id FROM vectorbt_results ORDER BY timestamp DESC LIMIT 1')
            result = cursor.fetchone()
            stats['latest_session'] = result[0] if result else None
            
            conn.close()
            
            return stats
            
        except Exception as e:
            print(f"❌ データベース統計取得エラー: {e}")
            return {}
    
    def export_to_csv(self, table_name: str, output_path: str = None) -> bool:
        """テーブルデータをCSVエクスポート"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{table_name}_export_{timestamp}.csv"
        
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(f'SELECT * FROM {table_name}', conn)
            conn.close()
            
            df.to_csv(output_path, index=False)
            print(f"✅ CSVエクスポート完了: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ CSVエクスポートエラー: {e}")
            return False

def main():
    """メイン実行"""
    print("🚀 MCP データベース連携システム")
    print("=" * 50)
    
    # データベース接続
    db = MCPDatabaseConnector()
    
    # 既存結果の読み込み・保存テスト
    if os.path.exists("vectorbt_wfa_results_20250716_235344.json"):
        print("\n📥 既存VectorBT結果読み込み...")
        with open("vectorbt_wfa_results_20250716_235344.json", 'r') as f:
            results = json.load(f)
        
        # データベース保存
        session_id = "vectorbt_test_20250716"
        db.save_vectorbt_results(results, session_id)
        
        # 結果照会
        print("\n📊 最優秀結果照会...")
        best_results = db.query_best_results(5)
        for i, result in enumerate(best_results, 1):
            print(f"  {i}. シャープレシオ: {result['sharpe_ratio']:.3f}, "
                  f"リターン: {result['total_return']:.2%}, "
                  f"セッション: {result['session_id']}")
    
    # データベース統計表示
    print("\n📈 データベース統計:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # CSVエクスポート
    print("\n📤 CSVエクスポート...")
    db.export_to_csv("vectorbt_results")

if __name__ == "__main__":
    main()