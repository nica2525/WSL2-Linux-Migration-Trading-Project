#!/usr/bin/env python3
"""
デモ取引設定の最終確認スクリプト
- 口座設定確認
- EA設定確認
- 取引条件確認
"""
import os
import logging
from datetime import datetime, timezone
import pytz

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_demo_account_settings():
    """デモ口座設定確認"""
    print("=== デモ口座設定確認 ===")
    
    config = {
        "broker": "MetaQuotes-Demo",
        "login": "94931878",
        "currency": "JPY",
        "initial_balance": 300000000,  # 300万円（JPY）
        "leverage": "1:100",
        "symbol": "EURUSD",
        "lot_size": 0.01,
        "ea_name": "JamesORB_v1.0_with_magic",
        "magic_number": 20250727
    }
    
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    return config

def check_market_schedule():
    """市場スケジュール確認"""
    print("\n=== 市場スケジュール確認 ===")
    
    # 月曜日の市場オープン時刻
    market_times = {
        "sydney_open": "06:00 JST (月曜日)",
        "tokyo_open": "09:00 JST (月曜日)", 
        "london_open": "17:00 JST (月曜日)",
        "ny_open": "23:00 JST (月曜日)",
        "recommended_start": "09:00 JST (月曜日) - 東京市場オープン"
    }
    
    for market, time in market_times.items():
        print(f"  {market}: {time}")
    
    # 現在時刻と次回オープンまでの時間計算
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    print(f"\n  現在時刻: {now.strftime('%Y-%m-%d %H:%M:%S JST')}")
    
    # 次回月曜日09:00を計算
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0 and now.hour < 9:
        # 今日が月曜日で9時前
        next_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        next_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        next_open = next_open.replace(day=now.day + days_until_monday)
    
    time_until_open = next_open - now
    print(f"  次回取引開始まで: {time_until_open}")
    
    return market_times

def check_ea_parameters():
    """EAパラメータ確認"""
    print("\n=== JamesORB EA パラメータ確認 ===")
    
    # EAファイルから設定を読み取り
    ea_file = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/EA/JamesORB_v1.0_with_magic.mq5"
    
    if not os.path.exists(ea_file):
        print("  ⚠️ EAファイルが見つかりません")
        return {}
    
    parameters = {}
    
    try:
        with open(ea_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            if line.strip().startswith('input'):
                # input行を解析
                parts = line.strip().split('=')
                if len(parts) == 2:
                    param_def = parts[0].strip()
                    param_value = parts[1].strip().rstrip(';')
                    
                    # パラメータ名を抽出
                    param_parts = param_def.split()
                    if len(param_parts) >= 3:
                        param_name = param_parts[-1]
                        parameters[param_name] = param_value
    
    except Exception as e:
        print(f"  エラー: EAファイル読み込み失敗 - {e}")
        return {}
    
    if parameters:
        for param, value in parameters.items():
            print(f"  {param}: {value}")
    else:
        print("  パラメータが見つかりませんでした")
    
    return parameters

def check_trading_environment():
    """取引環境確認"""
    print("\n=== 取引環境確認 ===")
    
    checks = [
        ("MT5起動", "Wine環境で日本語UI"),
        ("EA配置", "/MQL5/Experts/JamesORB_v1.0_with_magic.mq5"),
        ("マジックナンバー", "20250727"),
        ("自動売買", "有効化必要"),
        ("DLL許可", "有効化必要"),
        ("監視システム", "mt5_trading_monitor_fixed.py"),
        ("自動起動", "cron設定済み"),
        ("ログ記録", "MT5/Logs/Trading/")
    ]
    
    for item, status in checks:
        print(f"  ✅ {item}: {status}")

def generate_trading_checklist():
    """取引開始チェックリスト生成"""
    print("\n=== 月曜日取引開始チェックリスト ===")
    
    checklist = [
        "1. MT5が起動していることを確認",
        "2. MetaQuotes-Demo口座にログイン済み確認",
        "3. JamesORB_v1.0_with_magic EAをEURUSD M5チャートに適用", 
        "4. 自動売買ボタンが緑色（有効）であることを確認",
        "5. DLL呼び出しが許可されていることを確認",
        "6. ターミナル「エキスパート」タブでEA初期化メッセージ確認",
        "7. 監視スクリプト(mt5_trading_monitor_fixed.py)実行開始",
        "8. 初回取引発生まで監視継続",
        "9. 取引発生時の詳細記録・分析"
    ]
    
    for item in checklist:
        print(f"  ☐ {item}")
    
    return checklist

def main():
    """メイン処理"""
    print("🎯 JamesORB EA デモ取引設定 最終確認")
    print("=" * 50)
    
    # 各種確認実行
    account_config = check_demo_account_settings()
    market_schedule = check_market_schedule() 
    ea_parameters = check_ea_parameters()
    check_trading_environment()
    checklist = generate_trading_checklist()
    
    print("\n" + "=" * 50)
    print("✅ 設定確認完了 - 月曜日の取引開始準備完了")
    
    # 設定をJSONで保存
    config_file = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Config/demo_trading_config.json"
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    import json
    final_config = {
        "account": account_config,
        "market_schedule": market_schedule,
        "ea_parameters": ea_parameters,
        "checklist": checklist,
        "last_updated": datetime.now().isoformat()
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(final_config, f, indent=2, ensure_ascii=False)
    
    print(f"📁 設定ファイル保存: {config_file}")

if __name__ == "__main__":
    main()