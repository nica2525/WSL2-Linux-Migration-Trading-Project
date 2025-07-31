#!/bin/bash

# 生活リズム対応スマートlogrotate
# PC稼働時間帯にサイズベース実行
#
# 【設計思想】
# - PM22時PCシャットダウン環境での確実なログ管理
# - 時刻ベース(daily)→サイズベース(2MB/1MB)への変更
# - PC稼働時間(9:00-21:00)限定実行による生活リズム適合
#
# 【処理概要】
# 1. 時間帯チェック: 9:00-21:00以外は即座に終了
# 2. Git保存ログ: 2MB超過時にlogrotate実行
# 3. 監視ログ: 1MB超過時にlogrotate実行
# 4. システムログ記録: 成功・失敗をloggerで記録
#
# 【cron設定】
# */15 9-21 * * * (15分間隔、PC稼働時間のみ)
#
# Gemini査読: "非常に効果的かつ技術的に妥当な設計"

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
        if /usr/sbin/logrotate -s "$LOGROTATE_STATE" "$LOGROTATE_CONF" 2>/dev/null; then
            logger "Trading Project: Git log rotation completed successfully (${GIT_SIZE_KB}KB)"
        else
            logger "Trading Project: Git log rotation failed"
        fi
        exit 0
    fi
fi

# 監視ログが1MB超過時
if [[ -f "$MONITOR_LOG" ]]; then
    MONITOR_SIZE_KB=$(du -k "$MONITOR_LOG" | cut -f1)
    if [[ $MONITOR_SIZE_KB -ge 1024 ]]; then
        echo "[$(date '+%H:%M:%S')] 監視ログ ${MONITOR_SIZE_KB}KB -> logrotate実行"
        if /usr/sbin/logrotate -s "$LOGROTATE_STATE" "$LOGROTATE_CONF" 2>/dev/null; then
            logger "Trading Project: Monitor log rotation completed successfully (${MONITOR_SIZE_KB}KB)"
        else
            logger "Trading Project: Monitor log rotation failed"
        fi
        exit 0
    fi
fi

# サイズ制限内の場合は何もしない
exit 0
