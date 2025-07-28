"""
MT5 Direct Data Reader - ファイル直接読み取り方式
MT5から直接データを読み取る実装（Wine環境対応）
"""

import os
import json
import glob
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5DirectReader:
    """MT5データ直接読み取りクラス"""
    
    def __init__(self):
        self.wine_prefix = os.path.expanduser("~/.wine")
        self.mt5_data_paths = self._find_mt5_data_paths()
        
    def _find_mt5_data_paths(self) -> List[str]:
        """MT5データディレクトリの検索"""
        possible_paths = [
            # MT5標準データディレクトリ
            f"{self.wine_prefix}/drive_c/Program Files/MetaTrader 5/",
            # ユーザーデータディレクトリ
            f"{self.wine_prefix}/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/",
            # 共通ファイルディレクトリ
            f"{self.wine_prefix}/drive_c/ProgramData/MetaQuotes/Terminal/",
        ]
        
        found_paths = []
        for path in possible_paths:
            if os.path.exists(path):
                found_paths.append(path)
                logger.info(f"MT5データパス発見: {path}")
        
        return found_paths
    
    def read_account_info_from_logs(self) -> Optional[Dict]:
        """ログファイルから口座情報を読み取り"""
        try:
            # MT5ログディレクトリ
            log_dirs = [
                f"{self.wine_prefix}/drive_c/Program Files/MetaTrader 5/logs/",
                f"{self.wine_prefix}/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/*/logs/",
            ]
            
            for log_pattern in log_dirs:
                log_paths = glob.glob(log_pattern)
                
                for log_dir in log_paths:
                    if os.path.exists(log_dir):
                        # 最新のログファイルを取得
                        log_files = glob.glob(f"{log_dir}/*.log")
                        if log_files:
                            latest_log = max(log_files, key=os.path.getmtime)
                            account_data = self._parse_log_file(latest_log)
                            if account_data:
                                return account_data
            
            return None
            
        except Exception as e:
            logger.error(f"ログからの口座情報読み取りエラー: {e}")
            return None
    
    def _parse_log_file(self, log_file_path: str) -> Optional[Dict]:
        """ログファイルから口座情報を解析"""
        try:
            account_info = {}
            
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 口座情報の抽出（ログから特定のパターンを検索）
                import re
                
                # 残高情報の抽出
                balance_match = re.search(r'balance:\s*([\d.]+)', content, re.IGNORECASE)
                if balance_match:
                    account_info['balance'] = float(balance_match.group(1))
                
                # 有効証拠金の抽出
                equity_match = re.search(r'equity:\s*([\d.]+)', content, re.IGNORECASE)
                if equity_match:
                    account_info['equity'] = float(equity_match.group(1))
                
                # 証拠金の抽出
                margin_match = re.search(r'margin:\s*([\d.]+)', content, re.IGNORECASE)
                if margin_match:
                    account_info['margin'] = float(margin_match.group(1))
                
                # サーバー情報
                server_match = re.search(r'server:\s*([^\s]+)', content, re.IGNORECASE)
                if server_match:
                    account_info['server'] = server_match.group(1)
                
                # ログイン情報
                login_match = re.search(r'login:\s*(\d+)', content, re.IGNORECASE)
                if login_match:
                    account_info['login'] = int(login_match.group(1))
                
                if account_info:
                    account_info['timestamp'] = datetime.now().isoformat()
                    account_info['source'] = 'log_file'
                    return account_info
            
            return None
            
        except Exception as e:
            logger.error(f"ログファイル解析エラー: {e}")
            return None
    
    def read_positions_from_history(self) -> List[Dict]:
        """履歴ファイルからポジション情報を読み取り"""
        try:
            positions = []
            
            # 履歴ファイルの検索
            history_patterns = [
                f"{self.wine_prefix}/drive_c/Program Files/MetaTrader 5/profiles/*/history.dat",
                f"{self.wine_prefix}/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/*/profiles/*/history.dat",
            ]
            
            for pattern in history_patterns:
                history_files = glob.glob(pattern)
                
                for history_file in history_files:
                    if os.path.exists(history_file):
                        # バイナリファイルの読み取り（基本的な構造解析）
                        position_data = self._parse_history_file(history_file)
                        if position_data:
                            positions.extend(position_data)
            
            return positions
            
        except Exception as e:
            logger.error(f"履歴からのポジション読み取りエラー: {e}")
            return []
    
    def _parse_history_file(self, history_file_path: str) -> List[Dict]:
        """履歴ファイルからポジションデータを解析"""
        try:
            positions = []
            
            # 注意: MT5履歴ファイルは複雑なバイナリ形式
            # ここでは基本的な読み取りのみ実装
            with open(history_file_path, 'rb') as f:
                data = f.read()
                
                # 基本的なデータ解析（実際のフォーマットは複雑）
                if len(data) > 0:
                    logger.info(f"履歴ファイル読み取り: {len(data)} bytes")
                    
                    # 簡易的なポジション情報生成（実際のデータ解析は複雑）
                    positions.append({
                        'source': 'history_file',
                        'file_size': len(data),
                        'last_modified': datetime.fromtimestamp(os.path.getmtime(history_file_path)).isoformat()
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"履歴ファイル解析エラー: {e}")
            return []
    
    def get_real_account_data(self) -> Dict:
        """実際の口座データ取得"""
        try:
            # 複数の方法で口座データを取得
            account_data = {}
            
            # 方法1: ログファイルから読み取り
            log_data = self.read_account_info_from_logs()
            if log_data:
                account_data.update(log_data)
            
            # 方法2: 設定ファイルから読み取り
            config_data = self._read_config_files()
            if config_data:
                account_data.update(config_data)
            
            # 方法3: 一時ファイルから読み取り（スクリプト出力）
            temp_data = self._read_temp_files()
            if temp_data:
                account_data.update(temp_data)
            
            if account_data:
                account_data['retrieval_time'] = datetime.now().isoformat()
                account_data['data_sources'] = list(account_data.keys())
                
            return account_data
            
        except Exception as e:
            logger.error(f"実口座データ取得エラー: {e}")
            return {}
    
    def _read_config_files(self) -> Optional[Dict]:
        """設定ファイルから情報を読み取り"""
        try:
            config_data = {}
            
            # MT5設定ファイルの検索
            config_patterns = [
                f"{self.wine_prefix}/drive_c/Program Files/MetaTrader 5/config/*.ini",
                f"{self.wine_prefix}/drive_c/users/trader/AppData/Roaming/MetaQuotes/Terminal/*/config.dat",
            ]
            
            for pattern in config_patterns:
                config_files = glob.glob(pattern)
                
                for config_file in config_files:
                    if os.path.exists(config_file):
                        # 設定ファイルの解析
                        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # 設定値の抽出
                            if 'server' in content.lower():
                                config_data['config_found'] = True
                                config_data['config_file'] = config_file
            
            return config_data if config_data else None
            
        except Exception as e:
            logger.error(f"設定ファイル読み取りエラー: {e}")
            return None
    
    def _read_temp_files(self) -> Optional[Dict]:
        """一時ファイル（スクリプト出力）から読み取り"""
        try:
            temp_file = f"{self.wine_prefix}/drive_c/temp/account_info.json"
            
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    temp_data = json.load(f)
                    temp_data['source'] = 'temp_file'
                    return temp_data
            
            return None
            
        except Exception as e:
            logger.error(f"一時ファイル読み取りエラー: {e}")
            return None

# 実際のMT5データ取得関数
def get_real_mt5_data() -> Dict:
    """実際のMT5データを取得"""
    reader = MT5DirectReader()
    return reader.get_real_account_data()

# テスト実行
if __name__ == "__main__":
    print("MT5直接データ読み取りテスト")
    data = get_real_mt5_data()
    if data:
        print("✅ データ取得成功:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    else:
        print("❌ データ取得失敗")