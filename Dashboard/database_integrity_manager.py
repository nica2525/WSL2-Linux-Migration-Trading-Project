"""
Database Integrity Manager - データベース整合性管理システム
Phase 3移行の完全実装とデータ整合性保証
"""

import sqlite3
import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import shutil

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseIntegrityManager:
    """データベース整合性管理クラス"""
    
    def __init__(self, db_path: str = "dashboard.db"):
        self.db_path = db_path
        self.backup_dir = "database_backups"
        self.migration_log = []
        
        # バックアップディレクトリ作成
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self) -> str:
        """データベースのバックアップ作成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"dashboard_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # データベースファイルのコピー
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"✅ データベースバックアップ作成: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ バックアップ作成エラー: {e}")
            return ""
    
    def verify_database_structure(self) -> Dict:
        """データベース構造の検証"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブル一覧取得
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            structure_info = {
                'tables': {},
                'issues': [],
                'verification_time': datetime.now().isoformat()
            }
            
            # 各テーブルの構造確認
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                structure_info['tables'][table] = {
                    'columns': [{'name': col[1], 'type': col[2], 'notnull': col[3], 'default': col[4]} for col in columns],
                    'column_count': len(columns)
                }
            
            # Phase 3必須テーブルの確認
            required_tables = ['account_history', 'position_details', 'statistics_cache', 'system_monitoring']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                structure_info['issues'].append({
                    'type': 'missing_tables',
                    'tables': missing_tables,
                    'severity': 'high'
                })
            
            # account_historyのPhase 3カラム確認
            if 'account_history' in structure_info['tables']:
                account_columns = [col['name'] for col in structure_info['tables']['account_history']['columns']]
                required_columns = ['server_time', 'trade_allowed', 'trade_expert', 'margin_so_mode']
                missing_columns = [col for col in required_columns if col not in account_columns]
                
                if missing_columns:
                    structure_info['issues'].append({
                        'type': 'missing_columns',
                        'table': 'account_history',
                        'columns': missing_columns,
                        'severity': 'medium'
                    })
            
            conn.close()
            
            # 検証結果
            structure_info['status'] = 'healthy' if not structure_info['issues'] else 'needs_migration'
            
            return structure_info
            
        except Exception as e:
            logger.error(f"データベース構造検証エラー: {e}")
            return {'error': str(e)}
    
    def check_data_integrity(self) -> Dict:
        """データ整合性の検証"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            integrity_info = {
                'checks': {},
                'issues': [],
                'check_time': datetime.now().isoformat()
            }
            
            # 1. 外部キー制約チェック
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            if fk_violations:
                integrity_info['issues'].append({
                    'type': 'foreign_key_violations',
                    'count': len(fk_violations),
                    'details': fk_violations[:5]  # 最初の5件のみ
                })
            
            # 2. データ型整合性チェック
            tables_to_check = ['account_history', 'position_details', 'position_history']
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    integrity_info['checks'][table] = {'record_count': count}
                    
                    # NULLチェック（必須フィールド）
                    if table == 'account_history':
                        cursor.execute("SELECT COUNT(*) FROM account_history WHERE balance IS NULL OR equity IS NULL")
                        null_count = cursor.fetchone()[0]
                        if null_count > 0:
                            integrity_info['issues'].append({
                                'type': 'null_required_fields',
                                'table': table,
                                'count': null_count
                            })
                    
                except sqlite3.OperationalError as e:
                    integrity_info['issues'].append({
                        'type': 'table_access_error',
                        'table': table,
                        'error': str(e)
                    })
            
            # 3. 重複データチェック
            duplicate_checks = [
                ("position_details", "ticket, timestamp"),
                ("statistics_cache", "calculation_date, period_type")
            ]
            
            for table, fields in duplicate_checks:
                try:
                    cursor.execute(f"""
                        SELECT {fields}, COUNT(*) as cnt 
                        FROM {table} 
                        GROUP BY {fields} 
                        HAVING COUNT(*) > 1
                    """)
                    duplicates = cursor.fetchall()
                    if duplicates:
                        integrity_info['issues'].append({
                            'type': 'duplicate_records',
                            'table': table,
                            'count': len(duplicates)
                        })
                except sqlite3.OperationalError:
                    # テーブルが存在しない場合はスキップ
                    pass
            
            conn.close()
            
            # 整合性ステータス
            integrity_info['status'] = 'healthy' if not integrity_info['issues'] else 'has_issues'
            
            return integrity_info
            
        except Exception as e:
            logger.error(f"データ整合性チェックエラー: {e}")
            return {'error': str(e)}
    
    def perform_migration(self) -> Dict:
        """Phase 3マイグレーションの実行"""
        try:
            migration_result = {
                'started_at': datetime.now().isoformat(),
                'steps': [],
                'success': False,
                'backup_created': '',
                'errors': []
            }
            
            # 1. バックアップ作成
            backup_path = self.create_backup()
            migration_result['backup_created'] = backup_path
            
            if not backup_path:
                migration_result['errors'].append("バックアップ作成失敗")
                return migration_result
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 2. Phase 3スキーマ適用
            schema_steps = [
                {
                    'description': 'account_history テーブル拡張',
                    'sql': """
                        ALTER TABLE account_history ADD COLUMN server_time DATETIME;
                        ALTER TABLE account_history ADD COLUMN trade_allowed BOOLEAN DEFAULT 1;
                        ALTER TABLE account_history ADD COLUMN trade_expert BOOLEAN DEFAULT 1;
                        ALTER TABLE account_history ADD COLUMN margin_so_mode INTEGER DEFAULT 0;
                        ALTER TABLE account_history ADD COLUMN margin_so_call REAL DEFAULT 0;
                        ALTER TABLE account_history ADD COLUMN margin_so_so REAL DEFAULT 0;
                        ALTER TABLE account_history ADD COLUMN currency_digits INTEGER DEFAULT 2;
                        ALTER TABLE account_history ADD COLUMN fifo_close BOOLEAN DEFAULT 0;
                    """
                },
                {
                    'description': 'position_details テーブル作成',
                    'sql': """
                        CREATE TABLE IF NOT EXISTS position_details (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ticket INTEGER NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            symbol VARCHAR(10) NOT NULL,
                            type INTEGER NOT NULL,
                            volume REAL NOT NULL,
                            price_open REAL NOT NULL,
                            price_current REAL,
                            sl REAL DEFAULT 0,
                            tp REAL DEFAULT 0,
                            profit REAL NOT NULL,
                            swap REAL DEFAULT 0,
                            commission REAL DEFAULT 0,
                            magic INTEGER DEFAULT 0,
                            comment TEXT,
                            identifier INTEGER,
                            reason INTEGER DEFAULT 0,
                            external_id VARCHAR(50)
                        );
                    """
                },
                {
                    'description': 'statistics_cache テーブル作成',
                    'sql': """
                        CREATE TABLE IF NOT EXISTS statistics_cache (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            calculation_date DATE NOT NULL,
                            period_type VARCHAR(20) NOT NULL,
                            total_trades INTEGER DEFAULT 0,
                            winning_trades INTEGER DEFAULT 0,
                            losing_trades INTEGER DEFAULT 0,
                            gross_profit REAL DEFAULT 0,
                            gross_loss REAL DEFAULT 0,
                            profit_factor REAL DEFAULT 0,
                            expected_payoff REAL DEFAULT 0,
                            absolute_drawdown REAL DEFAULT 0,
                            maximal_drawdown REAL DEFAULT 0,
                            relative_drawdown REAL DEFAULT 0,
                            sharpe_ratio REAL DEFAULT 0,
                            sortino_ratio REAL DEFAULT 0,
                            calmar_ratio REAL DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(calculation_date, period_type)
                        );
                    """
                },
                {
                    'description': 'system_monitoring テーブル作成',
                    'sql': """
                        CREATE TABLE IF NOT EXISTS system_monitoring (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            component VARCHAR(50) NOT NULL,
                            metric_name VARCHAR(50) NOT NULL,
                            metric_value REAL NOT NULL,
                            status VARCHAR(20) DEFAULT 'normal',
                            message TEXT
                        );
                    """
                },
                {
                    'description': 'インデックス作成',
                    'sql': """
                        CREATE INDEX IF NOT EXISTS idx_position_details_timestamp ON position_details(timestamp);
                        CREATE INDEX IF NOT EXISTS idx_position_details_ticket ON position_details(ticket);
                        CREATE INDEX IF NOT EXISTS idx_statistics_cache_date_type ON statistics_cache(calculation_date, period_type);
                        CREATE INDEX IF NOT EXISTS idx_system_monitoring_timestamp ON system_monitoring(timestamp);
                        CREATE INDEX IF NOT EXISTS idx_system_monitoring_component ON system_monitoring(component);
                    """
                }
            ]
            
            # 各ステップを実行
            for step in schema_steps:
                try:
                    # 複数のSQL文を分割実行
                    sql_statements = [stmt.strip() for stmt in step['sql'].split(';') if stmt.strip()]
                    
                    for sql in sql_statements:
                        cursor.execute(sql)
                    
                    conn.commit()
                    
                    migration_result['steps'].append({
                        'description': step['description'],
                        'status': 'success',
                        'executed_at': datetime.now().isoformat()
                    })
                    
                    logger.info(f"✅ {step['description']} 完了")
                    
                except Exception as e:
                    error_msg = f"{step['description']} エラー: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    
                    migration_result['steps'].append({
                        'description': step['description'],
                        'status': 'error',
                        'error': str(e),
                        'executed_at': datetime.now().isoformat()
                    })
                    
                    migration_result['errors'].append(error_msg)
            
            conn.close()
            
            # 3. マイグレーション完了確認
            if not migration_result['errors']:
                migration_result['success'] = True
                logger.info("✅ Phase 3 データベースマイグレーション完了")
            else:
                logger.warning(f"⚠️ マイグレーション完了（{len(migration_result['errors'])}件のエラー）")
            
            migration_result['completed_at'] = datetime.now().isoformat()
            
            return migration_result
            
        except Exception as e:
            logger.error(f"マイグレーション実行エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def optimize_database(self) -> Dict:
        """データベース最適化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            optimization_result = {
                'started_at': datetime.now().isoformat(),
                'operations': [],
                'success': False
            }
            
            # 1. VACUUM実行
            cursor.execute("VACUUM")
            optimization_result['operations'].append({
                'operation': 'VACUUM',
                'status': 'completed',
                'description': 'データベースファイルの最適化・断片化解消'
            })
            
            # 2. ANALYZE実行
            cursor.execute("ANALYZE")
            optimization_result['operations'].append({
                'operation': 'ANALYZE',
                'status': 'completed',
                'description': 'クエリオプティマイザ統計情報の更新'
            })
            
            # 3. インデックス利用状況確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = cursor.fetchall()
            
            optimization_result['operations'].append({
                'operation': 'INDEX_CHECK',
                'status': 'completed',
                'description': f'{len(indexes)}個のインデックスを確認',
                'details': [idx[0] for idx in indexes]
            })
            
            conn.close()
            
            optimization_result['success'] = True
            optimization_result['completed_at'] = datetime.now().isoformat()
            
            logger.info("✅ データベース最適化完了")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"データベース最適化エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def run_comprehensive_integrity_check(self) -> Dict:
        """包括的整合性チェック・修復実行"""
        try:
            logger.info("🔍 データベース包括整合性チェック開始...")
            
            comprehensive_result = {
                'started_at': datetime.now().isoformat(),
                'structure_verification': {},
                'data_integrity': {},
                'migration_result': {},
                'optimization_result': {},
                'overall_status': 'unknown',
                'recommendations': []
            }
            
            # 1. 構造検証
            structure_info = self.verify_database_structure()
            comprehensive_result['structure_verification'] = structure_info
            
            # 2. データ整合性チェック
            integrity_info = self.check_data_integrity()
            comprehensive_result['data_integrity'] = integrity_info
            
            # 3. 必要に応じてマイグレーション実行
            if structure_info.get('status') == 'needs_migration':
                logger.info("🔧 マイグレーションが必要です。実行中...")
                migration_result = self.perform_migration()
                comprehensive_result['migration_result'] = migration_result
                
                if not migration_result.get('success'):
                    comprehensive_result['recommendations'].append(
                        "マイグレーションが失敗しました。バックアップからの復元を検討してください。"
                    )
            else:
                comprehensive_result['recommendations'].append("データベース構造は最新です。")
            
            # 4. データベース最適化
            optimization_result = self.optimize_database()
            comprehensive_result['optimization_result'] = optimization_result
            
            # 5. 全体ステータス判定
            issues_count = (
                len(structure_info.get('issues', [])) +
                len(integrity_info.get('issues', []))
            )
            
            if issues_count == 0:
                comprehensive_result['overall_status'] = 'excellent'
            elif issues_count <= 2:
                comprehensive_result['overall_status'] = 'good'
            elif issues_count <= 5:
                comprehensive_result['overall_status'] = 'needs_attention'
            else:
                comprehensive_result['overall_status'] = 'critical'
            
            comprehensive_result['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"✅ 包括整合性チェック完了: {comprehensive_result['overall_status']}")
            
            return comprehensive_result
            
        except Exception as e:
            logger.error(f"包括整合性チェックエラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def export_integrity_report(self, results: Dict, filename: str = "database_integrity_report.json"):
        """整合性チェック結果をレポートとして出力"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 整合性レポートを {filename} に出力しました")
            
        except Exception as e:
            logger.error(f"レポート出力エラー: {e}")

# テスト実行
if __name__ == "__main__":
    print("🔧 データベース整合性管理システム実行...")
    
    manager = DatabaseIntegrityManager()
    results = manager.run_comprehensive_integrity_check()
    
    if results and not results.get('error'):
        print(f"✅ 整合性チェック完了: {results['overall_status']}")
        print(f"  構造問題: {len(results['structure_verification'].get('issues', []))}件")
        print(f"  データ問題: {len(results['data_integrity'].get('issues', []))}件")
        
        if results.get('migration_result'):
            print(f"  マイグレーション: {'成功' if results['migration_result']['success'] else '失敗'}")
        
        # レポート出力
        manager.export_integrity_report(results)
    else:
        print(f"❌ 整合性チェック失敗: {results.get('error', '不明なエラー')}")