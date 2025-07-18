#!/usr/bin/env python3
"""
Phase 2: Real-time Signal Generation System
Phase2タスク2.1-2.3実装 - kiro設計計画に基づく実装

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 1.1, 1.2, 1.3 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import time
import logging
import aiosqlite
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from queue import PriorityQueue, Queue
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import sys
import os
import yaml

# 既存システムとの統合
sys.path.append(str(Path(__file__).parent))
from communication.tcp_bridge import TCPBridge
from communication.file_bridge import FileBridge

# 設定読み込み
def load_config(config_path: str = 'config.yaml', environment: str = 'production') -> Dict[str, Any]:
    """設定ファイル読み込み"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 環境別設定をマージ
        if environment in config.get('environments', {}):
            env_config = config['environments'][environment]
            # 環境固有設定で上書き
            for key, value in env_config.items():
                if '.' in key:
                    # ネストした設定 (例: "communication.file_bridge_dir")
                    keys = key.split('.')
                    target = config
                    for k in keys[:-1]:
                        target = target.setdefault(k, {})
                    target[keys[-1]] = value
                else:
                    config[key] = value
        
        return config
    except (FileNotFoundError, PermissionError) as e:
        logger.error(f"Configuration file access error: {e}")
        # フォールバック設定
    except yaml.YAMLError as e:
        logger.error(f"Configuration file parsing error: {e}")
        # フォールバック設定
    except Exception as e:
        logger.error(f"Unexpected configuration loading error: {e}")
        # フォールバック設定
        return {
            'data_processing': {'buffer_size': 10000, 'health_check_interval': 30},
            'signal_generation': {'quality_threshold': 0.7, 'max_signals_per_minute': 100},
            'communication': {
                'data_tcp_host': 'localhost', 'data_tcp_port': 9091,
                'signal_tcp_host': 'localhost', 'signal_tcp_port': 9090,
                'file_bridge_dir': '/mnt/c/MT4_Bridge',
                'reconnect_attempts': 3, 'reconnect_timeout': 5.0
            },
            'database': {'path': './realtime_signals.db'},
            'wfa_integration': {
                'default_params': {
                    'lookback_period': 20, 'breakout_threshold': 2.0,
                    'atr_period': 14, 'min_volume_ratio': 1.5
                }
            }
        }

# グローバル設定
CONFIG = load_config()

# ログ設定（設定ファイルベース）
def setup_logging(config: Dict[str, Any]):
    """設定に基づくログ設定"""
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'realtime_signal_generator.log')
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

setup_logging(CONFIG)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """市場データ構造"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

@dataclass
class TradingSignal:
    """取引シグナル構造 - kiro設計design.md準拠"""
    timestamp: datetime
    symbol: str
    action: str  # 'BUY', 'SELL', 'CLOSE'
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_quality: float = 0.0
    strategy_params: Dict = None
    priority: int = 1  # 1=High, 2=Medium, 3=Low
    
    def __post_init__(self):
        if self.strategy_params is None:
            self.strategy_params = {}
    
    def __lt__(self, other):
        return self.priority < other.priority

class MarketDataFeed:
    """
    Phase2タスク2.1: 市場データフィードインターフェース
    kiro設計tasks.md:59-65準拠
    """
    
    def __init__(self):
        self.is_running = False
        self.data_buffer = []
        self.buffer_lock = threading.Lock()
        self.subscribers = []
        # 設定から通信パラメータ取得
        comm_config = CONFIG.get('communication', {})
        self.tcp_bridge = TCPBridge(
            host=comm_config.get('data_tcp_host', 'localhost'), 
            port=comm_config.get('data_tcp_port', 9091)
        )
        self.file_bridge = FileBridge(
            message_dir=comm_config.get('file_bridge_dir', '/mnt/c/MT4_Bridge')
        )
        self.last_health_check = time.time()
        
    async def start(self):
        """データフィード開始"""
        logger.info("Market data feed starting...")
        self.is_running = True
        
        # TCP接続試行
        if await self._connect_tcp():
            logger.info("TCP connection established")
        else:
            logger.warning("TCP connection failed, using file bridge")
        
        # データ取得ループ開始
        asyncio.create_task(self._data_collection_loop())
        asyncio.create_task(self._health_monitor_loop())
        
    async def _connect_tcp(self) -> bool:
        """TCP接続確立（再接続ロジック強化）"""
        max_attempts = CONFIG.get('communication', {}).get('reconnect_attempts', 3)
        base_timeout = CONFIG.get('communication', {}).get('reconnect_timeout', 5.0)
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"TCP connection attempt {attempt + 1}/{max_attempts}")
                if await self.tcp_bridge.connect():
                    logger.info(f"TCP connection successful on attempt {attempt + 1}")
                    return True
            except (ConnectionError, OSError, TimeoutError) as e:
                logger.warning(f"TCP connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    # 指数バックオフ: 2^attempt * base_timeout
                    wait_time = base_timeout * (2 ** attempt)
                    logger.info(f"Waiting {wait_time:.1f}s before retry...")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected TCP connection error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    wait_time = base_timeout * (2 ** attempt)
                    await asyncio.sleep(wait_time)
        
        logger.error(f"TCP connection failed after {max_attempts} attempts")
        return False
    
    async def _data_collection_loop(self):
        """データ収集メインループ"""
        while self.is_running:
            try:
                # TCP経由でデータ取得試行
                data = await self._get_tcp_data()
                if not data:
                    # フォールバック: ファイル経由
                    data = await self._get_file_data()
                
                if data:
                    await self._process_market_data(data)
                    
                await asyncio.sleep(0.1)  # 100ms間隔
                
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.error(f"Data collection connection error: {e}")
                await asyncio.sleep(1)
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Data collection parsing error: {e}")
                await asyncio.sleep(0.1)  # より短い待機
            except Exception as e:
                logger.error(f"Unexpected data collection error: {e}")
                await asyncio.sleep(1)
    
    async def _get_tcp_data(self) -> Optional[Dict]:
        """TCP経由データ取得"""
        try:
            if self.tcp_bridge.is_connected():
                return await self.tcp_bridge.receive_data()
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"TCP data fetch connection failed: {e}")
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"TCP data fetch parsing failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected TCP data fetch error: {e}")
        return None
    
    async def _get_file_data(self) -> Optional[Dict]:
        """ファイル経由データ取得"""
        try:
            # ファイルブリッジからメッセージ受信
            message = await self.file_bridge.receive_message()
            if message and message.get('type') == 'market_data':
                return message.get('data')
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.warning(f"File data fetch access failed: {e}")
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            logger.warning(f"File data fetch parsing failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected file data fetch error: {e}")
        return None
    
    async def _process_market_data(self, raw_data: Dict):
        """データ処理・検証・バッファ管理"""
        try:
            # データ検証
            if not self._validate_data(raw_data):
                logger.warning(f"Invalid data received: {raw_data}")
                return
            
            # MarketDataオブジェクト作成
            market_data = MarketData(
                timestamp=datetime.fromisoformat(raw_data['timestamp']),
                symbol=raw_data['symbol'],
                open=float(raw_data['open']),
                high=float(raw_data['high']),
                low=float(raw_data['low']),
                close=float(raw_data['close']),
                volume=float(raw_data.get('volume', 0))
            )
            
            # バッファ管理（設定ベース）
            buffer_size = CONFIG.get('data_processing', {}).get('buffer_size', 10000)
            with self.buffer_lock:
                self.data_buffer.append(market_data)
                if len(self.data_buffer) > buffer_size:
                    self.data_buffer.pop(0)
            
            # 購読者に通知
            for subscriber in self.subscribers:
                await subscriber(market_data)
                
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Data processing validation error: {e}")
        except Exception as e:
            logger.error(f"Unexpected data processing error: {e}")
    
    def _validate_data(self, data: Dict) -> bool:
        """データ品質検証"""
        required_fields = ['timestamp', 'symbol', 'open', 'high', 'low', 'close']
        
        if not all(field in data for field in required_fields):
            return False
        
        try:
            o, h, l, c = float(data['open']), float(data['high']), float(data['low']), float(data['close'])
            # 基本的な価格整合性チェック
            if not (l <= o <= h and l <= c <= h):
                return False
            if any(price <= 0 for price in [o, h, l, c]):
                return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    async def _health_monitor_loop(self):
        """健全性監視ループ"""
        while self.is_running:
            try:
                current_time = time.time()
                health_interval = CONFIG.get('data_processing', {}).get('health_check_interval', 30)
                if current_time - self.last_health_check > health_interval:
                    await self._perform_health_check()
                    self.last_health_check = current_time
                
                await asyncio.sleep(10)
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.error(f"Health monitor connection error: {e}")
            except Exception as e:
                logger.error(f"Unexpected health monitor error: {e}")
    
    async def _perform_health_check(self):
        """健全性チェック実行（再接続ロジック強化）"""
        # TCP接続チェック
        if not self.tcp_bridge.is_connected():
            logger.warning("TCP connection lost, attempting reconnection...")
            reconnection_success = await self._connect_tcp()
            if not reconnection_success:
                logger.error("TCP reconnection failed, using file bridge only")
        
        # データ受信チェック
        with self.buffer_lock:
            if len(self.data_buffer) == 0:
                logger.warning("No data received recently")
            else:
                last_data_time = self.data_buffer[-1].timestamp
                time_diff = datetime.now() - last_data_time
                if time_diff.total_seconds() > 60:
                    logger.warning(f"Last data is {time_diff.total_seconds():.1f}s old")
                    # データ途絶時の再接続試行
                    if time_diff.total_seconds() > 120:  # 2分以上データなし
                        logger.warning("Data starvation detected, attempting TCP reconnection...")
                        await self._connect_tcp()
    
    def subscribe(self, callback):
        """データ購読登録"""
        self.subscribers.append(callback)
    
    def get_recent_data(self, symbol: str, count: int = 100) -> List[MarketData]:
        """最近のデータ取得"""
        with self.buffer_lock:
            symbol_data = [d for d in self.data_buffer if d.symbol == symbol]
            return symbol_data[-count:] if symbol_data else []

class SignalGenerator:
    """
    Phase2タスク2.2: シグナル生成エンジン
    kiro設計tasks.md:67-73準拠
    """
    
    def __init__(self, market_feed: MarketDataFeed):
        self.market_feed = market_feed
        self.wfa_params = {}
        self.is_running = False
        self.signal_queue = PriorityQueue()
        
        # WFA最適化結果読み込み
        self._load_wfa_parameters()
        
        # データ購読
        self.market_feed.subscribe(self._on_market_data)
    
    def _load_wfa_parameters(self):
        """WFA最適化結果からパラメータ読み込み"""
        try:
            # 既存enhanced_parallel_wfa_with_slippage.pyの結果ファイル探索
            results_files = list(Path('.').glob('*wfa_results*.json'))
            if results_files:
                latest_file = max(results_files, key=os.path.getctime)
                with open(latest_file, 'r') as f:
                    wfa_results = json.load(f)
                
                # 最適パラメータ抽出
                if 'best_parameters' in wfa_results:
                    self.wfa_params = wfa_results['best_parameters']
                    logger.info(f"WFA parameters loaded: {self.wfa_params}")
                else:
                    self._set_default_parameters()
            else:
                self._set_default_parameters()
                
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"WFA parameter file access error: {e}")
            self._set_default_parameters()
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"WFA parameter parsing error: {e}")
            self._set_default_parameters()
        except Exception as e:
            logger.error(f"Unexpected WFA parameter loading error: {e}")
            self._set_default_parameters()
    
    def _set_default_parameters(self):
        """デフォルトパラメータ設定（設定ファイルベース）"""
        default_params = CONFIG.get('wfa_integration', {}).get('default_params', {})
        self.wfa_params = {
            'lookback_period': default_params.get('lookback_period', 20),
            'breakout_threshold': default_params.get('breakout_threshold', 2.0),
            'volume_filter': default_params.get('volume_filter', True),
            'atr_period': default_params.get('atr_period', 14),
            'min_volume_ratio': default_params.get('min_volume_ratio', 1.5)
        }
        logger.info(f"Default parameters set from config: {self.wfa_params}")
    
    async def _on_market_data(self, market_data: MarketData):
        """市場データ受信時の処理"""
        try:
            # ブレイクアウトシグナル検出
            signal = await self._detect_breakout_signal(market_data)
            if signal:
                # シグナル品質評価
                signal.signal_quality = self._evaluate_signal_quality(signal, market_data)
                
                # 品質閾値チェック（設定ベース）
                quality_threshold = CONFIG.get('signal_generation', {}).get('quality_threshold', 0.7)
                if signal.signal_quality >= quality_threshold:
                    # 優先度設定
                    signal.priority = self._calculate_priority(signal)
                    
                    # キューに追加
                    await self.signal_queue.put(signal)
                    logger.info(f"Signal generated: {signal.action} {signal.symbol} (Quality: {signal.signal_quality:.3f})")
                
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Signal generation data error: {e}")
        except (OverflowError, ZeroDivisionError, TypeError) as e:
            logger.error(f"Signal generation calculation error: {e}")
        except Exception as e:
            logger.error(f"Unexpected signal generation error: {e}")
    
    async def _detect_breakout_signal(self, current_data: MarketData) -> Optional[TradingSignal]:
        """ブレイクアウトシグナル検出ロジック"""
        try:
            # 履歴データ取得
            historical_data = self.market_feed.get_recent_data(
                current_data.symbol, 
                self.wfa_params.get('lookback_period', 20) + 1
            )
            
            if len(historical_data) < self.wfa_params.get('lookback_period', 20):
                return None
            
            # DataFrame変換
            df = pd.DataFrame([d.to_dict() for d in historical_data])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # ブレイクアウト検出
            lookback = self.wfa_params.get('lookback_period', 20)
            current_price = current_data.close
            
            # 最高値・最安値計算
            recent_high = df['high'].tail(lookback).max()
            recent_low = df['low'].tail(lookback).min()
            
            # ATRベースの閾値
            atr_period = self.wfa_params.get('atr_period', 14)
            if len(df) >= atr_period:
                df['tr'] = np.maximum(
                    df['high'] - df['low'],
                    np.maximum(
                        abs(df['high'] - df['close'].shift(1)),
                        abs(df['low'] - df['close'].shift(1))
                    )
                )
                atr = df['tr'].tail(atr_period).mean()
                breakout_threshold = atr * self.wfa_params.get('breakout_threshold', 2.0)
            else:
                breakout_threshold = (recent_high - recent_low) * 0.1
            
            # ブレイクアウト判定
            if current_price > recent_high + breakout_threshold:
                # 上方ブレイクアウト
                return TradingSignal(
                    timestamp=current_data.timestamp,
                    symbol=current_data.symbol,
                    action='BUY',
                    quantity=self._calculate_position_size(current_data, 'BUY'),
                    price=current_price,
                    stop_loss=recent_low,
                    take_profit=current_price + (current_price - recent_low) * 2,
                    strategy_params=self.wfa_params.copy()
                )
            
            elif current_price < recent_low - breakout_threshold:
                # 下方ブレイクアウト
                return TradingSignal(
                    timestamp=current_data.timestamp,
                    symbol=current_data.symbol,
                    action='SELL',
                    quantity=self._calculate_position_size(current_data, 'SELL'),
                    price=current_price,
                    stop_loss=recent_high,
                    take_profit=current_price - (recent_high - current_price) * 2,
                    strategy_params=self.wfa_params.copy()
                )
            
            return None
            
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Breakout detection data error: {e}")
            return None
        except (OverflowError, ZeroDivisionError, TypeError) as e:
            logger.error(f"Breakout detection calculation error: {e}")
            return None
        except pd.errors.EmptyDataError as e:
            logger.warning(f"Breakout detection insufficient data: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected breakout detection error: {e}")
            return None
    
    def _evaluate_signal_quality(self, signal: TradingSignal, market_data: MarketData) -> float:
        """シグナル品質評価"""
        try:
            quality_score = 0.0
            
            # ボリューム評価
            historical_data = self.market_feed.get_recent_data(market_data.symbol, 20)
            if len(historical_data) >= 10:
                avg_volume = np.mean([d.volume for d in historical_data[-10:]])
                if market_data.volume > avg_volume * self.wfa_params.get('min_volume_ratio', 1.5):
                    quality_score += 0.3
            
            # 価格モメンタム評価
            if len(historical_data) >= 5:
                recent_prices = [d.close for d in historical_data[-5:]]
                price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                if (signal.action == 'BUY' and price_momentum > 0.001) or \
                   (signal.action == 'SELL' and price_momentum < -0.001):
                    quality_score += 0.4
            
            # リスク・リワード比
            if signal.stop_loss and signal.take_profit:
                risk = abs(signal.price - signal.stop_loss)
                reward = abs(signal.take_profit - signal.price)
                if risk > 0:
                    rr_ratio = reward / risk
                    if rr_ratio >= 2.0:
                        quality_score += 0.3
                    elif rr_ratio >= 1.5:
                        quality_score += 0.2
            
            return min(quality_score, 1.0)
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.error(f"Quality evaluation calculation error: {e}")
            return 0.0
        except (IndexError, KeyError) as e:
            logger.error(f"Quality evaluation data error: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Unexpected quality evaluation error: {e}")
            return 0.0
    
    def _calculate_priority(self, signal: TradingSignal) -> int:
        """シグナル優先度計算"""
        if signal.signal_quality >= 0.9:
            return 1  # High
        elif signal.signal_quality >= 0.8:
            return 2  # Medium
        else:
            return 3  # Low
    
    def _calculate_position_size(self, market_data: MarketData, action: str) -> float:
        """ポジションサイズ計算"""
        # 基本サイズ（後でリスク管理システムと統合）
        return 0.1
    
    async def get_next_signal(self) -> Optional[TradingSignal]:
        """次のシグナル取得"""
        try:
            if not self.signal_queue.empty():
                return await self.signal_queue.get()
        except asyncio.QueueEmpty:
            # 正常な状態（キューが空）
            pass
        except Exception as e:
            logger.error(f"Unexpected signal retrieval error: {e}")
        return None

class SignalTransmissionSystem:
    """
    Phase2タスク2.3: シグナル送信システム
    kiro設計tasks.md:75-81準拠
    """
    
    def __init__(self):
        # 設定から通信パラメータ取得
        comm_config = CONFIG.get('communication', {})
        self.tcp_bridge = TCPBridge(
            host=comm_config.get('signal_tcp_host', 'localhost'), 
            port=comm_config.get('signal_tcp_port', 9090)
        )
        self.file_bridge = FileBridge(
            message_dir=comm_config.get('file_bridge_dir', '/mnt/c/MT4_Bridge')
        )
        self.signal_history = []
        self.is_running = False
        self.transmission_queue = Queue()
        self.sent_signals_count = 0
        self.last_minute_reset = time.time()
        
        # データベース初期化（非同期なので後で実行）
        self._db_initialized = False
    
    async def _init_database(self):
        """シグナル記録用データベース初期化（非同期）"""
        try:
            db_path = CONFIG.get('database', {}).get('path', './realtime_signals.db')
            async with aiosqlite.connect(db_path) as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        symbol TEXT,
                        action TEXT,
                        quantity REAL,
                        price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        signal_quality REAL,
                        priority INTEGER,
                        strategy_params TEXT,
                        transmission_status TEXT,
                        transmission_time TEXT,
                        error_message TEXT
                    )
                ''')
                await conn.commit()
            logger.info("Signal database initialized (async)")
        except aiosqlite.Error as e:
            logger.error(f"Database initialization SQL error: {e}")
        except (OSError, PermissionError) as e:
            logger.error(f"Database initialization access error: {e}")
        except Exception as e:
            logger.error(f"Unexpected database initialization error: {e}")
    
    async def start(self):
        """送信システム開始"""
        logger.info("Signal transmission system starting...")
        
        # データベース初期化
        if not self._db_initialized:
            await self._init_database()
            self._db_initialized = True
        
        self.is_running = True
        
        # TCP接続確立
        if await self._connect_tcp():
            logger.info("Signal transmission TCP connected")
        else:
            logger.warning("TCP connection failed, using file transmission")
        
        # 送信ループ開始
        asyncio.create_task(self._transmission_loop())
        asyncio.create_task(self._rate_limit_monitor())
    
    async def _connect_tcp(self) -> bool:
        """TCP接続確立（再接続ロジック強化）"""
        max_attempts = CONFIG.get('communication', {}).get('reconnect_attempts', 3)
        base_timeout = CONFIG.get('communication', {}).get('reconnect_timeout', 5.0)
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Signal TCP connection attempt {attempt + 1}/{max_attempts}")
                if await self.tcp_bridge.connect():
                    logger.info(f"Signal TCP connection successful on attempt {attempt + 1}")
                    return True
            except (ConnectionError, OSError, TimeoutError) as e:
                logger.warning(f"Signal TCP connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    # 指数バックオフ: 2^attempt * base_timeout
                    wait_time = base_timeout * (2 ** attempt)
                    logger.info(f"Waiting {wait_time:.1f}s before retry...")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected signal TCP connection error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    wait_time = base_timeout * (2 ** attempt)
                    await asyncio.sleep(wait_time)
        
        logger.error(f"Signal TCP connection failed after {max_attempts} attempts")
        return False
    
    async def send_signal(self, signal: TradingSignal) -> bool:
        """シグナル送信"""
        try:
            # レート制限チェック
            if not self._check_rate_limit():
                logger.warning("Signal rate limit exceeded")
                return False
            
            # 送信実行
            success = await self._transmit_signal(signal)
            
            # 記録
            await self._record_signal(signal, success)
            
            if success:
                self.sent_signals_count += 1
                logger.info(f"Signal sent successfully: {signal.action} {signal.symbol}")
            else:
                logger.error(f"Signal transmission failed: {signal.action} {signal.symbol}")
            
            return success
            
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Signal transmission connection error: {e}")
            await self._record_signal(signal, False, f"Connection error: {e}")
            return False
        except (ValueError, TypeError, json.JSONEncodeError) as e:
            logger.error(f"Signal transmission data error: {e}")
            await self._record_signal(signal, False, f"Data error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected signal transmission error: {e}")
            await self._record_signal(signal, False, f"Unexpected error: {e}")
            return False
    
    def _check_rate_limit(self) -> bool:
        """送信レート制限チェック"""
        current_time = time.time()
        if current_time - self.last_minute_reset >= 60:
            self.sent_signals_count = 0
            self.last_minute_reset = current_time
        
        max_signals = CONFIG.get('signal_generation', {}).get('max_signals_per_minute', 100)
        return self.sent_signals_count < max_signals
    
    async def _transmit_signal(self, signal: TradingSignal) -> bool:
        """実際の送信処理"""
        signal_data = {
            'timestamp': signal.timestamp.isoformat(),
            'symbol': signal.symbol,
            'action': signal.action,
            'quantity': signal.quantity,
            'price': signal.price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'signal_quality': signal.signal_quality,
            'strategy_params': signal.strategy_params
        }
        
        # TCP送信試行（再接続ロジック強化）
        if self.tcp_bridge.is_connected():
            try:
                success = await self.tcp_bridge.send_data(signal_data)
                if success:
                    return True
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning(f"TCP transmission connection failed: {e}")
                # 接続失敗時の再接続試行
                logger.info("Attempting TCP reconnection for signal transmission...")
                if await self._connect_tcp():
                    try:
                        success = await self.tcp_bridge.send_data(signal_data)
                        if success:
                            logger.info("Signal sent successfully after reconnection")
                            return True
                    except Exception as reconnect_e:
                        logger.warning(f"Signal transmission failed even after reconnection: {reconnect_e}")
            except (ValueError, TypeError, json.JSONEncodeError) as e:
                logger.warning(f"TCP transmission data failed: {e}")
            except Exception as e:
                logger.warning(f"Unexpected TCP transmission error: {e}")
        
        # フォールバック: ファイル送信
        try:
            message = {
                'type': 'trading_signal',
                'data': signal_data,
                'timestamp': datetime.now().isoformat()
            }
            return await self.file_bridge.send_message(message, 'mt4')
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error(f"File transmission access failed: {e}")
            return False
        except (ValueError, TypeError, json.JSONEncodeError) as e:
            logger.error(f"File transmission data failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected file transmission error: {e}")
            return False
    
    async def _record_signal(self, signal: TradingSignal, success: bool, error_msg: str = None):
        """シグナル送信記録（非同期）"""
        try:
            db_path = CONFIG.get('database', {}).get('path', './realtime_signals.db')
            async with aiosqlite.connect(db_path) as conn:
                await conn.execute('''
                    INSERT INTO signals (
                        timestamp, symbol, action, quantity, price, stop_loss, take_profit,
                        signal_quality, priority, strategy_params, transmission_status,
                        transmission_time, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal.timestamp.isoformat(),
                    signal.symbol,
                    signal.action,
                    signal.quantity,
                    signal.price,
                    signal.stop_loss,
                    signal.take_profit,
                    signal.signal_quality,
                    signal.priority,
                    json.dumps(signal.strategy_params),
                    'SUCCESS' if success else 'FAILED',
                    datetime.now().isoformat(),
                    error_msg
                ))
                await conn.commit()
        except aiosqlite.Error as e:
            logger.error(f"Signal recording SQL error: {e}")
        except (OSError, PermissionError) as e:
            logger.error(f"Signal recording access error: {e}")
        except Exception as e:
            logger.error(f"Unexpected signal recording error: {e}")
    
    async def _transmission_loop(self):
        """送信処理ループ"""
        while self.is_running:
            try:
                if not self.transmission_queue.empty():
                    signal = self.transmission_queue.get_nowait()
                    await self.send_signal(signal)
                
                await asyncio.sleep(0.01)  # 10ms
                
            except asyncio.CancelledError:
                logger.info("Transmission loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected transmission loop error: {e}")
                await asyncio.sleep(1)
    
    async def _rate_limit_monitor(self):
        """レート制限監視"""
        while self.is_running:
            await asyncio.sleep(60)  # 1分ごと
            self.sent_signals_count = 0
            logger.debug("Signal rate limit reset")
    
    def queue_signal(self, signal: TradingSignal):
        """シグナルをキューに追加"""
        self.transmission_queue.put(signal)

class RealtimeSignalSystem:
    """
    Phase2: リアルタイムシグナル生成システム統合
    kiro設計design.md準拠
    """
    
    def __init__(self):
        self.market_feed = MarketDataFeed()
        self.signal_generator = SignalGenerator(self.market_feed)
        self.transmission_system = SignalTransmissionSystem()
        self.is_running = False
        
        logger.info("Realtime Signal System initialized")
    
    async def start(self):
        """システム開始"""
        logger.info("Starting Realtime Signal System...")
        
        try:
            # 各コンポーネント開始
            await self.market_feed.start()
            await self.transmission_system.start()
            
            self.is_running = True
            
            # メインループ
            await self._main_loop()
            
        except (ConnectionError, OSError) as e:
            logger.error(f"System startup connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected system startup error: {e}")
            raise
    
    async def _main_loop(self):
        """メイン処理ループ"""
        logger.info("Main processing loop started")
        
        while self.is_running:
            try:
                # シグナル取得
                signal = await self.signal_generator.get_next_signal()
                
                if signal:
                    # 送信システムにキュー
                    self.transmission_system.queue_signal(signal)
                    logger.info(f"Signal queued for transmission: {signal.action} {signal.symbol}")
                
                await asyncio.sleep(0.01)  # 10ms
                
            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected main loop error: {e}")
                await asyncio.sleep(1)
    
    async def stop(self):
        """システム停止"""
        logger.info("Stopping Realtime Signal System...")
        self.is_running = False
        # 各コンポーネントの停止処理は必要に応じて追加

async def main():
    """メイン実行関数"""
    system = RealtimeSignalSystem()
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    except (ConnectionError, OSError) as e:
        logger.error(f"System connection error: {e}")
    except Exception as e:
        logger.error(f"Unexpected system error: {e}")
    finally:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())