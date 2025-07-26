#!/usr/bin/env python3
"""
MT5 Git自動コミットスクリプト
既存のcron自動化システムに統合
"""

import datetime
import os
import subprocess

# MT5データパス（Windows用）
MT5_DATA_PATH = "D:\\MT4DATA\\MT5 OANDA"


def run_git_command(command, cwd=None):
    """Git コマンド実行"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or MT5_DATA_PATH,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_mt5_changes():
    """MT5フォルダの変更チェック"""
    if not os.path.exists(MT5_DATA_PATH):
        return False, "MT5データフォルダが見つかりません"

    # Git status確認
    success, stdout, stderr = run_git_command("git status --porcelain")
    if not success:
        return False, f"Git status失敗: {stderr}"

    has_changes = len(stdout.strip()) > 0
    return has_changes, stdout


def auto_commit_mt5():
    """MT5の変更を自動コミット"""
    has_changes, changes = check_mt5_changes()

    if not has_changes:
        print("MT5: 変更なし")
        return True

    print(f"MT5: 変更検出\n{changes}")

    # 自動追加・コミット
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    commands = ["git add .", f'git commit -m "auto: MT5自動更新 - {timestamp}"']

    for cmd in commands:
        success, stdout, stderr = run_git_command(cmd)
        if not success:
            print(f"エラー: {cmd}")
            print(f"STDERR: {stderr}")
            return False
        print(f"成功: {cmd}")

    return True


def main():
    """メイン処理"""
    print(f"MT5 Git自動更新開始: {datetime.datetime.now()}")

    try:
        success = auto_commit_mt5()
        if success:
            print("MT5 Git自動更新完了")
        else:
            print("MT5 Git自動更新失敗")
    except Exception as e:
        print(f"予期しないエラー: {e}")


if __name__ == "__main__":
    main()
