#!/usr/bin/env python3
"""
JamesORB監視ダッシュボード - kiro設計v1.0準拠
標準MT5 API + ハイブリッド通信 + Tailscale VPN + Basic認証
"""

import os
import sys
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

# プロジェクト共通ライブラリ
sys.path.append(str(Path(__file__).parent.parent))
from lib.config_manager import ConfigManager
from lib.logger_setup import get_logger
from lib.error_handler import ErrorHandler

# Web フレームワーク・セキュリティ
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_httpauth import HTTPBasicAuth
import MetaTrader5 as mt5

class SecurityConfig:
    """セキュリティ設定 - kiro設計準拠"""
    BASIC_AUTH_USERNAME = os.getenv('DASHBOARD_USER', 'trader')
    BASIC_AUTH_PASSWORD = os.getenv('DASHBOARD_PASS', 'jamesorb2025')
    SESSION_TIMEOUT = 3600  # 1時間
    
    @staticmethod
    def mask_account_number(account_num):
        """口座番号マスキング"""
        return f"****{str(account_num)[-4:]}"
    
    @staticmethod
    def sanitize_log_data(data):
        """ログデータのサニタイズ"""
        sensitive_keys = ['password', 'account', 'balance']
        return {k: '***' if k in sensitive_keys else v for k, v in data.items()}

class MT5ConnectionManager:
    """MT5接続管理 - 自動再接続機構付き"""
    def __init__(self, logger):
        self.logger = logger
        self.connected = False
        self.retry_count = 0
        self.max_retries = 3
        self.last_attempt = None
    
    def connect_with_retry(self):
        """自動再接続機構"""
        for attempt in range(self.max_retries):
            try:
                if mt5.initialize():
                    self.connected = True
                    self.retry_count = 0
                    self.logger.info(f"MT5接続成功 (試行{attempt + 1}回目)")
                    return True
                time.sleep(5)  # 5秒待機後リトライ
            except Exception as e:
                self.logger.warning(f"MT5接続試行{attempt + 1}失敗: {e}")
        
        self.connected = False
        self.logger.error(f"MT5接続失敗（{self.max_retries}回試行）")
        return False
    
    def get_account_info(self):
        """口座情報取得（エラーハンドリング付き）"""
        if not self.connected:
            self.connect_with_retry()
        
        try:
            account = mt5.account_info()
            return account._asdict() if account else None
        except Exception as e:
            self.logger.error(f"口座情報取得エラー: {e}")
            return None
    
    def get_positions(self):
        """ポジション取得（エラーハンドリング付き）"""
        if not self.connected:
            self.connect_with_retry()
        
        try:
            positions = mt5.positions_get()
            return list(positions) if positions else []
        except Exception as e:
            self.logger.error(f"ポジション取得エラー: {e}")
            return []

class TradingDashboard:
    def __init__(self):
        """ダッシュボード初期化 - kiro設計v1.0準拠"""
        self.config = ConfigManager()
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler()
        
        # MT5接続管理
        self.mt5_manager = MT5ConnectionManager(self.logger)
        
        # Flask + SocketIO設定
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.urandom(24)  # セキュア秘密鍵
        self.app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Basic認証設定
        self.auth = HTTPBasicAuth()
        
        # SQLiteデータベース初期化
        self.init_database()
        
        # バックグラウンドタスク
        self.last_data_update = None
        self.background_thread = None
        
        # ルート・ハンドラー設定
        self.setup_auth()
        self.setup_routes()
        self.setup_websocket_handlers()
        
        self.logger.info("=== JamesORB監視ダッシュボード v1.0 初期化完了 ===")
    
    def init_database(self):
        """SQLiteデータベース初期化 - kiro設計準拠"""
        db_path = Path(__file__).parent / 'dashboard.db'
        
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 口座情報履歴
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    balance REAL NOT NULL,
                    equity REAL NOT NULL,
                    margin REAL NOT NULL,
                    free_margin REAL NOT NULL,
                    margin_level REAL,
                    profit REAL NOT NULL
                )
            ''')
            
            # ポジション履歴
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS position_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ticket INTEGER NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    type INTEGER NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    current_price REAL,
                    profit REAL NOT NULL,
                    swap REAL DEFAULT 0,
                    comment TEXT
                )
            ''')
            
            # EA稼働状況
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ea_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) NOT NULL,
                    message TEXT,
                    positions_count INTEGER DEFAULT 0,
                    daily_profit REAL DEFAULT 0
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_timestamp ON account_history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_position_timestamp ON position_history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ea_timestamp ON ea_status(timestamp)')
            
            conn.commit()
        
        self.logger.info("SQLiteデータベース初期化完了")
    
    def setup_auth(self):
        """Basic認証設定 - kiro設計準拠"""
        @self.auth.verify_password
        def verify_password(username, password):
            return (username == SecurityConfig.BASIC_AUTH_USERNAME and 
                   password == SecurityConfig.BASIC_AUTH_PASSWORD)
    
    def setup_routes(self):
        """HTTP ルート設定"""
        
        @self.app.route('/')
        @self.auth.login_required
        def dashboard():
            """メインダッシュボード - Basic認証付き"""
            return render_template('dashboard.html')
        
        @self.app.route('/mobile')
        @self.auth.login_required
        def mobile_dashboard():
            """モバイル専用ダッシュボード - Basic認証付き"""
            return render_template('mobile_dashboard.html')
        
        @self.app.route('/manifest.json')
        def manifest():
            """PWAマニフェスト"""
            return jsonify({
                "name": "JamesORB Trading Dashboard",
                "short_name": "JamesORB",
                "description": "リアルタイム取引監視ダッシュボード",
                "start_url": "/mobile",
                "display": "standalone",
                "background_color": "#ffffff",
                "theme_color": "#2196F3",
                "icons": [{
                    "src": "/static/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                }]
            })
        
        @self.app.route('/service-worker.js')
        def service_worker():
            """Service Worker"""
            return send_from_directory('static/js', 'service-worker.js')
        
        @self.app.route('/api/status')
        @self.auth.login_required
        def api_status():
            """システム状態API - 認証付き"""
            try:
                status = self.get_system_status()
                # セキュリティ情報のサニタイズ
                sanitized = SecurityConfig.sanitize_log_data(status)
                return jsonify(sanitized)
            except Exception as e:
                self.logger.error(f"API status error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/positions')
        @self.auth.login_required
        def api_positions():
            """ポジション一覧API - 認証付き"""
            try:
                positions = self.get_positions()
                return jsonify(positions)
            except Exception as e:
                self.logger.error(f"API positions error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/account')
        @self.auth.login_required
        def api_account():
            """アカウント情報API - 認証付き"""
            try:
                account = self.get_account_info()
                # 口座番号マスキング
                if 'login' in account:
                    account['login'] = SecurityConfig.mask_account_number(account['login'])
                return jsonify(account)
            except Exception as e:
                self.logger.error(f"API account error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/history/<period>')
        @self.auth.login_required
        def api_history(period):
            """履歴データAPI - REST方式"""
            try:
                history = self.get_history_data(period)
                return jsonify(history)
            except Exception as e:
                self.logger.error(f"API history error: {e}")
                return jsonify({"error": str(e)}), 500
    
    def setup_websocket_handlers(self):
        """WebSocket ハンドラー設定"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """クライアント接続"""
            self.logger.info(f"クライアント接続: {request.sid}")
            emit('connected', {'status': 'success'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """クライアント切断"""
            self.logger.info(f"クライアント切断: {request.sid}")
        
        @self.socketio.on('request_data')
        def handle_data_request():
            """リアルタイムデータ要求"""
            try:
                data = self.get_realtime_data()
                emit('market_data', data)
            except Exception as e:
                self.logger.error(f"Data request error: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('request_refresh')
        def handle_refresh_request():
            """強制データ更新"""
            try:
                self.connect_mt5()
                data = self.get_realtime_data()
                emit('market_data', data)
                emit('notification', {'type': 'success', 'message': 'データ更新完了'})
            except Exception as e:
                self.logger.error(f"Refresh error: {e}")
                emit('error', {'message': str(e)})
    
    def connect_mt5(self):
        """MT5接続確立"""
        try:
            if not mt5.initialize():
                error_info = mt5.last_error()
                self.logger.warning(f"MT5初期化失敗: {error_info}")
                self.mt5_connected = False
                return False
            
            self.mt5_connected = True
            self.logger.info("MT5接続成功")
            return True
            
        except Exception as e:
            self.logger.error(f"MT5接続エラー: {e}")
            self.mt5_connected = False
            return False
    
    def get_system_status(self):
        """システム状態取得"""
        try:
            # MT5接続チェック
            if not self.mt5_connected:
                self.connect_mt5()
            
            # システム状態情報
            status = {
                'timestamp': datetime.now().isoformat(),
                'mt5_connected': self.mt5_connected,
                'last_update': self.last_data_update.isoformat() if self.last_data_update else None,
                'ea_status': self.get_ea_status(),
                'system_health': 'OK' if self.mt5_connected else 'WARNING'
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"System status error: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'mt5_connected': False,
                'error': str(e),
                'system_health': 'ERROR'
            }
    
    def get_ea_status(self):
        """EA稼働状態取得"""
        try:
            if not self.mt5_connected:
                return {'status': 'DISCONNECTED', 'name': 'Unknown'}
            
            # EA設定から情報取得
            ea_config = self.config.get_ea_config()
            
            # 実際のEA稼働チェック（簡易版）
            positions = mt5.positions_get()
            active_positions = len(positions) if positions else 0
            
            return {
                'name': ea_config.get('name', 'JamesORB_v1.0'),
                'status': 'RUNNING' if self.mt5_connected else 'STOPPED',
                'symbol': ea_config.get('symbol', 'EURUSD'),
                'timeframe': ea_config.get('timeframe', 'M5'),
                'active_positions': active_positions
            }
            
        except Exception as e:
            self.logger.error(f"EA status error: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def get_positions(self):
        """ポジション一覧取得"""
        try:
            if not self.mt5_connected:
                return []
            
            positions = mt5.positions_get()
            if not positions:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'open_time': datetime.fromtimestamp(pos.time).isoformat(),
                    'comment': pos.comment
                })
            
            return position_list
            
        except Exception as e:
            self.logger.error(f"Positions error: {e}")
            return []
    
    def get_account_info(self):
        """アカウント情報取得"""
        try:
            if not self.mt5_connected:
                return {}
            
            account = mt5.account_info()
            if not account:
                return {}
            
            return {
                'login': account.login,
                'balance': account.balance,
                'equity': account.equity,
                'margin': account.margin,
                'margin_free': account.margin_free,
                'margin_level': account.margin_level,
                'profit': account.profit,
                'currency': account.currency,
                'server': account.server,
                'leverage': account.leverage
            }
            
        except Exception as e:
            self.logger.error(f"Account info error: {e}")
            return {}
    
    def get_market_data(self):
        """市場データ取得"""
        try:
            if not self.mt5_connected:
                return {}
            
            # EURUSD価格取得
            symbol = "EURUSD"
            tick = mt5.symbol_info_tick(symbol)
            
            if not tick:
                return {}
            
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': round((tick.ask - tick.bid) * 100000, 1),  # pips
                'time': datetime.fromtimestamp(tick.time).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Market data error: {e}")
            return {}
    
    def get_realtime_data(self):
        """リアルタイムデータ統合取得"""
        try:
            self.last_data_update = datetime.now()
            
            data = {
                'timestamp': self.last_data_update.isoformat(),
                'system': self.get_system_status(),
                'ea': self.get_ea_status(),
                'account': self.get_account_info(),
                'positions': self.get_positions(),
                'market': self.get_market_data()
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Realtime data error: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def run(self, host='127.0.0.1', port=5000, debug=False):
        """ダッシュボードサーバー起動"""
        try:
            # MT5初期接続
            self.connect_mt5()
            
            self.logger.info(f"=== TradingDashboard 起動 ===")
            self.logger.info(f"URL: http://{host}:{port}")
            self.logger.info(f"Mobile: http://{host}:{port}/mobile")
            
            # Flask-SocketIO サーバー起動
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )
            
        except Exception as e:
            self.logger.error(f"Dashboard startup error: {e}")
            raise
        finally:
            # MT5接続終了
            if self.mt5_connected:
                mt5.shutdown()
                self.logger.info("MT5接続終了")

if __name__ == '__main__':
    # 開発用起動
    dashboard = TradingDashboard()
    dashboard.run(host='0.0.0.0', port=5000, debug=True)