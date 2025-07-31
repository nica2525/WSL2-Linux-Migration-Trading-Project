#!/bin/bash
# MT5を安全に起動（日本語ディレクトリ問題回避）

# 英語環境で起動
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export WINEDEBUG=-all

# ホームディレクトリから起動
cd $HOME

# MT5パス
MT5_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if [ -f "$MT5_PATH" ]; then
    echo "Starting MT5..."
    wine "$MT5_PATH" &
    echo "MT5 started. PID: $!"
    echo ""
    echo "Note: To avoid character encoding issues,"
    echo "MT5 is started from home directory."
    echo ""
    echo "After MT5 starts:"
    echo "1. Go to View > Languages"
    echo "2. Select your preferred language"
    echo "3. Restart MT5 if needed"
else
    echo "MT5 not found at: $MT5_PATH"
fi
