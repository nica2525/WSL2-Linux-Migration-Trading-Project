#!/bin/bash
# Linux環境構築スクリプト - WSL2→Native Linux移行
# 実行: bash linux_environment_setup.sh

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
    log_error "スクリプト実行中にエラーが発生しました (行: $1)"
    log_error "移行を中止します。問題を確認してください。"
    exit 1
}

trap 'error_handler $LINENO' ERR

log_info "=== WSL2→Linux移行: 環境構築開始 ==="

# 1. システム情報確認
log_info "システム情報確認中..."
echo "OS: $(lsb_release -d | cut -f2-)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "User: $(whoami)"
echo "Home: $HOME"

# 2. 事前チェック
log_info "事前環境チェック実行中..."

# ディスク容量チェック（最低5GB）
AVAILABLE_SPACE=$(df / | tail -1 | awk '{print $4}')
REQUIRED_SPACE=5242880  # 5GB in KB
if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    log_error "ディスク容量不足: ${AVAILABLE_SPACE}KB available, ${REQUIRED_SPACE}KB required"
    exit 1
fi
log_success "ディスク容量OK: $(( AVAILABLE_SPACE / 1024 / 1024 ))GB available"

# インターネット接続チェック
if ! ping -c 1 google.com >/dev/null 2>&1; then
    log_error "インターネット接続が必要です"
    exit 1
fi
log_success "インターネット接続OK"

# sudo権限チェック
if ! sudo -n true 2>/dev/null; then
    log_warning "sudo権限が必要です。パスワードを入力してください:"
    sudo true
fi
log_success "sudo権限OK"

# 3. パッケージマネージャー更新
log_info "パッケージリスト更新中..."
sudo apt-get update -qq

# 4. 基本依存関係インストール
log_info "基本パッケージインストール中..."
sudo apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    vim \
    htop \
    tree \
    jq

log_success "基本パッケージインストール完了"

# 5. Python3環境構築
log_info "Python3環境構築中..."

# Python3.10以上の確認
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "0.0.0")
REQUIRED_PYTHON="3.10.0"

if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
    log_info "Python3.10以上が必要です。インストール中..."
    sudo apt-get install -y python3.10 python3.10-dev python3.10-venv
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
fi

# pip3インストール・更新
if ! command -v pip3 >/dev/null 2>&1; then
    sudo apt-get install -y python3-pip
fi
pip3 install --upgrade pip --user

log_success "Python3環境構築完了 ($(python3 --version))"

# 6. Node.js環境構築
log_info "Node.js環境構築中..."

# Node.js 20.x インストール
if ! command -v node >/dev/null 2>&1 || [ "$(node --version | cut -d'v' -f2 | cut -d'.' -f1)" -lt "18" ]; then
    log_info "Node.js 20.x インストール中..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

log_success "Node.js環境構築完了 ($(node --version), npm $(npm --version))"

# 7. Git設定確認
log_info "Git設定確認中..."
if [ -z "$(git config --global user.name 2>/dev/null || true)" ]; then
    log_warning "Git user.nameが未設定です"
    echo "注意: 後でgit config --global user.name \"Your Name\"を実行してください"
fi

if [ -z "$(git config --global user.email 2>/dev/null || true)" ]; then
    log_warning "Git user.emailが未設定です"
    echo "注意: 後でgit config --global user.email \"your.email@domain.com\"を実行してください"
fi

# 8. 必要なPythonパッケージインストール
log_info "Python依存パッケージインストール中..."
pip3 install --user \
    pandas \
    numpy \
    requests \
    pyyaml \
    python-dateutil \
    psutil

log_success "Python依存パッケージインストール完了"

# 9. MCP必要パッケージ事前インストール
log_info "MCP依存パッケージインストール中..."
npm install -g @yusukedev/gemini-cli-mcp

log_success "MCP依存パッケージインストール完了"

# 10. ディレクトリ構造準備
log_info "ディレクトリ構造準備中..."
mkdir -p "$HOME/Trading-Development"
mkdir -p "$HOME/.claude/hooks"
mkdir -p "$HOME/.config/claude-desktop"

log_success "ディレクトリ構造準備完了"

# 11. 環境変数設定
log_info "環境変数設定中..."
cat >> "$HOME/.bashrc" << 'EOF'

# WSL2→Linux移行: 追加環境変数
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages:$PYTHONPATH"

# Claude Code最適化設定
export NODE_OPTIONS="--max-old-space-size=4096"
export PYTHONIOENCODING="utf-8"

EOF

log_success "環境変数設定完了"

# 12. 最終確認
log_info "環境構築最終確認中..."
echo "✅ OS: $(lsb_release -d | cut -f2-)"
echo "✅ Python: $(python3 --version)"
echo "✅ Node.js: $(node --version)"
echo "✅ npm: $(npm --version)"
echo "✅ Git: $(git --version)"
echo "✅ 利用可能ディスク容量: $(df -h / | tail -1 | awk '{print $4}')"

log_success "=== Linux環境構築完了 ==="
log_info "次のステップ: Claude Code CLIインストールを実行してください"
log_info "実行コマンド: bash claude_installation.sh"

# 環境変数反映のためbashrcリロード推奨メッセージ
log_warning "新しい環境変数を反映するため、以下を実行することを推奨:"
log_warning "source ~/.bashrc"