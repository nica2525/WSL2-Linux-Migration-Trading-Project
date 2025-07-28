#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5リアルタイム取引監視システム
JamesORBデモ取引（300万円、EURUSD、0.01ロット）専用監視システム

主要機能:
1. リアルタイムポジション監視
2. 取引履歴追跡
3. リアルタイム統計計算（PnL、DD、勝率等）
4. アラート・通知システム
5. パフォーマンス最適化

技術仕様:
- MetaTrader5 Python API使用
- 効率的なデータ取得とメモリ管理
- エラーハンドリング・接続断対応
- JSON形式でのデータ保存
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
from collections import deque
import psutil
import os
import sys


class MT5RealtimeMonitor:
    """MT5リアルタイム監視システム"""
    
    def __init__(self, 
                 symbol: str = "EURUSD",
                 initial_balance: float = 3000000.0,  # 300万円
                 lot_size: float = 0.01,
                 update_interval: int = 5,  # 5秒間隔
                 log_level: int = logging.INFO):
        """
        初期化
        
        Args:
            symbol: 監視対象シンボル
            initial_balance: 初期残高
            lot_size: 固定ロットサイズ
            update_interval: 更新間隔（秒）
            log_level: ログレベル
        """
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.lot_size = lot_size
        self.update_interval = update_interval
        
        # ログ設定
        self.setup_logging(log_level)
        
        # データ保存用
        self.position_history = deque(maxlen=1000)  # 最新1000件保持
        self.trade_history = []
        self.balance_history = deque(maxlen=1000)
        
        # 統計計算用
        self.max_balance = initial_balance
        self.max_drawdown = 0.0
        self.peak_balance = initial_balance
        
        # 監視状態
        self.is_monitoring = False
        self.monitor_thread = None
        
        # 接続状態
        self.is_connected = False
        
        # パフォーマンス監視
        self.process = psutil.Process()
        self.performance_data = deque(maxlen=100)
    
    def setup_logging(self, log_level: int):
        """ログ設定"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            format=log_format,
            level=log_level,
            handlers=[
                logging.FileHandler('mt5_realtime_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('MT5Monitor')
    
    def connect_mt5(self, 
                   login: Optional[int] = None,
                   password: Optional[str] = None,
                   server: Optional[str] = None,
                   path: Optional[str] = None,
                   timeout: int = 60000) -> bool:
        """
        MT5接続（エラーハンドリング付き）
        
        Args:
            login: ログインID
            password: パスワード
            server: サーバー名
            path: MT5実行ファイルパス
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            bool: 接続成功可否
        """
        try:
            # 既存接続をクリーンアップ
            if self.is_connected:
                mt5.shutdown()
                time.sleep(1)
            
            # MT5初期化
            if path:
                result = mt5.initialize(path, timeout=timeout)
            else:
                result = mt5.initialize(timeout=timeout)
            
            if not result:
                error = mt5.last_error()
                self.logger.error(f"MT5初期化失敗: {error}")
                return False
            
            # ログイン（パラメータが指定された場合）
            if login and password and server:
                login_result = mt5.login(login, password, server)
                if not login_result:
                    error = mt5.last_error()
                    self.logger.error(f"MT5ログイン失敗: {error}")
                    mt5.shutdown()
                    return False
            
            # 接続確認
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("アカウント情報取得失敗")
                mt5.shutdown()
                return False
            
            self.is_connected = True
            self.logger.info(f"MT5接続成功 - サーバー: {account_info.server}, 口座: {account_info.login}")
            return True
            
        except Exception as e:
            self.logger.error(f"MT5接続エラー: {e}")
            return False
    
    def disconnect_mt5(self):
        """MT5切断"""
        try:
            if self.is_connected:
                mt5.shutdown()
                self.is_connected = False
                self.logger.info("MT5接続を切断しました")
        except Exception as e:
            self.logger.error(f"MT5切断エラー: {e}")
    
    def get_account_info(self) -> Optional[Dict]:
        """アカウント情報取得"""
        try:
            if not self.is_connected:
                return None
            
            account_info = mt5.account_info()
            if account_info is None:
                return None
            
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'profit': account_info.profit,
                'timestamp': datetime.now()
            }
        except Exception as e:
            self.logger.error(f"アカウント情報取得エラー: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """ポジション情報取得"""
        try:
            if not self.is_connected:
                return []
            
            positions = mt5.positions_get(symbol=self.symbol)
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_data = {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'time': datetime.fromtimestamp(pos.time),
                    'comment': pos.comment,
                    'timestamp': datetime.now()
                }
                position_list.append(position_data)
            
            return position_list
        except Exception as e:
            self.logger.error(f"ポジション情報取得エラー: {e}")
            return []
    
    def get_trade_history(self, days_back: int = 1) -> List[Dict]:
        """取引履歴取得"""
        try:
            if not self.is_connected:
                return []
            
            # 取得期間設定
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            # 取引履歴取得
            history = mt5.history_deals_get(from_date, to_date, group=self.symbol)
            if history is None:
                return []
            
            trade_list = []
            for deal in history:
                trade_data = {
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'time': datetime.fromtimestamp(deal.time),
                    'type': deal.type,
                    'entry': deal.entry,
                    'volume': deal.volume,
                    'price': deal.price,
                    'profit': deal.profit,
                    'swap': deal.swap,
                    'commission': deal.commission,
                    'symbol': deal.symbol,
                    'comment': deal.comment
                }
                trade_list.append(trade_data)
            
            return trade_list
        except Exception as e:
            self.logger.error(f"取引履歴取得エラー: {e}")
            return []
    
    def calculate_statistics(self, account_info: Dict, positions: List[Dict]) -> Dict:
        """リアルタイム統計計算"""
        try:
            current_balance = account_info['balance']
            current_equity = account_info['equity']
            
            # 最大残高更新
            if current_equity > self.peak_balance:
                self.peak_balance = current_equity
            
            # ドローダウン計算
            current_dd = (self.peak_balance - current_equity) / self.peak_balance * 100
            if current_dd > self.max_drawdown:
                self.max_drawdown = current_dd
            
            # 総利益計算
            total_profit = sum([pos['profit'] for pos in positions])
            
            # 利益率計算
            profit_percentage = (current_equity - self.initial_balance) / self.initial_balance * 100
            
            # ポジション数
            position_count = len(positions)
            
            statistics = {
                'current_balance': current_balance,
                'current_equity': current_equity,
                'total_profit': total_profit,
                'profit_percentage': profit_percentage,
                'current_drawdown': current_dd,
                'max_drawdown': self.max_drawdown,
                'position_count': position_count,
                'peak_balance': self.peak_balance,
                'timestamp': datetime.now()
            }
            
            return statistics
        except Exception as e:
            self.logger.error(f"統計計算エラー: {e}")
            return {}
    
    def check_alerts(self, statistics: Dict) -> List[str]:
        """アラートチェック"""
        alerts = []
        
        try:
            # ドローダウンアラート
            if statistics.get('current_drawdown', 0) > 20.0:
                alerts.append(f"⚠️ 危険：ドローダウン {statistics['current_drawdown']:.2f}% - 20%を超過")
            elif statistics.get('current_drawdown', 0) > 10.0:
                alerts.append(f"⚠️ 注意：ドローダウン {statistics['current_drawdown']:.2f}% - 10%を超過")
            
            # 利益アラート
            if statistics.get('profit_percentage', 0) > 5.0:
                alerts.append(f"🎉 利益達成：{statistics['profit_percentage']:.2f}% - 5%超過")
            
            # ポジション数アラート
            if statistics.get('position_count', 0) > 5:
                alerts.append(f"⚠️ ポジション過多：{statistics['position_count']}個 - 5個超過")
            
        except Exception as e:
            self.logger.error(f"アラートチェックエラー: {e}")
        
        return alerts
    
    def save_data(self, data: Dict, filename: str):
        """データ保存"""
        try:
            os.makedirs('MT5_Results', exist_ok=True)
            filepath = os.path.join('MT5_Results', filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"データ保存エラー: {e}")
    
    def monitor_performance(self) -> Dict:
        """パフォーマンス監視"""
        try:
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            performance = {
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb,
                'timestamp': datetime.now()
            }
            
            self.performance_data.append(performance)
            return performance
            
        except Exception as e:
            self.logger.error(f"パフォーマンス監視エラー: {e}")
            return {}
    
    def monitoring_loop(self):
        """監視ループ"""
        self.logger.info("リアルタイム監視開始")
        
        while self.is_monitoring:
            try:
                # 接続確認
                if not self.is_connected:
                    self.logger.warning("MT5接続が切断されています。再接続を試行...")
                    if not self.connect_mt5():
                        time.sleep(self.update_interval)
                        continue
                
                # データ取得
                account_info = self.get_account_info()
                if account_info is None:
                    self.logger.warning("アカウント情報取得失敗")
                    time.sleep(self.update_interval)
                    continue
                
                positions = self.get_positions()
                statistics = self.calculate_statistics(account_info, positions)
                alerts = self.check_alerts(statistics)
                performance = self.monitor_performance()
                
                # データ保存
                monitoring_data = {
                    'account_info': account_info,
                    'positions': positions,
                    'statistics': statistics,
                    'alerts': alerts,
                    'performance': performance
                }
                
                # 履歴保存
                self.balance_history.append(account_info)
                self.position_history.append(positions)
                
                # ログ出力
                self.logger.info(f"残高: {account_info['balance']:,.0f}, "
                               f"評価損益: {account_info['profit']:,.0f}, "
                               f"ポジション数: {len(positions)}, "
                               f"DD: {statistics.get('current_drawdown', 0):.2f}%")
                
                # アラート表示
                for alert in alerts:
                    self.logger.warning(alert)
                
                # データ保存（JSON）
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.save_data(monitoring_data, f'realtime_monitor_{timestamp_str}.json')
                
                # 待機
                time.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                self.logger.info("監視停止要求を受信")
                break
            except Exception as e:
                self.logger.error(f"監視ループエラー: {e}")
                time.sleep(self.update_interval)
        
        self.logger.info("リアルタイム監視終了")
    
    def start_monitoring(self):
        """監視開始"""
        if self.is_monitoring:
            self.logger.warning("監視は既に開始されています")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.logger.info("リアルタイム監視スレッド開始")
    
    def stop_monitoring(self):
        """監視停止"""
        if not self.is_monitoring:
            self.logger.warning("監視は開始されていません")
            return
        
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        self.logger.info("リアルタイム監視停止")
    
    def generate_report(self) -> Dict:
        """監視レポート生成"""
        try:
            if not self.balance_history:
                return {"error": "監視データがありません"}
            
            # 最新データ
            latest_account = self.balance_history[-1]
            latest_positions = self.position_history[-1] if self.position_history else []
            
            # 統計計算
            balances = [data['balance'] for data in self.balance_history]
            equities = [data['equity'] for data in self.balance_history]
            
            report = {
                'monitoring_period': {
                    'start': self.balance_history[0]['timestamp'],
                    'end': latest_account['timestamp'],
                    'duration_hours': (latest_account['timestamp'] - self.balance_history[0]['timestamp']).total_seconds() / 3600
                },
                'account_summary': {
                    'initial_balance': self.initial_balance,
                    'current_balance': latest_account['balance'],
                    'current_equity': latest_account['equity'],
                    'total_profit': latest_account['balance'] - self.initial_balance,
                    'profit_percentage': (latest_account['balance'] - self.initial_balance) / self.initial_balance * 100
                },
                'risk_metrics': {
                    'max_drawdown': self.max_drawdown,
                    'peak_balance': self.peak_balance,
                    'current_drawdown': (self.peak_balance - latest_account['equity']) / self.peak_balance * 100
                },
                'position_summary': {
                    'current_positions': len(latest_positions),
                    'total_unrealized_pnl': sum([pos['profit'] for pos in latest_positions])
                },
                'performance_stats': {
                    'avg_cpu_usage': np.mean([p['cpu_percent'] for p in self.performance_data]) if self.performance_data else 0,
                    'avg_memory_mb': np.mean([p['memory_mb'] for p in self.performance_data]) if self.performance_data else 0
                },
                'generated_at': datetime.now()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            return {"error": str(e)}


def main():
    """メイン実行"""
    print("=== MT5リアルタイム取引監視システム ===")
    print("JamesORBデモ取引監視用")
    print()
    
    # 監視システム初期化
    monitor = MT5RealtimeMonitor(
        symbol="EURUSD",
        initial_balance=3000000.0,  # 300万円
        lot_size=0.01,
        update_interval=5  # 5秒間隔
    )
    
    try:
        # MT5接続
        print("MT5に接続中...")
        if not monitor.connect_mt5():
            print("❌ MT5接続失敗。プログラムを終了します。")
            return
        
        print("✅ MT5接続成功")
        
        # 監視開始
        monitor.start_monitoring()
        print("🔍 リアルタイム監視開始（Ctrl+Cで停止）")
        print()
        
        # メインループ（ユーザー入力待機）
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n監視停止要求を受信...")
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        # 監視停止
        monitor.stop_monitoring()
        
        # レポート生成
        print("📊 最終レポート生成中...")
        report = monitor.generate_report()
        monitor.save_data(report, 'final_monitoring_report.json')
        
        # MT5切断
        monitor.disconnect_mt5()
        print("✅ システム終了完了")


if __name__ == "__main__":
    main()