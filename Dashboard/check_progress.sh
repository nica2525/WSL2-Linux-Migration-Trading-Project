#\!/bin/bash
echo '=== 48時間テスト進捗状況 ==='
echo "現在時刻: $(date)"
START_TIME='2025-07-29 18:21:07'
CURRENT_TIME=$(date +%s)
START_SECONDS=$(date -d "$START_TIME" +%s)
ELAPSED=$((CURRENT_TIME - START_SECONDS))
HOURS=$((ELAPSED / 3600))
MINUTES=$(((ELAPSED % 3600) / 60))
PROGRESS=$(echo "scale=2; $ELAPSED / 172800 * 100" | bc)
echo "開始時刻: $START_TIME"
echo "経過時間: ${HOURS}時間${MINUTES}分"
echo "進捗: ${PROGRESS}% (48時間中)"
echo "データ更新数: $(grep -c data_updates /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/continuous_test.log 2>/dev/null || echo 'N/A')"
