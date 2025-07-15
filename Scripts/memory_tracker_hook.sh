#!/bin/bash
# Claude記憶追跡システム - Hooks強制実行スクリプト
# 作成日時: 2025-07-12 22:20 JST

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
TRACKER_FILE="$PROJECT_DIR/CLAUDE_REALTIME_MEMORY_TRACKER.md"
ACTION_COUNT_FILE="$PROJECT_DIR/.action_count"

# アクションカウンター初期化/増加
if [ ! -f "$ACTION_COUNT_FILE" ]; then
    echo "1" > "$ACTION_COUNT_FILE"
    ACTION_COUNT=1
else
    ACTION_COUNT=$(cat "$ACTION_COUNT_FILE")
    ACTION_COUNT=$((ACTION_COUNT + 1))
    echo "$ACTION_COUNT" > "$ACTION_COUNT_FILE"
fi

# 現在時刻取得
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S JST')

# 30アクション毎の記憶更新チェック
if [ $((ACTION_COUNT % 30)) -eq 0 ]; then
    echo "🧠 [記憶追跡] $CURRENT_TIME - 第$(((ACTION_COUNT / 30)))回目実行 (30アクション達成)"
    echo "📋 必須確認: ESSENTIAL_REFERENCES.md → 参照マップ読み込み"
    echo "🔄 記憶システムの手動更新が必要です"
    
    # Git管理対象ファイルに記録（フォルダ存在確認付き）
    mkdir -p "$PROJECT_DIR/docs"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 第$(((ACTION_COUNT / 30)))回目記憶追跡実行 (Action: $ACTION_COUNT)" >> "$PROJECT_DIR/docs/MEMORY_EXECUTION_HISTORY.md"
else
    # 10アクション毎に軽い確認
    if [ $((ACTION_COUNT % 10)) -eq 0 ]; then
        echo "📊 [記憶確認] アクション数: $ACTION_COUNT (次回記憶更新まで $((30 - (ACTION_COUNT % 30)))アクション)"
    fi
fi