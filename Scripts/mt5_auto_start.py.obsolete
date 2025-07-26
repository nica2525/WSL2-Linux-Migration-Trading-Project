#!/usr/bin/env python3
"""
MT5自動起動・EA適用スクリプト
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

# ログ設定
LOG_DIR = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'mt5_auto_start.log')),
        logging.StreamHandler()
    ]
)

# 設定
MT5_PATH = "/home/trader/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
PROFILE_PATH = "/home/trader/.wine/drive_c/Program Files/MetaTrader 5/profiles/default"
EA_CONFIG = {
    "name": "JamesORB_v1.0",
    "symbol": "EURUSD",
    "timeframe": "M5",
    "lot_size": 0.01
}

def check_mt5_running():
    """MT5が起動しているかチェック"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'terminal64.exe' in str(proc.info['cmdline']):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False, None

def start_mt5():
    """MT5を起動"""
    logging.info("MT5を起動します...")
    
    # 環境変数設定
    env = os.environ.copy()
    env['LANG'] = 'ja_JP.UTF-8'
    env['LC_ALL'] = 'ja_JP.UTF-8'
    env['WINEDEBUG'] = '-all'
    
    # ホームディレクトリから起動（日本語パス問題回避）
    os.chdir(os.path.expanduser("~"))
    
    try:
        # MT5起動コマンド
        cmd = ['wine', MT5_PATH, '/auto']
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 起動待機
        time.sleep(10)
        
        # 起動確認
        running, pid = check_mt5_running()
        if running:
            logging.info(f"MT5起動成功 (PID: {pid})")
            return True
        else:
            logging.error("MT5起動失敗")
            return False
            
    except Exception as e:
        logging.error(f"MT5起動エラー: {e}")
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
    
    startup_file = os.path.join(PROFILE_PATH, "startup.ini")
    os.makedirs(os.path.dirname(startup_file), exist_ok=True)
    
    with open(startup_file, 'w') as f:
        f.write(ini_content)
    
    logging.info(f"起動設定ファイル作成: {startup_file}")

def monitor_ea_status():
    """EA稼働状態を監視"""
    log_path = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/Logs/")
    
    # 最新ログファイルを取得
    try:
        logs = [f for f in os.listdir(log_path) if f.endswith('.log')]
        if not logs:
            logging.warning("ログファイルが見つかりません")
            return False
            
        latest_log = max(logs, key=lambda x: os.path.getmtime(os.path.join(log_path, x)))
        log_file = os.path.join(log_path, latest_log)
        
        # ログ内容確認
        with open(log_file, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
            
        if EA_CONFIG['name'] in content:
            logging.info("EA稼働確認済み")
            return True
        else:
            logging.warning("EAの稼働が確認できません")
            return False
            
    except Exception as e:
        logging.error(f"ログ確認エラー: {e}")
        return False

def main():
    """メイン処理"""
    logging.info("=== MT5自動起動システム開始 ===")
    
    # 1. 既存プロセスチェック
    running, pid = check_mt5_running()
    if running:
        logging.info(f"MT5は既に起動中です (PID: {pid})")
        return
    
    # 2. 起動設定作成
    create_startup_ini()
    
    # 3. MT5起動
    if start_mt5():
        # 4. EA稼働確認（30秒待機）
        time.sleep(30)
        if monitor_ea_status():
            logging.info("✅ MT5自動起動完了 - EA稼働中")
        else:
            logging.warning("⚠️ MT5は起動したがEA稼働未確認")
    else:
        logging.error("❌ MT5起動失敗")
        
    logging.info("=== 処理完了 ===")

if __name__ == "__main__":
    main()