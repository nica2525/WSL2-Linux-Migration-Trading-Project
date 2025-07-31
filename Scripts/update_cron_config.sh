#!/bin/bash
"""
cron設定更新スクリプト
リファクタリング後のスクリプト名に更新
"""

PROJECT_ROOT="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
TEMP_CRON="/tmp/crontab_update_$$"

echo "=== cron設定更新開始 ==="

# 現在のcron設定をバックアップ
crontab -l > "${PROJECT_ROOT}/cron_backup_$(date +%Y%m%d_%H%M%S).txt"
echo "✓ 現在のcron設定をバックアップしました"

# 新しいcron設定を作成
cat > $TEMP_CRON << 'EOF'
# Git自動保存（3分間隔）
*/3 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_git_auto_save.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_git_auto_save.log 2>&1

# システム監視（5分間隔）
*/5 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_system_monitor.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_monitor.log 2>&1

# ログローテーション（15分間隔、営業時間のみ）
*/15 9-21 * * * /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/smart_logrotate.sh

# MT5自動起動（システム起動時）- リファクタリング版
@reboot sleep 60 && /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/mt5_auto_start_fixed.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/mt5_cron.log 2>&1

# MT5定期チェック（30分毎）- リファクタリング版
*/30 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/mt5_auto_start_fixed.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/mt5_cron.log 2>&1

# 月曜日朝の確認（日本時間6:00 = UTC 21:00 日曜日）- リファクタリング版
0 21 * * 0 /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/mt5_auto_start_fixed.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/mt5_monday_check.log 2>&1

# 取引監視（15分間隔、営業時間のみ）- 新規追加
*/15 9-22 * * 1-5 CRON_MODE=1 /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/mt5_trading_monitor_fixed.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/trading_monitor_cron.log 2>&1

EOF

# cron設定を更新
crontab $TEMP_CRON

if [ $? -eq 0 ]; then
    echo "✅ cron設定更新完了"
    echo ""
    echo "=== 更新後のcron設定 ==="
    crontab -l
else
    echo "❌ cron設定更新失敗"
    # バックアップから復元
    latest_backup=$(ls -t ${PROJECT_ROOT}/cron_backup_*.txt | head -1)
    if [ -f "$latest_backup" ]; then
        crontab "$latest_backup"
        echo "🔄 バックアップから復元しました: $latest_backup"
    fi
    exit 1
fi

# 一時ファイル削除
rm -f $TEMP_CRON

echo ""
echo "=== 更新内容 ==="
echo "• MT5自動起動スクリプトをmt5_auto_start_fixed.py（リファクタリング版）に更新"
echo "• 取引監視スクリプトmt5_trading_monitor_fixed.py（リファクタリング版）を新規追加"
echo "• 営業時間（平日9-22時）の15分間隔で取引監視実行"
echo ""
echo "=== cron設定更新完了 ==="
