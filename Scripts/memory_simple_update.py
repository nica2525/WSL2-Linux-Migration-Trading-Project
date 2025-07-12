#!/usr/bin/env python3
"""
記憶追跡 - シンプル版（systemd/cron用）
デーモン機能除去、単一実行専用
"""

import os
import subprocess
import logging
from datetime import datetime

def setup_logging(project_dir):
    """ログ設定"""
    log_file = os.path.join(project_dir, '.memory_simple.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def get_current_git_commit_id(project_dir):
    """現在のGitコミットID取得"""
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                              capture_output=True, text=True, check=True,
                              cwd=project_dir, timeout=30)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown"

def get_memory_update_count(history_file):
    """記憶更新回数取得"""
    try:
        if not os.path.exists(history_file):
            return 0
        with open(history_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # systemd/cron実行回数をカウント
        return content.count("systemd記憶追跡実行") + content.count("cron記憶追跡実行")
    except Exception:
        return 0

def get_git_auto_save_pid(project_dir):
    """Git自動保存PID取得"""
    try:
        pid_file = os.path.join(project_dir, ".auto_git.pid")
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                return f.read().strip()
        return "systemd/cron"
    except Exception:
        return "不明"

def log_memory_update(project_dir, execution_type="systemd"):
    """記憶更新ログ記録"""
    history_file = os.path.join(project_dir, "docs", "MEMORY_EXECUTION_HISTORY.md")
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')
    
    # 更新回数取得
    update_count = get_memory_update_count(history_file) + 1
    
    # 情報収集
    git_commit_id = get_current_git_commit_id(project_dir)
    memory_pid = os.getpid()
    git_pid = get_git_auto_save_pid(project_dir)
    
    # ログエントリ作成
    log_entry = f"{current_time} - 第{update_count}回目{execution_type}記憶追跡実行 [Git:{git_commit_id}] [実行PID:{memory_pid}] [GitPID:{git_pid}]\n"
    
    try:
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        log_msg = f"記憶追跡#{update_count}実行完了 ({execution_type})"
        print(log_msg)
        logging.info(log_msg)
        print(f"Git状況: {git_commit_id} | 実行PID: {memory_pid} | GitPID: {git_pid}")
        
        return True
    except Exception as e:
        error_msg = f"記憶追跡エラー: {e}"
        print(error_msg)
        logging.error(error_msg)
        return False

def main():
    # プロジェクトディレクトリ決定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    setup_logging(project_dir)
    
    try:
        # 実行方式判定
        execution_type = "systemd" if "systemd" in os.environ.get('INVOCATION_ID', '') else "cron"
        log_memory_update(project_dir, execution_type)
    except Exception as e:
        logging.error(f"予期しないエラー: {e}")
        print(f"エラー: {e}")

if __name__ == "__main__":
    main()