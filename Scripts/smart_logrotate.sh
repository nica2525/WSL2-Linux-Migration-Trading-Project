#!/bin/bash

# 生活リズム対応スマートlogrotate
# PC稼働時間帯にサイズベース実行

source "$(dirname "$0")/path_resolver.sh"
PROJECT_DIR="$(get_project_dir)"

LOGROTATE_CONF="/home/trader/.logrotate.conf"
LOGROTATE_STATE="/home/trader/.logrotate.state"

# 時間帯確認（9-21時のみ実行）
CURRENT_HOUR=$(date +%H)
if [[ $CURRENT_HOUR -lt 9 || $CURRENT_HOUR -gt 21 ]]; then
    # PC稼働時間外は何もしない
    exit 0
fi

# ログファイルサイズ確認
GIT_LOG="$(get_log_file "cron_git_auto_save")"
MONITOR_LOG="$(get_log_file "cron_monitor")"

# Git保存ログが2MB超過時
if [[ -f "$GIT_LOG" ]]; then
    GIT_SIZE_KB=$(du -k "$GIT_LOG" | cut -f1)
    if [[ $GIT_SIZE_KB -ge 2048 ]]; then
        echo "[$(date '+%H:%M:%S')] Git保存ログ ${GIT_SIZE_KB}KB -> logrotate実行"
        /usr/sbin/logrotate -s "$LOGROTATE_STATE" "$LOGROTATE_CONF"
        exit 0
    fi
fi

# 監視ログが1MB超過時
if [[ -f "$MONITOR_LOG" ]]; then
    MONITOR_SIZE_KB=$(du -k "$MONITOR_LOG" | cut -f1)
    if [[ $MONITOR_SIZE_KB -ge 1024 ]]; then
        echo "[$(date '+%H:%M:%S')] 監視ログ ${MONITOR_SIZE_KB}KB -> logrotate実行"
        /usr/sbin/logrotate -s "$LOGROTATE_STATE" "$LOGROTATE_CONF"
        exit 0
    fi
fi

# サイズ制限内の場合は何もしない
exit 0