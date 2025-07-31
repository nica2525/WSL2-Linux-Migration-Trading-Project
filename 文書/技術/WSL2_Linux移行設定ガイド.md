# WSL2 → Native Linux 移行設定ガイド

## 🎯 移行概要
**移行元**: Windows 11 WSL2 (Ubuntu)  
**移行先**: Ubuntu 24.04.2 LTS (Native Linux)  
**接続方式**: VS Code Remote-SSH  

## 📋 Phase 1: GitHub移行準備（完了）

### ✅ 実施済み項目
1. **プロジェクトディレクトリGitリポジトリ化**
   - 機密情報除外: `.gitignore`拡張版作成
   - 初期コミット完了: 170ファイル、33,646行追加
   - コミットID: `d6919ec`

2. **移行対象確認**
   - JamesORB EA v2.05 (Product-ready)
   - SubAgent機能完全復旧版
   - MCP統合システム (4サーバー構成)
   - 品質管理プロトコル拡張版
   - 統計分析システム Phase1完了版

## 📦 Phase 2: 重要設定ファイル

### 🔧 Claude Code設定

#### `~/.claude/settings.json`
**Hook自動化システム設定**:
```json
{
  "hooks": {
    "sessionStart": {
      "command": "/home/trader/.claude/hooks/sessionStart.sh",
      "description": "Sub-Agent品質管理システム起動チェック",
      "timeout": 30000,
      "showOutput": true
    },
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command", 
            "command": "/bin/bash /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/session_record_rule_checker.sh"
          },
          {
            "type": "command",
            "command": "/bin/bash /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/document_rule_enforcer.sh"
          }
        ]
      },
      {
        "matcher": "Edit.*JamesORB.*\\.mq5",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/ea_version_control_rules_safe.sh"
          }
        ]
      },
      {
        "matcher": "Edit.*\\.mq5|Write.*\\.mq5",
        "hooks": [
          {
            "type": "command",
            "command": "/home/trader/.claude/hooks/mql5_implementation_guardian.sh \"${file_path}\" \"${operation}\"",
            "description": "MQL5実装前検証（Hook統合システム）",
            "timeout": 15000,
            "showOutput": true
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/memory_tracker_hook.sh"
          }
        ]
      }
    ]
  },
  "slashCommands": {
    "/session-start": "セッション開始時の必須確認プロトコルを実行",
    "/backtest-check": "MT5バックテスト状況確認"
  }
}
```

#### `~/.config/claude-desktop/config.json`
**MCP統合設定**:
```json
{
  "mcpServers": {
    "gemini": {
      "command": "npx",
      "args": ["-y", "@yusukedev/gemini-cli-mcp"],
      "env": {
        "GEMINI_API_KEY": "AIzaSyCk-pjU3V1VO8rRpHMR9mIfhBRwB6AD7oY",
        "GEMINI_MODEL": "gemini-2.0-flash",
        "GEMINI_TIMEOUT": "180000",
        "GEMINI_AUTO_FALLBACK": "true"
      }
    }
  }
}
```

### ⚡ cron自動化システム設定

#### 現在の状況
- **cron設定**: 現在削除済み（`no crontab for trader`）
- **自動化廃止理由**: Gemini査読により危険性指摘、手動実行に変更

#### 以前の設定（参考）
```bash
# Git自動保存（3分間隔）
*/3 * * * * /usr/bin/flock -n /tmp/git_auto_save.lock /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_git_auto_save.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_git_auto_save.log 2>&1

# システム監視（5分間隔）
*/5 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_system_monitor.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_monitor.log 2>&1
```

## 🚀 Phase 3: Linux移行手順

### 1. GitHub手動リポジトリ作成
1. **GitHub Web UI**でプライベートリポジトリ作成:
   - リポジトリ名: `WSL2-Linux-Migration-Trading-Project`
   - 説明: `WSL2からNative Linuxへの移行: JamesORB EA開発環境完全バックアップ`
   - プライベート設定

2. **リモート追加・プッシュ**:
```bash
git remote add origin https://github.com/nica2525/WSL2-Linux-Migration-Trading-Project.git
git branch -M main
git push -u origin main
```

### 2. Linux環境準備
```bash
# Node.js・npm（MCP必須）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python3・pip（スクリプト実行）
sudo apt-get update
sudo apt-get install -y python3 python3-pip

# Claude Code CLI（最新版）
# インストール手順はClaude公式サイト参照

# Git設定
git config --global user.name "nica2525"
git config --global user.email "your-email@domain.com"
```

### 3. プロジェクトクローン・復元
```bash
# プロジェクトクローン
cd /home/username
mkdir -p Trading-Development
cd Trading-Development
git clone https://github.com/nica2525/WSL2-Linux-Migration-Trading-Project.git 2.ブレイクアウト手法プロジェクト

# 権限復元
chmod +x 2.ブレイクアウト手法プロジェクト/Scripts/*.sh
chmod +x 2.ブレイクアウト手法プロジェクト/Scripts/*.py
```

### 4. Claude・MCP設定復元
```bash
# Claude設定ディレクトリ作成
mkdir -p ~/.claude/hooks
mkdir -p ~/.config/claude-desktop

# 設定ファイル復元（手動コピー）
# ~/.claude/settings.json
# ~/.config/claude-desktop/config.json

# MCP必要パッケージインストール
npm install -g @yusukedev/gemini-cli-mcp
```

### 5. VS Code Remote-SSH設定
```bash
# VS Code Server自動インストール確認
# 接続テスト・拡張機能同期確認
```

## 🔍 検証チェックリスト

### ✅ 移行完了確認項目
- [ ] GitHubリポジトリ正常作成・プッシュ完了
- [ ] Linux環境でのプロジェクトクローン成功
- [ ] Claude Code基本動作確認
- [ ] MCP 4サーバー接続確認 (filesystem, context7, fetch, gemini)
- [ ] SubAgent機能動作確認（3種エージェント）
- [ ] JamesORB EA v2.05読み込み・動作確認
- [ ] Hook自動化システム動作確認
- [ ] 統計分析システム動作確認
- [ ] VS Code Remote-SSH開発環境確認

### ⚠️ 既知の課題・注意事項
1. **MCP Gemini APIキー**: 機密情報のため手動設定必要
2. **Hook絶対パス**: Linux環境でのパス調整必要
3. **cron自動化**: 手動実行方式への変更推奨
4. **SubAgent安定性**: 完全復旧済みだが、大規模コンテキスト注意

## 📈 期待される効果

### パフォーマンス向上
- **WSL2制約排除**: 仮想化レイヤー5%性能劣化解消
- **I/O性能向上**: /mnt/c/アクセスの30-50倍速度低下解消
- **stdio transport最適化**: MCP通信安定性向上

### 開発効率向上
- **SubAgent機能**: 149ファイル依存関係解析2-3分完了
- **品質管理**: 拡張3段階レビューシステム継続
- **統計分析**: Phase1完了システムの継続活用

---

**最終更新**: 2025-07-31  
**作成者**: Claude (WSL2→Linux移行準備段階)