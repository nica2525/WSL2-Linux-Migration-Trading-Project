"""
MT5 Wine接続システム - Linux環境でのMT5実接続
MetaTrader5パッケージが利用できない環境での代替実装
"""

import subprocess
import json
import os
import time
import logging
import glob
from typing import Dict, List, Optional, Any
from datetime import datetime
import sqlite3

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5WineConnector:
    """Wine経由でのMT5接続管理"""
    
    def __init__(self, wine_path: str = "/usr/bin/wine", mt5_path: str = None):
        self.wine_path = wine_path
        self.mt5_path = mt5_path or self._find_mt5_executable()
        self.is_connected = False
        self.last_error = None
        
    def _find_mt5_executable(self) -> str:
        """MT5実行ファイルの自動検出"""
        possible_paths = [
            "~/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe",
            "~/.wine/drive_c/Program Files (x86)/MetaTrader 5/terminal64.exe",
            "~/.wine/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/*/MQL5/Experts/"
        ]
        
        for path in possible_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                logger.info(f"MT5実行ファイル発見: {expanded_path}")
                return expanded_path
        
        logger.warning("MT5実行ファイルが見つかりません")
        return None
    
    def connect(self, login: str = None, password: str = None, server: str = None) -> bool:
        """MT5への接続"""
        try:
            if not self.mt5_path or not os.path.exists(self.wine_path):
                self.last_error = "Wine環境またはMT5が見つかりません"
                return False
            
            # Wine経由でMT5プロセス確認
            result = subprocess.run(
                ["pgrep", "-f", "terminal64.exe"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("MT5プロセスが既に動作中です")
                self.is_connected = True
                return True
            
            # MT5起動
            if login and password and server:
                cmd = [
                    self.wine_path,
                    self.mt5_path,
                    f"/login:{login}",
                    f"/password:{password}",
                    f"/server:{server}"
                ]
            else:
                cmd = [self.wine_path, self.mt5_path]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 起動待機
            time.sleep(5)
            
            # 接続確認
            if self._verify_connection():
                self.is_connected = True
                logger.info("MT5接続成功")
                return True
            else:
                self.last_error = "MT5接続確認に失敗"
                return False
                
        except Exception as e:
            self.last_error = f"MT5接続エラー: {e}"
            logger.error(self.last_error)
            return False
    
    def _verify_connection(self) -> bool:
        """MT5接続状態の確認"""
        try:
            # MT5プロセス確認
            result = subprocess.run(
                ["pgrep", "-f", "terminal64.exe"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def get_account_info(self) -> Optional[Dict]:
        """口座情報の取得（ファイル経由）"""
        if not self.is_connected:
            return None
        
        try:
            # MT5からエクスポートされたデータファイルを読み込み
            account_file = os.path.expanduser("~/.wine/drive_c/temp/account_info.json")
            
            if os.path.exists(account_file):
                with open(account_file, 'r', encoding='utf-8') as f:
                    account_data = json.load(f)
                return account_data
            else:
                # ファイルが存在しない場合は、MQL5スクリプト経由で生成
                self._request_account_export()
                time.sleep(2)  # エクスポート待機
                
                if os.path.exists(account_file):
                    with open(account_file, 'r', encoding='utf-8') as f:
                        account_data = json.load(f)
                    return account_data
                
        except Exception as e:
            logger.error(f"口座情報取得エラー: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """ポジション情報の取得（ファイル経由）"""
        if not self.is_connected:
            return []
        
        try:
            positions_file = os.path.expanduser("~/.wine/drive_c/temp/positions.json")
            
            if os.path.exists(positions_file):
                with open(positions_file, 'r', encoding='utf-8') as f:
                    positions_data = json.load(f)
                return positions_data.get('positions', [])
            else:
                # MQL5スクリプト経由でポジション情報エクスポート
                self._request_positions_export()
                time.sleep(2)
                
                if os.path.exists(positions_file):
                    with open(positions_file, 'r', encoding='utf-8') as f:
                        positions_data = json.load(f)
                    return positions_data.get('positions', [])
                
            return []
            
        except Exception as e:
            logger.error(f"ポジション情報取得エラー: {e}")
            return []
    
    def _request_account_export(self):
        """MQL5スクリプトで口座情報エクスポート要求"""
        try:
            # MQL5スクリプトファイルパス
            experts_path = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Scripts")
            if not os.path.exists(experts_path):
                experts_path = os.path.expanduser("~/.wine/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/*/MQL5/Scripts")
                # Terminalディレクトリを実際に検索
                terminal_dirs = glob.glob(os.path.expanduser("~/.wine/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/*/MQL5/Scripts"))
                if terminal_dirs:
                    experts_path = terminal_dirs[0]
                else:
                    # フォールバック: tempディレクトリを使用
                    experts_path = os.path.expanduser("~/.wine/drive_c/temp")
                    
            os.makedirs(experts_path, exist_ok=True)
            
            # より実用的なMQL5スクリプト
            script_content = '''//+------------------------------------------------------------------+
//| Account Info Export Script - Real Implementation                  |
//+------------------------------------------------------------------+
void OnStart()
{
    string filename = "C:\\\\temp\\\\account_info.json";
    int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
    
    if(handle != INVALID_HANDLE)
    {
        // 口座情報の完全取得
        double balance = AccountInfoDouble(ACCOUNT_BALANCE);
        double equity = AccountInfoDouble(ACCOUNT_EQUITY);
        double margin = AccountInfoDouble(ACCOUNT_MARGIN);
        double free_margin = AccountInfoDouble(ACCOUNT_FREEMARGIN);
        double margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
        double profit = AccountInfoDouble(ACCOUNT_PROFIT);
        
        // サーバー情報
        string server = AccountInfoString(ACCOUNT_SERVER);
        long login = AccountInfoInteger(ACCOUNT_LOGIN);
        string currency = AccountInfoString(ACCOUNT_CURRENCY);
        
        // JSON形式で出力
        string json = "{";
        json += "\\"login\\":" + IntegerToString(login) + ",";
        json += "\\"server\\":\\"" + server + "\\",";
        json += "\\"currency\\":\\"" + currency + "\\",";
        json += "\\"balance\\":" + DoubleToString(balance, 2) + ",";
        json += "\\"equity\\":" + DoubleToString(equity, 2) + ",";
        json += "\\"margin\\":" + DoubleToString(margin, 2) + ",";
        json += "\\"free_margin\\":" + DoubleToString(free_margin, 2) + ",";
        json += "\\"margin_level\\":" + DoubleToString(margin_level, 2) + ",";
        json += "\\"profit\\":" + DoubleToString(profit, 2) + ",";
        json += "\\"trade_allowed\\":" + (AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) ? "true" : "false") + ",";
        json += "\\"trade_expert\\":" + (AccountInfoInteger(ACCOUNT_TRADE_EXPERT) ? "true" : "false") + ",";
        json += "\\"server_time\\":\\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\\",";
        json += "\\"local_time\\":\\"" + TimeToString(TimeLocal(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\\"";
        json += "}";
        
        FileWrite(handle, json);
        FileClose(handle);
        
        Print("✅ Account info exported to ", filename);
        Print("Balance: ", balance, ", Equity: ", equity);
    }
    else
    {
        Print("❌ Failed to create account export file");
    }
}'''
            
            script_path = os.path.join(experts_path, "AccountExport.mq5")
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            logger.info(f"口座情報エクスポートスクリプトを作成: {script_path}")
            
            # スクリプトコンパイル要求（MQL5コンパイラ経由）
            self._compile_and_run_script("AccountExport")
            
        except Exception as e:
            logger.error(f"口座情報エクスポートスクリプト作成エラー: {e}")
    
    def _compile_and_run_script(self, script_name: str):
        """MQL5スクリプトのコンパイル・実行"""
        try:
            # MetaEditor経由でコンパイル
            metaeditor_path = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/metaeditor64.exe")
            
            if os.path.exists(metaeditor_path):
                # コンパイルコマンド
                compile_cmd = [
                    self.wine_path,
                    metaeditor_path,
                    "/compile",
                    f"Scripts\\{script_name}.mq5"
                ]
                
                logger.info(f"MQL5スクリプトコンパイル開始: {script_name}")
                
                result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ {script_name}コンパイル成功")
                    
                    # 実行要求（MT5ターミナル経由）
                    time.sleep(2)  # コンパイル完了待機
                    self._execute_compiled_script(script_name)
                else:
                    logger.error(f"❌ {script_name}コンパイル失敗: {result.stderr}")
            else:
                logger.warning("MetaEditor not found, script compilation skipped")
                
        except Exception as e:
            logger.error(f"スクリプトコンパイルエラー: {e}")
    
    def _execute_compiled_script(self, script_name: str):
        """コンパイル済みスクリプトの実行"""
        try:
            # MT5ターミナルでスクリプト実行
            # 注意: 実際のMT5では手動実行が必要な場合があります
            logger.info(f"スクリプト {script_name} の実行を要求しました")
            logger.info("MT5ターミナルでScripts/{script_name}を手動実行してください")
            
        except Exception as e:
            logger.error(f"スクリプト実行エラー: {e}")
    
    def _request_positions_export(self):
        """MQL5スクリプトでポジション情報エクスポート要求"""
        try:
            script_content = '''
//+------------------------------------------------------------------+
//| Positions Export Script                                           |
//+------------------------------------------------------------------+
void OnStart()
{
    string filename = "C:\\\\temp\\\\positions.json";
    int handle = FileOpen(filename, FILE_WRITE|FILE_TXT);
    
    if(handle != INVALID_HANDLE)
    {
        string json = "{\\"positions\\":[";
        int total = PositionsTotal();
        
        for(int i = 0; i < total; i++)
        {
            if(PositionSelectByIndex(i))
            {
                if(i > 0) json += ",";
                json += "{";
                json += "\\"ticket\\":" + IntegerToString(PositionGetInteger(POSITION_TICKET)) + ",";
                json += "\\"symbol\\":\\"" + PositionGetString(POSITION_SYMBOL) + "\\",";
                json += "\\"type\\":" + IntegerToString(PositionGetInteger(POSITION_TYPE)) + ",";
                json += "\\"volume\\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + ",";
                json += "\\"price_open\\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 5) + ",";
                json += "\\"price_current\\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_CURRENT), 5) + ",";
                json += "\\"profit\\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2) + ",";
                json += "\\"swap\\":" + DoubleToString(PositionGetDouble(POSITION_SWAP), 2) + ",";
                json += "\\"sl\\":" + DoubleToString(PositionGetDouble(POSITION_SL), 5) + ",";
                json += "\\"tp\\":" + DoubleToString(PositionGetDouble(POSITION_TP), 5);
                json += "}";
            }
        }
        
        json += "]}";
        FileWrite(handle, json);
        FileClose(handle);
        Print("Positions exported to ", filename);
    }
}
'''
            
            script_path = os.path.expanduser("~/.wine/drive_c/temp/positions_export.mq5")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
                
            logger.info("ポジション情報エクスポートスクリプトを作成しました")
            
        except Exception as e:
            logger.error(f"ポジション情報エクスポートスクリプト作成エラー: {e}")
    
    def disconnect(self):
        """MT5との接続切断"""
        try:
            if self.is_connected:
                # MT5プロセス終了
                subprocess.run(["pkill", "-f", "terminal64.exe"], capture_output=True)
                self.is_connected = False
                logger.info("MT5接続を切断しました")
        except Exception as e:
            logger.error(f"MT5切断エラー: {e}")

# 実際のMT5接続に使用するラッパー関数
def create_mt5_connection() -> MT5WineConnector:
    """MT5接続インスタンスの作成"""
    return MT5WineConnector()

# 既存のmt5_mock.pyと互換性を保つためのエイリアス
def initialize(*args, **kwargs) -> bool:
    """MT5初期化（Wine版）"""
    connector = create_mt5_connection()
    return connector.connect()

def account_info():
    """口座情報取得（Wine版）"""
    connector = create_mt5_connection()
    if connector.connect():
        return connector.get_account_info()
    return None

def positions_get():
    """ポジション情報取得（Wine版）"""
    connector = create_mt5_connection()
    if connector.connect():
        return connector.get_positions()
    return []

def shutdown():
    """MT5切断（Wine版）"""
    connector = create_mt5_connection()
    connector.disconnect()