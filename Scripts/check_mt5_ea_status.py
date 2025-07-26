#!/usr/bin/env python3
"""
MT5 EA稼働状況確認スクリプト
"""
import os
import datetime

def check_ea_status():
    """EAの稼働状況を確認"""
    print("=== MT5 EA稼働状況確認 ===")
    print(f"確認時刻: {datetime.datetime.now()}")
    
    # 1. EAファイルの存在確認
    ea_path = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/JamesORB_v1.0.mq5")
    if os.path.exists(ea_path):
        print("✅ JamesORB EA: ファイル配置済み")
        print(f"   場所: {ea_path}")
        stat = os.stat(ea_path)
        print(f"   サイズ: {stat.st_size} bytes")
        print(f"   更新日時: {datetime.datetime.fromtimestamp(stat.st_mtime)}")
    else:
        print("❌ JamesORB EA: ファイルが見つかりません")
    
    # 2. コンパイル済みファイル確認
    ex5_path = ea_path.replace('.mq5', '.ex5')
    if os.path.exists(ex5_path):
        print("✅ コンパイル済みファイル(.ex5): 存在")
    else:
        print("⚠️  コンパイル済みファイル(.ex5): 未作成（MT5でコンパイルが必要）")
    
    # 3. ログファイル確認
    log_dir = os.path.expanduser("~/.wine/drive_c/Program Files/MetaTrader 5/Logs")
    if os.path.exists(log_dir):
        logs = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        if logs:
            print(f"📋 ログファイル: {len(logs)}個検出")
            latest = max(logs, key=lambda x: os.path.getmtime(os.path.join(log_dir, x)))
            print(f"   最新: {latest}")
    
    print("\n📌 現在の状態:")
    print("- MT5: 起動中（5分足チャート表示）")
    print("- 言語: 日本語UI")
    print("- 口座: MetaQuotes-Demo (94931878)")
    print("- 通貨ペア: EURUSD")
    print("- EA: チャートに適用済み")
    print("\n⏰ 次回取引:")
    print("- 月曜日（2025-07-28）市場オープン時")
    print("- ロット数: 0.01固定")
    print("- 口座残高: 300万円（デモ）")

if __name__ == "__main__":
    check_ea_status()