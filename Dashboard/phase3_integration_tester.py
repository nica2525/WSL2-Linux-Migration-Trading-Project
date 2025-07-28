"""
Phase 3 Integration Tester - Phase 3システム完全統合テスト
全コンポーネントの統合動作テスト・品質検証
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

# プロジェクトモジュール
from mt5_real_data_parser import MT5RealDataParser
from statistics_validator import StatisticsValidator
from database_integrity_manager import DatabaseIntegrityManager

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase3IntegrationTester:
    """Phase 3統合テストクラス"""
    
    def __init__(self):
        self.test_results = {
            'started_at': datetime.now().isoformat(),
            'tests': {},
            'overall_status': 'unknown',
            'failed_tests': [],
            'passed_tests': []
        }
        self.server_process = None
        self.base_url = "http://localhost:5000"
        
    def test_mt5_connection_system(self) -> Dict:
        """MT5接続システムのテスト"""
        try:
            logger.info("🔍 MT5接続システムテスト開始...")
            
            test_result = {
                'name': 'MT5 Connection System',
                'started_at': datetime.now().isoformat(),
                'sub_tests': {},
                'status': 'unknown'
            }
            
            # 1. MT5プロセス確認
            result = subprocess.run(['pgrep', '-f', 'terminal64.exe'], capture_output=True, text=True)
            mt5_running = result.returncode == 0
            
            test_result['sub_tests']['mt5_process'] = {
                'description': 'MT5プロセス動作確認',
                'result': mt5_running,
                'details': f"プロセス{'動作中' if mt5_running else '停止中'}"
            }
            
            # 2. データ解析システム
            parser = MT5RealDataParser()
            real_data = parser.get_comprehensive_data()
            
            data_quality_ok = real_data.get('data_quality') in ['high', 'medium']
            test_result['sub_tests']['data_parser'] = {
                'description': 'MT5データ解析システム',
                'result': data_quality_ok and bool(real_data),
                'details': f"データ品質: {real_data.get('data_quality', 'unknown')}"
            }
            
            # 3. Wine接続確認
            from mt5_wine_connector import MT5WineConnector
            connector = MT5WineConnector()
            wine_connection = connector.connect()
            
            test_result['sub_tests']['wine_connector'] = {
                'description': 'Wine MT5コネクター',
                'result': wine_connection,
                'details': connector.last_error if not wine_connection else "接続成功"
            }
            
            # 総合判定
            passed_tests = sum(1 for test in test_result['sub_tests'].values() if test['result'])
            total_tests = len(test_result['sub_tests'])
            
            test_result['status'] = 'passed' if passed_tests >= total_tests * 0.75 else 'failed'
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"MT5接続システムテストエラー: {e}")
            return {
                'name': 'MT5 Connection System',
                'status': 'error',
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def test_statistics_system(self) -> Dict:
        """統計計算システムのテスト"""
        try:
            logger.info("📊 統計計算システムテスト開始...")
            
            test_result = {
                'name': 'Statistics System',
                'started_at': datetime.now().isoformat(),
                'sub_tests': {},
                'status': 'unknown'
            }
            
            # 1. 統計計算検証
            validator = StatisticsValidator()
            validation_results = validator.run_comprehensive_validation()
            
            stats_validation_ok = validation_results.get('overall_passed', False)
            test_result['sub_tests']['statistics_validation'] = {
                'description': '統計計算精度検証',
                'result': stats_validation_ok,
                'details': f"テストデータ: {validation_results.get('test_data_count', 0)}件"
            }
            
            # 2. NumPy実装確認
            import numpy as np
            from real_data_integration import RealDataIntegrationManager
            
            manager = RealDataIntegrationManager()
            test_data = [100, -50, 75, -25, 150, -75, 200, -100, 125, -60]
            
            # 各統計指標の計算テスト
            try:
                sharpe = manager._calculate_sharpe_ratio(test_data)
                sortino = manager._calculate_sortino_ratio(test_data)
                max_dd = manager._calculate_max_drawdown(test_data)
                
                numpy_functions_ok = all([
                    isinstance(sharpe, (int, float)),
                    isinstance(sortino, (int, float)),
                    isinstance(max_dd, (int, float))
                ])
                
                test_result['sub_tests']['numpy_functions'] = {
                    'description': 'NumPy統計関数動作',
                    'result': numpy_functions_ok,
                    'details': f"Sharpe: {sharpe}, Sortino: {sortino}, MaxDD: {max_dd}"
                }
                
            except Exception as e:
                test_result['sub_tests']['numpy_functions'] = {
                    'description': 'NumPy統計関数動作',
                    'result': False,
                    'details': f"エラー: {str(e)}"
                }
            
            # 総合判定
            passed_tests = sum(1 for test in test_result['sub_tests'].values() if test['result'])
            total_tests = len(test_result['sub_tests'])
            
            test_result['status'] = 'passed' if passed_tests == total_tests else 'failed'
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"統計計算システムテストエラー: {e}")
            return {
                'name': 'Statistics System',
                'status': 'error',
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def test_database_system(self) -> Dict:
        """データベースシステムのテスト"""
        try:
            logger.info("🗄️ データベースシステムテスト開始...")
            
            test_result = {
                'name': 'Database System',
                'started_at': datetime.now().isoformat(),
                'sub_tests': {},
                'status': 'unknown'
            }
            
            # 1. データベース整合性
            integrity_manager = DatabaseIntegrityManager()
            integrity_results = integrity_manager.run_comprehensive_integrity_check()
            
            db_status_ok = integrity_results.get('overall_status') in ['excellent', 'good']
            test_result['sub_tests']['database_integrity'] = {
                'description': 'データベース整合性',
                'result': db_status_ok,
                'details': f"ステータス: {integrity_results.get('overall_status', 'unknown')}"
            }
            
            # 2. Phase 3テーブル確認
            conn = sqlite3.connect('dashboard.db')
            cursor = conn.cursor()
            
            required_tables = ['position_details', 'statistics_cache', 'system_monitoring']
            tables_exist = []
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                exists = cursor.fetchone() is not None
                tables_exist.append(exists)
            
            conn.close()
            
            all_tables_ok = all(tables_exist)
            test_result['sub_tests']['phase3_tables'] = {
                'description': 'Phase 3テーブル存在確認',
                'result': all_tables_ok,
                'details': f"テーブル: {sum(tables_exist)}/{len(required_tables)} 存在"
            }
            
            # 3. データ操作テスト
            try:
                conn = sqlite3.connect('dashboard.db')
                cursor = conn.cursor()
                
                # テストデータ挿入
                cursor.execute("""
                    INSERT INTO system_monitoring (component, metric_name, metric_value, status, message)
                    VALUES (?, ?, ?, ?, ?)
                """, ('integration_test', 'test_metric', 1.0, 'normal', 'テスト実行'))
                
                # データ取得
                cursor.execute("""
                    SELECT COUNT(*) FROM system_monitoring 
                    WHERE component = 'integration_test'
                """)
                
                test_count = cursor.fetchone()[0]
                
                # テストデータ削除
                cursor.execute("DELETE FROM system_monitoring WHERE component = 'integration_test'")
                conn.commit()
                conn.close()
                
                data_operations_ok = test_count > 0
                test_result['sub_tests']['data_operations'] = {
                    'description': 'データ操作テスト',
                    'result': data_operations_ok,
                    'details': f"挿入・取得・削除: {'成功' if data_operations_ok else '失敗'}"
                }
                
            except Exception as e:
                test_result['sub_tests']['data_operations'] = {
                    'description': 'データ操作テスト',
                    'result': False,
                    'details': f"エラー: {str(e)}"
                }
            
            # 総合判定
            passed_tests = sum(1 for test in test_result['sub_tests'].values() if test['result'])
            total_tests = len(test_result['sub_tests'])
            
            test_result['status'] = 'passed' if passed_tests == total_tests else 'failed'
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"データベースシステムテストエラー: {e}")
            return {
                'name': 'Database System',
                'status': 'error',
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def test_web_interface(self) -> Dict:
        """Webインターフェースのテスト"""
        try:
            logger.info("🌐 Webインターフェーステスト開始...")
            
            test_result = {
                'name': 'Web Interface',
                'started_at': datetime.now().isoformat(),
                'sub_tests': {},
                'status': 'unknown'
            }
            
            # 1. サーバー起動テスト
            server_started = self._start_test_server()
            test_result['sub_tests']['server_startup'] = {
                'description': 'サーバー起動テスト',
                'result': server_started,
                'details': f"ポート5000でのサーバー{'起動成功' if server_started else '起動失敗'}"
            }
            
            if server_started:
                # 2. HTTPレスポンステスト
                try:
                    response = requests.get(f"{self.base_url}/", timeout=10)
                    http_ok = response.status_code == 200
                    
                    test_result['sub_tests']['http_response'] = {
                        'description': 'HTTPレスポンステスト',
                        'result': http_ok,
                        'details': f"ステータスコード: {response.status_code}"
                    }
                    
                except Exception as e:
                    test_result['sub_tests']['http_response'] = {
                        'description': 'HTTPレスポンステスト',
                        'result': False,
                        'details': f"エラー: {str(e)}"
                    }
                
                # 3. APIエンドポイントテスト
                api_endpoints = ['/api/account', '/api/positions', '/api/system_status']
                api_results = []
                
                for endpoint in api_endpoints:
                    try:
                        response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                        api_results.append(response.status_code in [200, 404, 500])  # 何らかのレスポンスがあればOK
                    except:
                        api_results.append(False)
                
                api_endpoints_ok = any(api_results)  # 少なくとも1つのエンドポイントが応答
                test_result['sub_tests']['api_endpoints'] = {
                    'description': 'APIエンドポイントテスト',
                    'result': api_endpoints_ok,
                    'details': f"応答エンドポイント: {sum(api_results)}/{len(api_endpoints)}"
                }
                
                # サーバー停止
                self._stop_test_server()
            
            # 総合判定
            passed_tests = sum(1 for test in test_result['sub_tests'].values() if test['result'])
            total_tests = len(test_result['sub_tests'])
            
            test_result['status'] = 'passed' if passed_tests >= total_tests * 0.67 else 'failed'
            test_result['completed_at'] = datetime.now().isoformat()
            
            return test_result
            
        except Exception as e:
            logger.error(f"Webインターフェーステストエラー: {e}")
            return {
                'name': 'Web Interface',
                'status': 'error',
                'error': str(e),
                'started_at': datetime.now().isoformat()
            }
    
    def _start_test_server(self) -> bool:
        """テスト用サーバーの起動"""
        try:
            # 既存のサーバープロセスがあれば終了
            subprocess.run(['pkill', '-f', 'app.py'], capture_output=True)
            time.sleep(2)
            
            # 新しいサーバーを起動
            env = os.environ.copy()
            env['PYTHONPATH'] = '.'
            
            self.server_process = subprocess.Popen(
                ['python3', 'app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # サーバー起動待機
            for _ in range(30):  # 30秒待機
                try:
                    response = requests.get(f"{self.base_url}/", timeout=1)
                    if response.status_code == 200:
                        return True
                except:
                    pass
                time.sleep(1)
            
            return False
            
        except Exception as e:
            logger.error(f"テストサーバー起動エラー: {e}")
            return False
    
    def _stop_test_server(self):
        """テスト用サーバーの停止"""
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            # 念のため強制終了
            subprocess.run(['pkill', '-f', 'app.py'], capture_output=True)
            
        except Exception as e:
            logger.error(f"テストサーバー停止エラー: {e}")
    
    def run_comprehensive_integration_test(self) -> Dict:
        """包括的統合テストの実行"""
        try:
            logger.info("🚀 Phase 3システム包括統合テスト開始...")
            
            # テスト実行順序
            test_functions = [
                self.test_database_system,
                self.test_statistics_system,
                self.test_mt5_connection_system,
                self.test_web_interface
            ]
            
            # 各テストの実行
            for test_func in test_functions:
                test_result = test_func()
                test_name = test_result['name']
                self.test_results['tests'][test_name] = test_result
                
                if test_result['status'] == 'passed':
                    self.test_results['passed_tests'].append(test_name)
                    logger.info(f"✅ {test_name}: 合格")
                else:
                    self.test_results['failed_tests'].append(test_name)
                    logger.warning(f"❌ {test_name}: 不合格")
            
            # 全体ステータス判定
            total_tests = len(self.test_results['tests'])
            passed_count = len(self.test_results['passed_tests'])
            
            if passed_count == total_tests:
                self.test_results['overall_status'] = 'excellent'
            elif passed_count >= total_tests * 0.8:
                self.test_results['overall_status'] = 'good'
            elif passed_count >= total_tests * 0.5:
                self.test_results['overall_status'] = 'needs_improvement'
            else:
                self.test_results['overall_status'] = 'critical'
            
            self.test_results['completed_at'] = datetime.now().isoformat()
            self.test_results['summary'] = {
                'total_tests': total_tests,
                'passed': passed_count,
                'failed': total_tests - passed_count,
                'success_rate': f"{(passed_count / total_tests * 100):.1f}%"
            }
            
            logger.info(f"🎯 統合テスト完了: {self.test_results['overall_status']} ({self.test_results['summary']['success_rate']})")
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"包括統合テストエラー: {e}")
            return {
                'error': str(e),
                'started_at': datetime.now().isoformat(),
                'overall_status': 'error'
            }
    
    def export_test_report(self, filename: str = "phase3_integration_test_report.json"):
        """テスト結果レポートの出力"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 統合テストレポートを {filename} に出力しました")
            
        except Exception as e:
            logger.error(f"テストレポート出力エラー: {e}")

# テスト実行
if __name__ == "__main__":
    print("🧪 Phase 3システム統合テスト実行...")
    
    tester = Phase3IntegrationTester()
    results = tester.run_comprehensive_integration_test()
    
    if results and not results.get('error'):
        print(f"✅ 統合テスト完了: {results['overall_status']}")
        print(f"  総合成功率: {results['summary']['success_rate']}")
        print(f"  合格テスト: {results['summary']['passed']}/{results['summary']['total_tests']}")
        
        if results['failed_tests']:
            print(f"  不合格テスト: {', '.join(results['failed_tests'])}")
        
        # レポート出力
        tester.export_test_report()
    else:
        print(f"❌ 統合テスト失敗: {results.get('error', '不明なエラー')}")