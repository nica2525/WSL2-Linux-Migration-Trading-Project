#!/bin/bash
# トラブルシューティング・サポートスクリプト - WSL2→Native Linux移行
# 実行: bash troubleshoot_helper.sh

set -euo pipefail

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

log_fix() {
    echo -e "${CYAN}[FIX]${NC} $1"
}

show_menu() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                  Migration Troubleshooter                   ║
║                WSL2 → Linux 移行サポート                     ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    echo "🔧 利用可能な修復オプション:"
    echo "  1. 環境構築問題の診断・修復"
    echo "  2. Claude CLI インストール問題の修復"
    echo "  3. プロジェクト復元問題の診断・修復"
    echo "  4. 設定ファイル問題の診断・修復"
    echo "  5. MCP接続問題の診断・修復"
    echo "  6. 権限問題の一括修復"
    echo "  7. 全体診断・包括的修復"
    echo "  8. システム情報表示"
    echo "  9. ログファイル分析"
    echo "  0. 終了"
    echo
}

main() {
    while true; do
        show_menu
        read -p "選択してください (0-9): " choice
        echo
        
        case $choice in
            1) fix_environment_issues ;;
            2) fix_claude_installation ;;
            3) fix_project_restoration ;;
            4) fix_config_files ;;
            5) fix_mcp_connection ;;
            6) fix_permissions ;;
            7) comprehensive_diagnosis ;;
            8) show_system_info ;;
            9) analyze_logs ;;
            0) 
                log_info "トラブルシューティングを終了します"
                exit 0
                ;;
            *)
                log_error "無効な選択です: $choice"
                ;;
        esac
        
        echo
        read -p "続行するには Enter を押してください..."
        clear
    done
}

fix_environment_issues() {
    log_info "=== 環境構築問題の診断・修復 ==="
    
    # Python3確認・修復
    if ! command -v python3 >/dev/null 2>&1; then
        log_warning "Python3が見つかりません"
        log_fix "Python3インストール中..."
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-pip
        log_success "Python3インストール完了"
    else
        log_success "Python3確認: $(python3 --version)"
    fi
    
    # Node.js確認・修復
    if ! command -v node >/dev/null 2>&1 || [ "$(node --version | cut -d'v' -f2 | cut -d'.' -f1)" -lt "18" ]; then
        log_warning "Node.js 18+が見つかりません"
        log_fix "Node.js 20.x インストール中..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
        log_success "Node.jsインストール完了: $(node --version)"
    else
        log_success "Node.js確認: $(node --version)"
    fi
    
    # 基本パッケージ確認
    MISSING_PACKAGES=()
    CHECK_PACKAGES=("curl" "wget" "git" "build-essential")
    
    for package in "${CHECK_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        log_warning "不足パッケージ: ${MISSING_PACKAGES[*]}"
        log_fix "パッケージインストール中..."
        sudo apt-get install -y "${MISSING_PACKAGES[@]}"
        log_success "パッケージインストール完了"
    else
        log_success "基本パッケージ確認完了"
    fi
    
    # Python依存関係確認
    PYTHON_PACKAGES=("pandas" "numpy" "requests" "pyyaml")
    MISSING_PYTHON=()
    
    for package in "${PYTHON_PACKAGES[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            MISSING_PYTHON+=("$package")
        fi
    done
    
    if [ ${#MISSING_PYTHON[@]} -gt 0 ]; then
        log_warning "不足Pythonパッケージ: ${MISSING_PYTHON[*]}"
        log_fix "Pythonパッケージインストール中..."
        pip3 install --user "${MISSING_PYTHON[@]}"
        log_success "Pythonパッケージインストール完了"
    else
        log_success "Pythonパッケージ確認完了"
    fi
}

fix_claude_installation() {
    log_info "=== Claude CLI インストール問題の修復 ==="
    
    # Claude CLI確認
    if ! command -v claude >/dev/null 2>&1; then
        log_warning "Claude CLIが見つかりません"
        log_fix "Claude CLI自動インストール実行中..."
        
        # 一時ディレクトリでスクリプト実行
        TEMP_DIR=$(mktemp -d)
        trap "rm -rf $TEMP_DIR" EXIT
        
        SCRIPT_URL="https://raw.githubusercontent.com/nica2525/WSL2-Linux-Migration-Trading-Project/main/Scripts/migration/claude_installation.sh"
        
        if curl -fsSL "$SCRIPT_URL" > "$TEMP_DIR/claude_installation.sh"; then
            chmod +x "$TEMP_DIR/claude_installation.sh"
            echo "y" | bash "$TEMP_DIR/claude_installation.sh"
            
            # PATH反映
            export PATH="$HOME/.local/bin:$PATH"
            
            if command -v claude >/dev/null 2>&1; then
                log_success "Claude CLIインストール完了"
            else
                log_error "Claude CLIインストールに失敗しました"
            fi
        else
            log_error "インストールスクリプトのダウンロードに失敗しました"
        fi
    else
        log_success "Claude CLI確認: $(claude --version | head -1)"
        
        # 認証状況確認
        if claude whoami >/dev/null 2>&1; then
            log_success "Claude認証済み"
        else
            log_warning "Claude未認証です"
            log_info "認証するには: claude auth login"
        fi
    fi
    
    # PATH問題修復
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        log_warning "~/.local/bin がPATHに含まれていません"
        log_fix "PATH設定修復中..."
        
        # .bashrcにPATH追加
        if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$HOME/.bashrc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
            log_success ".bashrcにPATH設定追加完了"
        fi
        
        export PATH="$HOME/.local/bin:$PATH"
        log_success "現在のセッションでPATH設定完了"
    fi
}

fix_project_restoration() {
    log_info "=== プロジェクト復元問題の診断・修復 ==="
    
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    
    # プロジェクトディレクトリ確認
    if [ ! -d "$PROJECT_DIR" ]; then
        log_warning "プロジェクトディレクトリが見つかりません"
        log_fix "プロジェクト復元実行中..."
        
        mkdir -p "$HOME/Trading-Development"
        cd "$HOME/Trading-Development"
        
        if git clone https://github.com/nica2525/WSL2-Linux-Migration-Trading-Project.git "2.ブレイクアウト手法プロジェクト"; then
            log_success "プロジェクトクローン完了"
        else
            log_error "プロジェクトクローンに失敗しました"
            return 1
        fi
    else
        log_success "プロジェクトディレクトリ確認: $PROJECT_DIR"
    fi
    
    cd "$PROJECT_DIR"
    
    # 重要ファイル確認・修復
    CRITICAL_FILES=(
        "CLAUDE.md"
        "MT5/EA/JamesORB_v1.0.mq5"
        "Scripts/cron_system_monitor.py"
    )
    
    MISSING_FILES=()
    for file in "${CRITICAL_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            MISSING_FILES+=("$file")
        fi
    done
    
    if [ ${#MISSING_FILES[@]} -gt 0 ]; then
        log_warning "不足ファイル: ${MISSING_FILES[*]}"
        log_fix "Git pull実行で修復中..."
        
        git pull origin main
        log_success "ファイル同期完了"
    else
        log_success "重要ファイル確認完了"
    fi
    
    # 実行権限修復
    log_fix "実行権限修復中..."
    find Scripts -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true
    find Scripts -name "*.py" -type f -exec chmod +x {} \; 2>/dev/null || true
    log_success "実行権限修復完了"
}

fix_config_files() {
    log_info "=== 設定ファイル問題の診断・修復 ==="
    
    CLAUDE_CONFIG="$HOME/.claude/settings.json"
    MCP_CONFIG="$HOME/.config/claude-desktop/config.json"
    
    # Claude設定ファイル確認・修復
    if [ ! -f "$CLAUDE_CONFIG" ]; then
        log_warning "Claude設定ファイルが見つかりません"
        log_fix "設定ファイル復元実行中..."
        
        PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
        if [ -d "$PROJECT_DIR" ] && [ -x "$PROJECT_DIR/Scripts/migration/config_restore.sh" ]; then
            cd "$PROJECT_DIR"
            echo "n" | bash Scripts/migration/config_restore.sh
            log_success "設定ファイル復元完了"
        else
            log_error "設定復元スクリプトが見つかりません"
        fi
    else
        # 構文確認
        if python3 -m json.tool "$CLAUDE_CONFIG" >/dev/null 2>&1; then
            log_success "Claude設定ファイル構文確認完了"
        else
            log_error "Claude設定ファイル構文エラー"
            log_fix "バックアップ作成後、再生成します..."
            cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup"
            
            # 最小限の設定で再作成
            mkdir -p "$(dirname "$CLAUDE_CONFIG")"
            cat > "$CLAUDE_CONFIG" << 'EOF'
{
  "hooks": {},
  "slashCommands": {},
  "feedbackSurveyState": {
    "lastShownTime": 0
  }
}
EOF
            log_success "最小限の設定ファイル作成完了"
        fi
    fi
    
    # MCP設定ファイル確認・修復
    if [ ! -f "$MCP_CONFIG" ]; then
        log_warning "MCP設定ファイルが見つかりません"
        log_fix "MCP設定ファイル作成中..."
        
        mkdir -p "$(dirname "$MCP_CONFIG")"
        cat > "$MCP_CONFIG" << 'EOF'
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
        log_success "MCP設定ファイル作成完了"
        log_warning "Gemini APIキーの手動設定が必要です"
    else
        if python3 -m json.tool "$MCP_CONFIG" >/dev/null 2>&1; then
            log_success "MCP設定ファイル構文確認完了"
        else
            log_error "MCP設定ファイル構文エラー - 再作成します"
            cp "$MCP_CONFIG" "$MCP_CONFIG.backup"
            # 上記と同じ内容で再作成
            log_success "MCP設定ファイル再作成完了"
        fi
    fi
    
    # 権限修復
    chmod 600 "$CLAUDE_CONFIG" 2>/dev/null || true
    chmod 600 "$MCP_CONFIG" 2>/dev/null || true
    log_success "設定ファイル権限修復完了"
}

fix_mcp_connection() {
    log_info "=== MCP接続問題の診断・修復 ==="
    
    # MCP依存パッケージ確認
    if ! npm list -g @yusukedev/gemini-cli-mcp >/dev/null 2>&1; then
        log_warning "MCP依存パッケージが見つかりません"
        log_fix "MCPパッケージインストール中..."
        npm install -g @yusukedev/gemini-cli-mcp
        log_success "MCPパッケージインストール完了"
    else
        log_success "MCPパッケージ確認完了"
    fi
    
    # Gemini APIキー確認
    MCP_CONFIG="$HOME/.config/claude-desktop/config.json"
    if [ -f "$MCP_CONFIG" ] && grep -q "YOUR_GEMINI_API_KEY_HERE" "$MCP_CONFIG"; then
        log_warning "Gemini APIキーが未設定です"
        log_info "設定方法:"
        echo "  1. $MCP_CONFIG を編集"
        echo "  2. YOUR_GEMINI_API_KEY_HERE を実際のAPIキーに置換"
        echo "  3. Claude Codeを再起動"
    else
        log_success "Gemini APIキー設定確認完了"
    fi
    
    # Claude認証状況確認
    if command -v claude >/dev/null 2>&1; then
        if claude whoami >/dev/null 2>&1; then
            log_success "Claude認証確認完了"
        else
            log_warning "Claude未認証です"
            log_info "認証方法: claude auth login"
        fi
    else
        log_error "Claude CLIが見つかりません"
        log_info "先にClaude CLIの修復を実行してください"
    fi
}

fix_permissions() {
    log_info "=== 権限問題の一括修復 ==="
    
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "プロジェクトディレクトリが見つかりません"
        return 1
    fi
    
    cd "$PROJECT_DIR"
    
    # スクリプトファイル実行権限
    log_fix "スクリプトファイル実行権限修復中..."
    find . -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true
    find . -name "*.py" -type f -exec chmod +x {} \; 2>/dev/null || true
    
    # 設定ファイル権限
    log_fix "設定ファイル権限修復中..."
    chmod 600 "$HOME/.claude/settings.json" 2>/dev/null || true
    chmod 600 "$HOME/.config/claude-desktop/config.json" 2>/dev/null || true
    
    # Hooksディレクトリ権限
    if [ -d "$HOME/.claude/hooks" ]; then
        chmod -R 755 "$HOME/.claude/hooks" 2>/dev/null || true
    fi
    
    log_success "権限問題一括修復完了"
}

comprehensive_diagnosis() {
    log_info "=== 全体診断・包括的修復開始 ==="
    
    echo "🔍 段階的診断・修復を実行します..."
    echo
    
    # 各修復を順次実行
    fix_environment_issues
    echo
    
    fix_claude_installation
    echo
    
    fix_project_restoration
    echo
    
    fix_config_files
    echo
    
    fix_mcp_connection
    echo
    
    fix_permissions
    echo
    
    log_success "=== 包括的修復完了 ==="
    
    # 最終検証実行
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    if [ -d "$PROJECT_DIR" ] && [ -x "$PROJECT_DIR/Scripts/migration/migration_verification.sh" ]; then
        echo
        read -p "最終検証を実行しますか？ (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            cd "$PROJECT_DIR"
            bash Scripts/migration/migration_verification.sh
        fi
    fi
}

show_system_info() {
    log_info "=== システム情報表示 ==="
    
    echo "🖥️ システム基本情報:"
    echo "  - OS: $(lsb_release -d 2>/dev/null | cut -f2- || uname -a)"
    echo "  - カーネル: $(uname -r)"
    echo "  - アーキテクチャ: $(uname -m)"
    echo "  - ホスト名: $(hostname)"
    echo "  - ユーザー: $(whoami)"
    echo "  - ホームディレクトリ: $HOME"
    echo
    
    echo "🔧 開発環境:"
    if command -v python3 >/dev/null 2>&1; then
        echo "  - Python: $(python3 --version)"
    else
        echo "  - Python: 未インストール"
    fi
    
    if command -v node >/dev/null 2>&1; then
        echo "  - Node.js: $(node --version)"
        echo "  - npm: $(npm --version)"
    else
        echo "  - Node.js: 未インストール"
    fi
    
    if command -v git >/dev/null 2>&1; then
        echo "  - Git: $(git --version)"
    else
        echo "  - Git: 未インストール"
    fi
    
    if command -v claude >/dev/null 2>&1; then
        echo "  - Claude CLI: $(claude --version | head -1)"
    else
        echo "  - Claude CLI: 未インストール"
    fi
    echo
    
    echo "💾 ディスク使用量:"
    df -h /
    echo
    
    echo "🧠 メモリ使用量:"
    free -h
    echo
    
    echo "📁 プロジェクト状況:"
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    if [ -d "$PROJECT_DIR" ]; then
        echo "  - プロジェクトディレクトリ: 存在"
        echo "  - プロジェクトサイズ: $(du -sh "$PROJECT_DIR" | cut -f1)"
        echo "  - ファイル数: $(find "$PROJECT_DIR" -type f | wc -l)"
    else
        echo "  - プロジェクトディレクトリ: 未存在"
    fi
}

analyze_logs() {
    log_info "=== ログファイル分析 ==="
    
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    
    # Claude設定確認
    if [ -f "$HOME/.claude/settings.json" ]; then
        echo "📄 Claude設定ファイル状況:"
        echo "  - サイズ: $(stat -c%s "$HOME/.claude/settings.json") bytes"
        echo "  - 最終更新: $(stat -c%y "$HOME/.claude/settings.json")"
        
        if python3 -m json.tool "$HOME/.claude/settings.json" >/dev/null 2>&1; then
            echo "  - 構文状況: ✅ 正常"
        else
            echo "  - 構文状況: ❌ エラーあり"
        fi
    else
        echo "📄 Claude設定ファイル: 未存在"
    fi
    echo
    
    # MCP設定確認
    if [ -f "$HOME/.config/claude-desktop/config.json" ]; then
        echo "📄 MCP設定ファイル状況:"
        echo "  - サイズ: $(stat -c%s "$HOME/.config/claude-desktop/config.json") bytes"
        echo "  - 最終更新: $(stat -c%y "$HOME/.config/claude-desktop/config.json")"
        
        if python3 -m json.tool "$HOME/.config/claude-desktop/config.json" >/dev/null 2>&1; then
            echo "  - 構文状況: ✅ 正常"
        else
            echo "  - 構文状況: ❌ エラーあり"
        fi
        
        if grep -q "YOUR_GEMINI_API_KEY_HERE" "$HOME/.config/claude-desktop/config.json"; then
            echo "  - APIキー: ⚠️ 未設定"
        else
            echo "  - APIキー: ✅ 設定済み"
        fi
    else
        echo "📄 MCP設定ファイル: 未存在"
    fi
    echo
    
    # システムログ確認
    echo "📋 最近のシステムログ (エラー関連):"
    if journalctl --no-pager -n 20 -p err 2>/dev/null | head -10; then
        :
    else
        echo "  システムログにアクセスできません"
    fi
    echo
    
    # 移行検証レポート確認
    if [ -d "$PROJECT_DIR" ]; then
        cd "$PROJECT_DIR"
        echo "📊 移行検証レポート:"
        if ls migration_verification_report_*.txt 2>/dev/null | head -3; then
            echo "  最新レポート内容:"
            LATEST_REPORT=$(ls -t migration_verification_report_*.txt 2>/dev/null | head -1)
            if [ -n "$LATEST_REPORT" ]; then
                cat "$LATEST_REPORT"
            fi
        else
            echo "  移行検証レポートが見つかりません"
        fi
    fi
}

# メイン実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi