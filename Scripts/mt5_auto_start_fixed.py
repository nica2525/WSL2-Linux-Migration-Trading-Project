#!/usr/bin/env python3
"""
MT5自動起動・EA適用スクリプト（リファクタリング版）
共通ライブラリを使用した統一設計

Features:
- 設定外部化（YAML設定ファイル）
- 統一ログシステム
- 堅牢なエラーハンドリング
- MT5接続管理
- リトライ機構
- 設定妥当性検証
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib import (
    get_logger, get_mt5_connection, mt5_context,
    get_config, get_value,
    retry_on_failure, error_context, safe_execute,
    MT5ConnectionError, ConfigurationError
)


class MT5AutoStartSystem:
    """MT5自動起動システム"""
    
    def __init__(self):
        self.logger = get_logger("MT5AutoStart", "mt5_auto_start.log")
        
        # 設定読み込み
        try:
            self.mt5_config = get_config("mt5_config")
            self.ea_config = get_config("ea_config")
            self.system_config = get_config("system_config")
            
            # 設定妥当性確認
            self._validate_config()
            
        except Exception as e:
            self.logger.critical(f"設定読み込みエラー: {e}")
            raise ConfigurationError(f"設定初期化失敗: {e}")
        
        # MT5接続管理
        self.connection = get_mt5_connection("AutoStart")
        
        # タイムアウト設定
        self.startup_timeout = get_value("mt5_config", "mt5.startup_timeout", 30)
        self.ea_load_timeout = get_value("ea_config", "monitoring.check_interval", 60) * 10
    
    def _validate_config(self):
        """設定妥当性確認"""
        required_mt5_configs = [
            "mt5.terminal_path",
            "mt5.experts_dir",
            "mt5.startup_timeout"
        ]
        
        required_ea_configs = [
            "ea.name",
            "ea.symbol", 
            "ea.timeframe",
            "ea.lot_size"
        ]
        
        for config_path in required_mt5_configs:
            if not get_value("mt5_config", config_path):
                raise ConfigurationError(f"必須MT5設定が不足: {config_path}")
        
        for config_path in required_ea_configs:
            if not get_value("ea_config", config_path):
                raise ConfigurationError(f"必須EA設定が不足: {config_path}")
        
        self.logger.info("設定妥当性確認完了")
    
    @retry_on_failure(max_retries=3, retry_delay=5)
    def ensure_mt5_startup(self) -> bool:
        """MT5起動保証（リトライ付き）"""
        with error_context("MT5起動処理", critical=True):
            # 既存プロセス確認
            if self.connection.is_mt5_running():
                self.logger.info("MT5は既に起動中")
                return True
            
            # 起動設定作成
            if not self._create_startup_config():
                raise MT5ConnectionError("起動設定作成失敗")
            
            # MT5起動実行
            if not self.connection.start_mt5(wait_for_startup=True):
                raise MT5ConnectionError("MT5起動失敗")
            
            self.logger.info("MT5起動成功")
            return True
    
    def _create_startup_config(self) -> bool:
        """MT5起動設定ファイル作成"""
        try:
            # EA設定取得
            ea_name = get_value("ea_config", "ea.name")
            ea_symbol = get_value("ea_config", "ea.symbol") 
            ea_timeframe = get_value("ea_config", "ea.timeframe")
            
            # 取引設定取得
            demo_account = get_value("trading_config", "demo_account.login")
            
            # 起動設定内容
            ini_content = f"""[Common]
AutoTrade=1
NewsEnable=0
ExpertsDllImport=0
ExpertsEnabled=1

[Experts]
AllowLiveTrading=1
AllowDllImport=0
Enabled=1
Account={demo_account}
Profile=Default

[Charts]
ProfileLast=Default
MaxBars=50000

[StartUp]
Expert={ea_name}
Symbol={ea_symbol}
Period={ea_timeframe}

[Tester]
ReplaceReport=0
ShutdownTerminal=0
"""
            
            # 設定ファイル保存
            profiles_dir = get_value("mt5_config", "mt5.profiles_dir")
            startup_file = Path(profiles_dir) / "default" / "startup.ini"
            
            # ディレクトリ作成
            startup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル書き込み
            with open(startup_file, 'w', encoding='utf-8') as f:
                f.write(ini_content)
            
            self.logger.info(f"起動設定ファイル作成: {startup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"起動設定作成エラー: {e}")
            return False
    
    def _read_mt5_log(self, log_file: Path) -> str:
        """MT5ログファイル読み込み（複数エンコーディング対応）"""
        encodings = get_value("mt5_config", "mt5.log_encoding", 
                            ['utf-16-le', 'utf-8-sig', 'utf-8', 'cp1252'])
        
        for encoding in encodings:
            try:
                with open(log_file, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read()
            except Exception:
                continue
        
        self.logger.warning(f"ログファイル読み込み失敗: {log_file}")
        return ""
    
    def monitor_ea_status(self, timeout: int = None) -> bool:
        """EA稼働状態監視"""
        if timeout is None:
            timeout = self.ea_load_timeout
        
        with error_context("EA稼働監視"):
            logs_dir = Path(get_value("mt5_config", "mt5.logs_dir"))
            ea_name = get_value("ea_config", "ea.name")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # ログディレクトリ確認
                    if not logs_dir.exists():
                        self.logger.warning(f"ログディレクトリ未存在: {logs_dir}")
                        time.sleep(5)
                        continue
                    
                    # 最新ログファイル取得
                    log_files = list(logs_dir.glob("*.log"))
                    if not log_files:
                        self.logger.warning("ログファイルが見つかりません")
                        time.sleep(5)
                        continue
                    
                    latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                    
                    # ログ内容確認
                    content = self._read_mt5_log(latest_log)
                    
                    # EA稼働確認パターン
                    success_patterns = [
                        f"{ea_name} loaded successfully",
                        f"Expert {ea_name} loaded",
                        f"{ea_name} initialized",
                        "initialization finished",
                        "expert enabled"
                    ]
                    
                    for pattern in success_patterns:
                        if pattern.lower() in content.lower():
                            self.logger.info(f"EA稼働確認: {pattern}")
                            return True
                    
                    # エラーパターン確認
                    error_patterns = [
                        f"failed to load expert '{ea_name}'",
                        "expert initialization failed",
                        "invalid expert file"
                    ]
                    
                    for pattern in error_patterns:
                        if pattern.lower() in content.lower():
                            self.logger.error(f"EA読み込みエラー: {pattern}")
                            return False
                    
                except Exception as e:
                    self.logger.error(f"ログ確認エラー: {e}")
                
                time.sleep(5)
            
            self.logger.warning(f"EA稼働確認タイムアウト（{timeout}秒）")
            return False
    
    def get_system_status(self) -> dict:
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "mt5_running": self.connection.is_mt5_running(),
            "connection_status": self.connection.get_connection_status(),
            "ea_config": {
                "name": get_value("ea_config", "ea.name"),
                "symbol": get_value("ea_config", "ea.symbol"),
                "timeframe": get_value("ea_config", "ea.timeframe")
            }
        }
    
    def run_startup_sequence(self) -> bool:
        """起動シーケンス実行"""
        self.logger.info("=== MT5自動起動システム開始 ===")
        
        try:
            # 1. システム状態確認
            status = self.get_system_status()
            self.logger.info(f"初期状態: {status}")
            
            # 2. MT5起動保証
            if not self.ensure_mt5_startup():
                self.logger.error("❌ MT5起動失敗")
                return False
            
            # 少し待機（MT5完全起動まで）
            self.logger.info("MT5完全起動待機中...")
            time.sleep(10)
            
            # 3. EA稼働確認
            if self.monitor_ea_status():
                self.logger.info("✅ MT5自動起動完了 - EA稼働中")
                
                # 最終状態確認
                final_status = self.get_system_status()
                self.logger.info(f"最終状態: {final_status}")
                return True
            else:
                self.logger.warning("⚠️ MT5は起動したがEA稼働未確認")
                return False
                
        except Exception as e:
            self.logger.error(f"起動シーケンスエラー: {e}", exc_info=True)
            return False
        finally:
            self.logger.info("=== 起動シーケンス完了 ===")
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if hasattr(self, 'connection'):
            self.connection.disconnect_rpyc()


def main():
    """メイン処理"""
    system = None
    
    try:
        # システム初期化
        system = MT5AutoStartSystem()
        
        # 起動シーケンス実行
        success = system.run_startup_sequence()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"システムエラー: {e}")
        return 1
    finally:
        if system:
            system.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)