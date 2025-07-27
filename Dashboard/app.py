#!/usr/bin/env python3
"""
JamesORB取引ダッシュボード
ローカル実行用Flask+SocketIOアプリケーション
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクト共通ライブラリ
sys.path.append(str(Path(__file__).parent.parent))
from lib.config_manager import ConfigManager
from lib.logger_setup import setup_logger
from lib.error_handler import ErrorHandler

# Web フレームワーク
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import MetaTrader5 as mt5

class TradingDashboard:
    def __init__(self):
        """ダッシュボード初期化"""
        self.config = ConfigManager()
        self.logger = setup_logger(__name__)
        self.error_handler = ErrorHandler()
        
        # Flask + SocketIO設定
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'trading-dashboard-secret-key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # MT5接続設定
        self.mt5_connected = False
        self.last_data_update = None
        
        # ルート・ハンドラー設定
        self.setup_routes()
        self.setup_websocket_handlers()
        
        self.logger.info("=== TradingDashboard 初期化完了 ===")
    
    def setup_routes(self):
        """HTTP ルート設定"""
        
        @self.app.route('/')
        def dashboard():
            """メインダッシュボード"""
            return render_template('dashboard.html')
        
        @self.app.route('/mobile')
        def mobile_dashboard():
            """モバイル専用ダッシュボード"""
            return render_template('mobile_dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            """システム状態API"""
            try:
                status = self.get_system_status()
                return jsonify(status)
            except Exception as e:
                self.logger.error(f"API status error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/positions')
        def api_positions():
            """ポジション一覧API"""
            try:
                positions = self.get_positions()
                return jsonify(positions)
            except Exception as e:
                self.logger.error(f"API positions error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/account')
        def api_account():
            """アカウント情報API"""
            try:
                account = self.get_account_info()
                return jsonify(account)
            except Exception as e:
                self.logger.error(f"API account error: {e}")
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