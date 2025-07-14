#!/bin/bash

# VSCode拡張機能の一括インストールスクリプト

echo "=== VSCode拡張機能のインストール開始 ==="

# 拡張機能リスト
extensions=(
    "anthropic.claude-code"
    "eamodio.gitlens"
    "github.copilot"
    "github.copilot-chat"
    "gruntfuggly.todo-tree"
    "l-i-v.mql-tools"
    "mechatroner.rainbow-csv"
    "ms-ceintl.vscode-language-pack-ja"
    "ms-python.debugpy"
    "ms-python.python"
    "ms-python.vscode-pylance"
    "ms-vscode-remote.remote-wsl"
    "ms-vscode.cpptools"
    "ryu1kn.partial-diff"
    "shd101wyy.markdown-preview-enhanced"
)

# 各拡張機能をインストール
for extension in "${extensions[@]}"; do
    echo "インストール中: $extension"
    code --install-extension "$extension" --force
    if [ $? -eq 0 ]; then
        echo "✓ $extension インストール成功"
    else
        echo "✗ $extension インストール失敗"
    fi
done

echo "=== VSCode拡張機能のインストール完了 ==="
echo "VSCodeを再起動してください。"