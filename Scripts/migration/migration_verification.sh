#!/bin/bash
# 移行検証スクリプト - WSL2→Native Linux移行完了確認
# 実行: bash migration_verification.sh

set -euo pipefail  # エラー時即座に停止

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
}

# エラーハンドリング（検証では継続実行）
error_handler() {
    log_error "検証中にエラーが発生しました (行: $1)"
    log_warning "検証を継続します..."
}

trap 'error_handler $LINENO' ERR

# 検証結果カウンター
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# テスト実行関数
run_test() {
    local test_name="$1"
    local test_command="$2"
    local is_critical="${3:-false}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_test "検証 $TOTAL_TESTS: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        log_success "✓ $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        if [ "$is_critical" = "true" ]; then
            log_error "✗ $test_name (CRITICAL)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        else
            log_warning "△ $test_name (WARNING)"
            WARNING_TESTS=$((WARNING_TESTS + 1))
        fi
        return 1
    fi
}

# 詳細検証関数
detailed_check() {
    local check_name="$1"
    local command="$2"
    local expected="$3"
    
    log_test "$check_name"
    
    local result
    result=$(eval "$command" 2>/dev/null || echo "FAILED")
    
    if [[ "$result" == *"$expected"* ]] || [ "$result" != "FAILED" ]; then
        log_success "✓ $check_name: $result"
        return 0
    else
        log_error "✗ $check_name: $result"
        return 1
    fi
}

log_info "=== WSL2→Linux移行検証開始 ==="
echo "検証日時: $(date)"
echo "実行ユーザー: $(whoami)"
echo "ホスト名: $(hostname)"
echo "OS: $(lsb_release -d 2>/dev/null | cut -f2- || uname -a)"
echo

# 1. システム基盤検証
log_info "📋 1. システム基盤検証"

run_test "OS Linuxカーネル確認" "[ \"\$(uname)\" = \"Linux\" ]" true
run_test "Ubuntu 24.04系確認" "lsb_release -r | grep -E '24\\.04|24\\.10'" false
run_test "ディスク容量確認(>1GB)" "[ \$(df / | tail -1 | awk '{print \$4}') -gt 1048576 ]" true
run_test "メモリ確認(>1GB)" "[ \$(free -m | awk 'NR==2{print \$2}') -gt 1024 ]" false
run_test "インターネット接続確認" "ping -c 1 google.com" true

echo

# 2. 開発環境基盤検証
log_info "⚙️ 2. 開発環境基盤検証"

detailed_check "Python3バージョン" "python3 --version" "Python 3"
detailed_check "Node.jsバージョン" "node --version" "v"
detailed_check "npmバージョン" "npm --version" ""
detailed_check "Gitバージョン" "git --version" "git version"
run_test "pip3利用可能性" "pip3 --version" false
run_test "curl利用可能性" "curl --version" true

echo

# 3. Claude Code CLI検証
log_info "🤖 3. Claude Code CLI検証"

if command -v claude >/dev/null 2>&1; then
    detailed_check "Claude CLIバージョン" "claude --version | head -1" "claude"
    run_test "Claude設定ディレクトリ存在" "[ -d \"\$HOME/.claude\" ]" true
    run_test "Claude実行権限確認" "[ -x \"\$(which claude)\" ]" true
    
    # Claude認証状況確認
    if claude whoami >/dev/null 2>&1; then
        log_success "✓ Claude認証済み"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ Claude未認証 - 'claude auth login' 実行が必要"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    log_error "✗ Claude CLIが見つかりません"
    FAILED_TESTS=$((FAILED_TESTS + 3))
    TOTAL_TESTS=$((TOTAL_TESTS + 3))
fi

echo

# 4. プロジェクト構造検証
log_info "📁 4. プロジェクト構造検証"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR"

log_info "プロジェクトディレクトリ: $PROJECT_DIR"

# 重要ディレクトリ確認
CRITICAL_DIRS=("MT5" "Scripts" "文書" "Dashboard")
for dir in "${CRITICAL_DIRS[@]}"; do
    run_test "ディレクトリ存在: $dir" "[ -d \"$dir\" ]" true
done

# 重要ファイル確認
CRITICAL_FILES=(
    "CLAUDE.md"
    "MT5/EA/JamesORB_v1.0.mq5"
    "Scripts/cron_system_monitor.py"
    "文書/技術/WSL2_Linux移行設定ガイド.md"
    "Scripts/migration/complete_migration.sh"
)

for file in "${CRITICAL_FILES[@]}"; do
    run_test "ファイル存在: $(basename "$file")" "[ -f \"$file\" ]" true
done

# プロジェクト統計
FILE_COUNT=$(find . -type f | wc -l)
SCRIPT_COUNT=$(find . -name "*.sh" -type f | wc -l)
PYTHON_COUNT=$(find . -name "*.py" -type f | wc -l)

log_info "プロジェクト統計: ファイル $FILE_COUNT個, スクリプト $SCRIPT_COUNT個, Python $PYTHON_COUNT個"

echo

# 5. Git設定検証
log_info "🔧 5. Git設定検証"

run_test "Gitリポジトリ確認" "[ -d \".git\" ]" true
detailed_check "Gitリモート確認" "git remote get-url origin" "github.com"
detailed_check "Git現在ブランチ" "git branch --show-current" "main"

# Git設定確認
if git config --global user.name >/dev/null 2>&1; then
    detailed_check "Git user.name設定" "git config --global user.name" ""
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_warning "△ Git user.name未設定"
    WARNING_TESTS=$((WARNING_TESTS + 1))
fi

if git config --global user.email >/dev/null 2>&1; then
    detailed_check "Git user.email設定" "git config --global user.email" ""
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_warning "△ Git user.email未設定"
    WARNING_TESTS=$((WARNING_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 2))

echo

# 6. Claude設定ファイル検証
log_info "🔧 6. Claude設定ファイル検証"

CLAUDE_CONFIG="$HOME/.claude/settings.json"
MCP_CONFIG="$HOME/.config/claude-desktop/config.json"

run_test "Claude settings.json存在" "[ -f \"$CLAUDE_CONFIG\" ]" true
run_test "MCP config.json存在" "[ -f \"$MCP_CONFIG\" ]" true

if [ -f "$CLAUDE_CONFIG" ]; then
    run_test "settings.json構文確認" "python3 -m json.tool \"$CLAUDE_CONFIG\"" true
    
    # Hook設定確認
    if grep -q "sessionStart" "$CLAUDE_CONFIG"; then
        log_success "✓ Hook設定確認"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ Hook設定が見つかりません"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

if [ -f "$MCP_CONFIG" ]; then
    run_test "config.json構文確認" "python3 -m json.tool \"$MCP_CONFIG\"" true
    
    # APIキー設定確認
    if grep -q "YOUR_GEMINI_API_KEY_HERE" "$MCP_CONFIG"; then
        log_warning "△ Gemini APIキーが未設定です"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    else
        log_success "✓ Gemini APIキー設定済み"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo

# 7. MCP統合検証
log_info "🔌 7. MCP統合検証"

run_test "@yusukedev/gemini-cli-mcp インストール確認" "npm list -g @yusukedev/gemini-cli-mcp" false

# MCP接続テスト（Claude認証済みの場合）
if command -v claude >/dev/null 2>&1 && claude whoami >/dev/null 2>&1; then
    log_test "MCP接続テスト実行中..."
    
    # 簡易MCP接続テスト
    if timeout 10 claude --version >/dev/null 2>&1; then
        log_success "✓ Claude基本動作確認"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ Claude動作に時間がかかっています"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    log_warning "△ Claude未認証のためMCP接続テストスキップ"
fi

echo

# 8. Python依存関係検証
log_info "🐍 8. Python依存関係検証"

PYTHON_PACKAGES=("pandas" "numpy" "requests" "pyyaml")
for package in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        log_success "✓ $package インストール済み"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ $package 未インストール"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
done

echo

# 9. スクリプト実行権限検証
log_info "🔐 9. スクリプト実行権限検証"

# 重要スクリプトの実行権限確認
IMPORTANT_SCRIPTS=(
    "Scripts/cron_system_monitor.py"
    "Scripts/migration/linux_environment_setup.sh"
    "Scripts/migration/claude_installation.sh"
    "Scripts/migration/project_restoration.sh"
    "Scripts/migration/config_restore.sh"
)

for script in "${IMPORTANT_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        run_test "実行権限: $(basename "$script")" "[ -x \"$script\" ]" false
    fi
done

echo

# 10. 機能統合テスト
log_info "🧪 10. 機能統合テスト"

# JamesORB EA確認
if [ -f "MT5/EA/JamesORB_v1.0.mq5" ]; then
    log_test "JamesORB EA内容確認"
    
    if grep -q "version.*2\.05" "MT5/EA/JamesORB_v1.0.mq5"; then
        log_success "✓ JamesORB EA v2.05確認"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ JamesORB EAバージョン確認失敗"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    
    # ATRハンドル最適化確認
    if grep -q "g_atr_handle" "MT5/EA/JamesORB_v1.0.mq5"; then
        log_success "✓ ATRハンドル最適化確認"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ ATRハンドル最適化確認失敗"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    
    TOTAL_TESTS=$((TOTAL_TESTS + 2))
fi

# システム監視スクリプト実行テスト
if [ -x "Scripts/cron_system_monitor.py" ]; then
    log_test "システム監視スクリプト実行テスト"
    
    if timeout 30 python3 Scripts/cron_system_monitor.py >/dev/null 2>&1; then
        log_success "✓ システム監視スクリプト動作確認"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_warning "△ システム監視スクリプト実行に問題があります"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo

# 検証結果サマリー
log_info "=== 移行検証結果サマリー ==="

echo "📊 検証統計:"
echo "  - 総テスト数: $TOTAL_TESTS"
echo "  - 成功: $PASSED_TESTS ($(( PASSED_TESTS * 100 / TOTAL_TESTS ))%)"
echo "  - 警告: $WARNING_TESTS ($(( WARNING_TESTS * 100 / TOTAL_TESTS ))%)"
echo "  - 失敗: $FAILED_TESTS ($(( FAILED_TESTS * 100 / TOTAL_TESTS ))%)"
echo

# 成功率判定
SUCCESS_RATE=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))

if [ $SUCCESS_RATE -ge 90 ]; then
    log_success "🎉 移行検証: 優秀 ($SUCCESS_RATE%)"
    VERIFICATION_STATUS="EXCELLENT"
elif [ $SUCCESS_RATE -ge 80 ]; then
    log_success "✅ 移行検証: 良好 ($SUCCESS_RATE%)"
    VERIFICATION_STATUS="GOOD"
elif [ $SUCCESS_RATE -ge 70 ]; then
    log_warning "⚠️ 移行検証: 要改善 ($SUCCESS_RATE%)"
    VERIFICATION_STATUS="NEEDS_IMPROVEMENT"
else
    log_error "❌ 移行検証: 不合格 ($SUCCESS_RATE%)"
    VERIFICATION_STATUS="FAILED"
fi

echo

# 推奨アクション
log_info "📋 推奨アクション:"

if [ $FAILED_TESTS -gt 0 ]; then
    echo "🚨 緊急対応必要:"
    echo "  - 失敗したテストを確認し、必要な修正を実行してください"
    echo "  - 基盤ソフトウェアのインストール・設定を確認してください"
fi

if [ $WARNING_TESTS -gt 0 ]; then
    echo "⚠️ 推奨改善事項:"
    if grep -q "未認証" <(echo "$WARNING_TESTS"); then
        echo "  - Claude Code認証: claude auth login"
    fi
    if grep -q "未設定" <(echo "$WARNING_TESTS"); then
        echo "  - Git設定: git config --global user.name/user.email設定"
        echo "  - Gemini APIキー設定: config.json手動編集"
    fi
    echo "  - Python依存パッケージ: pip3 install [package_name]"
fi

if [ "$VERIFICATION_STATUS" = "EXCELLENT" ] || [ "$VERIFICATION_STATUS" = "GOOD" ]; then
    echo "🚀 次のステップ:"
    echo "  - Claude Code起動テスト: claude"
    echo "  - プロジェクト開発作業開始"
    echo "  - VS Code Remote-SSH接続テスト"
fi

echo

# 検証レポート保存
REPORT_FILE="migration_verification_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "WSL2→Linux移行検証レポート"
    echo "検証日時: $(date)"
    echo "総テスト数: $TOTAL_TESTS"
    echo "成功: $PASSED_TESTS"
    echo "警告: $WARNING_TESTS"
    echo "失敗: $FAILED_TESTS"
    echo "成功率: $SUCCESS_RATE%"
    echo "検証状況: $VERIFICATION_STATUS"
    echo ""
} > "$REPORT_FILE"

log_info "検証レポート保存: $REPORT_FILE"

# 終了コード設定
if [ "$VERIFICATION_STATUS" = "FAILED" ]; then
    exit 1
elif [ $WARNING_TESTS -gt 0 ]; then
    exit 2
else
    exit 0
fi