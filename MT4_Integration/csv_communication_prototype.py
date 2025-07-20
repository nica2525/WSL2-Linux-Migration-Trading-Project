#!/usr/bin/env python3
"""
CSV通信プロトタイプ実装
MT4-Python統合の最初のステップとして安全・確実なCSV通信を実装
"""

import csv
import os
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import threading
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVCommunicationPrototype:
    """CSV通信プロトタイプクラス"""
    
    def __init__(self, data_dir: str = "MT4_Data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # ファイルパス
        self.price_file = self.data_dir / "price_data.csv"
        self.signal_file = self.data_dir / "trading_signals.csv" 
        self.status_file = self.data_dir / "connection_status.csv"
        
        # 制御フラグ
        self.running = False
        self.last_heartbeat = time.time()
        
        # 価格データバッファ
        self.price_buffer = []
        self.max_buffer_size = 1000
        
        logger.info(f"CSV通信プロトタイプ初期化完了: {self.data_dir}")
    
    def start_monitoring(self):
        """モニタリング開始"""
        self.running = True
        
        # ステータスファイル初期化
        self._write_status("PYTHON_STARTED")
        
        # 価格データ監視スレッド開始
        price_thread = threading.Thread(target=self._monitor_price_data, daemon=True)
        price_thread.start()
        
        # ヘルスチェックスレッド開始
        health_thread = threading.Thread(target=self._health_check, daemon=True)
        health_thread.start()
        
        logger.info("CSV通信モニタリング開始")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """モニタリング停止"""
        self.running = False
        self._write_status("PYTHON_STOPPED")
        logger.info("CSV通信モニタリング停止")
    
    def _monitor_price_data(self):
        """価格データ監視"""
        last_modified = 0
        
        while self.running:
            try:
                if self.price_file.exists():
                    current_modified = self.price_file.stat().st_mtime
                    
                    if current_modified > last_modified:
                        self._process_price_update()
                        last_modified = current_modified
                
                time.sleep(0.1)  # 100ms間隔
                
            except Exception as e:
                logger.error(f"価格データ監視エラー: {e}")
                time.sleep(1)
    
    def _process_price_update(self):
        """価格データ更新処理"""
        try:
            # 最新価格データ読み込み
            with open(self.price_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            if not rows:
                return
                
            # 最新データを取得
            latest_data = rows[-1]
            
            # 価格データ検証
            required_fields = ['timestamp', 'symbol', 'bid', 'ask', 'volume']
            if not all(field in latest_data for field in required_fields):
                logger.warning(f"不完全な価格データ: {latest_data}")
                return
            
            # バッファに追加
            price_tick = {
                'timestamp': float(latest_data['timestamp']),
                'symbol': latest_data['symbol'],
                'bid': float(latest_data['bid']),
                'ask': float(latest_data['ask']),
                'volume': int(latest_data['volume'])
            }
            
            self.price_buffer.append(price_tick)
            
            # バッファサイズ制限
            if len(self.price_buffer) > self.max_buffer_size:
                self.price_buffer.pop(0)
            
            # ブレイクアウト判定
            self._check_breakout_signal(price_tick)
            
            # ハートビート更新
            self.last_heartbeat = time.time()
            
        except Exception as e:
            logger.error(f"価格データ処理エラー: {e}")
    
    def _check_breakout_signal(self, current_tick: Dict):
        """ブレイクアウトシグナル判定（Look-ahead bias修正版）"""
        if len(self.price_buffer) < 51:  # 確定足判定のため+1
            return
        
        try:
            # Look-ahead bias回避：最新ティックは除外し、確定した足のみ使用
            confirmed_data = self.price_buffer[-51:-1]  # 最新を除く50足
            prices = [tick['bid'] for tick in confirmed_data]
            
            # 移動平均とレンジ計算（確定足のみ）
            ma_20 = np.mean(prices[-20:])
            high_20 = max(prices[-20:])
            low_20 = min(prices[-20:])
            # 確定した最新足の価格で判定
            confirmed_price = confirmed_data[-1]['bid']
            
            # ブレイクアウト条件判定
            signal = None
            confidence = 0.0
            
            # 上方ブレイクアウト
            if confirmed_price > high_20 * 1.0005:  # 0.05% above high
                volatility = np.std(prices[-20:])
                if volatility > 0.0001:  # 最小ボラティリティ要件
                    signal = "BUY"
                    confidence = min(0.9, (confirmed_price - high_20) / (ma_20 * 0.01))
            
            # 下方ブレイクアウト  
            elif confirmed_price < low_20 * 0.9995:  # 0.05% below low
                volatility = np.std(prices[-20:])
                if volatility > 0.0001:
                    signal = "SELL"
                    confidence = min(0.9, (low_20 - confirmed_price) / (ma_20 * 0.01))
            
            # シグナル送信（確定足データを使用）
            if signal and confidence > 0.3:
                self._send_trading_signal(signal, confidence, confirmed_data[-1])
                
        except Exception as e:
            logger.error(f"ブレイクアウト判定エラー: {e}")
    
    def _send_trading_signal(self, action: str, confidence: float, tick_data: Dict):
        """取引シグナル送信"""
        try:
            signal_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': tick_data['symbol'],
                'action': action,
                'price': tick_data['bid'],
                'confidence': confidence,
                'volume': 0.1,  # デフォルトロットサイズ
                'stop_loss': self._calculate_stop_loss(tick_data['bid'], action),
                'take_profit': self._calculate_take_profit(tick_data['bid'], action)
            }
            
            # CSVファイルに書き込み
            file_exists = self.signal_file.exists()
            
            with open(self.signal_file, 'a', newline='') as f:
                fieldnames = ['timestamp', 'symbol', 'action', 'price', 'confidence', 
                            'volume', 'stop_loss', 'take_profit']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(signal_data)
            
            logger.info(f"取引シグナル送信: {action} {signal_data['symbol']} @ {signal_data['price']:.5f} (信頼度: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"シグナル送信エラー: {e}")
    
    def _calculate_stop_loss(self, price: float, action: str) -> float:
        """ストップロス計算"""
        atr_equivalent = 0.0020  # 固定ATR相当値 (20 pips)
        
        if action == "BUY":
            return price - atr_equivalent
        else:  # SELL
            return price + atr_equivalent
    
    def _calculate_take_profit(self, price: float, action: str) -> float:
        """テイクプロフィット計算"""
        atr_equivalent = 0.0040  # 固定ATR相当値 (40 pips)
        
        if action == "BUY":
            return price + atr_equivalent
        else:  # SELL
            return price - atr_equivalent
    
    def _write_status(self, status: str):
        """ステータス書き込み"""
        try:
            status_data = {
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'heartbeat': self.last_heartbeat
            }
            
            with open(self.status_file, 'w', newline='') as f:
                fieldnames = ['timestamp', 'status', 'heartbeat']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(status_data)
                
        except Exception as e:
            logger.error(f"ステータス書き込みエラー: {e}")
    
    def _health_check(self):
        """ヘルスチェック"""
        while self.running:
            try:
                current_time = time.time()
                
                # 30秒以上データ更新がない場合
                if current_time - self.last_heartbeat > 30:
                    logger.warning("データ受信タイムアウト - MT4接続確認が必要")
                    self._write_status("TIMEOUT_WARNING")
                else:
                    self._write_status("HEALTHY")
                
                time.sleep(10)  # 10秒間隔
                
            except Exception as e:
                logger.error(f"ヘルスチェックエラー: {e}")
                time.sleep(10)

def create_sample_price_data():
    """サンプル価格データ生成（テスト用）"""
    data_dir = Path("MT4_Data")
    data_dir.mkdir(exist_ok=True)
    
    price_file = data_dir / "price_data.csv"
    
    # サンプルデータ生成
    base_price = 1.1000
    timestamps = []
    prices = []
    
    for i in range(100):
        timestamp = time.time() - (100 - i) * 1
        price_change = np.random.normal(0, 0.0001)
        price = base_price + price_change
        
        data = {
            'timestamp': timestamp,
            'symbol': 'EURUSD',
            'bid': price,
            'ask': price + 0.0002,
            'volume': np.random.randint(10, 1000)
        }
        
        # ファイルに追記
        file_exists = price_file.exists()
        with open(price_file, 'a', newline='') as f:
            fieldnames = ['timestamp', 'symbol', 'bid', 'ask', 'volume']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                file_exists = True
            
            writer.writerow(data)
        
        time.sleep(0.1)  # 100ms間隔

def main():
    """メイン実行"""
    print("🔄 CSV通信プロトタイプ - MT4-Python統合テスト")
    print("=" * 60)
    
    # プロトタイプインスタンス生成
    csv_comm = CSVCommunicationPrototype()
    
    print("📊 サンプル価格データ生成中...")
    # 別スレッドでサンプルデータ生成
    data_thread = threading.Thread(target=create_sample_price_data, daemon=True)
    data_thread.start()
    
    print("🚀 CSV通信モニタリング開始...")
    # 通信監視開始
    csv_comm.start_monitoring()

if __name__ == "__main__":
    main()