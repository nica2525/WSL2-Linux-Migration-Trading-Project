#!/usr/bin/env python3
"""
48時間連続稼働テストスクリプト
Phase 1追加タスク - 安定性検証
"""

import os
import sys
import time
import json
import psutil
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
import requests

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/continuous_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContinuousOperationTest:
    """48時間連続稼働テスト"""
    
    def __init__(self):
        self.dashboard_pid = None
        self.start_time = None
        self.test_duration = 48 * 60 * 60  # 48時間（秒）
        self.check_interval = 60  # 1分間隔でチェック
        self.data_file = Path("/tmp/mt5_data/positions.json")
        self.dashboard_url = "http://localhost:5000"
        
        # メトリクス収集
        self.metrics = {
            'memory_usage': [],
            'cpu_usage': [],
            'file_handles': [],
            'response_times': [],
            'errors': [],
            'data_updates': 0
        }
        
    def start_dashboard(self):
        """ダッシュボード起動"""
        try:
            dashboard_path = Path("/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard")
            
            # 既存プロセス終了
            subprocess.run(["pkill", "-f", "python3 app.py"], capture_output=True)
            time.sleep(2)
            
            # ダッシュボード起動
            process = subprocess.Popen(
                ["python3", "app.py"],
                cwd=dashboard_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            self.dashboard_pid = process.pid
            logger.info(f"Dashboard started with PID: {self.dashboard_pid}")
            
            # 起動確認（最大30秒待機）
            for i in range(30):
                try:
                    response = requests.get(self.dashboard_url, timeout=5)
                    if response.status_code == 200:
                        logger.info("Dashboard startup confirmed")
                        return True
                except:
                    time.sleep(1)
                    
            logger.error("Dashboard startup failed")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            return False
    
    def create_test_data(self):
        """テスト用データ生成"""
        try:
            os.makedirs("/tmp/mt5_data", exist_ok=True)
            
            test_data = {
                "timestamp": datetime.now().isoformat(),
                "account": {
                    "balance": 3000000 + (time.time() % 1000),
                    "equity": 2990000 + (time.time() % 1000),
                    "profit": -10000 + (time.time() % 2000)
                },
                "positions": [
                    {
                        "ticket": int(time.time()) % 1000000,
                        "symbol": "EURUSD",
                        "type": "buy" if int(time.time()) % 2 == 0 else "sell",
                        "volume": 0.01 + (int(time.time()) % 10) * 0.01,
                        "profit": -500 + (time.time() % 1000),
                        "open_price": 1.08300 + (time.time() % 100) * 0.00001,
                        "current_price": 1.08350 + (time.time() % 100) * 0.00001,
                        "open_time": datetime.now().isoformat()
                    }
                ]
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(test_data, f)
                
            self.metrics['data_updates'] += 1
            logger.debug("Test data updated")
            
        except Exception as e:
            logger.error(f"Failed to create test data: {e}")
            self.metrics['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'type': 'data_creation'
            })
    
    def collect_metrics(self):
        """システムメトリクス収集"""
        try:
            if not self.dashboard_pid:
                return
                
            # プロセス情報取得
            try:
                process = psutil.Process(self.dashboard_pid)
                
                # メモリ使用量（MB）
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.metrics['memory_usage'].append({
                    'timestamp': datetime.now().isoformat(),
                    'rss_mb': memory_mb,
                    'vms_mb': memory_info.vms / 1024 / 1024
                })
                
                # CPU使用率
                cpu_percent = process.cpu_percent()
                self.metrics['cpu_usage'].append({
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent
                })
                
                # ファイルハンドル数
                try:
                    file_handles = len(process.open_files())
                    self.metrics['file_handles'].append({
                        'timestamp': datetime.now().isoformat(),
                        'count': file_handles
                    })
                except:
                    pass  # 権限エラーの場合は無視
                    
            except psutil.NoSuchProcess:
                logger.error("Dashboard process not found")
                self.metrics['errors'].append({
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Process not found',
                    'type': 'process_monitoring'
                })
                return False
                
            # HTTP応答時間測定
            try:
                start_time = time.time()
                response = requests.get(self.dashboard_url, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                self.metrics['response_times'].append({
                    'timestamp': datetime.now().isoformat(),
                    'response_time_ms': response_time,
                    'status_code': response.status_code
                })
                
                if response.status_code != 200:
                    logger.warning(f"HTTP response status: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"HTTP request failed: {e}")
                self.metrics['errors'].append({
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'type': 'http_request'
                })
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            self.metrics['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'type': 'metrics_collection'
            })
            return False
    
    def save_metrics(self):
        """メトリクス保存"""
        try:
            metrics_file = Path("/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/continuous_test_metrics.json")
            
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
                
            logger.info(f"Metrics saved to {metrics_file}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def generate_report(self):
        """テスト結果レポート生成"""
        try:
            end_time = datetime.now()
            duration = end_time - self.start_time
            
            # 統計計算
            memory_values = [m['rss_mb'] for m in self.metrics['memory_usage']]
            cpu_values = [c['cpu_percent'] for c in self.metrics['cpu_usage']]
            response_times = [r['response_time_ms'] for r in self.metrics['response_times']]
            
            report = {
                'test_summary': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_hours': duration.total_seconds() / 3600,
                    'target_duration_hours': self.test_duration / 3600,
                    'completed': duration.total_seconds() >= self.test_duration
                },
                'performance_metrics': {
                    'memory_usage': {
                        'max_mb': max(memory_values) if memory_values else 0,
                        'min_mb': min(memory_values) if memory_values else 0,
                        'avg_mb': sum(memory_values) / len(memory_values) if memory_values else 0
                    },
                    'cpu_usage': {
                        'max_percent': max(cpu_values) if cpu_values else 0,
                        'min_percent': min(cpu_values) if cpu_values else 0,
                        'avg_percent': sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    },
                    'response_time': {
                        'max_ms': max(response_times) if response_times else 0,
                        'min_ms': min(response_times) if response_times else 0,
                        'avg_ms': sum(response_times) / len(response_times) if response_times else 0
                    }
                },
                'stability_metrics': {
                    'total_errors': len(self.metrics['errors']),
                    'data_updates': self.metrics['data_updates'],
                    'successful_checks': len(self.metrics['response_times']),
                    'uptime_percentage': (len(self.metrics['response_times']) / (duration.total_seconds() / self.check_interval)) * 100 if duration.total_seconds() > 0 else 0
                },
                'errors': self.metrics['errors'][-10:] if self.metrics['errors'] else []  # 最新10件のエラー
            }
            
            report_file = Path("/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/continuous_test_report.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Test report generated: {report_file}")
            
            # サマリーログ出力
            logger.info("=== 48時間連続稼働テスト結果サマリー ===")
            logger.info(f"実行時間: {duration.total_seconds()/3600:.1f}時間")
            logger.info(f"最大メモリ使用量: {report['performance_metrics']['memory_usage']['max_mb']:.1f}MB")
            logger.info(f"平均CPU使用率: {report['performance_metrics']['cpu_usage']['avg_percent']:.1f}%")
            logger.info(f"平均応答時間: {report['performance_metrics']['response_time']['avg_ms']:.1f}ms")
            logger.info(f"稼働率: {report['stability_metrics']['uptime_percentage']:.1f}%")
            logger.info(f"総エラー数: {report['stability_metrics']['total_errors']}")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return None
    
    def run_test(self):
        """メインテスト実行"""
        logger.info("=== 48時間連続稼働テスト開始 ===")
        
        # ダッシュボード起動
        if not self.start_dashboard():
            logger.error("Dashboard startup failed. Test aborted.")
            return False
            
        self.start_time = datetime.now()
        logger.info(f"Test started at: {self.start_time}")
        
        try:
            checks_count = 0
            while True:
                current_time = datetime.now()
                elapsed = (current_time - self.start_time).total_seconds()
                
                # テスト終了条件チェック
                if elapsed >= self.test_duration:
                    logger.info("48時間テスト完了")
                    break
                    
                # データ更新
                self.create_test_data()
                
                # メトリクス収集
                if not self.collect_metrics():
                    logger.warning("Metrics collection failed")
                
                checks_count += 1
                
                # 進捗ログ（1時間ごと）
                if checks_count % 60 == 0:
                    hours_elapsed = elapsed / 3600
                    logger.info(f"進捗: {hours_elapsed:.1f}時間経過 ({hours_elapsed/48*100:.1f}%)")
                    self.save_metrics()  # 中間保存
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("テストが手動停止されました")
        except Exception as e:
            logger.error(f"テスト実行中にエラー: {e}")
        finally:
            # クリーンアップ
            if self.dashboard_pid:
                try:
                    subprocess.run(["kill", str(self.dashboard_pid)])
                    logger.info("Dashboard process terminated")
                except:
                    pass
            
            # 最終レポート生成
            self.save_metrics()
            report = self.generate_report()
            
            logger.info("=== テスト終了 ===")
            return report

def main():
    """メイン関数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # クイックテスト（5分間）
        logger.info("クイックテスト実行（5分間）")
        test = ContinuousOperationTest()
        test.test_duration = 5 * 60  # 5分
        test.check_interval = 10  # 10秒間隔
    else:
        # 通常の48時間テスト
        test = ContinuousOperationTest()
    
    result = test.run_test()
    
    if result:
        print("\n=== テスト結果サマリー ===")
        print(f"実行時間: {result['test_summary']['duration_hours']:.1f}時間")
        print(f"最大メモリ: {result['performance_metrics']['memory_usage']['max_mb']:.1f}MB")
        print(f"平均CPU: {result['performance_metrics']['cpu_usage']['avg_percent']:.1f}%")
        print(f"稼働率: {result['stability_metrics']['uptime_percentage']:.1f}%")
        print(f"エラー数: {result['stability_metrics']['total_errors']}")
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())