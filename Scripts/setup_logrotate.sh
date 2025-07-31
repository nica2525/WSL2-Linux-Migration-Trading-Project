#!/bin/bash

# logrotate設定スクリプト
# Gemini指摘: ログファイル肥大化防止

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
LOGROTATE_CONF="/home/trader/.logrotate.conf"
LOGROTATE_STATE="/home/trader/.logrotate.state"

echo "🔧 logrotate設定開始..."

# logrotate設定ファイル作成
cat > "$LOGROTATE_CONF" << 'EOF'
# Trading Project Log Rotation Configuration
# Gemini改善: ログ肥大化防止

/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_git_auto_save.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 trader trader
}

/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_monitor.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 trader trader
}

/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.memory_tracker.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 trader trader
}

/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.session_memory.log {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 644 trader trader
}
EOF

echo "✅ logrotate設定ファイル作成: $LOGROTATE_CONF"

# 初期状態ファイル作成
touch "$LOGROTATE_STATE"

# テスト実行
echo "🧪 logrotate動作テスト..."
TEST_OUTPUT=$(logrotate -d "$LOGROTATE_CONF" 2>&1)
if echo "$TEST_OUTPUT" | grep -i "error.*state file" > /dev/null; then
    echo "⚠️ 権限警告あり（正常動作）"
elif echo "$TEST_OUTPUT" | grep -i "error" | grep -v "state file" > /dev/null; then
    echo "❌ logrotate設定エラー"
    echo "$TEST_OUTPUT"
    exit 1
else
    echo "✅ logrotate設定テスト成功"
fi

# crontabにlogrotate追加
echo "📅 crontab更新中..."
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/bin/logrotate -s $LOGROTATE_STATE $LOGROTATE_CONF") | crontab -

echo ""
echo "🎉 logrotate設定完了"
echo "📋 設定内容:"
echo "   - Git保存ログ: 日次ローテーション、7日保持"
echo "   - 監視ログ: 日次ローテーション、7日保持"
echo "   - メモリログ: 日次ローテーション、7日保持"
echo "   - セッションログ: 週次ローテーション、4週保持"
echo "   - 実行時刻: 毎日2:00AM"
echo ""
echo "🔍 確認コマンド:"
echo "   crontab -l | grep logrotate"
echo "   logrotate -d $LOGROTATE_CONF"

exit 0
