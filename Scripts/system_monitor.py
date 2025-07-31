#!/usr/bin/env python3
"""
システム監視・アラートシステム
systemdサービス状況・プロセス健全性・ディスク使用量監視
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import psutil


class SystemMonitor:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.log_file = self.project_dir / ".system_monitor.log"
        self.alert_file = self.project_dir / "monitoring_alerts.json"

        # ログ設定
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # 監視対象systemdサービス
        self.monitored_services = [
            "git-auto-save.timer",
            "memory-tracker.timer",
            "backtest-automation.timer",
        ]

        # アラート閾値
        self.disk_usage_threshold = 85  # %
        self.memory_usage_threshold = 90  # %

    def check_systemd_services(self):
        """systemdサービス状況チェック"""
        service_status = {}
        alerts = []

        for service in self.monitored_services:
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                status = result.stdout.strip()
                service_status[service] = {
                    "status": status,
                    "active": status == "active",
                    "checked_at": datetime.now().isoformat(),
                }

                if status != "active":
                    alerts.append(
                        {
                            "type": "service_inactive",
                            "service": service,
                            "status": status,
                            "timestamp": datetime.now().isoformat(),
                            "severity": "high",
                        }
                    )

            except Exception as e:
                service_status[service] = {
                    "status": "check_failed",
                    "active": False,
                    "error": str(e),
                    "checked_at": datetime.now().isoformat(),
                }
                alerts.append(
                    {
                        "type": "service_check_failed",
                        "service": service,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "severity": "medium",
                    }
                )

        return service_status, alerts

    def check_system_resources(self):
        """システムリソース監視"""
        alerts = []

        # ディスク使用量チェック
        disk_usage = psutil.disk_usage(self.project_dir)
        disk_percent = (disk_usage.used / disk_usage.total) * 100

        if disk_percent > self.disk_usage_threshold:
            alerts.append(
                {
                    "type": "disk_usage_high",
                    "usage_percent": disk_percent,
                    "threshold": self.disk_usage_threshold,
                    "timestamp": datetime.now().isoformat(),
                    "severity": "medium",
                }
            )

        # メモリ使用量チェック
        memory = psutil.virtual_memory()
        if memory.percent > self.memory_usage_threshold:
            alerts.append(
                {
                    "type": "memory_usage_high",
                    "usage_percent": memory.percent,
                    "threshold": self.memory_usage_threshold,
                    "timestamp": datetime.now().isoformat(),
                    "severity": "medium",
                }
            )

        return {
            "disk_usage_percent": disk_percent,
            "memory_usage_percent": memory.percent,
            "checked_at": datetime.now().isoformat(),
        }, alerts

    def check_git_auto_save_activity(self):
        """Git自動保存活動チェック"""
        alerts = []

        try:
            # 最新のGitコミット時刻取得
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
            time_since_last_commit = datetime.now() - last_commit_time

            # 10分以上コミットがない場合（変更があるのに自動保存されていない可能性）
            if time_since_last_commit > timedelta(minutes=10):
                # Git変更状況確認
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=self.project_dir,
                    timeout=10,
                )

                if status_result.stdout.strip():  # 変更があるのにコミットされていない
                    alerts.append(
                        {
                            "type": "git_auto_save_stalled",
                            "last_commit_time": last_commit_time.isoformat(),
                            "minutes_since_last_commit": int(
                                time_since_last_commit.total_seconds() / 60
                            ),
                            "has_uncommitted_changes": True,
                            "timestamp": datetime.now().isoformat(),
                            "severity": "high",
                        }
                    )

            return {
                "last_commit_time": last_commit_time.isoformat(),
                "minutes_since_last_commit": int(
                    time_since_last_commit.total_seconds() / 60
                ),
                "checked_at": datetime.now().isoformat(),
            }, alerts

        except Exception as e:
            alerts.append(
                {
                    "type": "git_check_failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "severity": "medium",
                }
            )
            return {"error": str(e)}, alerts

    def save_alerts(self, all_alerts):
        """アラート保存"""
        if not all_alerts:
            return

        try:
            # 既存アラート読み込み
            existing_alerts = []
            if self.alert_file.exists():
                with open(self.alert_file) as f:
                    existing_alerts = json.load(f)

            # 新しいアラート追加（最新100件保持）
            all_alerts_combined = existing_alerts + all_alerts
            all_alerts_combined = all_alerts_combined[-100:]

            # 保存
            with open(self.alert_file, "w") as f:
                json.dump(all_alerts_combined, f, indent=2)

        except Exception as e:
            logging.error(f"アラート保存エラー: {e}")

    def run_monitoring_cycle(self):
        """監視サイクル実行"""
        logging.info("システム監視サイクル開始")

        all_alerts = []

        # systemdサービス監視
        service_status, service_alerts = self.check_systemd_services()
        all_alerts.extend(service_alerts)

        # システムリソース監視
        resource_status, resource_alerts = self.check_system_resources()
        all_alerts.extend(resource_alerts)

        # Git自動保存監視
        git_status, git_alerts = self.check_git_auto_save_activity()
        all_alerts.extend(git_alerts)

        # 監視結果ログ記録
        active_services = sum(
            1 for status in service_status.values() if status.get("active", False)
        )
        logging.info(
            f"監視完了: サービス{active_services}/{len(self.monitored_services)}稼働, "
            f"ディスク{resource_status['disk_usage_percent']:.1f}%, "
            f"メモリ{resource_status['memory_usage_percent']:.1f}%, "
            f"アラート{len(all_alerts)}件"
        )

        # アラート保存
        if all_alerts:
            self.save_alerts(all_alerts)
            logging.warning(f"アラート{len(all_alerts)}件発生")

            # 高重要度アラートがある場合のコンソール出力
            high_severity_alerts = [
                a for a in all_alerts if a.get("severity") == "high"
            ]
            if high_severity_alerts:
                print(f"🚨 高重要度アラート {len(high_severity_alerts)}件発生!")
                for alert in high_severity_alerts:
                    print(
                        f"  - {alert['type']}: {alert.get('service', '')} {alert.get('error', '')}"
                    )

        return {
            "services": service_status,
            "resources": resource_status,
            "git": git_status,
            "alerts": all_alerts,
            "monitoring_time": datetime.now().isoformat(),
        }


def main():
    """メイン実行"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    monitor = SystemMonitor(project_dir)
    result = monitor.run_monitoring_cycle()

    # 簡単なサマリー出力
    print(f"監視完了 - アラート: {len(result['alerts'])}件")


if __name__ == "__main__":
    main()
