#!/bin/bash
# Wine環境でのMT5日本語化設定スクリプト

echo "=== Wine MT5 日本語化設定 ==="

# 1. 日本語フォントのインストール
echo "1. 日本語フォントをインストール..."
sudo apt-get update
sudo apt-get install -y fonts-takao fonts-ipafont fonts-ipaexfont fonts-noto-cjk

# 2. Wine設定で日本語フォントを登録
echo "2. Wineレジストリに日本語フォントを登録..."
cat > /tmp/wine_japanese_fonts.reg << 'EOF'
REGEDIT4

[HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\FontSubstitutes]
"MS Gothic"="Takao Gothic"
"MS PGothic"="Takao PGothic"
"MS Mincho"="Takao Mincho"
"MS PMincho"="Takao PMincho"
"MS UI Gothic"="Takao Gothic"
"Yu Gothic"="Noto Sans CJK JP"
"Meiryo"="Noto Sans CJK JP"
"Meiryo UI"="Noto Sans CJK JP"

[HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\Fonts]
"Takao Gothic (TrueType)"="TakaoGothic.ttf"
"Takao PGothic (TrueType)"="TakaoPGothic.ttf"
"Takao Mincho (TrueType)"="TakaoMincho.ttf"
"Takao PMincho (TrueType)"="TakaoPMincho.ttf"
EOF

wine regedit /tmp/wine_japanese_fonts.reg

# 3. Wine環境変数設定
echo "3. Wine環境変数を設定..."
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8

# 4. ロケール生成
echo "4. 日本語ロケールを生成..."
sudo locale-gen ja_JP.UTF-8
sudo update-locale

# 5. Wineのフォントキャッシュをクリア
echo "5. Wineフォントキャッシュをクリア..."
rm -rf ~/.cache/wine

# 6. MT5起動用スクリプト作成
echo "6. MT5日本語起動スクリプトを作成..."
cat > /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/start_mt5_japanese.sh << 'EOF'
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
EOF

chmod +x /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/start_mt5_japanese.sh

echo "=== 設定完了 ==="
echo "以下のコマンドでMT5を日本語環境で起動できます："
echo "./Scripts/start_mt5_japanese.sh"
echo ""
echo "追加の手順："
echo "1. MT5を起動後、メニューから View > Languages > 日本語 を選択"
echo "2. MT5を再起動"
