#!/bin/bash

# VSCode WSL問題修正スクリプト

echo "=== VSCode WSL問題修正開始 ==="

# 1. tmpディレクトリの権限修正
echo "1. tmpディレクトリの権限修正"
sudo chmod 777 /tmp 2>/dev/null || chmod 755 /tmp 2>/dev/null || echo "権限修正スキップ"

# 2. VSCodeプロセスの完全終了
echo "2. VSCodeプロセスの完全終了"
pkill -f "code" 2>/dev/null || echo "VSCodeプロセスなし"

# 3. VSCode設定の確認・修正
echo "3. VSCode設定の確認・修正"
mkdir -p ~/.vscode-server/extensions
mkdir -p ~/.config/Code/User

# 4. .vscode/settings.jsonの作成
echo "4. プロジェクト設定の作成"
cat > .vscode/settings.json << 'EOF'
{
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/**": true,
        "**/.vscode/**": true
    },
    "files.exclude": {
        "**/.git": false,
        "**/.DS_Store": true,
        "**/Thumbs.db": true,
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/.mypy_cache": true,
        "**/.ruff_cache": true
    },
    "explorer.confirmDelete": false,
    "explorer.confirmDragAndDrop": false,
    "python.defaultInterpreterPath": "/usr/bin/python3",
    "python.terminal.activateEnvironment": false,
    "terminal.integrated.defaultProfile.linux": "bash",
    "remote.WSL.fileWatcher.polling": true,
    "remote.WSL.fileWatcher.pollingInterval": 5000,
    "files.autoSave": "afterDelay",
    "files.autoSaveDelay": 1000
}
EOF

# 5. workspace設定の作成
echo "5. workspace設定の作成"
cat > .vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "cwd": "${workspaceFolder}"
        }
    ]
}
EOF

# 6. 正しいディレクトリでVSCode起動
echo "6. 正しいディレクトリでVSCode起動"
cd /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト

# 7. WSL経由でVSCode起動（バックグラウンド）
echo "7. WSL経由でVSCode起動"
export DISPLAY=:0
code . --remote wsl+Ubuntu --disable-extension-host-worker 2>/dev/null &

echo "=== VSCode WSL問題修正完了 ==="
echo ""
echo "VSCode起動方法:"
echo "1. WSL内で: code ."
echo "2. Windows PowerShellで: wsl code ."
echo "3. WSL拡張機能でリモート接続"
echo ""
echo "エクスプローラー表示されない場合:"
echo "- View > Explorer (Ctrl+Shift+E)"
echo "- File > Open Folder でプロジェクトフォルダーを選択"