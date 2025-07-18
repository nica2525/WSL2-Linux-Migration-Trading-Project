#!/usr/bin/env python3
"""
TCP通信ブリッジ - Python-MT4間通信の主要プロトコル
非同期ソケット処理・自動再接続・ハートビート機構
"""

import asyncio
import socket
import json
import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """メッセージタイプ定義"""
    HEARTBEAT = "heartbeat"
    SIGNAL = "signal"
    CONFIRMATION = "confirmation"
    PARAMETER_UPDATE = "parameter_update"
    STATUS_REQUEST = "status_request"
    ERROR = "error"

@dataclass
class TradingSignal:
    """取引シグナル"""
    timestamp: float
    symbol: str
    action: str  # "BUY", "SELL", "CLOSE"
    price: float
    volume: float
    slippage: float
    confidence: float
    lookback_period: int
    signal_id: str

@dataclass
class TradingMessage:
    """通信メッセージ"""
    message_type: MessageType
    timestamp: float
    data: Dict[str, Any]
    message_id: str
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps({
            'message_type': self.message_type.value,
            'timestamp': self.timestamp,
            'data': self.data,
            'message_id': self.message_id
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TradingMessage':
        """JSON形式から復元"""
        data = json.loads(json_str)
        return cls(
            message_type=MessageType(data['message_type']),
            timestamp=data['timestamp'],
            data=data['data'],
            message_id=data['message_id']
        )

class ConnectionState(Enum):
    """接続状態"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

class TCPBridge:
    """
    TCP通信ブリッジ
    Python-MT4間の高速・安定通信を実現
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 8888,
                 reconnect_delay: float = 1.0,
                 max_reconnect_attempts: int = 3,
                 heartbeat_interval: float = 5.0,
                 timeout: float = 10.0):
        """
        初期化
        
        Args:
            host: 接続先ホスト
            port: 接続先ポート
            reconnect_delay: 再接続間隔(秒)
            max_reconnect_attempts: 最大再接続試行回数
            heartbeat_interval: ハートビート間隔(秒)
            timeout: タイムアウト(秒)
        """
        self.host = host
        self.port = port
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval
        self.timeout = timeout
        
        # 接続状態
        self.connection_state = ConnectionState.DISCONNECTED
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        
        # ハートビート監視
        self.last_heartbeat_received = time.time()
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # メッセージ処理
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.pending_confirmations: Dict[str, asyncio.Event] = {}
        
        # 統計情報
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'connection_attempts': 0,
            'successful_connections': 0,
            'connection_errors': 0,
            'last_error': None
        }
        
        # 非同期実行用
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"TCP Bridge初期化: {self.host}:{self.port}")
    
    async def connect(self) -> bool:
        """
        TCP接続確立
        
        Returns:
            bool: 接続成功可否
        """
        self.connection_state = ConnectionState.CONNECTING
        self.stats['connection_attempts'] += 1
        
        try:
            logger.info(f"TCP接続試行: {self.host}:{self.port}")
            
            # 接続確立
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            
            self.connection_state = ConnectionState.CONNECTED
            self.stats['successful_connections'] += 1
            self.last_heartbeat_received = time.time()
            
            logger.info(f"TCP接続成功: {self.host}:{self.port}")
            
            # ハートビート開始
            self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            
            return True
            
        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            self.stats['connection_errors'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"TCP接続失敗: {e}")
            return False
    
    async def disconnect(self):
        """TCP接続切断"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        
        self.connection_state = ConnectionState.DISCONNECTED
        self.reader = None
        self.writer = None
        
        logger.info("TCP接続切断完了")
    
    async def send_message(self, message: TradingMessage) -> bool:
        """
        メッセージ送信
        
        Args:
            message: 送信メッセージ
            
        Returns:
            bool: 送信成功可否
        """
        if self.connection_state != ConnectionState.CONNECTED:
            logger.warning("TCP未接続: メッセージ送信失敗")
            return False
        
        try:
            # メッセージシリアライゼーション
            message_data = message.to_json() + "\n"
            
            # 送信
            self.writer.write(message_data.encode('utf-8'))
            await self.writer.drain()
            
            self.stats['messages_sent'] += 1
            logger.debug(f"メッセージ送信: {message.message_type.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False
    
    async def send_signal(self, signal: TradingSignal) -> bool:
        """
        取引シグナル送信
        
        Args:
            signal: 取引シグナル
            
        Returns:
            bool: 送信成功可否
        """
        message = TradingMessage(
            message_type=MessageType.SIGNAL,
            timestamp=time.time(),
            data=asdict(signal),
            message_id=signal.signal_id
        )
        
        return await self.send_message(message)
    
    async def wait_for_confirmation(self, message_id: str, timeout: float = 5.0) -> bool:
        """
        確認応答待機
        
        Args:
            message_id: メッセージID
            timeout: タイムアウト(秒)
            
        Returns:
            bool: 確認応答受信可否
        """
        if message_id not in self.pending_confirmations:
            self.pending_confirmations[message_id] = asyncio.Event()
        
        try:
            await asyncio.wait_for(
                self.pending_confirmations[message_id].wait(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"確認応答タイムアウト: {message_id}")
            return False
        finally:
            self.pending_confirmations.pop(message_id, None)
    
    async def start_listening(self):
        """メッセージ受信開始"""
        if self.connection_state != ConnectionState.CONNECTED:
            logger.warning("TCP未接続: リスニング開始失敗")
            return
        
        logger.info("TCP受信開始")
        
        try:
            while self.connection_state == ConnectionState.CONNECTED:
                # メッセージ受信
                data = await self.reader.readline()
                if not data:
                    break
                
                try:
                    # メッセージデシリアライゼーション
                    message_str = data.decode('utf-8').strip()
                    message = TradingMessage.from_json(message_str)
                    
                    self.stats['messages_received'] += 1
                    logger.debug(f"メッセージ受信: {message.message_type.value}")
                    
                    # メッセージ処理
                    await self._handle_message(message)
                    
                except Exception as e:
                    logger.error(f"メッセージ処理エラー: {e}")
                    
        except Exception as e:
            logger.error(f"TCP受信エラー: {e}")
            self.connection_state = ConnectionState.ERROR
    
    async def _handle_message(self, message: TradingMessage):
        """メッセージ処理"""
        # ハートビート更新
        if message.message_type == MessageType.HEARTBEAT:
            self.last_heartbeat_received = time.time()
            return
        
        # 確認応答処理
        if message.message_type == MessageType.CONFIRMATION:
            message_id = message.data.get('message_id')
            if message_id in self.pending_confirmations:
                self.pending_confirmations[message_id].set()
            return
        
        # カスタムハンドラー実行
        if message.message_type in self.message_handlers:
            handler = self.message_handlers[message.message_type]
            await handler(message)
    
    async def _heartbeat_monitor(self):
        """ハートビート監視"""
        while self.connection_state == ConnectionState.CONNECTED:
            try:
                # ハートビート送信
                heartbeat_message = TradingMessage(
                    message_type=MessageType.HEARTBEAT,
                    timestamp=time.time(),
                    data={'status': 'alive'},
                    message_id=f"heartbeat_{int(time.time())}"
                )
                
                await self.send_message(heartbeat_message)
                
                # ハートビート受信確認
                if time.time() - self.last_heartbeat_received > self.heartbeat_interval * 2:
                    logger.warning("ハートビート受信タイムアウト")
                    self.connection_state = ConnectionState.ERROR
                    break
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"ハートビート監視エラー: {e}")
                break
    
    async def auto_reconnect(self) -> bool:
        """
        自動再接続
        
        Returns:
            bool: 再接続成功可否
        """
        if self.connection_state == ConnectionState.RECONNECTING:
            return False
        
        self.connection_state = ConnectionState.RECONNECTING
        
        for attempt in range(self.max_reconnect_attempts):
            logger.info(f"自動再接続試行: {attempt + 1}/{self.max_reconnect_attempts}")
            
            await asyncio.sleep(self.reconnect_delay)
            
            if await self.connect():
                logger.info("自動再接続成功")
                return True
        
        logger.error("自動再接続失敗")
        self.connection_state = ConnectionState.ERROR
        return False
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """メッセージハンドラー登録"""
        self.message_handlers[message_type] = handler
        logger.info(f"メッセージハンドラー登録: {message_type.value}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """接続状態取得"""
        return {
            'state': self.connection_state.value,
            'host': self.host,
            'port': self.port,
            'last_heartbeat': self.last_heartbeat_received,
            'stats': self.stats.copy()
        }
    
    def __del__(self):
        """デストラクター"""
        if self.executor:
            self.executor.shutdown(wait=False)

async def main():
    """テスト実行"""
    bridge = TCPBridge()
    
    # 接続テスト
    if await bridge.connect():
        print("接続成功")
        
        # テストシグナル送信
        test_signal = TradingSignal(
            timestamp=time.time(),
            symbol="USDJPY",
            action="BUY",
            price=150.00,
            volume=0.1,
            slippage=0.0001,
            confidence=0.85,
            lookback_period=20,
            signal_id="test_001"
        )
        
        if await bridge.send_signal(test_signal):
            print("シグナル送信成功")
        
        # 状態確認
        status = bridge.get_connection_status()
        print(f"接続状態: {status}")
        
        await bridge.disconnect()
    else:
        print("接続失敗")

if __name__ == "__main__":
    asyncio.run(main())