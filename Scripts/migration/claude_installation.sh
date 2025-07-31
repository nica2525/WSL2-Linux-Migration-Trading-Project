#!/bin/bash
# Claude Code CLI自動インストールスクリプト - WSL2→Native Linux移行  
# 実行: bash claude_installation.sh

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
    log_error "Claude CLI インストール中にエラーが発生しました (行: $1)"
    log_error "インストールを中止します。問題を確認してください。"
    exit 1
}

trap 'error_handler $LINENO' ERR

log_info "=== Claude Code CLI 自動インストール開始 ==="

# 1. システム情報確認
log_info "システム情報確認中..."
ARCH=$(uname -m)
OS=$(uname -s)

if [ "$OS" != "Linux" ]; then
    log_error "このスクリプトはLinux環境専用です"
    exit 1
fi

log_info "OS: $OS, Architecture: $ARCH"

# 2. 既存インストール確認
if command -v claude >/dev/null 2>&1; then
    CURRENT_VERSION=$(claude --version 2>/dev/null | head -1 || echo "不明")
    log_warning "Claude Code は既にインストールされています: $CURRENT_VERSION"
    read -p "再インストールしますか? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "インストールをスキップします"
        exit 0
    fi
fi

# 3. 一時ディレクトリ作成
TEMP_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

log_info "一時ディレクトリ: $TEMP_DIR"

# 4. Claude Code最新版URL取得
log_info "Claude Code最新版情報取得中..."

# GitHubリリースAPIから最新版URL取得
LATEST_RELEASE_URL="https://api.github.com/repos/anthropics/claude-code/releases/latest"

# アーキテクチャ判定
case "$ARCH" in
    x86_64)
        ARCH_SUFFIX="x64"
        ;;
    aarch64|arm64)
        ARCH_SUFFIX="arm64"
        ;;
    *)
        log_error "サポートされていないアーキテクチャ: $ARCH"
        exit 1
        ;;
esac

# 最新版ダウンロードURL構築
DOWNLOAD_URL="https://github.com/anthropics/claude-code/releases/latest/download/claude-code-linux-${ARCH_SUFFIX}.tar.gz"

log_info "ダウンロードURL: $DOWNLOAD_URL"

# 5. Claude Code ダウンロード
log_info "Claude Code ダウンロード中..."
cd "$TEMP_DIR"

if ! curl -L -o "claude-code.tar.gz" "$DOWNLOAD_URL"; then
    log_error "ダウンロードに失敗しました"
    
    # フォールバック: 固定版URL試行
    log_warning "フォールバック: 固定版URLで再試行中..."
    FALLBACK_URL="https://github.com/anthropics/claude-code/releases/download/v1.0.70/claude-code-linux-${ARCH_SUFFIX}.tar.gz"
    if ! curl -L -o "claude-code.tar.gz" "$FALLBACK_URL"; then
        log_error "フォールバックダウンロードも失敗しました"
        log_error "手動インストールが必要です: https://docs.anthropic.com/en/docs/claude-code"
        exit 1
    fi
fi

log_success "ダウンロード完了"

# 6. ファイル検証
log_info "ダウンロードファイル検証中..."
if [ ! -f "claude-code.tar.gz" ] || [ ! -s "claude-code.tar.gz" ]; then
    log_error "ダウンロードファイルが無効です"
    exit 1
fi

FILE_SIZE=$(stat -c%s "claude-code.tar.gz")
log_info "ファイルサイズ: $(( FILE_SIZE / 1024 / 1024 ))MB"

if [ "$FILE_SIZE" -lt 10485760 ]; then  # 10MB未満は異常
    log_error "ダウンロードファイルサイズが異常です"
    exit 1
fi

# 7. アーカイブ展開
log_info "アーカイブ展開中..."
if ! tar -xzf "claude-code.tar.gz"; then
    log_error "アーカイブ展開に失敗しました"
    exit 1
fi

# 8. インストール先準備
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

log_info "インストール先: $INSTALL_DIR"

# 9. Claude Code インストール
log_info "Claude Code インストール中..."

# 実行ファイル配置
if [ -f "claude" ]; then
    cp "claude" "$INSTALL_DIR/claude"
    chmod +x "$INSTALL_DIR/claude"
elif [ -f "claude-code" ]; then
    cp "claude-code" "$INSTALL_DIR/claude"
    chmod +x "$INSTALL_DIR/claude"
else
    # ディレクトリ構造が異なる場合の対応
    find . -name "claude*" -type f -executable | head -1 | xargs -I {} cp {} "$INSTALL_DIR/claude"
    chmod +x "$INSTALL_DIR/claude"
fi

if [ ! -f "$INSTALL_DIR/claude" ]; then
    log_error "Claude実行ファイルが見つかりません"
    exit 1
fi

log_success "Claude Code インストール完了"

# 10. PATH設定確認
log_info "PATH設定確認中..."
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    log_warning "~/.local/bin がPATHに含まれていません"
    
    # .bashrcにPATH追加
    if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$HOME/.bashrc"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        log_info ".bashrcにPATH設定を追加しました"
    fi
    
    # 現在のセッションでPATH更新
    export PATH="$HOME/.local/bin:$PATH"
fi

# 11. インストール検証
log_info "インストール検証中..."
sleep 2  # ファイルシステム同期待機

if command -v claude >/dev/null 2>&1; then
    INSTALLED_VERSION=$(claude --version 2>/dev/null | head -1 || echo "バージョン情報取得失敗")
    log_success "Claude Code インストール成功: $INSTALLED_VERSION"
else
    log_error "Claude Code の実行確認に失敗しました"
    log_error "PATH設定を確認してください: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi

# 12. 初期設定確認
log_info "初期設定確認中..."

# 設定ディレクトリ存在確認
CLAUDE_CONFIG_DIR="$HOME/.claude"
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    mkdir -p "$CLAUDE_CONFIG_DIR"
    log_info "Claude設定ディレクトリ作成: $CLAUDE_CONFIG_DIR"
fi

# 13. セットアップ完了メッセージ
log_success "=== Claude Code CLI インストール完了 ==="
echo
echo "📋 インストール情報:"
echo "  - 実行ファイル: $INSTALL_DIR/claude"
echo "  - バージョン: $INSTALLED_VERSION"
echo "  - 設定ディレクトリ: $CLAUDE_CONFIG_DIR"
echo
echo "🚀 次のステップ:"
echo "  1. 新しいターミナルを開くか、以下を実行:"
echo "     source ~/.bashrc"
echo "  2. Claude Code認証:"
echo "     claude auth login"
echo "  3. プロジェクト復元スクリプト実行:"
echo "     bash project_restoration.sh"
echo
log_warning "重要: 現在のターミナルでclaudeコマンドを使用するには:"
log_warning "export PATH=\"\$HOME/.local/bin:\$PATH\" を実行してください"

# 14. 自動PATH反映（オプション）
read -p "現在のターミナルでPATHを自動反映しますか？ (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    log_info "PATH反映をスキップしました"
else
    export PATH="$HOME/.local/bin:$PATH"
    log_success "現在のターミナルでPATH反映完了"
    
    # 確認
    if command -v claude >/dev/null 2>&1; then
        log_success "claude コマンドが利用可能です"
    else
        log_warning "claude コマンドの確認に失敗しました"
    fi
fi