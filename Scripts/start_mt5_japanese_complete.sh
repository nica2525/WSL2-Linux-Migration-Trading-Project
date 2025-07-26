#!/bin/bash
# MT5を完全日本語環境で起動

# 日本語環境設定
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
export WINEDEBUG=-all

# ホームディレクトリから起動（パス問題回避）
cd $HOME

# MT5パス
MT5_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if [ -f "$MT5_PATH" ]; then
    echo "MT5を日本語環境で起動します..."
    wine "$MT5_PATH" &
    echo ""
    echo "起動完了。MT5内で以下を確認してください："
    echo "1. 表示 > 言語 > 日本語 を選択"
    echo "2. MT5を再起動すると日本語UIになります"
else
    echo "MT5が見つかりません: $MT5_PATH"
fi
