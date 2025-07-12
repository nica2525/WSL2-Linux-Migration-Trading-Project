#!/usr/bin/env python3
"""
完全自動Git保存システム
料金発生ゼロ・3分間隔・バックグラウンド実行
"""

import os
import time
import subprocess
import argparse
from datetime import datetime

class AutoGitCommit:
    def __init__(self, project_dir, interval=180):
        self.project_dir = project_dir
        self.interval = interval
        self.monitor_extensions = [
            '.py', '.mq4', '.mq5', '.md', '.json', '.txt', '.csv',
            '.yaml', '.yml', '.sh', '.bat', '.sql', '.xml'
        ]
    
    def has_changes(self):
        """変更の有無確認"""
        try:
            os.chdir(self.project_dir)
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, check=True)
            return len(result.stdout.strip()) > 0
        except subprocess.CalledProcessError:
            return False
    
    def commit_changes(self):
        """変更をコミット"""
        try:
            os.chdir(self.project_dir)
            
            # ステージング
            subprocess.run(['git', 'add', '.'], check=True)
            
            # コミット（日本時間明記）
            commit_msg = f"自動保存 - {datetime.now().strftime('%Y-%m-%d %H:%M JST')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            print(f"[{datetime.now()}] 自動保存完了: {commit_msg}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[{datetime.now()}] 自動保存エラー: {e}")
            return False
    
    def run_daemon(self):
        """デーモンモード実行"""
        print(f"[{datetime.now()}] 自動Git保存デーモン開始")
        print(f"監視対象: {self.project_dir}")
        print(f"実行間隔: {self.interval}秒")
        
        while True:
            try:
                if self.has_changes():
                    print(f"[{datetime.now()}] 変更検出 - 自動保存実行中...")
                    self.commit_changes()
                else:
                    print(f"[{datetime.now()}] 変更なし")
                
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                print(f"[{datetime.now()}] 自動Git保存停止")
                break
            except Exception as e:
                print(f"[{datetime.now()}] 予期しないエラー: {e}")
                time.sleep(self.interval)

def main():
    parser = argparse.ArgumentParser(description='自動Git保存システム')
    parser.add_argument('--daemon', action='store_true', help='デーモンモードで実行')
    parser.add_argument('--interval', type=int, default=180, help='実行間隔（秒）')
    parser.add_argument('--project-dir', default=None, help='プロジェクトディレクトリ')
    
    args = parser.parse_args()
    
    # プロジェクトディレクトリ決定
    if args.project_dir:
        project_dir = args.project_dir
    else:
        # スクリプトの親ディレクトリを使用
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
    
    auto_git = AutoGitCommit(project_dir, args.interval)
    
    if args.daemon:
        auto_git.run_daemon()
    else:
        # 1回実行
        if auto_git.has_changes():
            auto_git.commit_changes()
        else:
            print("変更なし")

if __name__ == "__main__":
    main()