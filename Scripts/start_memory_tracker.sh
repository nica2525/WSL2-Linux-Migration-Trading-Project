#!/bin/bash
# 時間ベース記憶追跡システム制御スクリプト

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$PROJECT_DIR/Scripts/time_based_memory_tracker.py"
PID_FILE="$PROJECT_DIR/.memory_tracker.pid"
LOG_FILE="$PROJECT_DIR/.memory_tracker.log"

start_daemon() {
    if [ -f "$PID_FILE" ]; then
        if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
            echo "✅ 時間ベース記憶追跡は既に実行中です (PID: $(cat "$PID_FILE"))"
            return 0
        else
            echo "🔄 古いPIDファイルを削除中..."
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🧠 時間ベース記憶追跡システム開始..."
    echo "📁 監視対象: $PROJECT_DIR"
    echo "⏰ 実行間隔: 30分"
    
    # バックグラウンドでデーモン起動
    nohup python3 "$SCRIPT_PATH" --daemon --interval 30 > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    echo "✅ 記憶追跡開始完了 (PID: $!)"
    echo "📋 ログファイル: $LOG_FILE"
    echo "🛑 停止コマンド: $0 stop"
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "🛑 記憶追跡を停止中... (PID: $PID)"
            kill "$PID"
            rm -f "$PID_FILE"
            echo "✅ 停止完了"
        else
            echo "⚠️ プロセスが見つかりません"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ 記憶追跡は実行されていません"
    fi
}

status_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 時間ベース記憶追跡実行中 (PID: $PID)"
            echo "📊 最新ログ:"
            tail -5 "$LOG_FILE" 2>/dev/null || echo "ログファイルなし"
        else
            echo "❌ PIDファイルはあるがプロセス停止中"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ 記憶追跡は停止中"
    fi
}

case "$1" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        stop_daemon
        sleep 2
        start_daemon
        ;;
    status)
        status_daemon
        ;;
    test)
        echo "🧪 記憶追跡テスト実行..."
        python3 "$SCRIPT_PATH"
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|test}"
        echo ""
        echo "🧠 時間ベース記憶追跡システム"
        echo "⏰ 30分間隔で自動記憶更新"
        echo "🔧 Hooks障害に対する代替システム"
        exit 1
        ;;
esac