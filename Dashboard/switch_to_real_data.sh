#!/bin/bash
# JamesORB実データ切り替えスクリプト

echo "=== JamesORB実データ切り替え開始 ==="

# 1. 既存テストスクリプト停止
echo "1. テストスクリプト停止中..."
pkill -f "PositionExporter.mq5" 2>/dev/null || true

# 2. JamesORB実データスクリプト開始指示
echo "2. MT5でJamesORBExporter.mq5を手動実行してください"
echo "   場所: /home/trader/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Scripts/"
echo "   ファイル: JamesORBExporter.mq5"

# 3. データファイル確認
echo "3. データファイル監視開始..."
echo "   監視対象: /tmp/mt5_data/positions.json"

# データファイルの変更を監視
old_timestamp=""
for i in {1..30}
do
    if [ -f "/tmp/mt5_data/positions.json" ]; then
        new_timestamp=$(jq -r '.timestamp' /tmp/mt5_data/positions.json 2>/dev/null)
        if [ "$new_timestamp" != "$old_timestamp" ] && [ "$new_timestamp" != "null" ]; then
            echo "   ✅ データ更新検知: $new_timestamp"
            
            # 実データかチェック（チケット番号パターン）
            ticket=$(jq -r '.positions[0].ticket' /tmp/mt5_data/positions.json 2>/dev/null)
            if [ "$ticket" != "null" ] && [ ${#ticket} -gt 5 ]; then
                echo "   ✅ 実データ確認: チケット$ticket"
                echo "   🎯 切り替え成功！"
                break
            fi
            old_timestamp="$new_timestamp"
        fi
    fi
    echo "   ⏳ 待機中... ($i/30)"
    sleep 2
done

# 4. ダッシュボード確認
echo "4. ダッシュボード確認"
echo "   URL: http://localhost:5000"
echo "   実データが表示されることを確認してください"

echo "=== 切り替え完了 ==="