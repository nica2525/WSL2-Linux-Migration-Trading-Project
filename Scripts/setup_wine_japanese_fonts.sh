#!/bin/bash
# Wine環境への日本語フォント登録（フォントインストール後に実行）

echo "=== Wine日本語フォント登録 ==="

# 1. インストール済みフォントの確認
echo "1. 日本語フォントを確認..."
if ! fc-list :lang=ja | grep -q "Takao\|IPA\|Noto"; then
    echo "❌ 日本語フォントが見つかりません"
    echo "先に manual_japanese_setup.txt の手順を実行してください"
    exit 1
fi

echo "✅ 日本語フォントを検出"

# 2. Wineのフォントディレクトリ準備
echo "2. Wineフォントディレクトリを準備..."
mkdir -p ~/.wine/drive_c/windows/Fonts

# 3. 日本語フォントをWineにコピー
echo "3. フォントをWineにコピー..."
for font in /usr/share/fonts/truetype/takao-gothic/*.ttf \
           /usr/share/fonts/truetype/takao-mincho/*.ttf \
           /usr/share/fonts/opentype/ipafont-gothic/*.ttf \
           /usr/share/fonts/opentype/ipafont-mincho/*.ttf \
           /usr/share/fonts/opentype/noto/*.ttc; do
    if [ -f "$font" ]; then
        cp -f "$font" ~/.wine/drive_c/windows/Fonts/ 2>/dev/null
    fi
done

# 4. Wineレジストリ設定
echo "4. Wineレジストリを設定..."
cat > /tmp/wine_jp_complete.reg << 'EOF'
REGEDIT4

[HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\FontSubstitutes]
"MS Gothic"="TakaoGothic"
"MS PGothic"="TakaoPGothic"
"MS Mincho"="TakaoMincho"
"MS PMincho"="TakaoPMincho"
"MS UI Gothic"="TakaoGothic"
"Yu Gothic"="Noto Sans CJK JP"
"Yu Gothic UI"="Noto Sans CJK JP"
"Meiryo"="IPAexGothic"
"Meiryo UI"="IPAexGothic"

[HKEY_CURRENT_USER\Software\Wine\Fonts\Replacements]
"MS Gothic"="TakaoGothic"
"MS PGothic"="TakaoPGothic"
"MS Mincho"="TakaoMincho"
"MS PMincho"="TakaoPMincho"
"MS UI Gothic"="TakaoGothic"

[HKEY_CURRENT_USER\Control Panel\International]
"Locale"="00000411"
"sCountry"="Japan"
"sLanguage"="JPN"
"iCountry"="81"
EOF

wine regedit /tmp/wine_jp_complete.reg

# 5. 環境変数設定ファイル
echo "5. MT5起動スクリプトを更新..."
cat > /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/start_mt5_japanese_complete.sh << 'EOF'
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
EOF

chmod +x /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/start_mt5_japanese_complete.sh

echo ""
echo "=== 設定完了 ==="
echo "MT5を日本語環境で起動: ./Scripts/start_mt5_japanese_complete.sh"
echo ""
echo "トラブルシューティング："
echo "- 文字化けする場合: winecfg でGraphicsタブのDPIを調整"
echo "- フォントが反映されない場合: ~/.wine を削除して再設定"