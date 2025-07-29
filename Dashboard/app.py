#!/usr/bin/env python3
"""
Phase 1 Trading Dashboard - ファイル監視ベース軽量実装
リアルタイムポジション監視に特化したシンプルなアーキテクチャ
"""

import os
import json
import time
import logging
from datetime import datetime
from threading import Thread
from pathlib import Path

from flask import Flask, render_template
import socketio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionDataHandler(FileSystemEventHandler):
    """MT5ポジションデータファイル監視ハンドラー"""
    
    def __init__(self, socketio_instance):
        self.sio = socketio_instance
        self.last_data = None
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith('positions.json'):
            self.process_position_data(event.src_path)
    
    def process_position_data(self, file_path):
        """ポジションデータを読み込み、WebSocketで配信"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # データが変更された場合のみ配信
            if data != self.last_data:
                self.sio.emit('position_update', data)
                logger.info(f"📊 Position data updated: {len(data.get('positions', []))} positions")
                self.last_data = data
                
        except Exception as e:
            logger.error(f"❌ Failed to process position data: {e}")
            self.sio.emit('error', {'message': str(e)})

class Phase1Dashboard:
    """Phase 1 軽量ダッシュボード"""
    
    def __init__(self):
        # Flask アプリケーション
        self.app = Flask(__name__)
        
        # SocketIO設定（プロトコル互換性修正）
        self.sio = socketio.Server(
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
            async_mode='eventlet'
        )
        self.app.wsgi_app = socketio.WSGIApp(self.sio, self.app.wsgi_app)
        
        # ファイル監視設定
        self.data_path = Path("/tmp/mt5_data")
        self.data_path.mkdir(exist_ok=True)
        
        self.observer = Observer()
        self.handler = PositionDataHandler(self.sio)
        
        # ルーティング設定
        self.setup_routes()
        self.setup_socketio_events()
        
        logger.info("✅ Phase 1 Dashboard initialized")
    
    def setup_routes(self):
        """HTTPルート設定"""
        
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
    
    def setup_socketio_events(self):
        """WebSocketイベント設定"""
        
        @self.sio.event
        def connect(sid, environ):
            logger.info(f"🔗 Client connected: {sid}")
            # 接続時に最新データを送信
            self.send_latest_data(sid)
        
        @self.sio.event
        def disconnect(sid):
            logger.info(f"🔌 Client disconnected: {sid}")
        
        @self.sio.event
        def request_data(sid, data):
            """クライアントからのデータ要求"""
            self.send_latest_data(sid)
    
    def send_latest_data(self, sid):
        """最新のポジションデータを送信"""
        position_file = self.data_path / "positions.json"
        
        if position_file.exists():
            try:
                with open(position_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.sio.emit('position_update', data, room=sid)
            except Exception as e:
                logger.error(f"❌ Failed to send latest data: {e}")
                self.sio.emit('error', {'message': 'Failed to load position data'}, room=sid)
        else:
            # データファイルが存在しない場合のダミーデータ
            dummy_data = {
                "timestamp": datetime.now().isoformat(),
                "account": {"balance": 0, "equity": 0, "profit": 0},
                "positions": []
            }
            self.sio.emit('position_update', dummy_data, room=sid)
    
    def start_file_monitoring(self):
        """ファイル監視開始"""
        self.observer.schedule(self.handler, str(self.data_path), recursive=False)
        self.observer.start()
        logger.info(f"👁️ File monitoring started: {self.data_path}")
    
    def stop_file_monitoring(self):
        """ファイル監視停止"""
        self.observer.stop()
        self.observer.join()
        logger.info("👁️ File monitoring stopped")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """サーバー起動"""
        try:
            # ファイル監視開始
            self.start_file_monitoring()
            
            logger.info("=== Phase 1 Trading Dashboard ===")
            logger.info(f"URL: http://{host}:{port}")
            logger.info("機能: リアルタイムポジション監視")
            logger.info("アーキテクチャ: ファイル監視ベース")
            
            # Flask-SocketIO サーバー起動
            import eventlet
            eventlet.wsgi.server(eventlet.listen((host, port)), self.app)
            
        except KeyboardInterrupt:
            logger.info("🛑 Server stopped by user")
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
            raise
        finally:
            self.stop_file_monitoring()

# アプリケーション実行
if __name__ == '__main__':
    dashboard = Phase1Dashboard()
    dashboard.run(debug=False)