#!/bin/bash
# Wine MT5 日本語化設定（簡易版）

echo "=== Wine MT5 日本語化設定（簡易版） ==="

# 1. Wine環境でのフォント設定
echo "1. Wineフォント設定..."
mkdir -p ~/.wine/drive_c/windows/Fonts

# 2. システムフォントからリンク（存在する場合）
echo "2. システムフォントをチェック..."
if [ -d "/usr/share/fonts" ]; then
    # DejaVuフォントなど、既存のUnicodeフォントを利用
    find /usr/share/fonts -name "*.ttf" -o -name "*.otf" | while read font; do
        ln -sf "$font" ~/.wine/drive_c/windows/Fonts/ 2>/dev/null
    done
    echo "システムフォントをリンクしました"
fi

# 3. Wine設定（レジストリ）
echo "3. Wineレジストリ設定..."
cat > /tmp/wine_font_fallback.reg << 'EOF'
REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\Fonts\Replacements]
"MS Gothic"="DejaVu Sans"
"MS PGothic"="DejaVu Sans"
"MS UI Gothic"="DejaVu Sans"
"Arial"="DejaVu Sans"
"Tahoma"="DejaVu Sans"

[HKEY_CURRENT_USER\Control Panel\International]
"Locale"="00000411"
"sCountry"="Japan"
"sLanguage"="JPN"
EOF

wine regedit /tmp/wine_font_fallback.reg

# 4. MT5パスを探す
echo "4. MT5インストールパスを検索..."
MT5_PATH=$(find ~/.wine -name "terminal64.exe" 2>/dev/null | head -1)

if [ -z "$MT5_PATH" ]; then
    echo "MT5が見つかりません。手動でパスを指定してください。"
    MT5_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
fi

echo "MT5パス: $MT5_PATH"

# 5. 起動スクリプト更新
echo "5. MT5起動スクリプトを作成..."
cat > /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/start_mt5_utf8.sh << EOF
#!/bin/bash
# MT5をUTF-8環境で起動

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export WINEDEBUG=-all
export WINEPREFIX=\$HOME/.wine

MT5_PATH="$MT5_PATH"

if [ -f "\$MT5_PATH" ]; then
    echo "MT5を起動します..."
    echo "起動後、View > Languages から言語を選択してください"
    wine "\$MT5_PATH" &
else
    echo "MT5が見つかりません: \$MT5_PATH"
fi
EOF

chmod +x /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/start_mt5_utf8.sh

echo ""
echo "=== 設定完了 ==="
echo "MT5を起動: ./Scripts/start_mt5_utf8.sh"
echo ""
echo "MT5起動後の手順："
echo "1. View > Languages メニューから言語を選択"
echo "2. 日本語が表示されない場合は、英語で使用してください"
echo "3. EAは言語に関係なく動作します"