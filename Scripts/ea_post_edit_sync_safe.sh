#!/bin/bash
# EAファイル編集後の自動同期スクリプト (安全版)

# --- 厳格設定 ---
set -euo pipefail

# --- 設定変数 ---
PROJECT_ROOT="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
CANONICAL_EA_NAME="JamesORB_v1.0.mq5"
CANONICAL_EA_PATH="${PROJECT_ROOT}/MT5/EA/${CANONICAL_EA_NAME}"
VERSION_FILE="${PROJECT_ROOT}/MT5/EA/VERSION_HISTORY.md"
MT5_EA_PATH="/home/trader/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/${CANONICAL_EA_NAME}"

# --- エラーハンドリング関数 ---
log_info() {
    echo "  ✅ $1"
}

log_warning() {
    echo "  ⚠️  $1"
}

log_error() {
    echo "  ❌ $1" >&2
}

# --- メイン処理 ---
echo "🔄 EA編集後自動同期実行（安全モード）"
echo "========================================"

# プロジェクトルートに移動（失敗しても継続）
if ! cd "$PROJECT_ROOT" 2>/dev/null; then
    log_warning "プロジェクトルートに移動できません: ${PROJECT_ROOT}"
    exit 1
fi

# 1. EAファイル存在確認
echo "1. EAファイル存在確認..."
if [ -f "$CANONICAL_EA_PATH" ]; then
    log_info "正規EAファイル存在: $(basename "$CANONICAL_EA_PATH")"

    # ファイル情報表示
    size=$(stat -f%z "$CANONICAL_EA_PATH" 2>/dev/null || stat -c%s "$CANONICAL_EA_PATH" 2>/dev/null || echo "不明")
    modified=$(stat -f%Sm "$CANONICAL_EA_PATH" 2>/dev/null || stat -c%y "$CANONICAL_EA_PATH" 2>/dev/null || echo "不明")
    log_info "サイズ: ${size} bytes, 更新日時: ${modified}"
else
    log_error "正規EAファイルが見つかりません: $CANONICAL_EA_PATH"
    exit 1
fi

# 2. MT5への安全な同期
echo "2. MT5への同期処理..."
MT5_DIR=$(dirname "$MT5_EA_PATH")

# MT5ディレクトリ存在確認・作成
if [ ! -d "$MT5_DIR" ]; then
    if mkdir -p "$MT5_DIR" 2>/dev/null; then
        log_info "MT5ディレクトリ作成: $MT5_DIR"
    else
        log_error "MT5ディレクトリ作成失敗: $MT5_DIR"
        exit 1
    fi
fi

# 既存ファイルのバックアップ
if [ -f "$MT5_EA_PATH" ]; then
    backup_name="${MT5_EA_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    if cp "$MT5_EA_PATH" "$backup_name" 2>/dev/null; then
        log_info "既存ファイルバックアップ: $(basename "$backup_name")"
    else
        log_warning "バックアップ作成失敗（続行）"
    fi
fi

# 同期実行
if cp -p "$CANONICAL_EA_PATH" "$MT5_EA_PATH" 2>/dev/null; then
    log_info "同期完了: $MT5_EA_PATH"

    # 同期確認
    if [ -f "$MT5_EA_PATH" ]; then
        mt5_size=$(stat -f%z "$MT5_EA_PATH" 2>/dev/null || stat -c%s "$MT5_EA_PATH" 2>/dev/null || echo "0")
        if [ "$size" = "$mt5_size" ]; then
            log_info "同期検証OK: サイズ一致"
        else
            log_warning "同期検証NG: サイズ不一致 (元:${size}, MT5:${mt5_size})"
        fi
    fi
else
    log_error "MT5への同期失敗"
    exit 1
fi

# 3. Git状態確認（エラーでも継続）
echo "3. Git状態確認..."
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    # EA関連の変更チェック
    if git status --porcelain 2>/dev/null | grep -q "MT5/EA/"; then
        echo "  📝 Git変更検出:"
        git status --short -- "MT5/EA/" 2>/dev/null || true
        echo "  💡 推奨コマンド: git add MT5/EA/ && git commit -m 'EA v2.0X: 変更内容'"
    else
        log_info "EA関連の変更なし"
    fi

    # 全体の変更チェック
    if git status --porcelain 2>/dev/null | grep -q "."; then
        uncommitted=$(git status --porcelain 2>/dev/null | wc -l || echo "0")
        log_info "未コミット変更: ${uncommitted}個のファイル"
    else
        log_info "Git状態はクリーン"
    fi
else
    log_warning "Git環境が利用できません"
fi

# 4. バージョン履歴確認
echo "4. バージョン履歴確認..."
if [ -f "$VERSION_FILE" ]; then
    if git status --porcelain 2>/dev/null | grep -q "VERSION_HISTORY.md"; then
        log_info "バージョン履歴更新検出"
    else
        log_warning "バージョン履歴未更新 - 手動更新を推奨"
        echo "  📝 更新推奨: $VERSION_FILE"
    fi
else
    log_warning "バージョン履歴ファイル不存在: $VERSION_FILE"
fi

# 5. 同期サマリー
echo "5. 同期サマリー..."
log_info "正規EA: $(basename "$CANONICAL_EA_PATH")"
log_info "MT5EA: $(basename "$MT5_EA_PATH")"
log_info "同期時刻: $(date '+%Y-%m-%d %H:%M:%S')"

# MT5プロセス確認（参考情報）
if pgrep -f "terminal64.exe" >/dev/null 2>&1; then
    log_info "MT5プロセス稼働中"
else
    log_warning "MT5プロセス未検出"
fi

echo "========================================"
echo "✅ 同期処理完了（安全モード）"
echo "🔔 MT5を再起動してEAの変更を反映してください"
