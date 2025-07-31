#!/bin/bash

# WSL移行完了スクリプト
# 新環境（Ubuntu-E）で実行する完全移行スクリプト

set -e
echo "🔧 WSL移行完了スクリプト開始 - $(date)"

# 現在の環境確認
echo "📍 現在の環境確認:"
echo "ホスト名: $(hostname)"
echo "ユーザー: $(whoami)"
echo "ホーム: $HOME"
echo "現在地: $(pwd)"

# 1. プロジェクトディレクトリの移行
echo "🔄 1. プロジェクトディレクトリの移行"
if [ ! -d "$HOME/Trading-Development" ]; then
    echo "プロジェクトディレクトリを移行中..."
    cp -r /mnt/e/Trading-Development $HOME/Trading-Development
    echo "✅ プロジェクト移行完了"
else
    echo "⚠️  プロジェクトディレクトリは既に存在します"
fi

# 移行先に移動
cd $HOME/Trading-Development/2.ブレイクアウト手法プロジェクト

# 2. cron設定の復旧
echo "🔄 2. cron設定の復旧"
cat > temp_crontab.txt << 'EOF'
*/3 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_git_auto_save.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_git_auto_save.log 2>&1
*/5 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_system_monitor.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_monitor.log 2>&1
EOF

crontab temp_crontab.txt
rm temp_crontab.txt
echo "✅ cron設定復旧完了"

# 3. Claude設定の更新
echo "🔄 3. Claude設定の更新"
# バックアップ作成
cp ~/.claude/settings.json ~/.claude/settings_pre_migration_backup.json

# 新しいClaude設定を作成
cat > ~/.claude/settings.json << 'EOF'
{
  "mcpServers": {
    "duckdb": {
      "command": "/home/trader/.local/bin/uvx",
      "args": ["mcp-server-duckdb", "--db-path", "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/mcp_data/backtest_analysis.db"],
      "env": {
        "PATH": "/home/trader/.local/bin:$PATH"
      }
    },
    "neon": {
      "command": "npx",
      "args": ["-y", "@neondatabase/mcp-server-neon", "start", "napi_0jpaa7mcu9n6163o1nx9lsnvqmd7tlhy3oc3nz8u5yvh95y9zgx3mrzo3ktxlwh4"],
      "env": {
        "NODE_ENV": "production"
      }
    },
    "sqlite": {
      "command": "python",
      "args": ["-m", "mcp_server_sqlite", "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/mcp_data/trading_analysis.db"],
      "env": {
        "PATH": "/home/trader/.local/bin:$PATH"
      }
    },
    "postgres": {
      "command": "/home/trader/miniconda3/envs/python312/bin/python",
      "args": ["-m", "mcp_server_postgres", "--host", "localhost", "--port", "5432", "--database", "trading_analysis"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://localhost:5432/trading_analysis"
      }
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "PLACEHOLDER_TOKEN_HERE"
      }
    },
    "docker": {
      "command": "npx",
      "args": ["mcp-server-docker"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  },
  "projects": {
    "trading-breakout": {
      "name": "ブレイクアウト手法プロジェクト",
      "path": "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト",
      "description": "MT4自動売買システム開発・MCP統合環境",
      "tags": ["trading", "mt4", "mcp", "ai"],
      "lastAccessed": "2025-07-14"
    }
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash",
            "args": [
              "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/memory_tracker_hook.sh"
            ]
          }
        ]
      }
    ],
    "Start": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash",
            "args": [
              "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/session_start_memory.sh"
            ]
          }
        ]
      }
    ]
  }
}
EOF
echo "✅ Claude設定更新完了"

# 4. VSCode拡張機能の復旧
echo "🔄 4. VSCode拡張機能の復旧"
if [ -f "vscode_extensions_backup.txt" ]; then
    echo "VSCode拡張機能を復旧中..."
    while IFS= read -r extension; do
        if [ -n "$extension" ]; then
            echo "インストール中: $extension"
            code --install-extension "$extension" --force
        fi
    done < vscode_extensions_backup.txt
    echo "✅ VSCode拡張機能復旧完了"
else
    echo "⚠️  VSCode拡張機能バックアップファイルが見つかりません"
fi

# 5. 動作確認
echo "🧪 5. 動作確認"

# cron動作確認
echo "cron動作確認:"
ps aux | grep cron | grep -v grep || echo "cronサービスが起動していません"

# Git動作確認
echo "Git動作確認:"
git status

# Claude設定確認
echo "Claude設定確認:"
cat ~/.claude/settings.json | grep "Trading-Development" | head -3

# 6. 移行完了メッセージ
echo "🎉 WSL移行完了!"
echo "📊 移行完了サマリー:"
echo "- プロジェクトパス: $HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
echo "- cron設定: 復旧済み"
echo "- Claude設定: 更新済み"
echo "- VSCode拡張機能: 復旧済み"
echo ""
echo "🔄 次のステップ:"
echo "1. VSCodeを再起動してください"
echo "2. WSL Remote拡張で新環境に接続してください"
echo "3. Claude Codeの動作を確認してください"
echo ""
echo "📝 移行完了時刻: $(date)"
