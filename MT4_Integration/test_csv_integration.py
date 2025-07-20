#!/usr/bin/env python3
"""
CSV統合テストスクリプト
MT4-Python統合の動作確認とデバッグ用
"""

import csv
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import threading
import logging
import argparse

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVIntegrationTest:
    """CSV統合テストクラス"""
    
    def __init__(self, data_dir: str = "MT4_Data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # ファイルパス
        self.price_file = self.data_dir / "price_data.csv"
        self.signal_file = self.data_dir / "trading_signals.csv"
        self.status_file = self.data_dir / "connection_status.csv"
        
        # テスト統計
        self.test_stats = {
            'signals_sent': 0,
            'signals_executed': 0,
            'test_duration': 0,
            'avg_signal_latency': 0,
            'max_signal_latency': 0
        }
        
        logger.info(f"CSV統合テスト初期化: {self.data_dir}")
    
    def run_full_integration_test(self, duration_minutes: int = 5):
        """完全統合テスト実行"""
        print("🧪 MT4-Python CSV統合テスト開始")
        print("=" * 60)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # テスト開始通知
        self._write_test_signal("TEST_START", 0.0)
        
        signal_count = 0
        latencies = []
        
        while time.time() < end_time:
            try:
                # ランダムなブレイクアウトシグナル生成
                if np.random.random() < 0.1:  # 10%の確率
                    signal_time = time.time()
                    
                    # テストシグナル送信
                    signal_type = np.random.choice(['BUY', 'SELL'])
                    confidence = np.random.uniform(0.3, 0.9)
                    price = 1.1000 + np.random.normal(0, 0.001)
                    
                    self._send_test_signal(signal_type, confidence, price)
                    signal_count += 1
                    
                    # レスポンス時間測定
                    response_time = self._measure_response_time(signal_time)
                    if response_time > 0:
                        latencies.append(response_time)
                
                # MT4ステータス確認
                mt4_status = self._check_mt4_status()
                if mt4_status:
                    logger.info(f"MT4ステータス: {mt4_status}")
                
                time.sleep(1)  # 1秒間隔
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"テスト実行エラー: {e}")
                time.sleep(1)
        
        # テスト終了処理
        test_duration = time.time() - start_time
        self._write_test_signal("TEST_END", 0.0)
        
        # 統計計算
        self.test_stats.update({
            'signals_sent': signal_count,
            'test_duration': test_duration,
            'avg_signal_latency': np.mean(latencies) if latencies else 0,
            'max_signal_latency': max(latencies) if latencies else 0
        })
        
        # 結果表示
        self._display_test_results()
    
    def _send_test_signal(self, action: str, confidence: float, price: float):
        """テストシグナル送信"""
        try:
            signal_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': 'EURUSD',
                'action': action,
                'price': price,
                'confidence': confidence,
                'volume': 0.01,  # テスト用小ロット
                'stop_loss': price - 0.002 if action == 'BUY' else price + 0.002,
                'take_profit': price + 0.003 if action == 'BUY' else price - 0.003
            }
            
            # ファイル書き込み
            file_exists = self.signal_file.exists()
            
            with open(self.signal_file, 'a', newline='') as f:
                fieldnames = ['timestamp', 'symbol', 'action', 'price', 'confidence',
                            'volume', 'stop_loss', 'take_profit']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(signal_data)
            
            logger.info(f"テストシグナル送信: {action} @ {price:.5f} (信頼度: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"テストシグナル送信エラー: {e}")
    
    def _write_test_signal(self, signal_type: str, value: float):
        """テスト制御シグナル書き込み"""
        try:
            with open(self.signal_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(), 'TEST', signal_type, 
                    value, 0.0, 0.0, 0.0, 0.0
                ])
        except Exception as e:
            logger.error(f"テスト制御シグナル書き込みエラー: {e}")
    
    def _measure_response_time(self, signal_time: float) -> float:
        """レスポンス時間測定"""
        try:
            # 5秒間MT4からの応答を監視
            for _ in range(50):
                if self.status_file.exists():
                    with open(self.status_file, 'r') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        
                    if rows:
                        latest_status = rows[-1]
                        status_time = float(latest_status.get('heartbeat', 0))
                        
                        if status_time > signal_time:
                            return status_time - signal_time
                
                time.sleep(0.1)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"レスポンス時間測定エラー: {e}")
            return 0.0
    
    def _check_mt4_status(self) -> str:
        """MT4ステータス確認"""
        try:
            if not self.status_file.exists():
                return "NO_STATUS_FILE"
            
            with open(self.status_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return "EMPTY_STATUS"
            
            latest_status = rows[-1]
            status = latest_status.get('status', 'UNKNOWN')
            timestamp = latest_status.get('timestamp', '')
            
            return f"{status} ({timestamp})"
            
        except Exception as e:
            logger.error(f"MT4ステータス確認エラー: {e}")
            return "ERROR"
    
    def _display_test_results(self):
        """テスト結果表示"""
        print("\n🎯 CSV統合テスト結果")
        print("=" * 60)
        print(f"   テスト時間: {self.test_stats['test_duration']:.1f}秒")
        print(f"   送信シグナル数: {self.test_stats['signals_sent']}")
        print(f"   平均レスポンス時間: {self.test_stats['avg_signal_latency']:.3f}秒")
        print(f"   最大レスポンス時間: {self.test_stats['max_signal_latency']:.3f}秒")
        
        # 推奨事項
        print("\n📋 評価・推奨事項:")
        
        if self.test_stats['avg_signal_latency'] < 1.0:
            print("   ✅ レスポンス時間良好（1秒未満）")
        elif self.test_stats['avg_signal_latency'] < 3.0:
            print("   ⚠️ レスポンス時間やや遅い（1-3秒）")
        else:
            print("   ❌ レスポンス時間問題あり（3秒以上）")
        
        if self.test_stats['signals_sent'] > 0:
            print("   ✅ シグナル送信機能正常")
        else:
            print("   ❌ シグナル送信機能に問題")
        
        print("\n🔄 次のステップ:")
        print("   1. MT4でEAが正常に動作していることを確認")
        print("   2. ZeroMQ実装への移行を検討")
        print("   3. リアルタイム性能の詳細測定")

def simulate_price_feed(data_dir: str, duration_seconds: int = 300):
    """価格データフィード模擬"""
    data_path = Path(data_dir)
    price_file = data_path / "price_data.csv"
    
    base_price = 1.1000
    current_price = base_price
    
    logger.info(f"価格データフィード開始: {duration_seconds}秒間")
    
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        try:
            # 価格変動シミュレーション
            price_change = np.random.normal(0, 0.0001)
            current_price += price_change
            
            # 異常値防止
            if abs(current_price - base_price) > 0.01:
                current_price = base_price + np.random.normal(0, 0.001)
            
            # 価格データ書き込み
            with open(price_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'symbol', 'bid', 'ask', 'volume'])
                writer.writerow([
                    time.time(), 'EURUSD', current_price, 
                    current_price + 0.0002, np.random.randint(10, 1000)
                ])
            
            time.sleep(0.1)  # 100ms間隔
            
        except Exception as e:
            logger.error(f"価格フィードエラー: {e}")
            time.sleep(1)

def main():
    """メイン実行"""
    parser = argparse.ArgumentParser(description='MT4-Python CSV統合テスト')
    parser.add_argument('--duration', type=int, default=5, help='テスト時間（分）')
    parser.add_argument('--data-dir', type=str, default='MT4_Data', help='データディレクトリ')
    parser.add_argument('--simulate-price', action='store_true', help='価格データ模擬生成')
    
    args = parser.parse_args()
    
    print("🧪 MT4-Python CSV統合テストシステム")
    print("=" * 60)
    
    # 価格データ模擬生成（オプション）
    if args.simulate_price:
        price_thread = threading.Thread(
            target=simulate_price_feed, 
            args=(args.data_dir, args.duration * 60),
            daemon=True
        )
        price_thread.start()
        time.sleep(1)  # 価格フィード開始待機
    
    # 統合テスト実行
    test_runner = CSVIntegrationTest(args.data_dir)
    test_runner.run_full_integration_test(args.duration)

if __name__ == "__main__":
    main()