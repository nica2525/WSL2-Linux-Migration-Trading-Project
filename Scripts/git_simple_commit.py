#!/usr/bin/env python3
"""
Git自動保存 - シンプル版（systemd/cron用）
デーモン機能除去、単一実行専用
"""

import logging
import os
import subprocess
from datetime import datetime


def setup_logging(project_dir):
    """ログ設定"""
    log_file = os.path.join(project_dir, ".git_simple.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def has_changes(project_dir):
    """変更の有無確認"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_dir,
            timeout=30,
        )
        return len(result.stdout.strip()) > 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logging.error(f"git status エラー: {e}")
        return False


def commit_changes(project_dir):
    """変更をコミット"""
    try:
        # ステージング
        subprocess.run(["git", "add", "."], check=True, cwd=project_dir, timeout=60)

        # コミット
        commit_msg = f"自動保存 - {datetime.now().strftime('%Y-%m-%d %H:%M JST')}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg], check=True, cwd=project_dir, timeout=60
        )

        log_msg = f"自動保存完了: {commit_msg}"
        print(log_msg)
        logging.info(log_msg)
        return True

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        error_msg = f"自動保存エラー: {e}"
        print(error_msg)
        logging.error(error_msg)
        return False


def main():
    # プロジェクトディレクトリ決定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    setup_logging(project_dir)

    try:
        if has_changes(project_dir):
            commit_changes(project_dir)
        else:
            logging.info("変更なし")
            print("変更なし")
    except Exception as e:
        logging.error(f"予期しないエラー: {e}")
        print(f"エラー: {e}")


if __name__ == "__main__":
    main()
