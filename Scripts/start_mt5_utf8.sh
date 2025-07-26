#!/bin/bash
# MT5をUTF-8環境で起動

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export WINEDEBUG=-all
export WINEPREFIX=$HOME/.wine

MT5_PATH="/home/trader/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if [ -f "$MT5_PATH" ]; then
    echo "MT5を起動します..."
    echo "起動後、View > Languages から言語を選択してください"
    wine "$MT5_PATH" &
else
    echo "MT5が見つかりません: $MT5_PATH"
fi
