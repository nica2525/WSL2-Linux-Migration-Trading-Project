#!/usr/bin/env python3
"""
時間ベース記憶追跡システム
30分間隔で自動実行・Git自動保存と並行稼働
"""

import os
import time
import subprocess
from datetime import datetime, timedelta

class TimeBasedMemoryTracker:
    def __init__(self, project_dir, interval_minutes=30):
        self.project_dir = project_dir
        self.interval_seconds = interval_minutes * 60
        self.history_file = os.path.join(project_dir, "docs", "MEMORY_EXECUTION_HISTORY.md")
        self.pid_file = os.path.join(project_dir, ".memory_tracker.pid")
        
    def log_memory_update(self, reason="定期実行"):
        """記憶更新をログ記録"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')
        log_entry = f"{current_time} - 時間ベース記憶追跡実行 ({reason})\n"
        
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print(f"🧠 [記憶追跡] {current_time} - {reason}")
            print("📋 必須確認: CLAUDE_UNIFIED_SYSTEM.md → 統合情報読み込み")
            return True
        except Exception as e:
            print(f"❌ ログ記録エラー: {e}")
            return False
    
    def should_trigger_memory_update(self):
        """記憶更新が必要かチェック"""
        try:
            # 最後の更新時刻を取得
            if not os.path.exists(self.history_file):
                return True, "初回実行"
                
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 最新の時間ベース記録を探す
            last_time_based = None
            for line in reversed(lines):
                if "時間ベース記憶追跡実行" in line:
                    # 2025-07-13 07:45:30 JST 形式から時刻抽出
                    time_str = line.split(' - ')[0]
                    last_time_based = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S JST')
                    break
            
            if last_time_based is None:
                return True, "時間ベース初回実行"
            
            # 30分経過チェック
            now = datetime.now()
            elapsed = now - last_time_based
            if elapsed.total_seconds() >= self.interval_seconds:
                return True, f"30分経過 (前回: {last_time_based.strftime('%H:%M')})"
            
            return False, f"待機中 (次回: {(last_time_based + timedelta(seconds=self.interval_seconds)).strftime('%H:%M')})"
            
        except Exception as e:
            print(f"⚠️ 時刻チェックエラー: {e}")
            return True, "エラー回復実行"
    
    def run_daemon(self):
        """デーモンモード実行"""
        print(f"[{datetime.now()}] 時間ベース記憶追跡デーモン開始")
        print(f"監視対象: {self.project_dir}")
        print(f"実行間隔: {self.interval_seconds // 60}分")
        
        # 起動時に即座にチェック
        should_trigger, reason = self.should_trigger_memory_update()
        if should_trigger:
            self.log_memory_update(reason)
        else:
            print(f"📊 {reason}")
        
        while True:
            try:
                should_trigger, reason = self.should_trigger_memory_update()
                if should_trigger:
                    self.log_memory_update(reason)
                else:
                    print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] {reason}")
                
                # 5分毎にチェック（30分間隔での実行判定）
                time.sleep(300)  # 5分
                
            except KeyboardInterrupt:
                print(f"[{datetime.now()}] 時間ベース記憶追跡停止")
                break
            except Exception as e:
                print(f"[{datetime.now()}] 予期しないエラー: {e}")
                time.sleep(300)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='時間ベース記憶追跡システム')
    parser.add_argument('--daemon', action='store_true', help='デーモンモードで実行')
    parser.add_argument('--interval', type=int, default=30, help='実行間隔（分）')
    parser.add_argument('--project-dir', default=None, help='プロジェクトディレクトリ')
    
    args = parser.parse_args()
    
    # プロジェクトディレクトリ決定
    if args.project_dir:
        project_dir = args.project_dir
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
    
    tracker = TimeBasedMemoryTracker(project_dir, args.interval)
    
    if args.daemon:
        tracker.run_daemon()
    else:
        # 1回実行
        should_trigger, reason = tracker.should_trigger_memory_update()
        if should_trigger:
            tracker.log_memory_update(reason)
        else:
            print(f"📊 {reason}")

if __name__ == "__main__":
    main()