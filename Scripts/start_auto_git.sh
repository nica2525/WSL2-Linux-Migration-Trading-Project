#!/bin/bash
# 完全自動Git保存開始スクリプト
# 料金発生ゼロ・バックグラウンド実行

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$PROJECT_DIR/Scripts/auto_git_commit.py"
PID_FILE="$PROJECT_DIR/.auto_git.pid"
LOG_FILE="$PROJECT_DIR/.auto_git.log"

start_daemon() {
    if [ -f "$PID_FILE" ]; then
        if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
            echo "✅ 自動Git保存は既に実行中です (PID: $(cat "$PID_FILE"))"
            return 0
        else
            echo "🔄 古いPIDファイルを削除中..."
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "🚀 完全自動Git保存システム開始..."
    echo "📁 監視対象: $PROJECT_DIR"
    echo "💰 料金: 0円 (ローカル処理のみ)"
    
    # バックグラウンドでデーモン起動
    nohup python3 "$SCRIPT_PATH" --daemon --interval 3 > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    echo "✅ 自動Git保存開始完了 (PID: $!)"
    echo "📋 ログファイル: $LOG_FILE"
    echo "🛑 停止コマンド: $0 stop"
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "🛑 自動Git保存を停止中... (PID: $PID)"
            kill "$PID"
            rm -f "$PID_FILE"
            echo "✅ 停止完了"
        else
            echo "⚠️ プロセスが見つかりません"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ 自動Git保存は実行されていません"
    fi
}

status_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 自動Git保存実行中 (PID: $PID)"
            echo "📊 最新ログ:"
            tail -5 "$LOG_FILE" 2>/dev/null || echo "ログファイルなし"
        else
            echo "❌ PIDファイルはあるがプロセス停止中"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ 自動Git保存は停止中"
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
    *)
        echo "使用方法: $0 {start|stop|restart|status}"
        echo ""
        echo "🤖 完全自動Git保存システム"
        echo "💰 料金: 0円 (ローカル処理のみ)"
        echo "🔄 3分間隔でファイル変更を自動コミット"
        exit 1
        ;;
esac