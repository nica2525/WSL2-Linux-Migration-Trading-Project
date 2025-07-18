#!/usr/bin/env python3
"""
ファイルベース通信ブリッジ - Python-MT4間のフォールバック通信
ファイルロック機構・クロスプラットフォーム互換性
"""

import os
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile
import hashlib
try:
    import portalocker
    PORTALOCKER_AVAILABLE = True
except ImportError:
    PORTALOCKER_AVAILABLE = False
    try:
        import fcntl
        FCNTL_AVAILABLE = True
    except ImportError:
        FCNTL_AVAILABLE = False
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("警告: watchdogモジュールが利用できません。ファイル監視機能が制限されます。")
    
    # 代替クラス定義
    class FileSystemEventHandler:
        def on_created(self, event):
            pass
            
    class Observer:
        def __init__(self):
            pass
        def schedule(self, handler, path, recursive=False):
            pass
        def start(self):
            pass
        def stop(self):
            pass
        def join(self):
            pass

from concurrent.futures import ThreadPoolExecutor
import queue
import uuid

# 共通インポート
try:
    from .tcp_bridge import TradingMessage, TradingSignal, MessageType
except ImportError:
    from tcp_bridge import TradingMessage, TradingSignal, MessageType

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FileMessage:
    """ファイルメッセージ"""
    message: TradingMessage
    timestamp: float
    sender: str
    status: str  # "pending", "processing", "processed", "failed"
    retry_count: int = 0

class FileBridgeHandler(FileSystemEventHandler):
    """ファイルシステムイベントハンドラー"""
    
    def __init__(self, bridge: 'FileBridge'):
        self.bridge = bridge
        
    def on_created(self, event):
        """ファイル作成イベント"""
        if event.is_directory:
            return
            
        if event.src_path.endswith('.msg'):
            logger.debug(f"新規メッセージファイル検出: {event.src_path}")
            self.bridge._process_message_file(event.src_path)

class FileBridge:
    """
    ファイルベース通信ブリッジ
    TCP通信のフォールバック機構として動作
    """
    
    def __init__(self,
                 message_dir: str = None,
                 sender_id: str = "python",
                 cleanup_interval: float = 300.0,  # 5分
                 max_retry_count: int = 3,
                 file_timeout: float = 30.0):
        """
        初期化
        
        Args:
            message_dir: メッセージディレクトリ
            sender_id: 送信者ID
            cleanup_interval: クリーンアップ間隔(秒)
            max_retry_count: 最大リトライ回数
            file_timeout: ファイルタイムアウト(秒)
        """
        # メッセージディレクトリ設定
        if message_dir is None:
            message_dir = os.path.join(tempfile.gettempdir(), "mt4_bridge_messages")
        
        self.message_dir = Path(message_dir)
        self.sender_id = sender_id
        self.cleanup_interval = cleanup_interval
        self.max_retry_count = max_retry_count
        self.file_timeout = file_timeout
        
        # ディレクトリ作成
        self.message_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir = self.message_dir / "inbox"
        self.outbox_dir = self.message_dir / "outbox"
        self.processed_dir = self.message_dir / "processed"
        self.failed_dir = self.message_dir / "failed"
        
        for dir_path in [self.inbox_dir, self.outbox_dir, self.processed_dir, self.failed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 監視システム
        self.observer = Observer()
        self.handler = FileBridgeHandler(self)
        if WATCHDOG_AVAILABLE:
            self.observer.schedule(self.handler, str(self.inbox_dir), recursive=False)
        else:
            logger.warning("ファイル監視機能が無効です。ポーリング方式を使用します。")
        
        # メッセージ処理
        self.message_queue = queue.Queue()
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.processing_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        
        # 実行制御
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 統計情報
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'files_cleaned': 0,
            'lock_failures': 0
        }
        
        # ファイルロック機能確認
        if PORTALOCKER_AVAILABLE:
            logger.info("クロスプラットフォームファイルロック（portalocker）使用")
        elif FCNTL_AVAILABLE:
            logger.info("Unix系ファイルロック（fcntl）使用")
        else:
            logger.warning("ファイルロック機能なし - 並行アクセスに注意")
        
        logger.info(f"ファイルブリッジ初期化: {self.message_dir}")
    
    def start(self):
        """監視・処理開始"""
        if self.running:
            logger.warning("ファイルブリッジは既に実行中")
            return
        
        self.running = True
        
        # ファイル監視開始
        if WATCHDOG_AVAILABLE:
            self.observer.start()
        else:
            logger.info("ポーリング方式でファイル監視開始")
        
        # メッセージ処理スレッド開始
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # クリーンアップスレッド開始
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_files)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        logger.info("ファイルブリッジ開始")
    
    def stop(self):
        """監視・処理停止"""
        if not self.running:
            return
        
        self.running = False
        
        # ファイル監視停止
        if WATCHDOG_AVAILABLE:
            self.observer.stop()
            self.observer.join()
        
        # スレッド終了待機
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
        
        # エグゼキューター終了
        self.executor.shutdown(wait=True)
        
        logger.info("ファイルブリッジ停止")
    
    def send_message(self, message: TradingMessage) -> bool:
        """
        メッセージ送信
        
        Args:
            message: 送信メッセージ
            
        Returns:
            bool: 送信成功可否
        """
        try:
            # ファイルメッセージ作成
            file_message = FileMessage(
                message=message,
                timestamp=time.time(),
                sender=self.sender_id,
                status="pending"
            )
            
            # ファイル名生成
            filename = f"{message.message_id}_{int(time.time() * 1000)}.msg"
            filepath = self.outbox_dir / filename
            
            # ファイル書き込み（ロック付き）
            return self._write_message_file(filepath, file_message)
            
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False
    
    def send_signal(self, signal: TradingSignal) -> bool:
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
        
        return self.send_message(message)
    
    def _write_message_file(self, filepath: Path, file_message: FileMessage) -> bool:
        """
        メッセージファイル書き込み
        
        Args:
            filepath: ファイルパス
            file_message: ファイルメッセージ
            
        Returns:
            bool: 書き込み成功可否
        """
        try:
            # 一時ファイルに書き込み
            temp_path = filepath.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                # クロスプラットフォームファイルロック
                if PORTALOCKER_AVAILABLE:
                    portalocker.lock(f, portalocker.LOCK_EX)
                elif FCNTL_AVAILABLE:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                # JSON書き込み
                message_data = {
                    'message': {
                        'message_type': file_message.message.message_type.value,
                        'timestamp': file_message.message.timestamp,
                        'data': file_message.message.data,
                        'message_id': file_message.message.message_id
                    },
                    'file_timestamp': file_message.timestamp,
                    'sender': file_message.sender,
                    'status': file_message.status,
                    'retry_count': file_message.retry_count,
                    'checksum': self._calculate_checksum(file_message.message)
                }
                json.dump(message_data, f, indent=2)
                
                # ファイルロック解除
                if PORTALOCKER_AVAILABLE:
                    portalocker.unlock(f)
                elif FCNTL_AVAILABLE:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # 一時ファイルを正式ファイルに移動
            temp_path.rename(filepath)
            
            self.stats['messages_sent'] += 1
            logger.debug(f"メッセージファイル書き込み成功: {filepath}")
            
            return True
            
        except Exception as e:
            logger.error(f"メッセージファイル書き込みエラー: {e}")
            self.stats['lock_failures'] += 1
            return False
    
    def _process_message_file(self, filepath: str):
        """
        メッセージファイル処理
        
        Args:
            filepath: ファイルパス
        """
        try:
            # キューに追加
            self.message_queue.put(filepath)
            
        except Exception as e:
            logger.error(f"メッセージファイル処理エラー: {e}")
    
    def _process_messages(self):
        """メッセージ処理ループ"""
        while self.running:
            try:
                # メッセージファイル取得
                filepath = self.message_queue.get(timeout=1.0)
                
                # ファイル処理
                self._handle_message_file(filepath)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"メッセージ処理ループエラー: {e}")
    
    def _handle_message_file(self, filepath: str):
        """
        メッセージファイル処理
        
        Args:
            filepath: ファイルパス
        """
        try:
            file_path = Path(filepath)
            
            # ファイル読み込み
            file_message = self._read_message_file(file_path)
            if not file_message:
                return
            
            # メッセージ処理
            message = file_message.message
            
            # カスタムハンドラー実行
            if message.message_type in self.message_handlers:
                handler = self.message_handlers[message.message_type]
                handler(message)
            
            # 処理済みファイルに移動
            processed_path = self.processed_dir / file_path.name
            file_path.rename(processed_path)
            
            self.stats['messages_processed'] += 1
            logger.debug(f"メッセージ処理完了: {filepath}")
            
        except Exception as e:
            logger.error(f"メッセージファイル処理エラー: {e}")
            self._move_to_failed(filepath)
    
    def _read_message_file(self, filepath: Path) -> Optional[FileMessage]:
        """
        メッセージファイル読み込み
        
        Args:
            filepath: ファイルパス
            
        Returns:
            FileMessage: ファイルメッセージ（読み込み失敗時None）
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # クロスプラットフォームファイルロック（共有）
                if PORTALOCKER_AVAILABLE:
                    portalocker.lock(f, portalocker.LOCK_SH)
                elif FCNTL_AVAILABLE:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                
                # JSON読み込み
                data = json.load(f)
                
                # ファイルロック解除
                if PORTALOCKER_AVAILABLE:
                    portalocker.unlock(f)
                elif FCNTL_AVAILABLE:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # メッセージ復元
            message_data = data['message']
            message = TradingMessage(
                message_type=MessageType(message_data['message_type']),
                timestamp=message_data['timestamp'],
                data=message_data['data'],
                message_id=message_data['message_id']
            )
            
            # チェックサム検証
            expected_checksum = data.get('checksum')
            actual_checksum = self._calculate_checksum(message)
            
            if expected_checksum != actual_checksum:
                logger.warning(f"チェックサム不一致: {filepath}")
                return None
            
            # ファイルメッセージ作成
            file_message = FileMessage(
                message=message,
                timestamp=data['file_timestamp'],
                sender=data['sender'],
                status=data['status'],
                retry_count=data.get('retry_count', 0)
            )
            
            self.stats['messages_received'] += 1
            return file_message
            
        except Exception as e:
            logger.error(f"メッセージファイル読み込みエラー: {e}")
            return None
    
    def _calculate_checksum(self, message: TradingMessage) -> str:
        """
        メッセージチェックサム計算
        
        Args:
            message: メッセージ
            
        Returns:
            str: チェックサム
        """
        content = f"{message.message_type.value}{message.timestamp}{message.message_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _move_to_failed(self, filepath: str):
        """
        失敗ファイルディレクトリに移動
        
        Args:
            filepath: ファイルパス
        """
        try:
            file_path = Path(filepath)
            failed_path = self.failed_dir / file_path.name
            
            file_path.rename(failed_path)
            self.stats['messages_failed'] += 1
            
        except Exception as e:
            logger.error(f"失敗ファイル移動エラー: {e}")
    
    def _cleanup_old_files(self):
        """古いファイルクリーンアップ"""
        while self.running:
            try:
                current_time = time.time()
                
                # 各ディレクトリのクリーンアップ
                for directory in [self.processed_dir, self.failed_dir]:
                    for file_path in directory.glob('*.msg'):
                        try:
                            # ファイル作成時刻確認
                            file_time = file_path.stat().st_mtime
                            
                            if current_time - file_time > self.file_timeout:
                                file_path.unlink()
                                self.stats['files_cleaned'] += 1
                                logger.debug(f"古いファイル削除: {file_path}")
                                
                        except Exception as e:
                            logger.warning(f"ファイル削除エラー: {e}")
                
                # クリーンアップ間隔待機
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"クリーンアップエラー: {e}")
                time.sleep(self.cleanup_interval)
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """
        メッセージハンドラー登録
        
        Args:
            message_type: メッセージタイプ
            handler: ハンドラー関数
        """
        self.message_handlers[message_type] = handler
        logger.info(f"ファイルブリッジハンドラー登録: {message_type.value}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        ステータス取得
        
        Returns:
            Dict[str, Any]: ステータス情報
        """
        return {
            'running': self.running,
            'message_dir': str(self.message_dir),
            'sender_id': self.sender_id,
            'stats': self.stats.copy(),
            'queue_size': self.message_queue.qsize(),
            'directories': {
                'inbox': len(list(self.inbox_dir.glob('*.msg'))),
                'outbox': len(list(self.outbox_dir.glob('*.msg'))),
                'processed': len(list(self.processed_dir.glob('*.msg'))),
                'failed': len(list(self.failed_dir.glob('*.msg')))
            }
        }
    
    def __del__(self):
        """デストラクター"""
        self.stop()

def main():
    """テスト実行"""
    bridge = FileBridge()
    
    try:
        # 開始
        bridge.start()
        
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
            signal_id=str(uuid.uuid4())
        )
        
        print("テストシグナル送信...")
        if bridge.send_signal(test_signal):
            print("✅ シグナル送信成功")
        else:
            print("❌ シグナル送信失敗")
        
        # ステータス表示
        time.sleep(1)
        status = bridge.get_status()
        print(f"ステータス: {status}")
        
        # 少し待機
        time.sleep(5)
        
    finally:
        bridge.stop()

if __name__ == "__main__":
    main()