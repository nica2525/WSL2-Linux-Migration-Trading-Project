#!/usr/bin/env python3
"""
MT5自動起動・EA適用スクリプト（改善版）
- Wine環境でMT5を起動
- JamesORB EAの稼働確認
- エラー時の自動復旧
"""
import os
import subprocess
import time
import psutil
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ログ設定
LOG_DIR = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ログローテーション設定（5MB x 5ファイル）
log_file_path = os.path.join(LOG_DIR, 'mt5_auto_start.log')
file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 設定
MT5_PATH = "/home/trader/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
PROFILE_PATH = "/home/trader/.wine/drive_c/Program Files/MetaTrader 5/profiles/default"
EA_CONFIG = {
    "name": "JamesORB_v1.0",
    "symbol": "EURUSD",
    "timeframe": "M5",
    "lot_size": 0.01
}

# タイムアウト設定
MT5_START_TIMEOUT = 30  # MT5起動のタイムアウト（秒）
EA_LOAD_TIMEOUT = 60    # EA読み込みのタイムアウト（秒）

def check_mt5_running():
    """MT5が起動しているかチェック"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            if proc.info['name'] and 'terminal64.exe' in proc.info['name'].lower():
                return True, proc.info['pid']
    except Exception as e:
        logger.error(f"プロセスチェックエラー: {e}")
    return False, None

def wait_for_mt5_start(timeout=MT5_START_TIMEOUT):
    """MT5の起動を待つ（タイムアウト付き）"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        running, pid = check_mt5_running()
        if running:
            logger.info(f"MT5起動確認 (PID: {pid})")
            return True
        time.sleep(2)  # 2秒おきにチェック
    return False

def start_mt5():
    """MT5を起動"""
    logger.info("MT5を起動します...")
    
    # 環境変数設定
    env = os.environ.copy()
    env['LANG'] = 'ja_JP.UTF-8'
    env['LC_ALL'] = 'ja_JP.UTF-8'
    env['WINEDEBUG'] = '-all'
    
    try:
        # MT5起動コマンド（出力を破棄してハングアップを防ぐ）
        cmd = ['wine', MT5_PATH, '/auto']
        proc = subprocess.Popen(
            cmd, 
            env=env, 
            cwd=os.path.expanduser("~"),  # cwdで作業ディレクトリ指定
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # 起動待機
        if wait_for_mt5_start():
            logger.info("MT5起動成功")
            return True
        else:
            logger.error(f"MT5起動タイムアウト（{MT5_START_TIMEOUT}秒）")
            # タイムアウトした場合、プロセスを終了
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
            return False
            
    except Exception as e:
        logger.error(f"MT5起動エラー: {e}")
        return False

def create_startup_ini():
    """MT5自動起動設定ファイル作成"""
    ini_content = f"""[Common]
AutoTrade=1
NewsEnable=0

[Experts]
AllowLiveTrading=1
AllowDllImport=0
Enabled=1
Account=94931878
Profile=Default

[Charts]
ProfileLast=Default
MaxBars=50000

[StartUp]
Expert={EA_CONFIG['name']}
Symbol={EA_CONFIG['symbol']}
Period={EA_CONFIG['timeframe']}
"""
    
    try:
        startup_file = os.path.join(PROFILE_PATH, "startup.ini")
        os.makedirs(os.path.dirname(startup_file), exist_ok=True)
        
        with open(startup_file, 'w', encoding='utf-8') as f:
            f.write(ini_content)
        
        logger.info(f"起動設定ファイル作成: {startup_file}")
        return True
    except Exception as e:
        logger.error(f"起動設定ファイル作成エラー: {e}")
        return False

def read_log_file(log_file):
    """ログファイルを複数のエンコーディングで読み込み"""
    encodings = ['utf-16-le', 'utf-8-sig', 'utf-8', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(log_file, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
        except Exception:
            continue
    
    # すべて失敗した場合
    logger.warning(f"ログファイル読み込み失敗: {log_file}")
    return ""

def monitor_ea_status(timeout=EA_LOAD_TIMEOUT):
    """EA稼働状態を監視（タイムアウト付き）"""
    log_path = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Logs/")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # ログディレクトリの存在確認
            if not os.path.exists(log_path):
                logger.warning(f"ログディレクトリが存在しません: {log_path}")
                time.sleep(5)
                continue
            
            # 最新ログファイルを取得
            logs = [f for f in os.listdir(log_path) if f.endswith('.log')]
            if not logs:
                logger.warning("ログファイルが見つかりません")
                time.sleep(5)
                continue
                
            latest_log = max(logs, key=lambda x: os.path.getmtime(os.path.join(log_path, x)))
            log_file = os.path.join(log_path, latest_log)
            
            # ログ内容確認
            content = read_log_file(log_file)
            
            # EA初期化成功のパターンをチェック
            success_patterns = [
                f"{EA_CONFIG['name']} loaded successfully",
                f"Expert {EA_CONFIG['name']} loaded",
                f"{EA_CONFIG['name']}' initialized",
                "initialization finished"
            ]
            
            for pattern in success_patterns:
                if pattern.lower() in content.lower():
                    logger.info(f"EA稼働確認済み: {pattern}")
                    return True
            
            # エラーパターンのチェック
            if f"failed to load expert '{EA_CONFIG['name']}'" in content.lower():
                logger.error("EAの読み込みに失敗しました")
                return False
                
        except Exception as e:
            logger.error(f"ログ確認エラー: {e}")
        
        time.sleep(5)  # 5秒おきにチェック
    
    logger.warning(f"EA稼働確認タイムアウト（{timeout}秒）")
    return False

def main():
    """メイン処理"""
    logger.info("=== MT5自動起動システム開始 ===")
    
    try:
        # 1. 既存プロセスチェック
        running, pid = check_mt5_running()
        if running:
            logger.info(f"MT5は既に起動中です (PID: {pid})")
            # 既に起動している場合もEA状態を確認
            if monitor_ea_status(timeout=30):
                logger.info("✅ EA稼働確認済み")
            return
        
        # 2. 起動設定作成
        if not create_startup_ini():
            logger.error("起動設定ファイルの作成に失敗しました")
            return
        
        # 3. MT5起動
        if start_mt5():
            # 4. EA稼働確認
            if monitor_ea_status():
                logger.info("✅ MT5自動起動完了 - EA稼働中")
            else:
                logger.warning("⚠️ MT5は起動したがEA稼働未確認")
        else:
            logger.error("❌ MT5起動失敗")
            
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
    finally:
        logger.info("=== 処理完了 ===")

if __name__ == "__main__":
    main()