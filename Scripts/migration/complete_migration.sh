#!/bin/bash
# WSL2→Native Linux完全移行スクリプト - ワンコマンド実行
# 実行: bash <(curl -s https://raw.githubusercontent.com/nica2525/WSL2-Linux-Migration-Trading-Project/main/Scripts/migration/complete_migration.sh)

set -euo pipefail  # エラー時即座に停止

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ロゴ表示
show_logo() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                   WSL2 → Linux Migration                    ║
║              Trading Project Complete Setup                 ║
║                                                              ║
║   JamesORB EA v2.05 | SubAgent | MCP Integration | Claude   ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

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

log_phase() {
    echo -e "${MAGENTA}[PHASE]${NC} $1"
}

# エラーハンドリング
error_handler() {
    log_error "移行処理中に致命的エラーが発生しました (行: $1)"
    log_error "移行を中止しています..."
    
    # エラー発生時のクリーンアップ
    cleanup_on_error
    exit 1
}

cleanup_on_error() {
    log_warning "エラー発生によるクリーンアップ実行中..."
    
    # 一時ファイル削除
    [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
    
    # 部分的に作成されたディレクトリのクリーンアップ（オプション）
    # これは慎重に行う必要があります
    
    log_info "クリーンアップ完了"
}

trap 'error_handler $LINENO' ERR

# プログレスバー関数
show_progress() {
    local current=$1
    local total=$2
    local description="$3"
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    
    printf "\r${BLUE}[PROGRESS]${NC} "
    printf "["
    printf "%*s" $filled | tr ' ' '█'
    printf "%*s" $((width - filled)) | tr ' ' '░'
    printf "] %d%% - %s" "$percentage" "$description"
    
    if [ $current -eq $total ]; then
        echo
    fi
}

# メイン処理開始
main() {
    show_logo
    
    log_info "=== WSL2→Native Linux完全移行開始 ==="
    log_info "開始時刻: $(date)"
    log_info "実行ユーザー: $(whoami)"
    log_info "実行ディレクトリ: $(pwd)"
    echo
    
    # パラメータ解析
    PHASE_ONLY=""
    SKIP_VERIFICATION=false
    QUIET_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env-only)
                PHASE_ONLY="env"
                shift
                ;;
            --claude-only)
                PHASE_ONLY="claude"
                shift
                ;;
            --project-only)
                PHASE_ONLY="project"
                shift
                ;;
            --config-only)
                PHASE_ONLY="config"
                shift
                ;;
            --verify-only)
                PHASE_ONLY="verify"
                shift
                ;;
            --skip-verification)
                SKIP_VERIFICATION=true
                shift
                ;;
            --quiet)
                QUIET_MODE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 段階的実行
    if [ -z "$PHASE_ONLY" ]; then
        # 完全移行実行
        execute_complete_migration
    else
        # 指定段階のみ実行
        execute_phase_only "$PHASE_ONLY"
    fi
}

show_help() {
    cat << EOF
使用方法: bash complete_migration.sh [オプション]

完全移行（デフォルト）:
  bash complete_migration.sh

段階別実行:
  --env-only          環境構築のみ実行
  --claude-only       Claude CLI インストールのみ
  --project-only      プロジェクト復元のみ
  --config-only       設定ファイル復元のみ
  --verify-only       検証のみ実行

その他オプション:
  --skip-verification 検証をスキップ
  --quiet            詳細出力を抑制
  --help             このヘルプを表示

実行例:
  # 完全移行
  bash <(curl -s https://raw.githubusercontent.com/nica2525/WSL2-Linux-Migration-Trading-Project/main/Scripts/migration/complete_migration.sh)
  
  # 環境構築のみ
  bash complete_migration.sh --env-only
EOF
}

execute_complete_migration() {
    log_phase "完全移行モード開始"
    
    local total_phases=5
    local current_phase=0
    
    # Phase 1: 環境構築
    current_phase=$((current_phase + 1))
    show_progress $current_phase $total_phases "Linux環境構築中..."
    execute_phase_1_environment
    
    # Phase 2: Claude CLI インストール
    current_phase=$((current_phase + 1))
    show_progress $current_phase $total_phases "Claude CLI インストール中..."
    execute_phase_2_claude
    
    # Phase 3: プロジェクト復元
    current_phase=$((current_phase + 1))
    show_progress $current_phase $total_phases "プロジェクト復元中..."
    execute_phase_3_project
    
    # Phase 4: 設定ファイル復元
    current_phase=$((current_phase + 1))
    show_progress $current_phase $total_phases "設定ファイル復元中..."
    execute_phase_4_config
    
    # Phase 5: 検証
    if [ "$SKIP_VERIFICATION" = false ]; then
        current_phase=$((current_phase + 1))
        show_progress $current_phase $total_phases "移行検証中..."
        execute_phase_5_verification
    else
        log_warning "検証をスキップしました"
    fi
    
    # 完了処理
    migration_completed
}

execute_phase_only() {
    local phase="$1"
    
    log_phase "段階別実行モード: $phase"
    
    case "$phase" in
        "env")
            execute_phase_1_environment
            ;;
        "claude")
            execute_phase_2_claude
            ;;
        "project")
            execute_phase_3_project
            ;;
        "config")
            execute_phase_4_config
            ;;
        "verify")
            execute_phase_5_verification
            ;;
        *)
            log_error "無効なフェーズ: $phase"
            exit 1
            ;;
    esac
    
    log_success "フェーズ '$phase' 完了"
}

execute_phase_1_environment() {
    log_phase "Phase 1: Linux環境構築"
    
    # 一時ディレクトリ作成
    TEMP_DIR=$(mktemp -d)
    cleanup() {
        rm -rf "$TEMP_DIR"
    }
    trap cleanup EXIT
    
    # スクリプトダウンロード・実行
    SCRIPT_URL="https://raw.githubusercontent.com/nica2525/WSL2-Linux-Migration-Trading-Project/main/Scripts/migration/linux_environment_setup.sh"
    
    log_info "環境構築スクリプトダウンロード中..."
    if curl -fsSL "$SCRIPT_URL" > "$TEMP_DIR/linux_environment_setup.sh"; then
        chmod +x "$TEMP_DIR/linux_environment_setup.sh"
        log_success "ダウンロード完了"
        
        log_info "環境構築実行中..."
        if [ "$QUIET_MODE" = true ]; then
            bash "$TEMP_DIR/linux_environment_setup.sh" >/dev/null 2>&1
        else
            bash "$TEMP_DIR/linux_environment_setup.sh"
        fi
        
        log_success "Phase 1完了: Linux環境構築"
    else
        log_error "スクリプトダウンロードに失敗しました"
        exit 1
    fi
}

execute_phase_2_claude() {
    log_phase "Phase 2: Claude CLI インストール"
    
    # スクリプトダウンロード・実行
    SCRIPT_URL="https://raw.githubusercontent.com/nica2525/WSL2-Linux-Migration-Trading-Project/main/Scripts/migration/claude_installation.sh"
    
    log_info "Claude CLIインストールスクリプトダウンロード中..."
    if curl -fsSL "$SCRIPT_URL" > "$TEMP_DIR/claude_installation.sh"; then
        chmod +x "$TEMP_DIR/claude_installation.sh"
        log_success "ダウンロード完了"
        
        log_info "Claude CLI インストール実行中..."
        if [ "$QUIET_MODE" = true ]; then
            echo "y" | bash "$TEMP_DIR/claude_installation.sh" >/dev/null 2>&1
        else
            echo "y" | bash "$TEMP_DIR/claude_installation.sh"
        fi
        
        # PATH反映
        export PATH="$HOME/.local/bin:$PATH"
        
        log_success "Phase 2完了: Claude CLI インストール"
    else
        log_error "スクリプトダウンロードに失敗しました"
        exit 1
    fi
}

execute_phase_3_project() {
    log_phase "Phase 3: プロジェクト復元"
    
    # プロジェクトディレクトリ準備
    mkdir -p "$HOME/Trading-Development"
    cd "$HOME/Trading-Development"
    
    # スクリプトダウンロード・実行
    SCRIPT_URL="https://raw.githubusercontent.com/nica2525/WSL2-Linux-Migration-Trading-Project/main/Scripts/migration/project_restoration.sh"
    
    log_info "プロジェクト復元スクリプトダウンロード中..."
    if curl -fsSL "$SCRIPT_URL" > "$TEMP_DIR/project_restoration.sh"; then
        chmod +x "$TEMP_DIR/project_restoration.sh"
        log_success "ダウンロード完了"
        
        log_info "プロジェクト復元実行中..."
        if [ "$QUIET_MODE" = true ]; then
            echo "n" | bash "$TEMP_DIR/project_restoration.sh" >/dev/null 2>&1
        else
            echo "n" | bash "$TEMP_DIR/project_restoration.sh"
        fi
        
        log_success "Phase 3完了: プロジェクト復元"
    else
        log_error "スクリプトダウンロードに失敗しました"
        exit 1
    fi
}

execute_phase_4_config() {
    log_phase "Phase 4: 設定ファイル復元"
    
    # プロジェクトディレクトリ確認
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "プロジェクトディレクトリが見つかりません: $PROJECT_DIR"
        log_error "先にPhase 3 (プロジェクト復元)を実行してください"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    
    log_info "設定ファイル復元実行中..."
    if [ -x "Scripts/migration/config_restore.sh" ]; then
        if [ "$QUIET_MODE" = true ]; then
            echo "n" | bash Scripts/migration/config_restore.sh >/dev/null 2>&1
        else
            echo "n" | bash Scripts/migration/config_restore.sh
        fi
        
        log_success "Phase 4完了: 設定ファイル復元"
    else
        log_error "設定復元スクリプトが見つかりません"
        exit 1
    fi
}

execute_phase_5_verification() {
    log_phase "Phase 5: 移行検証"
    
    # プロジェクトディレクトリ確認
    PROJECT_DIR="$HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "プロジェクトディレクトリが見つかりません"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    
    log_info "移行検証実行中..."
    if [ -x "Scripts/migration/migration_verification.sh" ]; then
        bash Scripts/migration/migration_verification.sh
        VERIFICATION_EXIT_CODE=$?
        
        case $VERIFICATION_EXIT_CODE in
            0)
                log_success "Phase 5完了: 移行検証 - 完全成功"
                ;;
            1)
                log_error "Phase 5: 移行検証 - 致命的問題あり"
                exit 1
                ;;
            2)
                log_warning "Phase 5完了: 移行検証 - 警告あり"
                ;;
            *)
                log_warning "Phase 5: 移行検証 - 不明な終了コード: $VERIFICATION_EXIT_CODE"
                ;;
        esac
    else
        log_error "検証スクリプトが見つかりません"
        exit 1
    fi
}

migration_completed() {
    echo
    log_success "=== WSL2→Native Linux 完全移行完了 ==="
    
    echo -e "${GREEN}"
    cat << 'EOF'
  ████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗██████╗ 
  ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
     ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗
     ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
     ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
         MIGRATION COMPLETE - READY FOR DEVELOPMENT!
EOF
    echo -e "${NC}"
    
    echo "🎉 移行完了時刻: $(date)"
    echo
    echo "📋 移行された環境:"
    echo "  - ✅ Linux基盤環境 (Python3, Node.js, Git)"
    echo "  - ✅ Claude Code CLI"
    echo "  - ✅ JamesORB EA v2.05 (ATRハンドル最適化・動的ロット計算)"
    echo "  - ✅ SubAgent機能 (3種エージェント)"
    echo "  - ✅ MCP統合システム (4サーバー構成)"
    echo "  - ✅ 品質管理プロトコル (拡張3段階レビュー)"
    echo "  - ✅ 統計分析システム (Phase1完了版)"
    echo
    echo "🚀 次のステップ:"
    echo "  1. Claude Code認証:"
    echo "     claude auth login"
    echo
    echo "  2. Gemini APIキー設定 (MCP用):"
    echo "     ~/.config/claude-desktop/config.json を編集"
    echo
    echo "  3. Git設定 (推奨):"
    echo "     git config --global user.name \"Your Name\""
    echo "     git config --global user.email \"your.email@domain.com\""
    echo
    echo "  4. VS Code Remote-SSH接続テスト"
    echo
    echo "  5. 開発作業開始!"
    echo
    echo "📁 プロジェクト場所:"
    echo "  $HOME/Trading-Development/2.ブレイクアウト手法プロジェクト"
    echo
    echo "📖 詳細ガイド:"
    echo "  文書/技術/WSL2_Linux移行設定ガイド.md"
    echo
    log_info "完全移行が正常に完了しました！開発環境をお楽しみください！"
}

# スクリプト実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi