#!/bin/bash
# MT5を日本語環境で起動

export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
export WINEDEBUG=-all

# MT5のパスを設定（実際のパスに合わせて調整してください）
MT5_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if [ -f "$MT5_PATH" ]; then
    echo "MT5を日本語環境で起動します..."
    wine "$MT5_PATH" &
else
    echo "MT5が見つかりません: $MT5_PATH"
    echo "正しいパスを設定してください"
fi
