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
# MT5インポート（Wine環境対応）
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    print("✅ MetaTrader5パッケージが利用可能")
except ImportError:
    print("⚠️ MetaTrader5パッケージが利用できません - モックを使用")
    import mt5_mock as mt5
    MT5_AVAILABLE = False

# セキュリティライブラリー
try:
    from flask_httpauth import HTTPBasicAuth
except ImportError:
    print("警告: flask-httpauthがインストールされていません")
    print("pip install flask-httpauth でインストールしてください")
    class HTTPBasicAuth:
        def __init__(self): pass
        def login_required(self, f): return f
        def verify_password(self, f): return f

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
        """WebSocket ハンドラー設定 - kiro設計準拠"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """クライアント接続時の初期データ送信"""
            self.logger.info(f"クライアント接続: {request.sid}")
            
            # 初期データ送信
            try:
                emit('connected', {'status': 'success', 'timestamp': datetime.now().isoformat()})
                emit('account_info', self.get_account_info())
                emit('positions', self.get_positions())
                emit('ea_status', self.get_ea_status())
                emit('system_status', self.get_system_status())
            except Exception as e:
                self.logger.error(f"初期データ送信エラー: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """クライアント切断"""
            self.logger.info(f"クライアント切断: {request.sid}")
        
        @self.socketio.on('request_data')
        def handle_data_request():
            """リアルタイムデータ要求 - メインユース"""
            try:
                data = self.get_realtime_data()
                emit('market_data', data)
            except Exception as e:
                self.logger.error(f"Data request error: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('request_history')
        def handle_history_request(data):
            """履歴データ要求（REST的処理）"""
            try:
                period = data.get('period', '1h') if data else '1h'
                history = self.get_history_data(period)
                emit('history_data', history)
            except Exception as e:
                self.logger.error(f"History request error: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('request_refresh')
        def handle_refresh_request():
            """強制データ更新 - 再接続付き"""
            try:
                # MT5再接続
                self.mt5_manager.connect_with_retry()
                
                # 最新データ取得・送信
                data = self.get_realtime_data()
                emit('market_data', data)
                emit('notification', {
                    'type': 'success', 
                    'message': f'データ更新完了 - {datetime.now().strftime("%H:%M:%S")}'
                })
            except Exception as e:
                self.logger.error(f"Refresh error: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('set_update_interval')
        def handle_update_interval(data):
            """更新間隔設定（モバイルバッテリー配慮）"""
            try:
                interval = data.get('interval', 5) if data else 5
                # 未実装: 将来のバッテリー配慮機能
                emit('notification', {
                    'type': 'info',
                    'message': f'更新間隔: {interval}秒 (未実装)'
                })
            except Exception as e:
                emit('error', {'message': str(e)})
    
    def start_background_update(self):
        """バックグラウンド更新タスク開始 - 5秒間隔"""
        if self.background_thread is None:
            self.background_thread = threading.Thread(target=self._background_update_loop)
            self.background_thread.daemon = True
            self.background_thread.start()
            self.logger.info("バックグラウンド更新タスク開始")
    
    def _background_update_loop(self):
        """バックグラウンド更新ループ - kiro設計準拠"""
        while True:
            try:
                if self.mt5_manager.connected:
                    # リアルタイムデータ更新
                    data = self.get_realtime_data()
                    self.socketio.emit('market_data', data)
                    
                    # データベース保存
                    self.save_to_database(data)
                    
                    self.last_data_update = datetime.now()
                
                time.sleep(5)  # 5秒間隔
                
            except Exception as e:
                self.logger.error(f"バックグラウンド更新エラー: {e}")
                time.sleep(10)  # エラー時は10秒待機
    
    def save_to_database(self, data):
        """データベース保存 - kiro設計準拠"""
        try:
            db_path = Path(__file__).parent / 'dashboard.db'
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # 口座情報保存
                if 'account' in data and data['account']:
                    account = data['account']
                    cursor.execute('''
                        INSERT INTO account_history 
                        (balance, equity, margin, free_margin, margin_level, profit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        account.get('balance', 0),
                        account.get('equity', 0),
                        account.get('margin', 0),
                        account.get('margin_free', 0),
                        account.get('margin_level', 0),
                        account.get('profit', 0)
                    ))
                
                # EA状態保存
                if 'ea' in data and data['ea']:
                    ea = data['ea']
                    cursor.execute('''
                        INSERT INTO ea_status (status, message, positions_count)
                        VALUES (?, ?, ?)
                    ''', (
                        ea.get('status', 'UNKNOWN'),
                        ea.get('name', ''),
                        ea.get('active_positions', 0)
                    ))
                
                conn.commit()
        
        except Exception as e:
            self.logger.error(f"データベース保存エラー: {e}")
    
    def get_history_data(self, period):
        """履歴データ取得 - REST API用"""
        try:
            db_path = Path(__file__).parent / 'dashboard.db'
            
            # 期間設定
            hours = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}.get(period, 24)
            cutoff = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # 口座履歴取得
                cursor.execute('''
                    SELECT timestamp, balance, equity, profit
                    FROM account_history 
                    WHERE timestamp > ?
                    ORDER BY timestamp
                ''', (cutoff.isoformat(),))
                
                history = [{
                    'timestamp': row[0],
                    'balance': row[1],
                    'equity': row[2],
                    'profit': row[3]
                } for row in cursor.fetchall()]
                
                return {'period': period, 'data': history}
        
        except Exception as e:
            self.logger.error(f"履歴データ取得エラー: {e}")
            return {'period': period, 'data': []}
    
    def get_system_status(self):
        """システム状態取得 - 改良版"""
        try:
            # MT5接続チェック
            if not self.mt5_manager.connected:
                self.mt5_manager.connect_with_retry()
            
            # システム状態情報
            status = {
                'timestamp': datetime.now().isoformat(),
                'mt5_connected': self.mt5_manager.connected,
                'last_update': self.last_data_update.isoformat() if self.last_data_update else None,
                'ea_status': self.get_ea_status(),
                'system_health': 'OK' if self.mt5_manager.connected else 'WARNING',
                'connection_retries': self.mt5_manager.retry_count
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
        """EA稼働状態取得 - 改良版"""
        try:
            if not self.mt5_manager.connected:
                return {'status': 'DISCONNECTED', 'name': 'Unknown'}
            
            # EA設定から情報取得
            ea_config = self.config.get_ea_config()
            
            # 実際のEA稼働チェック
            positions = self.mt5_manager.get_positions()
            active_positions = len(positions) if positions else 0
            
            # 今日の利益計算
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_profit = sum(pos.profit for pos in positions if 
                             datetime.fromtimestamp(pos.time) >= today_start)
            
            return {
                'name': ea_config.get('name', 'JamesORB_v1.0'),
                'status': 'RUNNING' if self.mt5_manager.connected else 'STOPPED',
                'symbol': ea_config.get('symbol', 'EURUSD'),
                'timeframe': ea_config.get('timeframe', 'M5'),
                'active_positions': active_positions,
                'today_profit': round(today_profit, 2) if positions else 0.0,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"EA status error: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def get_positions(self):
        """ポジション一覧取得 - 改良版"""
        try:
            positions = self.mt5_manager.get_positions()
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
                    'profit': round(pos.profit, 2),
                    'profit_pips': round((pos.price_current - pos.price_open) * 
                                       (100000 if pos.symbol == 'EURUSD' else 100), 1),
                    'swap': pos.swap,
                    'open_time': datetime.fromtimestamp(pos.time).isoformat(),
                    'duration': str(datetime.now() - datetime.fromtimestamp(pos.time)).split('.')[0],
                    'comment': pos.comment or 'No comment'
                })
            
            return position_list
            
        except Exception as e:
            self.logger.error(f"Positions error: {e}")
            return []
    
    def get_account_info(self):
        """アカウント情報取得 - 改良版"""
        try:
            account_data = self.mt5_manager.get_account_info()
            if not account_data:
                return {}
            
            # 計算項目追加
            margin_level = account_data.get('margin_level', 0)
            equity = account_data.get('equity', 0)
            balance = account_data.get('balance', 0)
            
            return {
                'login': account_data.get('login', 0),
                'balance': round(account_data.get('balance', 0), 2),
                'equity': round(equity, 2),
                'margin': round(account_data.get('margin', 0), 2),
                'margin_free': round(account_data.get('margin_free', 0), 2),
                'margin_level': round(margin_level, 2) if margin_level else None,
                'profit': round(account_data.get('profit', 0), 2),
                'profit_percent': round(((equity - balance) / balance * 100), 2) if balance > 0 else 0,
                'currency': account_data.get('currency', 'USD'),
                'server': account_data.get('server', 'Unknown'),
                'leverage': account_data.get('leverage', 0),
                'margin_level_status': self._get_margin_status(margin_level)
            }
            
        except Exception as e:
            self.logger.error(f"Account info error: {e}")
            return {}
    
    def _get_margin_status(self, margin_level):
        """証拠金レベル状態判定"""
        if not margin_level:
            return 'UNKNOWN'
        elif margin_level >= 1000:
            return 'EXCELLENT'
        elif margin_level >= 500:
            return 'GOOD'
        elif margin_level >= 200:
            return 'WARNING'
        elif margin_level >= 100:
            return 'DANGER'
        else:
            return 'CRITICAL'
    
    def get_market_data(self):
        """市場データ取得 - 改良版"""
        try:
            if not self.mt5_manager.connected:
                return {}
            
            # EURUSD価格取得
            symbol = "EURUSD"
            tick = mt5.symbol_info_tick(symbol)
            
            if not tick:
                return {}
            
            # スプレッドと中値計算
            spread_pips = round((tick.ask - tick.bid) * 100000, 1)
            mid_price = round((tick.bid + tick.ask) / 2, 5)
            
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'mid': mid_price,
                'spread': spread_pips,
                'spread_status': 'NARROW' if spread_pips <= 1.5 else 'WIDE' if spread_pips >= 3.0 else 'NORMAL',
                'time': datetime.fromtimestamp(tick.time).isoformat(),
                'server_time': datetime.fromtimestamp(tick.time).strftime('%H:%M:%S')
            }
            
        except Exception as e:
            self.logger.error(f"Market data error: {e}")
            return {}
    
    def get_realtime_data(self):
        """リアルタイムデータ統合取得 - 改良版"""
        try:
            self.last_data_update = datetime.now()
            
            # 各データ取得
            system_status = self.get_system_status()
            ea_status = self.get_ea_status()
            account_info = self.get_account_info()
            positions = self.get_positions()
            market_data = self.get_market_data()
            
            # 統合データ
            data = {
                'timestamp': self.last_data_update.isoformat(),
                'server_time': self.last_data_update.strftime('%H:%M:%S'),
                'system': system_status,
                'ea': ea_status,
                'account': account_info,
                'positions': positions,
                'market': market_data,
                'summary': {
                    'total_positions': len(positions),
                    'total_profit': sum(pos.get('profit', 0) for pos in positions),
                    'connection_health': 'OK' if self.mt5_manager.connected else 'ERROR',
                    'data_freshness': 'リアルタイム'
                }
            }
            
            return data
            
        except Exception as e:
            self.logger.error(f"Realtime data error: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'system': {'system_health': 'ERROR'},
                'summary': {'connection_health': 'ERROR'}
            }
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """ダッシュボードサーバー起動 - kiro設計準拠"""
        try:
            # MT5初期接続
            self.mt5_manager.connect_with_retry()
            
            # バックグラウンド更新開始
            self.start_background_update()
            
            self.logger.info(f"=== JamesORB監視ダッシュボード v1.0 起動 ===")
            self.logger.info(f"URL: http://{host}:{port}")
            self.logger.info(f"Mobile: http://{host}:{port}/mobile")
            self.logger.info(f"認証: Basic ({SecurityConfig.BASIC_AUTH_USERNAME})")
            self.logger.info(f"VPN: Tailscale推奨")
            
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
            if self.mt5_manager.connected:
                mt5.shutdown()
                self.logger.info("MT5接続終了")

if __name__ == '__main__':
    # kiro設計v1.0準拠の本格起動
    print("JamesORB監視ダッシュボード v1.0")
    print("kiro設計アーキテクチャ準拠")
    print("認証情報: trader / jamesorb2025")
    print("Tailscale VPN推奨")
    
    dashboard = TradingDashboard()
    dashboard.run(host='0.0.0.0', port=5000, debug=False)