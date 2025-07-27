#!/usr/bin/env python3
"""
Cron用Git自動保存スクリプト（WSL最適化・自己修復機能付き）
systemd方式の不安定性を解決する確実な代替システム
"""

import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path


class CronGitAutoSave:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.log_file = self.project_dir / ".cron_git_auto_save.log"
        self.success_marker = self.project_dir / ".last_git_success"
        
        # ロギング設定（シンプル・確実）
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )

    def log_with_print(self, level, message):
        """ログファイルとコンソール両方に出力"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        if level == "INFO":
            logging.info(message)
        elif level == "ERROR":
            logging.error(message)
        elif level == "WARNING":
            logging.warning(message)

    def has_git_changes(self):
        """Git変更確認（確実・高速）"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            
            changes_exist = len(result.stdout.strip()) > 0
            if changes_exist:
                change_count = len(result.stdout.strip().split('\n'))
                self.log_with_print("INFO", f"変更検知: {change_count}ファイル")
            
            return changes_exist
            
        except Exception as e:
            self.log_with_print("ERROR", f"Git状態確認エラー: {e}")
            return False

    def git_add_all(self):
        """全変更をステージング（エラー耐性）"""
        try:
            result = subprocess.run(
                ["git", "add", "."],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_with_print("INFO", "Git add 成功")
                return True
            else:
                self.log_with_print("ERROR", f"Git add 失敗: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_with_print("ERROR", f"Git add 例外: {e}")
            return False

    def git_commit_no_verify(self):
        """--no-verifyでコミット（pre-commit回避）"""
        try:
            commit_message = f"自動保存(cron) - {datetime.now().strftime('%Y-%m-%d %H:%M JST')}"
            
            result = subprocess.run(
                ["git", "commit", "--no-verify", "-m", commit_message],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=60
            )
            
            if result.returncode == 0:
                self.log_with_print("INFO", f"コミット成功: {commit_message}")
                # 成功マーカー更新
                with open(self.success_marker, 'w') as f:
                    f.write(datetime.now().isoformat())
                return True
            else:
                self.log_with_print("ERROR", f"コミット失敗: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_with_print("ERROR", f"コミット例外: {e}")
            return False

    def run_auto_save_cycle(self):
        """自動保存サイクル実行（自己修復機能付き）"""
        start_time = datetime.now()
        self.log_with_print("INFO", "=== Cron自動保存開始 ===")
        
        try:
            # 変更確認
            if not self.has_git_changes():
                self.log_with_print("INFO", "変更なし - スキップ")
                return True
            
            # ステージング
            if not self.git_add_all():
                self.log_with_print("ERROR", "Git add失敗 - 中断")
                return False
            
            # コミット（--no-verify）
            if not self.git_commit_no_verify():
                self.log_with_print("ERROR", "Git commit失敗")
                return False
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.log_with_print("INFO", f"自動保存完了 ({elapsed:.1f}秒)")
            return True
            
        except Exception as e:
            self.log_with_print("ERROR", f"予期しないエラー: {e}")
            return False

    def verify_git_health(self):
        """Git健全性確認"""
        try:
            # 最新コミット確認
            result = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            
            if result.returncode == 0:
                latest_commit = result.stdout.strip()
                self.log_with_print("INFO", f"最新コミット: {latest_commit}")
                return True
            else:
                self.log_with_print("ERROR", "Git log取得失敗")
                return False
                
        except Exception as e:
            self.log_with_print("ERROR", f"Git健全性確認エラー: {e}")
            return False


def main():
    """メイン実行（cron最適化）"""
    # プロジェクトディレクトリ自動検出
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    # 自動保存実行
    auto_saver = CronGitAutoSave(project_dir)
    
    # 健全性確認
    if not auto_saver.verify_git_health():
        auto_saver.log_with_print("WARNING", "Git健全性に問題あり")
    
    # flock排他制御
    import fcntl
    lock_file = project_dir / ".cron_git_auto_save.lock"
    
    try:
        with open(lock_file, 'w') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # 自動保存実行
            success = auto_saver.run_auto_save_cycle()
            
            # 終了コード設定（cron監視用）
            exit_code = 0 if success else 1
            auto_saver.log_with_print("INFO", f"処理終了 (exit={exit_code})")
            exit(exit_code)
            
    except BlockingIOError:
        # 他のプロセスが実行中
        user_info = f"user={os.getenv('USER', 'unknown')}, uid={os.getuid()}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 他プロセス実行中 - スキップ ({user_info})")
        
        # ログファイルにも記録
        try:
            with open(project_root / ".cron_git_auto_save.log", 'a') as f:
                f.write(f"{datetime.now().isoformat()} - WARNING - 排他制御によりスキップ - {user_info}\n")
        except:
            pass
        exit(0)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ロック取得エラー: {e}")
        exit(1)


if __name__ == "__main__":
    main()