#!/usr/bin/env python3
"""
重要システムファイル整合性チェック
自動Git保存システムの破壊防止
"""

import os
import sys
from pathlib import Path


def check_critical_files():
    """重要ファイルの存在確認"""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    critical_files = [
        "Scripts/auto_git_commit.py",
        "Scripts/start_auto_git.sh",
        "Scripts/auto_git_commit.py.backup",
    ]

    missing_files = []

    for file_path in critical_files:
        full_path = project_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        print("🚨 重要システムファイルが不足しています:")
        for file_path in missing_files:
            print(f"   ❌ {file_path}")

        # バックアップからの復旧試行
        if "Scripts/auto_git_commit.py" in missing_files:
            backup_path = project_dir / "Scripts/auto_git_commit.py.backup"
            target_path = project_dir / "Scripts/auto_git_commit.py"

            if backup_path.exists():
                print("🔧 バックアップからの復旧を試行中...")
                try:
                    import shutil

                    shutil.copy2(backup_path, target_path)
                    os.chmod(target_path, 0o755)
                    print("✅ auto_git_commit.py 復旧完了")
                except Exception as e:
                    print(f"❌ 復旧失敗: {e}")

        return False
    else:
        print("✅ 全ての重要システムファイルが存在します")
        return True


def main():
    """メイン実行"""
    print("🔍 重要システムファイル整合性チェック開始")

    if check_critical_files():
        print("🎯 システム整合性確認完了")
        sys.exit(0)
    else:
        print("⚠️ システム整合性に問題があります")
        sys.exit(1)


if __name__ == "__main__":
    main()
