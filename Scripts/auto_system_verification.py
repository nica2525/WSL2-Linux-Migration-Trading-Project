#!/usr/bin/env python3
"""
自動システム検証スクリプト
15分後に自動実行してシステム正常稼働を確認
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path


class AutoSystemVerification:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.verification_log = self.project_dir / "system_verification_log.json"
        self.start_time = datetime.now()

    def verify_git_auto_save(self):
        """Git自動保存動作確認"""
        try:
            # 最新コミット時刻取得
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_dir,
                timeout=10,
            )

            last_commit_timestamp = int(result.stdout.strip())
            last_commit_time = datetime.fromtimestamp(last_commit_timestamp)
            time_since_commit = datetime.now() - last_commit_time

            # 15分以内にコミットがあるかチェック
            working_properly = time_since_commit < timedelta(minutes=15)

            return {
                "service": "git_auto_save",
                "status": "working" if working_properly else "stalled",
                "last_commit_time": last_commit_time.isoformat(),
                "minutes_since_commit": int(time_since_commit.total_seconds() / 60),
                "expected_max_minutes": 3,
            }

        except Exception as e:
            return {"service": "git_auto_save", "status": "error", "error": str(e)}

    def verify_systemd_timers(self):
        """systemdタイマー動作確認"""
        timers = [
            "git-auto-save.timer",
            "memory-tracker.timer",
            "backtest-automation.timer",
            "system-monitor.timer",
        ]
        results = []

        for timer in timers:
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "is-active", timer],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                status = result.stdout.strip()
                results.append(
                    {"timer": timer, "status": status, "working": status == "active"}
                )

            except Exception as e:
                results.append(
                    {
                        "timer": timer,
                        "status": "error",
                        "error": str(e),
                        "working": False,
                    }
                )

        return results

    def verify_system_monitor(self):
        """システム監視動作確認"""
        try:
            # system_monitor.pyを実行してアラート数確認
            result = subprocess.run(
                ["python3", str(self.project_dir / "Scripts" / "system_monitor.py")],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=30,
            )

            # 出力からアラート数を抽出
            output = result.stdout
            if "アラート: 0件" in output:
                alert_count = 0
            elif "アラート: " in output:
                try:
                    alert_count = int(output.split("アラート: ")[1].split("件")[0])
                except:
                    alert_count = -1
            else:
                alert_count = -1

            return {
                "service": "system_monitor",
                "status": "working" if result.returncode == 0 else "error",
                "alert_count": alert_count,
                "output": output[-200:] if output else "",  # 最後の200文字のみ
            }

        except Exception as e:
            return {"service": "system_monitor", "status": "error", "error": str(e)}

    def run_comprehensive_verification(self):
        """包括的システム検証実行"""
        verification_time = datetime.now()

        results = {
            "verification_time": verification_time.isoformat(),
            "verification_start": self.start_time.isoformat(),
            "minutes_elapsed": int(
                (verification_time - self.start_time).total_seconds() / 60
            ),
            "git_auto_save": self.verify_git_auto_save(),
            "systemd_timers": self.verify_systemd_timers(),
            "system_monitor": self.verify_system_monitor(),
        }

        # 総合評価
        git_ok = results["git_auto_save"]["status"] == "working"
        timers_ok = all(t["working"] for t in results["systemd_timers"])
        monitor_ok = results["system_monitor"]["status"] == "working"

        results["overall_status"] = (
            "healthy" if (git_ok and timers_ok and monitor_ok) else "degraded"
        )
        results["healthy_services"] = sum([git_ok, timers_ok, monitor_ok])
        results["total_services"] = 3

        # 結果保存
        self.save_verification_result(results)

        # 結果表示
        self.display_verification_result(results)

        return results

    def save_verification_result(self, results):
        """検証結果保存"""
        try:
            # 既存ログ読み込み
            existing_logs = []
            if self.verification_log.exists():
                with open(self.verification_log) as f:
                    existing_logs = json.load(f)

            # 新しい結果追加（最新20件保持）
            existing_logs.append(results)
            existing_logs = existing_logs[-20:]

            # 保存
            with open(self.verification_log, "w") as f:
                json.dump(existing_logs, f, indent=2)

        except Exception as e:
            print(f"検証結果保存エラー: {e}")

    def display_verification_result(self, results):
        """検証結果表示"""
        print(f"\n🔍 自動システム検証結果 ({results['verification_time'][:19]})")
        print(f"⏱️  経過時間: {results['minutes_elapsed']}分")
        print(f"📊 総合ステータス: {results['overall_status'].upper()}")
        print(f"✅ 正常サービス: {results['healthy_services']}/{results['total_services']}")

        # Git自動保存
        git = results["git_auto_save"]
        status_icon = "✅" if git["status"] == "working" else "❌"
        print(
            f"{status_icon} Git自動保存: {git['status']} ({git.get('minutes_since_commit', '?')}分前)"
        )

        # systemdタイマー
        active_timers = sum(1 for t in results["systemd_timers"] if t["working"])
        total_timers = len(results["systemd_timers"])
        timer_icon = "✅" if active_timers == total_timers else "❌"
        print(f"{timer_icon} systemdタイマー: {active_timers}/{total_timers}稼働中")

        # システム監視
        monitor = results["system_monitor"]
        monitor_icon = "✅" if monitor["status"] == "working" else "❌"
        alert_info = (
            f"アラート{monitor.get('alert_count', '?')}件"
            if monitor["status"] == "working"
            else "エラー"
        )
        print(f"{monitor_icon} システム監視: {monitor['status']} ({alert_info})")

        if results["overall_status"] == "healthy":
            print("\n🎉 全システム正常稼働中 - 修復成功確認")
        else:
            print("\n⚠️  一部システムに問題あり - 追加調査が必要")


def main():
    """メイン実行"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    verifier = AutoSystemVerification(project_dir)

    print("🚀 15分後自動システム検証を開始...")
    print("⏰ 開始時刻:", verifier.start_time.strftime("%Y-%m-%d %H:%M:%S JST"))
    print("⏳ 15分待機中...")

    # 15分待機
    time.sleep(15 * 60)  # 15分 = 900秒

    # 検証実行
    verifier.run_comprehensive_verification()


if __name__ == "__main__":
    main()
