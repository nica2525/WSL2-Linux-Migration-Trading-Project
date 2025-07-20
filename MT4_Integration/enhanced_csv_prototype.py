#!/usr/bin/env python3
"""
強化されたCSV通信プロトタイプ（Gemini査読結果対応版）
- Look-ahead bias完全排除
- 堅牢なエラーハンドリング
- パフォーマンス改善
- ZeroMQ移行準備
"""

import csv
import os
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Union
import threading
import logging
from dataclasses import dataclass
from enum import Enum
import queue
import json

# ログ設定強化
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_communication.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """取引シグナルタイプ"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class PriceTick:
    """価格ティックデータ"""
    timestamp: float
    symbol: str
    bid: float
    ask: float
    volume: int
    
    def __post_init__(self):
        """データ検証"""
        if self.bid <= 0 or self.ask <= 0:
            raise ValueError(f"Invalid price: bid={self.bid}, ask={self.ask}")
        if self.ask < self.bid:
            raise ValueError(f"Ask ({self.ask}) < Bid ({self.bid})")
        if self.volume < 0:
            raise ValueError(f"Invalid volume: {self.volume}")

@dataclass
class TradingSignal:
    """取引シグナル"""
    timestamp: datetime
    symbol: str
    action: SignalType
    price: float
    confidence: float
    volume: float
    stop_loss: float
    take_profit: float
    
    def __post_init__(self):
        """データ検証"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Invalid confidence: {self.confidence}")
        if self.volume <= 0:
            raise ValueError(f"Invalid volume: {self.volume}")

class BreakoutDetector:
    """ブレイクアウト検出器（Look-ahead bias完全排除版）"""
    
    def __init__(self, lookback_period: int = 20, min_volatility: float = 0.0001):
        self.lookback_period = lookback_period
        self.min_volatility = min_volatility
        self.price_history = []
        
    def add_confirmed_tick(self, tick: PriceTick) -> Optional[TradingSignal]:
        """確定ティック追加とシグナル判定"""
        self.price_history.append(tick)
        
        # 履歴サイズ制限
        if len(self.price_history) > 1000:
            self.price_history.pop(0)
        
        # 最小履歴数チェック
        if len(self.price_history) < self.lookback_period + 1:
            return None
        
        try:
            return self._detect_breakout_signal()
        except Exception as e:
            logger.error(f"ブレイクアウト検出エラー: {e}")
            return None
    
    def _detect_breakout_signal(self) -> Optional[TradingSignal]:
        """Look-ahead bias完全排除ブレイクアウト検出"""
        # 最新の確定足を除いて過去データで計算
        historical_prices = [tick.bid for tick in self.price_history[:-1]]
        
        if len(historical_prices) < self.lookback_period:
            return None
        
        # レンジ計算（最新足は除外）
        recent_prices = historical_prices[-self.lookback_period:]
        high_range = max(recent_prices)
        low_range = min(recent_prices)
        ma_price = np.mean(recent_prices)
        volatility = np.std(recent_prices)
        
        # ボラティリティフィルター
        if volatility < self.min_volatility:
            return None
        
        # 確定した最新足の価格
        current_tick = self.price_history[-1]
        current_price = current_tick.bid
        
        # ブレイクアウト判定
        signal_type = None
        confidence = 0.0
        
        # 上方ブレイクアウト
        if current_price > high_range * 1.0005:  # 0.05% above high
            signal_type = SignalType.BUY
            confidence = min(0.9, (current_price - high_range) / (ma_price * 0.01))
            
        # 下方ブレイクアウト
        elif current_price < low_range * 0.9995:  # 0.05% below low
            signal_type = SignalType.SELL
            confidence = min(0.9, (low_range - current_price) / (ma_price * 0.01))
        
        # シグナル生成
        if signal_type and confidence > 0.3:
            return TradingSignal(
                timestamp=datetime.now(),
                symbol=current_tick.symbol,
                action=signal_type,
                price=current_price,
                confidence=confidence,
                volume=0.1,  # デフォルトロット
                stop_loss=self._calculate_stop_loss(current_price, signal_type, volatility),
                take_profit=self._calculate_take_profit(current_price, signal_type, volatility)
            )
        
        return None
    
    def _calculate_stop_loss(self, price: float, signal_type: SignalType, volatility: float) -> float:
        """動的ストップロス計算"""
        atr_equivalent = max(0.0020, volatility * 2)  # 最小20pips、動的ATR
        
        if signal_type == SignalType.BUY:
            return price - atr_equivalent
        else:
            return price + atr_equivalent
    
    def _calculate_take_profit(self, price: float, signal_type: SignalType, volatility: float) -> float:
        """動的テイクプロフィット計算"""
        atr_equivalent = max(0.0040, volatility * 3)  # 最小40pips、動的ATR
        
        if signal_type == SignalType.BUY:
            return price + atr_equivalent
        else:
            return price - atr_equivalent

class FileMonitor:
    """堅牢なファイル監視システム"""
    
    def __init__(self, file_path: Path, callback, poll_interval: float = 0.1):
        self.file_path = file_path
        self.callback = callback
        self.poll_interval = poll_interval
        self.last_modified = 0
        self.running = False
        
    def start(self):
        """監視開始"""
        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        logger.info(f"ファイル監視開始: {self.file_path}")
    
    def stop(self):
        """監視停止"""
        self.running = False
        logger.info(f"ファイル監視停止: {self.file_path}")
    
    def _monitor_loop(self):
        """監視ループ"""
        consecutive_errors = 0
        max_errors = 10
        
        while self.running:
            try:
                if self.file_path.exists():
                    current_modified = self.file_path.stat().st_mtime
                    
                    if current_modified > self.last_modified:
                        self.last_modified = current_modified
                        self.callback()
                        consecutive_errors = 0  # エラー回数リセット
                
                time.sleep(self.poll_interval)
                
            except PermissionError as e:
                logger.warning(f"ファイルアクセス権限エラー: {e}")
                time.sleep(1)
            except OSError as e:
                consecutive_errors += 1
                logger.error(f"ファイルシステムエラー ({consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    logger.critical("連続エラー回数上限到達、監視停止")
                    break
                    
                time.sleep(min(consecutive_errors, 5))  # 指数バックオフ
            except Exception as e:
                logger.error(f"予期しないエラー: {e}")
                time.sleep(1)

class EnhancedCSVCommunicator:
    """強化されたCSV通信システム"""
    
    def __init__(self, data_dir: str = "MT4_Data", config: Optional[Dict] = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 設定
        self.config = config or self._get_default_config()
        
        # ファイルパス
        self.price_file = self.data_dir / "price_data.csv"
        self.signal_file = self.data_dir / "trading_signals.csv"
        self.status_file = self.data_dir / "connection_status.csv"
        
        # コンポーネント
        self.breakout_detector = BreakoutDetector(
            lookback_period=self.config['breakout']['lookback_period'],
            min_volatility=self.config['breakout']['min_volatility']
        )
        
        # ファイル監視
        self.price_monitor = FileMonitor(
            self.price_file, 
            self._process_price_update,
            self.config['monitoring']['poll_interval']
        )
        
        # 状態管理
        self.running = False
        self.last_heartbeat = time.time()
        self.signal_queue = queue.Queue(maxsize=100)
        
        logger.info(f"強化CSV通信システム初期化完了: {self.data_dir}")
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            'breakout': {
                'lookback_period': 20,
                'min_volatility': 0.0001
            },
            'monitoring': {
                'poll_interval': 0.1,
                'heartbeat_interval': 10,
                'timeout_threshold': 30
            },
            'risk_management': {
                'max_signals_per_minute': 10,
                'min_signal_interval': 5
            }
        }
    
    def start(self):
        """システム開始"""
        self.running = True
        
        # ステータス初期化
        self._write_status("ENHANCED_PYTHON_STARTED")
        
        # ファイル監視開始
        self.price_monitor.start()
        
        # ヘルスチェック開始
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        
        # シグナル処理開始
        signal_thread = threading.Thread(target=self._signal_processing_loop, daemon=True)
        signal_thread.start()
        
        logger.info("強化CSV通信システム開始")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """システム停止"""
        self.running = False
        self.price_monitor.stop()
        self._write_status("ENHANCED_PYTHON_STOPPED")
        logger.info("強化CSV通信システム停止")
    
    def _process_price_update(self):
        """価格データ更新処理（強化版）"""
        try:
            # ファイルロック対応の読み込み
            tick_data = self._safe_read_price_file()
            if not tick_data:
                return
            
            # データ検証と変換
            try:
                tick = PriceTick(
                    timestamp=float(tick_data['timestamp']),
                    symbol=tick_data['symbol'],
                    bid=float(tick_data['bid']),
                    ask=float(tick_data['ask']),
                    volume=int(tick_data['volume'])
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"無効な価格データ: {e}")
                return
            
            # ブレイクアウト検出
            signal = self.breakout_detector.add_confirmed_tick(tick)
            
            if signal:
                # シグナルキューに追加
                try:
                    self.signal_queue.put_nowait(signal)
                    logger.info(f"シグナル生成: {signal.action.value} @ {signal.price:.5f}")
                except queue.Full:
                    logger.warning("シグナルキューが満杯、古いシグナルを破棄")
                    try:
                        self.signal_queue.get_nowait()
                        self.signal_queue.put_nowait(signal)
                    except queue.Empty:
                        pass
            
            self.last_heartbeat = time.time()
            
        except Exception as e:
            logger.error(f"価格データ処理エラー: {e}")
    
    def _safe_read_price_file(self) -> Optional[Dict]:
        """安全な価格ファイル読み込み"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                with open(self.price_file, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                if rows:
                    return rows[-1]  # 最新行
                    
            except (PermissionError, FileNotFoundError):
                if attempt < max_attempts - 1:
                    time.sleep(0.01)  # 10ms待機
                    continue
                logger.warning("価格ファイル読み込み失敗")
            except Exception as e:
                logger.error(f"価格ファイル読み込みエラー: {e}")
                break
        
        return None
    
    def _signal_processing_loop(self):
        """シグナル処理ループ"""
        last_signal_time = 0
        signal_count_minute = 0
        minute_start = time.time()
        
        while self.running:
            try:
                # レート制限チェック
                current_time = time.time()
                if current_time - minute_start > 60:
                    signal_count_minute = 0
                    minute_start = current_time
                
                # シグナル取得（タイムアウト付き）
                signal = self.signal_queue.get(timeout=1)
                
                # レート制限
                if signal_count_minute >= self.config['risk_management']['max_signals_per_minute']:
                    logger.warning("シグナル送信レート制限に達しました")
                    continue
                
                if current_time - last_signal_time < self.config['risk_management']['min_signal_interval']:
                    logger.info("シグナル間隔が短すぎるため送信をスキップ")
                    continue
                
                # シグナル送信
                if self._send_trading_signal(signal):
                    signal_count_minute += 1
                    last_signal_time = current_time
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"シグナル処理エラー: {e}")
    
    def _send_trading_signal(self, signal: TradingSignal) -> bool:
        """取引シグナル送信（原子的操作）"""
        try:
            # 一時ファイルに書き込み後、原子的移動
            temp_file = self.signal_file.with_suffix('.tmp')
            
            signal_data = {
                'timestamp': signal.timestamp.isoformat(),
                'symbol': signal.symbol,
                'action': signal.action.value,
                'price': signal.price,
                'confidence': signal.confidence,
                'volume': signal.volume,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit
            }
            
            file_exists = self.signal_file.exists()
            
            with open(temp_file, 'w', newline='') as f:
                fieldnames = ['timestamp', 'symbol', 'action', 'price', 'confidence',
                            'volume', 'stop_loss', 'take_profit']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(signal_data)
            
            # 原子的移動
            temp_file.replace(self.signal_file)
            
            logger.info(f"シグナル送信成功: {signal.action.value} {signal.symbol} @ {signal.price:.5f}")
            return True
            
        except Exception as e:
            logger.error(f"シグナル送信エラー: {e}")
            return False
    
    def _health_check_loop(self):
        """ヘルスチェックループ"""
        while self.running:
            try:
                current_time = time.time()
                
                if current_time - self.last_heartbeat > self.config['monitoring']['timeout_threshold']:
                    logger.warning("データ受信タイムアウト - MT4接続確認が必要")
                    self._write_status("TIMEOUT_WARNING")
                else:
                    self._write_status("HEALTHY")
                
                time.sleep(self.config['monitoring']['heartbeat_interval'])
                
            except Exception as e:
                logger.error(f"ヘルスチェックエラー: {e}")
                time.sleep(self.config['monitoring']['heartbeat_interval'])
    
    def _write_status(self, status: str):
        """ステータス書き込み"""
        try:
            status_data = {
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'heartbeat': self.last_heartbeat,
                'queue_size': self.signal_queue.qsize()
            }
            
            with open(self.status_file, 'w', newline='') as f:
                fieldnames = ['timestamp', 'status', 'heartbeat', 'queue_size']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(status_data)
                
        except Exception as e:
            logger.error(f"ステータス書き込みエラー: {e}")

def main():
    """メイン実行"""
    print("🚀 強化されたCSV通信プロトタイプ - Gemini査読対応版")
    print("=" * 60)
    
    # 設定読み込み
    config_file = Path("enhanced_csv_config.json")
    config = None
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"✅ 設定ファイル読み込み: {config_file}")
        except Exception as e:
            print(f"⚠️ 設定ファイル読み込み失敗: {e}")
    
    # システム起動
    communicator = EnhancedCSVCommunicator(config=config)
    communicator.start()

if __name__ == "__main__":
    main()