#!/bin/bash

# WSL環境セットアップスクリプト
# WSL移行後の完全環境復旧用

echo "=== WSL環境セットアップ開始 ==="

# 1. 必要なディレクトリの作成
echo "1. ディレクトリ構造の確認・作成"
mkdir -p ~/.claude
mkdir -p ~/.config/Code/User
mkdir -p ~/.vscode-server/extensions

# 2. 権限設定の修正
echo "2. 権限設定の修正"
sudo chown -R $USER:$USER $HOME 2>/dev/null || echo "権限修正をスキップ (sudoなし)"

# 3. Git設定の復旧
echo "3. Git設定の復旧"
git config --global user.name "trader"
git config --global user.email "trader@trading-development.local"
git config --global init.defaultBranch main

# 4. Python環境の確認
echo "4. Python環境の確認"
python3 --version
pip3 --version

# 5. Node.js環境の確認
echo "5. Node.js環境の確認"
node --version 2>/dev/null || echo "Node.js未インストール"
npm --version 2>/dev/null || echo "npm未インストール"

# 6. Claude設定の確認
echo "6. Claude設定の確認"
if [ -f ~/.claude/settings.json ]; then
    echo "✓ Claude設定ファイル存在"
else
    echo "✗ Claude設定ファイルが見つかりません"
fi

# 7. MCP設定の確認
echo "7. MCP設定の確認"
if [ -f .env.mcp ]; then
    echo "✓ MCP環境設定ファイル存在"
else
    echo "✗ MCP環境設定ファイルが見つかりません"
fi

# 8. cron自動化システムの確認
echo "8. cron自動化システムの確認"
crontab -l 2>/dev/null || echo "cron設定が見つかりません"

# 9. VSCode拡張機能のインストール
echo "9. VSCode拡張機能のインストール"
if command -v code &> /dev/null; then
    echo "VSCode CLI利用可能 - 拡張機能インストール開始"
    ./install_vscode_extensions.sh
else
    echo "VSCode CLI利用不可 - 手動インストールが必要"
fi

echo "=== WSL環境セットアップ完了 ==="
echo ""
echo "次のステップ:"
echo "1. VSCodeを起動して拡張機能を確認"
echo "2. Claude Codeでプロジェクトを開く"
echo "3. MCP設定を確認"
echo "4. cron自動化システムを確認"