#!/bin/bash
# MT5自動起動のcron設定スクリプト

echo "=== MT5自動起動cron設定 ==="

# 1. cron設定ファイル作成
CRON_FILE="/tmp/mt5_cron_setup"
SCRIPT_PATH="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/mt5_auto_start.py"

# 既存のcrontab取得
crontab -l > "$CRON_FILE" 2>/dev/null || echo "# MT5 Auto Start Cron" > "$CRON_FILE"

# MT5自動起動設定が既に存在するかチェック
if grep -q "mt5_auto_start.py" "$CRON_FILE"; then
    echo "⚠️ MT5自動起動設定は既に存在します"
else
    echo "新規設定を追加します..."

    # cron設定追加
    cat >> "$CRON_FILE" << EOF

# MT5自動起動（システム起動時）
@reboot sleep 60 && /usr/bin/python3 $SCRIPT_PATH >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/mt5_cron.log 2>&1

# MT5定期チェック（30分毎）- 停止時の自動再起動
*/30 * * * * /usr/bin/python3 $SCRIPT_PATH >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/mt5_cron.log 2>&1

# 月曜日朝の確認（日本時間6:00 = UTC 21:00 日曜日）
0 21 * * 0 /usr/bin/python3 $SCRIPT_PATH >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Logs/mt5_monday_check.log 2>&1
EOF

    # crontab更新
    crontab "$CRON_FILE"
    echo "✅ cron設定を追加しました"
fi

# 設定確認
echo ""
echo "=== 現在のMT5関連cron設定 ==="
crontab -l | grep -E "mt5|MT5"

# テスト実行オプション
echo ""
echo "=== テスト実行 ==="
echo "今すぐMT5自動起動をテストしますか？"
echo "実行: python3 $SCRIPT_PATH"
