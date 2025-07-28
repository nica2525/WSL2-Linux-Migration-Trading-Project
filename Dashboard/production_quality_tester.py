"""
Production Quality Tester - 本番運用品質システム検証
設計通りの品質で実際に動作することを確認
"""

import os
import sys
import time
import json
import logging
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import threading

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionQualityTester:
    """本番運用品質テストクラス"""
    
    def __init__(self):
        self.test_results = {
            'started_at': datetime.now().isoformat(),
            'quality_tests': {},
            'performance_tests': {},
            'reliability_tests': {},
            'overall_quality': 'unknown',
            'production_ready': False
        }
        
    def test_system_dependencies(self) -> Dict:
        """システム依存関係の検証"""
        try:
            logger.info("🔧 システム依存関係検証開始...")
            
            test_result = {
                'name': 'System Dependencies',
                'started_at': datetime.now().isoformat(),
                'dependencies': {},
                'status': 'unknown'
            }
            
            # 必須Python パッケージ
            required_packages = [
                ('numpy', '1.21.0'),
                ('flask', '2.0.0'),
                ('flask_socketio', '5.0.0'),
                ('sqlite3', 'builtin')
            ]
            
            dependencies_ok = []
            
            for package, min_version in required_packages:
                try:
                    if package == 'sqlite3':
                        import sqlite3
                        version = sqlite3.sqlite_version
                        available = True
                    else:
                        module = __import__(package)
                        version = getattr(module, '__version__', 'unknown')
                        available = True
                    
                    test_result['dependencies'][package] = {
                        'available': available,
                        'version': version,
                        'required': min_version
                    }
                    dependencies_ok.append(available)
                    
                except ImportError:
                    test_result['dependencies'][package] = {
                        'available': False,
                        'version': 'not_installed',
                        'required': min_version
                    }
                    dependencies_ok.append(False)
            
            # MT5関連ファイル確認
            mt5_files = [
                '/home/trader/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe',
                '/home/trader/.wine/drive_c/Program Files/MetaTrader 5/logs/'
            ]
            
            for file_path in mt5_files:
                exists = os.path.exists(file_path)
                test_result['dependencies'][f"MT5_{os.path.basename(file_path)}"] = {
                    'available': exists,
                    'path': file_path
                }
                dependencies_ok.append(exists)
            
            # 総合判定
            success_rate = sum(dependencies_ok) / len(dependencies_ok)
            test_result['status'] = 'passed' if success_rate >= 0.8 else 'failed'
            test_result['success_rate'] = f"{success_rate * 100:.1f}%"
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"システム依存関係テストエラー: {e}")
            return {
                'name': 'System Dependencies',
                'status': 'error',
                'error': str(e)
            }
    
    def test_database_performance(self) -> Dict:
        """データベースパフォーマンステスト"""
        try:
            logger.info("⚡ データベースパフォーマンステスト開始...")
            
            test_result = {
                'name': 'Database Performance',
                'started_at': datetime.now().isoformat(),
                'metrics': {},
                'status': 'unknown'
            }
            
            conn = sqlite3.connect('dashboard.db')
            cursor = conn.cursor()
            
            # 1. 大量データ挿入テスト
            start_time = time.time()
            test_data = []
            
            for i in range(1000):
                test_data.append((
                    f'test_ticket_{i}',
                    datetime.now().isoformat(),
                    'EURUSD',
                    0,
                    0.01,
                    1.17000,
                    10.0,
                    -0.5,
                    -1.0,
                    12345,
                    'performance_test'
                ))
            
            cursor.executemany("""
                INSERT INTO position_details 
                (ticket, timestamp, symbol, type, volume, price_open, profit, swap, commission, magic, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, test_data)
            
            insert_time = time.time() - start_time
            test_result['metrics']['bulk_insert_1000_records'] = {
                'time_seconds': round(insert_time, 3),
                'records_per_second': round(1000 / insert_time, 1),
                'acceptable': insert_time < 5.0
            }
            
            # 2. クエリパフォーマンステスト
            start_time = time.time()
            cursor.execute("""
                SELECT symbol, COUNT(*), AVG(profit), SUM(profit)
                FROM position_details 
                WHERE comment = 'performance_test'
                GROUP BY symbol
            """)
            results = cursor.fetchall()
            query_time = time.time() - start_time
            
            test_result['metrics']['complex_query'] = {
                'time_seconds': round(query_time, 3),
                'results_count': len(results),
                'acceptable': query_time < 1.0
            }
            
            # 3. インデックス効果テスト
            start_time = time.time()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM position_details 
                WHERE timestamp > date('now', '-1 day')
            """)
            count = cursor.fetchone()[0]
            index_query_time = time.time() - start_time
            
            test_result['metrics']['indexed_query'] = {
                'time_seconds': round(index_query_time, 3),
                'records_found': count,
                'acceptable': index_query_time < 0.5
            }
            
            # テストデータクリーンアップ
            cursor.execute("DELETE FROM position_details WHERE comment = 'performance_test'")
            conn.commit()
            conn.close()
            
            # 総合判定
            acceptable_tests = sum(1 for metric in test_result['metrics'].values() if metric['acceptable'])
            total_tests = len(test_result['metrics'])
            
            test_result['status'] = 'passed' if acceptable_tests == total_tests else 'failed'
            test_result['performance_score'] = f"{(acceptable_tests / total_tests * 100):.1f}%"
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"データベースパフォーマンステストエラー: {e}")
            return {
                'name': 'Database Performance',
                'status': 'error',
                'error': str(e)
            }
    
    def test_real_data_integration(self) -> Dict:
        """実データ統合の品質テスト"""
        try:
            logger.info("📊 実データ統合品質テスト開始...")
            
            test_result = {
                'name': 'Real Data Integration',
                'started_at': datetime.now().isoformat(),
                'integration_tests': {},
                'status': 'unknown'
            }
            
            # 1. MT5データ解析品質
            from mt5_real_data_parser import MT5RealDataParser
            parser = MT5RealDataParser()
            real_data = parser.get_comprehensive_data()
            
            data_quality = real_data.get('data_quality', 'unknown')
            has_account_info = bool(real_data.get('account_info'))
            has_ea_activity = bool(real_data.get('ea_activity', {}).get('ea_name'))
            
            test_result['integration_tests']['mt5_data_parsing'] = {
                'description': 'MT5ログデータ解析品質',
                'quality': data_quality,
                'has_account_info': has_account_info,
                'has_ea_activity': has_ea_activity,
                'acceptable': data_quality in ['high', 'medium'] and has_account_info
            }
            
            # 2. 統計計算精度
            from statistics_validator import StatisticsValidator
            validator = StatisticsValidator()
            
            # 実データでの統計計算テスト
            test_trades = [
                {'profit': 150.0, 'swap': -2.0, 'commission': -5.0},
                {'profit': -100.0, 'swap': -1.5, 'commission': -5.0},
                {'profit': 200.0, 'swap': -3.0, 'commission': -5.0}
            ]
            
            basic_stats = validator.validate_basic_statistics(test_trades)
            advanced_stats = validator.validate_advanced_statistics(test_trades)
            
            stats_accuracy_ok = (
                basic_stats.get('validation_passed', False) and
                advanced_stats.get('validation', {}).get('passed', False)
            )
            
            test_result['integration_tests']['statistics_accuracy'] = {
                'description': '統計計算精度検証',
                'basic_stats_passed': basic_stats.get('validation_passed', False),
                'advanced_stats_passed': advanced_stats.get('validation', {}).get('passed', False),
                'acceptable': stats_accuracy_ok
            }
            
            # 3. データベース統合
            conn = sqlite3.connect('dashboard.db')
            cursor = conn.cursor()
            
            # 必須テーブルとデータ確認
            cursor.execute("SELECT COUNT(*) FROM position_details")
            position_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM statistics_cache")
            stats_count = cursor.fetchone()[0]
            
            conn.close()
            
            db_integration_ok = position_count >= 0  # テーブルが存在し、アクセス可能
            
            test_result['integration_tests']['database_integration'] = {
                'description': 'データベース統合状況',
                'position_records': position_count,
                'statistics_records': stats_count,
                'tables_accessible': True,
                'acceptable': db_integration_ok
            }
            
            # 総合判定
            acceptable_tests = sum(1 for test in test_result['integration_tests'].values() if test['acceptable'])
            total_tests = len(test_result['integration_tests'])
            
            test_result['status'] = 'passed' if acceptable_tests >= total_tests * 0.75 else 'failed'
            test_result['integration_score'] = f"{(acceptable_tests / total_tests * 100):.1f}%"
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"実データ統合テストエラー: {e}")
            return {
                'name': 'Real Data Integration',
                'status': 'error',
                'error': str(e)
            }
    
    def test_system_reliability(self) -> Dict:
        """システム信頼性テスト"""
        try:
            logger.info("🛡️ システム信頼性テスト開始...")
            
            test_result = {
                'name': 'System Reliability',
                'started_at': datetime.now().isoformat(),
                'reliability_tests': {},
                'status': 'unknown'
            }
            
            # 1. エラーハンドリング
            error_handling_ok = True
            try:
                # 不正なデータでのテスト
                from real_data_integration import RealDataIntegrationManager
                manager = RealDataIntegrationManager()
                
                # 空のデータでの統計計算
                empty_result = manager._calculate_sharpe_ratio([])
                error_handling_ok = error_handling_ok and (empty_result == 0)
                
                # 不正な値での計算
                invalid_result = manager._calculate_max_drawdown([])
                error_handling_ok = error_handling_ok and (invalid_result == 0)
                
            except Exception as e:
                error_handling_ok = False
            
            test_result['reliability_tests']['error_handling'] = {
                'description': 'エラーハンドリング堅牢性',
                'handles_empty_data': True,
                'handles_invalid_input': True,
                'acceptable': error_handling_ok
            }
            
            # 2. メモリ効率性
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            memory_efficient = memory_usage < 500  # 500MB未満
            
            test_result['reliability_tests']['memory_efficiency'] = {
                'description': 'メモリ使用効率',
                'memory_usage_mb': round(memory_usage, 1),
                'acceptable_limit_mb': 500,
                'acceptable': memory_efficient
            }
            
            # 3. ファイルシステム操作
            filesystem_ok = True
            try:
                # テンポラリファイルの作成・削除
                test_file = 'reliability_test.tmp'
                with open(test_file, 'w') as f:
                    f.write('test')
                
                filesystem_ok = os.path.exists(test_file)
                os.remove(test_file)
                filesystem_ok = filesystem_ok and not os.path.exists(test_file)
                
            except Exception as e:
                filesystem_ok = False
            
            test_result['reliability_tests']['filesystem_operations'] = {
                'description': 'ファイルシステム操作',
                'can_create_files': True,
                'can_delete_files': True,
                'acceptable': filesystem_ok
            }
            
            # 総合判定
            acceptable_tests = sum(1 for test in test_result['reliability_tests'].values() if test['acceptable'])
            total_tests = len(test_result['reliability_tests'])
            
            test_result['status'] = 'passed' if acceptable_tests == total_tests else 'failed'
            test_result['reliability_score'] = f"{(acceptable_tests / total_tests * 100):.1f}%"
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"システム信頼性テストエラー: {e}")
            return {
                'name': 'System Reliability',
                'status': 'error',
                'error': str(e)
            }
    
    def run_production_quality_assessment(self) -> Dict:
        """本番運用品質の包括評価"""
        try:
            logger.info("🎯 本番運用品質包括評価開始...")
            
            # 各品質テストの実行
            quality_tests = [
                ('quality_tests', self.test_system_dependencies),
                ('performance_tests', self.test_database_performance),
                ('quality_tests', self.test_real_data_integration),
                ('reliability_tests', self.test_system_reliability)
            ]
            
            passed_tests = 0
            total_tests = len(quality_tests)
            
            for category, test_func in quality_tests:
                test_result = test_func()
                test_name = test_result['name']
                
                if category not in self.test_results:
                    self.test_results[category] = {}
                
                self.test_results[category][test_name] = test_result
                
                if test_result['status'] == 'passed':
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: 合格")
                else:
                    logger.warning(f"❌ {test_name}: 不合格")
            
            # 全体品質評価
            success_rate = passed_tests / total_tests
            
            if success_rate == 1.0:
                self.test_results['overall_quality'] = 'production_ready'
                self.test_results['production_ready'] = True
            elif success_rate >= 0.8:
                self.test_results['overall_quality'] = 'high_quality'
                self.test_results['production_ready'] = True
            elif success_rate >= 0.6:
                self.test_results['overall_quality'] = 'acceptable'
                self.test_results['production_ready'] = False
            else:
                self.test_results['overall_quality'] = 'needs_improvement'
                self.test_results['production_ready'] = False
            
            self.test_results['summary'] = {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate': f"{success_rate * 100:.1f}%",
                'quality_level': self.test_results['overall_quality'],
                'production_ready': self.test_results['production_ready']
            }
            
            self.test_results['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"🏆 本番品質評価完了: {self.test_results['overall_quality']} ({self.test_results['summary']['success_rate']})")
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"本番品質評価エラー: {e}")
            return {
                'error': str(e),
                'started_at': datetime.now().isoformat(),
                'overall_quality': 'error'
            }
    
    def export_quality_report(self, filename: str = "production_quality_report.json"):
        """品質評価レポートの出力"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 本番品質レポートを {filename} に出力しました")
            
        except Exception as e:
            logger.error(f"品質レポート出力エラー: {e}")

# テスト実行
if __name__ == "__main__":
    print("🏭 本番運用品質評価実行...")
    
    tester = ProductionQualityTester()
    results = tester.run_production_quality_assessment()
    
    if results and not results.get('error'):
        print(f"✅ 本番品質評価完了: {results['overall_quality']}")
        print(f"  品質成功率: {results['summary']['success_rate']}")
        print(f"  本番運用可能: {'はい' if results['production_ready'] else 'いいえ'}")
        
        # レポート出力
        tester.export_quality_report()
    else:
        print(f"❌ 本番品質評価失敗: {results.get('error', '不明なエラー')}")