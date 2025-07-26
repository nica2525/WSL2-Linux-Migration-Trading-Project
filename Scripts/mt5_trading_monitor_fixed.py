#!/usr/bin/env python3
"""
MT5取引監視システム（リファクタリング版）
共通ライブラリを使用した統一設計

Features:
- 設定外部化（YAML設定ファイル）  
- 統一ログシステム
- 堅牢なエラーハンドリング
- MT5接続管理（Wine/RPYC対応）
- リトライ機構・自動復旧
- ファイルロック・アトミック書き込み
- 設定妥当性検証
"""

import os
import sys
import json
import time
import fcntl
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib import (
    get_logger, get_mt5_connection, mt5_context,
    get_config, get_value,
    retry_on_failure, error_context, safe_execute,
    MT5ConnectionError, ConfigurationError, FileOperationError
)


class TradingDataManager:
    """取引データ管理クラス"""
    
    def __init__(self, logger_name: str = "TradingData"):
        self.logger = get_logger(logger_name)
        
        # ファイルパス設定
        log_dir = get_value("system_config", "logging.log_dir", "MT5/Logs")
        self.data_dir = Path(project_root) / log_dir / "Trading"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.trade_file = self.data_dir / "trades.json"
        self.lock_file = self.data_dir / ".trades.lock"
        
        # 取引データ
        self.trades = self._load_trades()
    
    def _load_trades(self) -> List[Dict[str, Any]]:
        """取引記録読み込み（ファイルロック対応）"""
        if not self.trade_file.exists():
            self.logger.info("取引記録ファイルが存在しません。新規作成します")
            return []
        
        try:
            with error_context("取引記録読み込み"):
                with open(self.trade_file, 'r', encoding='utf-8') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        self.logger.info(f"取引記録読み込み完了: {len(data)}件")
                        return data
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON読み込みエラー: {e}")
            # バックアップ作成
            backup_file = self.trade_file.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            self.trade_file.rename(backup_file)
            self.logger.info(f"破損ファイルをバックアップ: {backup_file}")
            return []
            
        except Exception as e:
            self.logger.error(f"取引記録読み込みエラー: {e}")
            raise FileOperationError(f"取引記録読み込み失敗: {e}")
    
    @retry_on_failure(max_retries=3, retry_delay=1)
    def save_trades(self) -> bool:
        """取引記録保存（アトミック書き込み）"""
        temp_file = self.trade_file.with_suffix('.tmp')
        
        try:
            with error_context("取引記録保存"):
                # 一時ファイルに書き込み
                with open(temp_file, 'w', encoding='utf-8') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(self.trades, f, indent=2, ensure_ascii=False)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                # アトミックに置換
                temp_file.replace(self.trade_file)
                self.logger.debug(f"取引記録保存完了: {len(self.trades)}件")
                return True
                
        except Exception as e:
            self.logger.error(f"取引記録保存エラー: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise FileOperationError(f"取引記録保存失敗: {e}")
    
    def add_trade(self, trade_info: Dict[str, Any]) -> bool:
        """新規取引追加"""
        try:
            # 重複チェック
            ticket = trade_info.get('ticket')
            if any(t['ticket'] == ticket for t in self.trades):
                self.logger.warning(f"重複取引: チケット{ticket}")
                return False
            
            self.trades.append(trade_info)
            self.save_trades()
            
            self.logger.info(f"新規取引記録: {trade_info['type']} {trade_info['volume']}ロット @ {trade_info['open_price']}")
            return True
            
        except Exception as e:
            self.logger.error(f"取引追加エラー: {e}")
            return False
    
    def update_trade(self, ticket: int, update_data: Dict[str, Any]) -> bool:
        """取引情報更新"""
        try:
            for trade in self.trades:
                if trade.get('ticket') == ticket:
                    trade.update(update_data)
                    self.save_trades()
                    self.logger.info(f"取引更新: チケット{ticket}")
                    return True
            
            self.logger.warning(f"更新対象の取引が見つかりません: チケット{ticket}")
            return False
            
        except Exception as e:
            self.logger.error(f"取引更新エラー: {e}")
            return False
    
    def get_trades_summary(self) -> Dict[str, Any]:
        """取引サマリー生成"""
        if not self.trades:
            return {"total": 0, "open": 0, "closed": 0, "profit": 0, "win_rate": 0}
        
        open_trades = [t for t in self.trades if t.get("status") == "OPEN"]
        closed_trades = [t for t in self.trades if t.get("status") == "CLOSED"]
        
        if closed_trades:
            total_profit = sum(t.get("profit", 0) for t in closed_trades)
            total_commission = sum(t.get("commission", 0) for t in closed_trades)
            total_swap = sum(t.get("swap", 0) for t in closed_trades)
            net_profit = total_profit + total_commission + total_swap
            
            win_trades = [t for t in closed_trades if t.get("profit", 0) > 0]
            win_rate = len(win_trades) / len(closed_trades) * 100 if closed_trades else 0
        else:
            net_profit = 0
            win_rate = 0
        
        return {
            "total": len(self.trades),
            "open": len(open_trades),
            "closed": len(closed_trades),
            "profit": net_profit,
            "win_rate": win_rate,
            "last_update": datetime.now().isoformat()
        }


class MT5TradingMonitor:
    """MT5取引監視システム"""
    
    def __init__(self):
        self.logger = get_logger("TradingMonitor", "trading_monitor.log")
        
        # 設定読み込み
        try:
            self.ea_config = get_config("ea_config")
            self.trading_config = get_config("trading_config")
            self.system_config = get_config("system_config")
            
            # 設定妥当性確認
            self._validate_config()
            
        except Exception as e:
            self.logger.critical(f"設定読み込みエラー: {e}")
            raise ConfigurationError(f"設定初期化失敗: {e}")
        
        # MT5接続管理
        self.connection = get_mt5_connection("TradingMonitor")
        
        # データ管理
        self.data_manager = TradingDataManager()
        
        # 監視設定
        self.ea_magic = get_value("ea_config", "ea.magic_number", 20250727)
        self.symbol = get_value("ea_config", "ea.symbol", "EURUSD")
        self.check_interval = get_value("ea_config", "monitoring.check_interval", 60)
        self.summary_interval = get_value("ea_config", "monitoring.summary_interval", 900)
        
        # 状態管理
        self.last_position_count = 0
        self.error_count = 0
        self.max_errors = get_value("system_config", "error_handling.max_retries", 5)
    
    def _validate_config(self):
        """設定妥当性確認"""
        required_ea_configs = [
            "ea.name",
            "ea.symbol",
            "ea.magic_number",
            "monitoring.check_interval"
        ]
        
        required_trading_configs = [
            "demo_account.login"
        ]
        
        for config_path in required_ea_configs:
            if not get_value("ea_config", config_path):
                raise ConfigurationError(f"必須EA設定が不足: {config_path}")
        
        for config_path in required_trading_configs:
            if not get_value("trading_config", config_path):
                raise ConfigurationError(f"必須取引設定が不足: {config_path}")
        
        self.logger.info("設定妥当性確認完了")
    
    @retry_on_failure(max_retries=3, retry_delay=10)
    def ensure_mt5_connection(self) -> bool:
        """MT5接続保証（リトライ付き）"""
        with error_context("MT5接続確保", critical=True):
            if self.connection.check_connection():
                return True
            
            return self.connection.ensure_connection()
    
    def get_positions(self) -> List[Any]:
        """ポジション情報取得"""
        try:
            with self.connection.connection_context() as mt5:
                positions_data = mt5.positions_get(symbol=self.symbol)
                return positions_data if positions_data else []
        except Exception as e:
            self.logger.error(f"ポジション取得エラー: {e}")
            return []
    
    def get_history_deals(self, date_from: datetime, date_to: datetime) -> List[Any]:
        """取引履歴取得"""
        try:
            with self.connection.connection_context() as mt5:
                deals_data = mt5.history_deals_get(date_from, date_to)
                return deals_data if deals_data else []
        except Exception as e:
            self.logger.error(f"履歴取得エラー: {e}")
            return []
    
    def monitor_positions(self) -> bool:
        """ポジション監視"""
        try:
            with error_context("ポジション監視"):
                positions = self.get_positions()
                
                # EAのポジションのみフィルタリング
                ea_positions = [p for p in positions 
                              if getattr(p, 'magic', None) == self.ea_magic]
                
                current_count = len(ea_positions)
                
                # 新規ポジション検出
                if current_count > self.last_position_count:
                    self.logger.info(f"🔔 新規ポジション検出！ ({current_count}個)")
                    self._handle_new_positions(ea_positions)
                
                # ポジション決済検出
                elif current_count < self.last_position_count:
                    self.logger.info(f"💰 ポジション決済検出！ (残り{current_count}個)")
                    self._check_closed_positions()
                
                self.last_position_count = current_count
                return True
                
        except Exception as e:
            self.logger.error(f"ポジション監視エラー: {e}")
            return False
    
    def _handle_new_positions(self, positions: List[Any]):
        """新規ポジション処理"""
        existing_tickets = {t['ticket'] for t in self.data_manager.trades 
                          if t.get('status') == 'OPEN'}
        
        for pos in positions:
            ticket = getattr(pos, 'ticket', None)
            
            if ticket and ticket not in existing_tickets:
                trade_info = self._create_trade_info(pos)
                self.data_manager.add_trade(trade_info)
    
    def _create_trade_info(self, position: Any) -> Dict[str, Any]:
        """ポジション情報から取引情報作成"""
        return {
            "ticket": getattr(position, 'ticket', 0),
            "symbol": getattr(position, 'symbol', ''),
            "type": "BUY" if getattr(position, 'type', -1) == 0 else "SELL",
            "volume": getattr(position, 'volume', 0),
            "open_price": getattr(position, 'price_open', 0),
            "open_time": datetime.fromtimestamp(getattr(position, 'time', 0)).isoformat(),
            "sl": getattr(position, 'sl', 0),
            "tp": getattr(position, 'tp', 0),
            "status": "OPEN",
            "profit": 0,
            "magic": getattr(position, 'magic', 0),
            "ea_name": get_value("ea_config", "ea.name", "Unknown"),
            "recorded_at": datetime.now().isoformat()
        }
    
    def _check_closed_positions(self):
        """決済ポジション確認"""
        today = datetime.now()
        days_back = get_value("ea_config", "monitoring.deal_history_days", 2)
        date_from = today - timedelta(days=days_back)
        
        deals = self.get_history_deals(date_from, today)
        
        for deal in deals:
            symbol = getattr(deal, 'symbol', '')
            magic = getattr(deal, 'magic', None)
            
            if symbol == self.symbol and magic == self.ea_magic:
                self._update_closed_position(deal)
    
    def _update_closed_position(self, deal: Any):
        """決済情報更新"""
        position_id = getattr(deal, 'position_id', None)
        if not position_id:
            return
        
        update_data = {
            "status": "CLOSED",
            "close_price": getattr(deal, 'price', 0),
            "close_time": datetime.fromtimestamp(getattr(deal, 'time', 0)).isoformat(),
            "profit": getattr(deal, 'profit', 0),
            "commission": getattr(deal, 'commission', 0),
            "swap": getattr(deal, 'swap', 0),
            "closed_at": datetime.now().isoformat()
        }
        
        if self.data_manager.update_trade(position_id, update_data):
            profit = update_data.get('profit', 0)
            self.logger.info(f"取引決済: チケット{position_id} 利益: ${profit:.2f}")
    
    def generate_summary(self) -> str:
        """取引サマリー生成"""
        summary_data = self.data_manager.get_trades_summary()
        
        summary = f"""
=== JamesORB EA 取引サマリー ===
総取引数: {summary_data['total']}
オープン中: {summary_data['open']}
決済済み: {summary_data['closed']}
純利益: ${summary_data['profit']:.2f}
勝率: {summary_data['win_rate']:.1f}%
監視時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
EA: {get_value("ea_config", "ea.name")} (Magic: {self.ea_magic})
================================
"""
        return summary
    
    def run_single_check(self) -> bool:
        """単発チェック実行（cron用）"""
        self.logger.info("=== 単発取引監視開始 ===")
        
        try:
            if not self.ensure_mt5_connection():
                self.logger.error("MT5接続失敗")
                return False
            
            # 監視実行
            success = self.monitor_positions()
            
            # サマリー生成
            summary = self.generate_summary()
            self.logger.info(summary)
            print(summary)  # cron出力用
            
            return success
            
        except Exception as e:
            self.logger.error(f"単発チェックエラー: {e}")
            return False
        finally:
            self.connection.disconnect_rpyc()
    
    def run_continuous_monitor(self) -> bool:
        """継続監視実行"""
        self.logger.info("=== 継続取引監視開始 ===")
        
        try:
            if not self.ensure_mt5_connection():
                self.logger.error("MT5接続失敗")
                return False
            
            while True:
                try:
                    # 監視実行
                    if self.monitor_positions():
                        self.error_count = 0
                    else:
                        self.error_count += 1
                    
                    # 定期サマリー出力
                    if datetime.now().minute % (self.summary_interval // 60) == 0:
                        summary = self.generate_summary()
                        self.logger.info(summary)
                    
                    # エラー上限チェック
                    if self.error_count >= self.max_errors:
                        self.logger.error("エラー回数上限。再接続試行")
                        self.connection.disconnect_rpyc()
                        time.sleep(30)
                        
                        if not self.ensure_mt5_connection():
                            self.logger.error("再接続失敗。監視終了")
                            return False
                        
                        self.error_count = 0
                    
                    time.sleep(self.check_interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("監視終了（ユーザー中断）")
                    break
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"監視エラー ({self.error_count}/{self.max_errors}): {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"継続監視エラー: {e}")
            return False
        finally:
            self.connection.disconnect_rpyc()
            self.logger.info("=== 継続監視終了 ===")


def main():
    """メイン処理"""
    try:
        monitor = MT5TradingMonitor()
        
        # 動作モード判定
        if os.environ.get('CRON_MODE'):
            # cron用単発チェック
            success = monitor.run_single_check()
            return 0 if success else 1
        else:
            # 継続監視
            success = monitor.run_continuous_monitor()
            return 0 if success else 1
            
    except Exception as e:
        print(f"システムエラー: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)