#!/bin/bash
# 48時間連続稼働テスト開始スクリプト
# 作成日: 2025-07-29

TEST_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard"
LOG_FILE="$TEST_DIR/48hour_test.log"

echo "=== 48時間連続稼働テスト開始準備 ===" | tee $LOG_FILE
echo "開始時刻: $(date)" | tee -a $LOG_FILE
echo "テスト期間: 48時間（2025-07-29 18:30 ～ 2025-07-31 18:30予定）" | tee -a $LOG_FILE

# 事前チェック
echo -e "\n📋 事前チェック実行中..." | tee -a $LOG_FILE

# ディスク容量チェック
DISK_USAGE=$(df -h $TEST_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
echo "ディスク使用率: ${DISK_USAGE}%" | tee -a $LOG_FILE

if [ $DISK_USAGE -gt 90 ]; then
    echo "⚠️  警告: ディスク使用率が90%を超えています" | tee -a $LOG_FILE
fi

# メモリ確認
MEMORY_USAGE=$(free | grep '^Mem:' | awk '{printf("%.1f", $3/$2 * 100.0)}')
echo "メモリ使用率: ${MEMORY_USAGE}%" | tee -a $LOG_FILE

# 必要ファイル確認
if [ ! -f "$TEST_DIR/test_continuous_operation.py" ]; then
    echo "❌ エラー: テストスクリプトが見つかりません" | tee -a $LOG_FILE
    exit 1
fi

if [ ! -f "$TEST_DIR/app.py" ]; then
    echo "❌ エラー: ダッシュボードアプリが見つかりません" | tee -a $LOG_FILE
    exit 1
fi

echo "✅ 事前チェック完了" | tee -a $LOG_FILE

# テスト開始
echo -e "\n🚀 48時間テスト開始..." | tee -a $LOG_FILE
echo "詳細ログ: $TEST_DIR/continuous_test.log" | tee -a $LOG_FILE
echo "中断方法: Ctrl+C または pkill -f test_continuous_operation" | tee -a $LOG_FILE

# バックグラウンドでテスト実行
cd $TEST_DIR
nohup python3 test_continuous_operation.py > /dev/null 2>&1 &
TEST_PID=$!

echo "テストプロセスID: $TEST_PID" | tee -a $LOG_FILE
echo $TEST_PID > $TEST_DIR/test_pid.txt

echo -e "\n📊 進捗確認方法:" | tee -a $LOG_FILE
echo "  tail -f $TEST_DIR/continuous_test.log" | tee -a $LOG_FILE
echo "  cat $TEST_DIR/continuous_test_metrics.json" | tee -a $LOG_FILE

echo -e "\n✅ 48時間テスト開始完了" | tee -a $LOG_FILE
echo "テストは48時間後（2025-07-31 18:30頃）に自動完了します" | tee -a $LOG_FILE
