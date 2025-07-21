#!/usr/bin/env python3
"""
統一通信ライブラリ - リファクタリング後
TCP・ファイル・Named Pipe通信の統一インターフェース

重複排除対象:
- 各モジュールでの通信ブリッジ個別初期化
- 設定の分散管理
- エラーハンドリングの重複
"""

import asyncio
import logging
import json
import socket
from pathlib import Path
from typing import Dict, Any, Optional, Union, Protocol
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod

from common_config import GLOBAL_CONFIG, setup_unified_logging

logger = setup_unified_logging(GLOBAL_CONFIG, 'unified_communication')

@dataclass
class CommunicationMessage:
    """統一通信メッセージ"""
    message_id: str
    message_type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    priority: int = 0

class CommunicationProtocol(Protocol):
    """通信プロトコルインターフェース"""
    
    async def connect(self) -> bool:
        """接続"""
        ...
    
    async def disconnect(self) -> bool:
        """切断"""
        ...
    
    async def send_message(self, message: CommunicationMessage) -> bool:
        """メッセージ送信"""
        ...
    
    async def receive_message(self) -> Optional[CommunicationMessage]:
        """メッセージ受信"""
        ...
    
    def is_connected(self) -> bool:
        """接続状態確認"""
        ...

class TCPCommunicationChannel:
    """TCP通信チャネル - 統一実装"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or GLOBAL_CONFIG.communication.tcp_host
        self.port = port or GLOBAL_CONFIG.communication.tcp_port
        self.reader = None
        self.writer = None
        self.connected = False
        
    async def connect(self) -> bool:
        """TCP接続確立"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True
            logger.info(f"TCP接続成功: {self.host}:{self.port}")
            return True
            
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"TCP接続失敗: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"TCP接続予期しないエラー: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """TCP接続切断"""
        try:
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
            self.connected = False
            logger.info("TCP接続切断完了")
            return True
            
        except Exception as e:
            logger.error(f"TCP切断エラー: {e}")
            return False
    
    async def send_message(self, message: CommunicationMessage) -> bool:
        """TCPメッセージ送信"""
        if not self.connected or not self.writer:
            return False
            
        try:
            data = {
                'message_id': message.message_id,
                'message_type': message.message_type,
                'data': message.data,
                'timestamp': message.timestamp.isoformat(),
                'source': message.source,
                'priority': message.priority
            }
            
            json_data = json.dumps(data) + '\n'
            self.writer.write(json_data.encode('utf-8'))
            await self.writer.drain()
            
            logger.debug(f"TCP送信成功: {message.message_id}")
            return True
            
        except (ConnectionError, OSError) as e:
            logger.error(f"TCP送信接続エラー: {e}")
            self.connected = False
            return False
        except (json.JSONEncodeError, UnicodeEncodeError) as e:
            logger.error(f"TCP送信データエラー: {e}")
            return False
        except Exception as e:
            logger.error(f"TCP送信予期しないエラー: {e}")
            return False
    
    async def receive_message(self) -> Optional[CommunicationMessage]:
        """TCPメッセージ受信"""
        if not self.connected or not self.reader:
            return None
            
        try:
            data = await self.reader.readline()
            if not data:
                logger.warning("TCP接続が閉じられました")
                self.connected = False
                return None
                
            json_data = json.loads(data.decode('utf-8').strip())
            
            return CommunicationMessage(
                message_id=json_data['message_id'],
                message_type=json_data['message_type'],
                data=json_data['data'],
                timestamp=datetime.fromisoformat(json_data['timestamp']),
                source=json_data['source'],
                priority=json_data.get('priority', 0)
            )
            
        except (ConnectionError, OSError) as e:
            logger.error(f"TCP受信接続エラー: {e}")
            self.connected = False
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"TCP受信データエラー: {e}")
            return None
        except Exception as e:
            logger.error(f"TCP受信予期しないエラー: {e}")
            return None
    
    def is_connected(self) -> bool:
        """TCP接続状態"""
        return self.connected

class FileCommunicationChannel:
    """ファイル通信チャネル - 統一実装"""
    
    def __init__(self, bridge_dir: str = None):
        self.bridge_dir = Path(bridge_dir or GLOBAL_CONFIG.communication.file_bridge_dir)
        self.connected = False
        
    async def connect(self) -> bool:
        """ファイルブリッジ接続"""
        try:
            self.bridge_dir.mkdir(parents=True, exist_ok=True)
            
            # 接続テスト用ファイル作成
            test_file = self.bridge_dir / "connection_test.tmp"
            test_file.write_text("test", encoding='utf-8')
            test_file.unlink()
            
            self.connected = True
            logger.info(f"ファイルブリッジ接続成功: {self.bridge_dir}")
            return True
            
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"ファイルブリッジ接続失敗: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"ファイルブリッジ予期しないエラー: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """ファイルブリッジ切断"""
        self.connected = False
        logger.info("ファイルブリッジ切断完了")
        return True
    
    async def send_message(self, message: CommunicationMessage) -> bool:
        """ファイルメッセージ送信"""
        if not self.connected:
            return False
            
        try:
            data = {
                'message_id': message.message_id,
                'message_type': message.message_type,
                'data': message.data,
                'timestamp': message.timestamp.isoformat(),
                'source': message.source,
                'priority': message.priority
            }
            
            # 一意ファイル名生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{message.message_type}_{message.message_id}_{timestamp}.json"
            file_path = self.bridge_dir / filename
            
            # アトミック書き込み
            temp_path = file_path.with_suffix('.tmp')
            temp_path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            temp_path.rename(file_path)
            
            logger.debug(f"ファイル送信成功: {filename}")
            return True
            
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"ファイル送信権限エラー: {e}")
            return False
        except (json.JSONEncodeError, UnicodeEncodeError) as e:
            logger.error(f"ファイル送信データエラー: {e}")
            return False
        except Exception as e:
            logger.error(f"ファイル送信予期しないエラー: {e}")
            return False
    
    async def receive_message(self) -> Optional[CommunicationMessage]:
        """ファイルメッセージ受信"""
        if not self.connected:
            return None
            
        try:
            # 最新ファイル取得
            json_files = list(self.bridge_dir.glob("*.json"))
            if not json_files:
                return None
                
            # 作成時間でソート
            latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
            
            # ファイル読み込み
            json_data = json.loads(latest_file.read_text(encoding='utf-8'))
            
            # 処理済みマーク
            processed_file = latest_file.with_suffix('.processed')
            latest_file.rename(processed_file)
            
            return CommunicationMessage(
                message_id=json_data['message_id'],
                message_type=json_data['message_type'],
                data=json_data['data'],
                timestamp=datetime.fromisoformat(json_data['timestamp']),
                source=json_data['source'],
                priority=json_data.get('priority', 0)
            )
            
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"ファイル受信権限エラー: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"ファイル受信データエラー: {e}")
            return None
        except Exception as e:
            logger.error(f"ファイル受信予期しないエラー: {e}")
            return None
    
    def is_connected(self) -> bool:
        """ファイルブリッジ接続状態"""
        return self.connected

class UnifiedCommunicationManager:
    """統一通信マネージャー - 重複排除の中核"""
    
    def __init__(self, prefer_tcp: bool = True):
        self.prefer_tcp = prefer_tcp
        self.tcp_channel = TCPCommunicationChannel()
        self.file_channel = FileCommunicationChannel()
        self.active_channel = None
        
    async def initialize(self) -> bool:
        """通信チャネル初期化"""
        try:
            if self.prefer_tcp:
                # TCP優先で接続試行
                tcp_success = await self.tcp_channel.connect()
                if tcp_success:
                    self.active_channel = self.tcp_channel
                    logger.info("TCP通信チャネル使用")
                    return True
                    
                # TCP失敗時はファイルにフォールバック
                logger.warning("TCP接続失敗、ファイル通信にフォールバック")
                file_success = await self.file_channel.connect()
                if file_success:
                    self.active_channel = self.file_channel
                    logger.info("ファイル通信チャネル使用")
                    return True
            else:
                # ファイル優先
                file_success = await self.file_channel.connect()
                if file_success:
                    self.active_channel = self.file_channel
                    logger.info("ファイル通信チャネル使用")
                    return True
                    
                # ファイル失敗時はTCPにフォールバック
                tcp_success = await self.tcp_channel.connect()
                if tcp_success:
                    self.active_channel = self.tcp_channel
                    logger.info("TCP通信チャネル使用")
                    return True
            
            logger.error("全通信チャネル接続失敗")
            return False
            
        except Exception as e:
            logger.error(f"通信初期化エラー: {e}")
            return False
    
    async def send_message(self, message_type: str, data: Dict[str, Any], 
                          source: str = "system", priority: int = 0) -> bool:
        """統一メッセージ送信"""
        if not self.active_channel:
            logger.error("アクティブな通信チャネルがありません")
            return False
            
        message = CommunicationMessage(
            message_id=f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            message_type=message_type,
            data=data,
            timestamp=datetime.now(),
            source=source,
            priority=priority
        )
        
        return await self.active_channel.send_message(message)
    
    async def receive_message(self) -> Optional[CommunicationMessage]:
        """統一メッセージ受信"""
        if not self.active_channel:
            return None
            
        return await self.active_channel.receive_message()
    
    async def stop(self) -> bool:
        """通信停止"""
        success = True
        
        if self.tcp_channel:
            success &= await self.tcp_channel.disconnect()
            
        if self.file_channel:
            success &= await self.file_channel.disconnect()
            
        self.active_channel = None
        logger.info("統一通信マネージャー停止完了")
        return success
    
    def get_active_channel_type(self) -> str:
        """アクティブチャネル種別"""
        if self.active_channel == self.tcp_channel:
            return "TCP"
        elif self.active_channel == self.file_channel:
            return "FILE"
        else:
            return "NONE"
    
    def is_connected(self) -> bool:
        """通信接続状態"""
        return self.active_channel is not None and self.active_channel.is_connected()

# シングルトンインスタンス（オプション）
_global_comm_manager = None

async def get_global_communication_manager() -> UnifiedCommunicationManager:
    """グローバル通信マネージャー取得"""
    global _global_comm_manager
    
    if _global_comm_manager is None:
        _global_comm_manager = UnifiedCommunicationManager()
        await _global_comm_manager.initialize()
    
    return _global_comm_manager

async def cleanup_global_communication():
    """グローバル通信クリーンアップ"""
    global _global_comm_manager
    
    if _global_comm_manager:
        await _global_comm_manager.stop()
        _global_comm_manager = None

if __name__ == "__main__":
    # 統一通信テスト
    async def test_unified_communication():
        print("統一通信システムテスト開始")
        
        manager = UnifiedCommunicationManager()
        success = await manager.initialize()
        
        if success:
            print(f"アクティブチャネル: {manager.get_active_channel_type()}")
            
            # テストメッセージ送信
            test_data = {"symbol": "EURUSD", "price": 1.0850}
            send_success = await manager.send_message(
                "TEST_SIGNAL", test_data, "test_system"
            )
            
            if send_success:
                print("テストメッセージ送信成功")
            else:
                print("テストメッセージ送信失敗")
        else:
            print("通信初期化失敗")
        
        await manager.stop()
        print("統一通信テスト完了")
    
    asyncio.run(test_unified_communication())