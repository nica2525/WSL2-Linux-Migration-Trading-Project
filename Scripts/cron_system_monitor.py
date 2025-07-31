#!/usr/bin/env python3
"""
Cron用システム監視スクリプト（簡素・確実）
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


def check_git_auto_save_health(project_dir):
    """Git自動保存健全性確認"""
    try:
        # 最新コミット時刻取得
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=10,
        )

        if result.returncode != 0:
            return {"status": "error", "message": "git log失敗"}

        last_commit_timestamp = int(result.stdout.strip())
        last_commit_time = datetime.fromtimestamp(last_commit_timestamp)
        minutes_since = int((datetime.now() - last_commit_time).total_seconds() / 60)

        # 10分以上古い場合は警告
        status = "healthy" if minutes_since < 10 else "stalled"

        return {
            "status": status,
            "last_commit": last_commit_time.strftime("%Y-%m-%d %H:%M JST"),
            "minutes_since": minutes_since,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_cron_service():
    """cron稼働確認"""
    try:
        result = subprocess.run(
            ["pgrep", "cron"], capture_output=True, text=True, timeout=5
        )

        running = result.returncode == 0
        return {
            "status": "running" if running else "stopped",
            "pids": result.stdout.strip().split("\n") if running else [],
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_mcp_health():
    """MCP健全性確認（簡易版）"""
    try:
        # MCPステータスファイル確認
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent
        status_file = project_dir / ".mcp_health_status.json"

        if status_file.exists():
            with open(status_file) as f:
                status_data = json.load(f)

            # 最終チェックが5分以内か確認
            last_check = datetime.fromisoformat(status_data["timestamp"])
            minutes_since = int((datetime.now() - last_check).total_seconds() / 60)

            if minutes_since > 5:
                return {"status": "stale", "message": f"最終チェック: {minutes_since}分前"}

            return {
                "status": status_data["health_status"].lower(),
                "connected_servers": len(status_data.get("connected_servers", [])),
                "zombie_count": status_data.get("zombie_count", 0),
            }
        else:
            # ステータスファイルがない場合は、簡易チェック実行
            result = subprocess.run(
                ["claude", "mcp", "list"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and "✓ Connected" in result.stdout:
                return {"status": "healthy", "message": "MCP接続確認"}
            else:
                return {"status": "unhealthy", "message": "MCP接続失敗"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    """メイン監視実行"""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    # 監視実行
    git_health = check_git_auto_save_health(project_dir)
    cron_health = check_cron_service()
    mcp_health = check_mcp_health()

    # 結果表示
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")
    print(f"🔍 システム監視 ({timestamp})")

    # Git自動保存状況
    git_icon = (
        "✅"
        if git_health["status"] == "healthy"
        else "❌"
        if git_health["status"] == "stalled"
        else "⚠️"
    )
    print(f"{git_icon} Git自動保存: {git_health['status']}")
    if "last_commit" in git_health:
        print(
            f"   最新コミット: {git_health['last_commit']} ({git_health['minutes_since']}分前)"
        )

    # Cron状況
    cron_icon = "✅" if cron_health["status"] == "running" else "❌"
    print(f"{cron_icon} Cron稼働: {cron_health['status']}")

    # MCP状況
    mcp_icon = (
        "✅"
        if mcp_health["status"] == "healthy"
        else "❌"
        if mcp_health["status"] == "unhealthy"
        else "⚠️"
    )
    print(f"{mcp_icon} MCP接続: {mcp_health['status']}")
    if "connected_servers" in mcp_health:
        print(f"   接続サーバー数: {mcp_health['connected_servers']}")
    if "zombie_count" in mcp_health and mcp_health["zombie_count"] > 0:
        print(f"   ⚠️ ゾンビプロセス: {mcp_health['zombie_count']}個")

    # アラート判定
    alerts = []
    if git_health["status"] == "stalled":
        alerts.append("Git自動保存停滞")
    if cron_health["status"] != "running":
        alerts.append("Cron停止")
    if mcp_health["status"] in ["unhealthy", "error"]:
        alerts.append("MCP異常")

    if alerts:
        print(f"🚨 アラート: {', '.join(alerts)}")
    else:
        print("✅ 全システム正常")

    # 簡易ログ保存
    log_file = project_dir / ".cron_monitor.log"
    with open(log_file, "a") as f:
        f.write(
            f"{timestamp}: Git={git_health['status']}, Cron={cron_health['status']}, MCP={mcp_health['status']}, Alerts={len(alerts)}\n"
        )


if __name__ == "__main__":
    main()
