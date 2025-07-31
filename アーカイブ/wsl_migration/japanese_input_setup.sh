#!/bin/bash

# 日本語入力問題自動修正スクリプト

echo "=== 日本語入力問題修正開始 ==="

# 1. 日本語ロケールの設定
echo "1. 日本語ロケールの設定"
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8

# 2. .bashrcに環境変数を追加
echo "2. .bashrcに環境変数を追加"
if ! grep -q "export LANG=ja_JP.UTF-8" ~/.bashrc; then
    echo 'export LANG=ja_JP.UTF-8' >> ~/.bashrc
    echo 'export LC_ALL=ja_JP.UTF-8' >> ~/.bashrc
    echo '✓ 環境変数を.bashrcに追加しました'
else
    echo '✓ 環境変数は既に設定済みです'
fi

# 3. VSCode用の設定ファイルを作成
echo "3. VSCode用設定ファイルの作成"
mkdir -p ~/.config/Code/User
cat > ~/.config/Code/User/settings.json << 'EOF'
{
    "keyboard.dispatch": "keyCode",
    "terminal.integrated.allowChords": false,
    "terminal.integrated.detectLocale": "auto",
    "terminal.integrated.inheritEnv": true,
    "terminal.integrated.profiles.linux": {
        "bash": {
            "path": "bash",
            "args": [],
            "env": {
                "LANG": "ja_JP.UTF-8",
                "LC_ALL": "ja_JP.UTF-8"
            }
        }
    },
    "terminal.integrated.commandsToSkipShell": [
        "language-status.show"
    ]
}
EOF

# 4. Claude用の設定ファイルを作成
echo "4. Claude用設定ファイルの作成"
mkdir -p ~/.claude
cat > ~/.claude/terminal.json << 'EOF'
{
    "terminal": {
        "shell": "/bin/bash",
        "env": {
            "LANG": "ja_JP.UTF-8",
            "LC_ALL": "ja_JP.UTF-8"
        }
    }
}
EOF

# 5. 現在のターミナルに設定を適用
echo "5. 現在のターミナルに設定を適用"
source ~/.bashrc

echo "=== 日本語入力問題修正完了 ==="
echo ""
echo "設定が完了しました。以下の方法で日本語入力を試してください:"
echo ""
echo "🔧 キーボードショートカット:"
echo "- Alt + ` (半角/全角キー)"
echo "- Ctrl + Space"
echo "- Windows + Space"
echo ""
echo "📋 確認方法:"
echo "1. 新しいターミナルを開く"
echo "2. echo LANG で ja_JP.UTF-8 が表示されるか確認"
echo "3. VSCodeを再起動"
echo ""
echo "⚠️  まだ問題が続く場合は、以下を試してください:"
echo "1. Windows側のIME設定を確認"
echo "2. VSCodeの拡張機能「Japanese Language Pack」をインストール"
echo "3. WSL再起動: wsl --shutdown && wsl"
