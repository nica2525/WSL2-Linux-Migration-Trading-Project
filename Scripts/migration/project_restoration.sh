#!/bin/bash
# プロジェクト復元スクリプト - WSL2→Native Linux移行
# 実行: bash project_restoration.sh

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
    log_error "プロジェクト復元中にエラーが発生しました (行: $1)"
    log_error "復元を中止します。問題を確認してください。"
    exit 1
}

trap 'error_handler $LINENO' ERR

log_info "=== WSL2→Linux移行: プロジェクト復元開始 ==="

# 1. 環境変数・設定
GITHUB_REPO="https://github.com/nica2525/WSL2-Linux-Migration-Trading-Project.git"
PROJECT_NAME="2.ブレイクアウト手法プロジェクト"
BASE_DIR="$HOME/Trading-Development"
PROJECT_DIR="$BASE_DIR/$PROJECT_NAME"

log_info "設定情報:"
echo "  - GitHubリポジトリ: $GITHUB_REPO"
echo "  - プロジェクトディレクトリ: $PROJECT_DIR"
echo "  - 現在のユーザー: $(whoami)"

# 2. 事前チェック
log_info "事前環境チェック実行中..."

# Git コマンド確認
if ! command -v git >/dev/null 2>&1; then
    log_error "Gitがインストールされていません"
    log_error "先に linux_environment_setup.sh を実行してください"
    exit 1
fi

# インターネット接続確認
if ! ping -c 1 github.com >/dev/null 2>&1; then
    log_error "GitHub への接続が確認できません"
    exit 1
fi

log_success "事前チェック完了"

# 3. ベースディレクトリ作成・移動
log_info "ベースディレクトリ準備中..."
mkdir -p "$BASE_DIR"
cd "$BASE_DIR"

log_info "作業ディレクトリ: $(pwd)"

# 4. 既存プロジェクト確認
if [ -d "$PROJECT_DIR" ]; then
    log_warning "プロジェクトディレクトリが既に存在します: $PROJECT_DIR"
    
    # Git リポジトリかチェック
    if [ -d "$PROJECT_DIR/.git" ]; then
        log_info "既存のGitリポジトリが見つかりました"
        
        cd "$PROJECT_DIR"
        
        # リモートURL確認
        CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "未設定")
        if [ "$CURRENT_REMOTE" = "$GITHUB_REPO" ]; then
            log_info "同じリポジトリです。プルで更新します..."
            
            # 未保存変更確認
            if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
                log_warning "未保存の変更があります"
                git status --porcelain
                
                read -p "変更を破棄してプルしますか？ [y/N]: " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    git reset --hard HEAD
                    git clean -fd
                    log_info "未保存変更を破棄しました"
                else
                    log_info "プルをスキップします"
                    exit 0
                fi
            fi
            
            # プル実行
            git pull origin main
            log_success "プロジェクト更新完了"
            
        else
            log_error "異なるリポジトリです: $CURRENT_REMOTE"
            read -p "ディレクトリを削除して新規クローンしますか？ [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cd "$BASE_DIR"
                rm -rf "$PROJECT_DIR"
                log_info "既存ディレクトリを削除しました"
            else
                log_info "復元をキャンセルしました"
                exit 0
            fi
        fi
    else
        log_error "Gitリポジトリではありません"
        read -p "ディレクトリを削除して新規クローンしますか？ [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$PROJECT_DIR"
            log_info "既存ディレクトリを削除しました"
        else
            log_info "復元をキャンセルしました"
            exit 0
        fi
    fi
fi

# 5. プロジェクトクローン
if [ ! -d "$PROJECT_DIR" ]; then
    log_info "プロジェクトクローン中..."
    
    if ! git clone "$GITHUB_REPO" "$PROJECT_NAME"; then
        log_error "クローンに失敗しました"
        log_error "リポジトリURLを確認してください: $GITHUB_REPO"
        exit 1
    fi
    
    log_success "プロジェクトクローン完了"
fi

# 6. プロジェクトディレクトリ移動・確認
cd "$PROJECT_DIR"
log_info "プロジェクトディレクトリ: $(pwd)"

# ファイル数確認
FILE_COUNT=$(find . -type f | wc -l)
log_info "ファイル数: $FILE_COUNT"

if [ "$FILE_COUNT" -lt 50 ]; then
    log_warning "ファイル数が少ない可能性があります"
fi

# 7. 重要ファイル存在確認
log_info "重要ファイル存在確認中..."

CRITICAL_FILES=(
    "CLAUDE.md"
    "MT5/EA/JamesORB_v1.0.mq5"
    "Scripts/cron_system_monitor.py"
    "文書/技術/WSL2_Linux移行設定ガイド.md"
)

MISSING_FILES=()
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "✓ $file"
    else
        log_error "✗ $file (欠損)"
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    log_error "重要ファイルが欠損しています:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    log_error "リポジトリ状態を確認してください"
    exit 1
fi

# 8. 実行権限復元
log_info "実行権限復元中..."

# スクリプトファイルに実行権限付与
find Scripts -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true
find Scripts -name "*.py" -type f -exec chmod +x {} \; 2>/dev/null || true

# 新しく作成された移行スクリプトに実行権限付与
find Scripts/migration -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

# その他の実行可能ファイル
chmod +x .autostart_git 2>/dev/null || true
chmod +x .bashrc_claude_protection 2>/dev/null || true
chmod +x .clauderc 2>/dev/null || true

# Dashboardスクリプト
find Dashboard -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

log_success "実行権限復元完了"

# 9. Python環境確認・パッケージインストール
log_info "Python依存関係確認中..."

# requirements.txtが存在する場合インストール
if [ -f "requirements.txt" ]; then
    log_info "requirements.txtからパッケージインストール中..."
    pip3 install --user -r requirements.txt
elif [ -f "pyproject.toml" ]; then
    log_info "pyproject.tomlが見つかりました"
    # 主要な依存パッケージを手動インストール
    pip3 install --user pandas numpy requests pyyaml python-dateutil psutil
else
    log_info "依存関係ファイルなし。主要パッケージをインストール..."
    pip3 install --user pandas numpy requests pyyaml python-dateutil psutil
fi

log_success "Python依存関係セットアップ完了"

# 10. ディレクトリ構造確認
log_info "ディレクトリ構造確認中..."

EXPECTED_DIRS=(
    "MT5"
    "Scripts"
    "文書"
    "Dashboard"
)

for dir in "${EXPECTED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        DIR_SIZE=$(du -sh "$dir" | cut -f1)
        log_success "✓ $dir ($DIR_SIZE)"
    else
        log_warning "✗ $dir (見つかりません)"
    fi
done

# 11. Git設定確認
log_info "Git設定確認中..."

# リモートURL確認
REMOTE_URL=$(git remote get-url origin)
log_info "リモートURL: $REMOTE_URL"

# ブランチ確認
CURRENT_BRANCH=$(git branch --show-current)
log_info "現在のブランチ: $CURRENT_BRANCH"

# 最新コミット確認
LATEST_COMMIT=$(git log -1 --format="%h - %s (%ci)")
log_info "最新コミット: $LATEST_COMMIT"

# 12. プロジェクト統計情報
log_info "プロジェクト統計情報..."

echo "📊 プロジェクト統計:"
echo "  - 総ファイル数: $(find . -type f | wc -l)"
echo "  - Pythonファイル数: $(find . -name "*.py" | wc -l)"
echo "  - MQL5ファイル数: $(find . -name "*.mq5" | wc -l)"
echo "  - Shellスクリプト数: $(find . -name "*.sh" | wc -l)"
echo "  - Markdownファイル数: $(find . -name "*.md" | wc -l)"

# プロジェクトサイズ
PROJECT_SIZE=$(du -sh . | cut -f1)
echo "  - プロジェクトサイズ: $PROJECT_SIZE"

# 13. 最終確認
log_success "=== プロジェクト復元完了 ==="
echo
echo "📁 プロジェクト場所: $PROJECT_DIR"
echo "📊 復元されたファイル数: $FILE_COUNT"
echo "🌟 プロジェクトサイズ: $PROJECT_SIZE"
echo
echo "🚀 次のステップ:"
echo "  1. 設定ファイル復元:"
echo "     bash Scripts/migration/config_restore.sh"
echo "  2. 移行検証:"
echo "     bash Scripts/migration/migration_verification.sh"
echo "  3. Claude Code認証:"
echo "     claude auth login"
echo
log_info "プロジェクト復元が正常に完了しました"

# 14. 自動的に次のスクリプト実行確認
read -p "続けて設定ファイル復元を実行しますか？ (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    log_info "設定ファイル復元は後で手動実行してください"
    log_info "実行コマンド: bash Scripts/migration/config_restore.sh"
else
    log_info "設定ファイル復元を開始します..."
    exec bash Scripts/migration/config_restore.sh
fi