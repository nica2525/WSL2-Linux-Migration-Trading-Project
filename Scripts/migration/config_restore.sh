#!/bin/bash
# 設定ファイル自動復元スクリプト - WSL2→Native Linux移行
# 実行: bash config_restore.sh

set -euo pipefail  # エラー時即座に停止

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# エラーハンドリング
error_handler() {
    log_error "設定ファイル復元中にエラーが発生しました (行: $1)"
    log_error "復元を中止します。問題を確認してください。"
    exit 1
}

trap 'error_handler $LINENO' ERR

log_info "=== WSL2→Linux移行: 設定ファイル復元開始 ==="

# 1. 環境変数・パス設定
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLAUDE_CONFIG_DIR="$HOME/.claude"
CLAUDE_HOOKS_DIR="$CLAUDE_CONFIG_DIR/hooks"
CLAUDE_DESKTOP_CONFIG_DIR="$HOME/.config/claude-desktop"

log_info "設定情報:"
echo "  - プロジェクトディレクトリ: $PROJECT_DIR"
echo "  - Claude設定ディレクトリ: $CLAUDE_CONFIG_DIR"
echo "  - Claude Desktop設定ディレクトリ: $CLAUDE_DESKTOP_CONFIG_DIR"

# 2. ディレクトリ作成
log_info "設定ディレクトリ作成中..."
mkdir -p "$CLAUDE_CONFIG_DIR"
mkdir -p "$CLAUDE_HOOKS_DIR"
mkdir -p "$CLAUDE_DESKTOP_CONFIG_DIR"

log_success "設定ディレクトリ作成完了"

# 3. Claude Code Hooks設定復元
log_info "Claude Code Hooks設定復元中..."

# settings.json テンプレート作成
cat > "$CLAUDE_CONFIG_DIR/settings.json" << EOF
{
  "hooks": {
    "sessionStart": {
      "command": "$CLAUDE_HOOKS_DIR/sessionStart.sh",
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
            "command": "/bin/bash $PROJECT_DIR/Scripts/session_record_rule_checker.sh"
          },
          {
            "type": "command",
            "command": "/bin/bash $PROJECT_DIR/Scripts/document_rule_enforcer.sh"
          }
        ]
      },
      {
        "matcher": "Edit.*JamesORB.*\\\\.mq5",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash $PROJECT_DIR/Scripts/ea_version_control_rules_safe.sh"
          }
        ]
      },
      {
        "matcher": "Edit.*\\\\.mq5|Write.*\\\\.mq5",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_HOOKS_DIR/mql5_implementation_guardian.sh \\\"\\\${file_path}\\\" \\\"\\\${operation}\\\"",
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
            "command": "/bin/bash $PROJECT_DIR/Scripts/memory_tracker_hook.sh"
          }
        ]
      },
      {
        "matcher": "Edit.*JamesORB.*\\\\.mq5",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash $PROJECT_DIR/Scripts/ea_post_edit_sync_safe.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash $PROJECT_DIR/Scripts/session_start_memory.sh"
          }
        ]
      }
    ],
    "onError": {
      "command": "$CLAUDE_HOOKS_DIR/error_learning_system.sh \\\"\\\${error_type}\\\" \\\"\\\${error_message}\\\" \\\"\\\${source}\\\"",
      "description": "エラー発生時自動学習システム",
      "timeout": 15000,
      "showOutput": false
    }
  },
  "slashCommands": {
    "/session-start": "セッション開始時の必須確認プロトコルを実行:\\n1. cron自動化システム確認\\n2. 最新セッション記録確認\\n3. Git作業履歴確認\\n4. 品質状況確認\\n5. マネージャー学習ログ確認",
    "/backtest-check": "MT5バックテスト状況確認:\\n1. MT5_Results/フォルダ確認\\n2. 最新xlsx結果ファイル確認（Reportバックテスト・Reportフォワード）\\n3. 操作ログ.txt確認\\n4. JamesORB EA動作分析\\n5. 次回作業項目整理"
  },
  "feedbackSurveyState": {
    "lastShownTime": $(date +%s)000
  }
}
EOF

log_success "Claude Code settings.json 復元完了"

# 4. Hookスクリプト作成
log_info "Hookスクリプト作成中..."

# sessionStart.sh 作成
cat > "$CLAUDE_HOOKS_DIR/sessionStart.sh" << 'EOF'
#!/bin/bash
# セッション開始時チェックスクリプト

echo "🚀 Sub-Agent品質管理システム起動チェック"

# 基本システム確認
echo "✅ システム時刻: $(date)"
echo "✅ 作業ディレクトリ: $(pwd)"

# Python・Node.js確認
if command -v python3 >/dev/null 2>&1; then
    echo "✅ Python: $(python3 --version)"
else
    echo "❌ Python3が見つかりません"
fi

if command -v node >/dev/null 2>&1; then
    echo "✅ Node.js: $(node --version)"
else
    echo "❌ Node.jsが見つかりません"
fi

# MCP接続確認（簡易）
if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude Code: $(claude --version 2>/dev/null | head -1 || echo '確認失敗')"
else
    echo "❌ Claude Codeが見つかりません"
fi

echo "🎯 セッション開始準備完了"
EOF

chmod +x "$CLAUDE_HOOKS_DIR/sessionStart.sh"

# mql5_implementation_guardian.sh 作成
cat > "$CLAUDE_HOOKS_DIR/mql5_implementation_guardian.sh" << 'EOF'
#!/bin/bash
# MQL5実装前検証スクリプト

FILE_PATH="$1"
OPERATION="$2"

echo "🛡️ MQL5実装前検証開始"
echo "ファイル: $FILE_PATH"
echo "操作: $OPERATION"

# ファイル存在確認
if [ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ]; then
    echo "✅ ファイル確認: $(basename "$FILE_PATH")"
    
    # MQL5構文の基本チェック
    if grep -q "OnInit\|OnTick\|OnDeinit" "$FILE_PATH"; then
        echo "✅ MQL5基本構造確認"
    else
        echo "⚠️ MQL5基本構造の確認推奨"
    fi
    
    # 危険なパターンチェック
    if grep -q "delete\|free\|malloc" "$FILE_PATH"; then
        echo "⚠️ メモリ管理関数が検出されました - 慎重に確認してください"
    fi
    
else
    echo "⚠️ ファイルパスが未指定または存在しません"
fi

echo "🎯 MQL5実装前検証完了"
EOF

chmod +x "$CLAUDE_HOOKS_DIR/mql5_implementation_guardian.sh"

# error_learning_system.sh 作成
cat > "$CLAUDE_HOOKS_DIR/error_learning_system.sh" << 'EOF'
#!/bin/bash
# エラー学習システム

ERROR_TYPE="$1"
ERROR_MESSAGE="$2"
SOURCE="$3"

echo "🚨 エラー学習システム起動"
echo "エラータイプ: $ERROR_TYPE"
echo "ソース: $SOURCE"

# ログファイル作成
LOG_FILE="$HOME/.claude/error_learning.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] $ERROR_TYPE - $SOURCE: $ERROR_MESSAGE" >> "$LOG_FILE"

echo "📝 エラーログ記録完了: $LOG_FILE"
EOF

chmod +x "$CLAUDE_HOOKS_DIR/error_learning_system.sh"

log_success "Hookスクリプト作成完了"

# 5. MCP設定復元
log_info "MCP設定復元中..."

# config.json テンプレート作成（APIキー要手動入力）
cat > "$CLAUDE_DESKTOP_CONFIG_DIR/config.json" << 'EOF'
{
  "mcpServers": {
    "gemini": {
      "command": "npx",
      "args": ["-y", "@yusukedev/gemini-cli-mcp"],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE",
        "GEMINI_MODEL": "gemini-2.0-flash",
        "GEMINI_TIMEOUT": "180000",
        "GEMINI_AUTO_FALLBACK": "true"
      }
    }
  }
}
EOF

log_warning "MCP設定ファイル作成完了 - APIキーの手動設定が必要です"

# 6. パス調整の実行
log_info "設定ファイル内のパス調整実行中..."

# settings.jsonの絶対パス確認・調整
if [ -f "$CLAUDE_CONFIG_DIR/settings.json" ]; then
    # パス置換実行（実際のパスで更新済み）
    log_success "settings.json パス調整完了"
else
    log_error "settings.json が見つかりません"
    exit 1
fi

# 7. 設定ファイル権限設定
log_info "設定ファイル権限設定中..."

# 適切な権限設定
chmod 600 "$CLAUDE_CONFIG_DIR/settings.json" 2>/dev/null || true
chmod 600 "$CLAUDE_DESKTOP_CONFIG_DIR/config.json" 2>/dev/null || true
chmod -R 755 "$CLAUDE_HOOKS_DIR" 2>/dev/null || true

log_success "設定ファイル権限設定完了"

# 8. 設定内容検証
log_info "設定内容検証中..."

# settings.json構文チェック
if ! python3 -m json.tool "$CLAUDE_CONFIG_DIR/settings.json" >/dev/null 2>&1; then
    log_error "settings.json の構文エラーが検出されました"
    exit 1
fi

# config.json構文チェック
if ! python3 -m json.tool "$CLAUDE_DESKTOP_CONFIG_DIR/config.json" >/dev/null 2>&1; then
    log_error "config.json の構文エラーが検出されました"
    exit 1
fi

log_success "設定ファイル構文検証完了"

# 9. 依存スクリプト存在確認
log_info "依存スクリプト存在確認中..."

REQUIRED_SCRIPTS=(
    "$PROJECT_DIR/Scripts/session_record_rule_checker.sh"
    "$PROJECT_DIR/Scripts/document_rule_enforcer.sh"
    "$PROJECT_DIR/Scripts/ea_version_control_rules_safe.sh"
    "$PROJECT_DIR/Scripts/memory_tracker_hook.sh"
    "$PROJECT_DIR/Scripts/ea_post_edit_sync_safe.sh"
    "$PROJECT_DIR/Scripts/session_start_memory.sh"
)

MISSING_SCRIPTS=()
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        # 実行権限確認・付与
        chmod +x "$script" 2>/dev/null || true
        log_success "✓ $(basename "$script")"
    else
        log_warning "✗ $(basename "$script") (見つかりません)"
        MISSING_SCRIPTS+=("$script")
    fi
done

if [ ${#MISSING_SCRIPTS[@]} -gt 0 ]; then
    log_warning "一部のスクリプトが見つかりません。機能制限がある可能性があります。"
fi

# 10. 最終設定確認
log_info "最終設定確認..."

echo "📋 復元された設定:"
echo "  - Claude設定: $CLAUDE_CONFIG_DIR/settings.json"
echo "  - MCP設定: $CLAUDE_DESKTOP_CONFIG_DIR/config.json"
echo "  - Hooksスクリプト: $CLAUDE_HOOKS_DIR/ ($(ls "$CLAUDE_HOOKS_DIR" | wc -l)個)"
echo "  - 依存スクリプト: $(( ${#REQUIRED_SCRIPTS[@]} - ${#MISSING_SCRIPTS[@]} ))/${#REQUIRED_SCRIPTS[@]} 個利用可能"

# 11. 手動設定必要事項の表示
log_success "=== 設定ファイル復元完了 ==="
echo
echo "🔧 手動設定が必要な項目:"
echo
echo "1. **Gemini APIキー設定** (必須):"
echo "   ファイル: $CLAUDE_DESKTOP_CONFIG_DIR/config.json"
echo "   設定項目: GEMINI_API_KEY"
echo "   現在の値: YOUR_GEMINI_API_KEY_HERE"
echo "   → 実際のGemini APIキーに置換してください"
echo
echo "2. **Claude Code認証** (必須):"
echo "   実行コマンド: claude auth login"
echo
echo "3. **Git設定確認** (推奨):"
echo "   git config --global user.name \"Your Name\""
echo "   git config --global user.email \"your.email@domain.com\""
echo
echo "🚀 次のステップ:"
echo "  1. APIキー設定完了後、移行検証を実行:"
echo "     bash Scripts/migration/migration_verification.sh"
echo "  2. Claude Code起動テスト:"
echo "     claude --version"
echo

# 12. APIキー設定ヘルパー
read -p "今すぐGemini APIキーを設定しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Gemini APIキーを入力してください:"
    read -r API_KEY
    
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "YOUR_GEMINI_API_KEY_HERE" ]; then
        # APIキー置換
        sed -i "s/YOUR_GEMINI_API_KEY_HERE/$API_KEY/g" "$CLAUDE_DESKTOP_CONFIG_DIR/config.json"
        log_success "Gemini APIキー設定完了"
        
        # 設定ファイル権限再設定
        chmod 600 "$CLAUDE_DESKTOP_CONFIG_DIR/config.json"
        
        echo "🎉 MCP設定が完了しました！"
    else
        log_warning "APIキーが入力されませんでした。後で手動設定してください。"
    fi
else
    log_info "APIキー設定は後で手動実行してください"
fi

log_info "設定ファイル復元が正常に完了しました"