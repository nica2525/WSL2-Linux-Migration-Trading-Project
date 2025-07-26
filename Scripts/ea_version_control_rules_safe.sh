#!/bin/bash
# EAファイル バージョン管理ルール強制実行スクリプト (安全版)

# --- 厳格設定 ---
set -euo pipefail

# --- 設定変数 ---
PROJECT_ROOT="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
CANONICAL_EA_NAME="JamesORB_v1.0.mq5"
CANONICAL_EA_PATH="${PROJECT_ROOT}/MT5/EA/${CANONICAL_EA_NAME}"
VERSION_FILE="${PROJECT_ROOT}/MT5/EA/VERSION_HISTORY.md"
MT5_EA_DIR="/home/trader/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/"
TRASH_DIR="${PROJECT_ROOT}/.ea_trash"

# --- エラーハンドリング関数 ---
die() {
    echo "❌ エラー: $1" >&2
    exit 1
}

log_info() {
    echo "  ✅ $1"
}

log_warning() {
    echo "  ⚠️  $1"
}

# --- メイン処理 ---
echo "🛡️ EAファイル バージョン管理ルール強制実行 (安全モード)"
echo "======================================================"

# プロジェクトルートに移動
cd "$PROJECT_ROOT" || die "プロジェクトルートに移動できません: ${PROJECT_ROOT}"

# ゴミ箱ディレクトリ作成
mkdir -p "$TRASH_DIR" || die "ゴミ箱ディレクトリ作成失敗: ${TRASH_DIR}"

# ルール1: 重複ファイル検索・安全な移動
echo "1. 重複EAファイルをゴミ箱へ移動中..."
duplicate_count=0

# プロジェクト内での重複検索
while IFS= read -r -d '' file; do
    # 正規ファイル自体は除外
    if [ "$(realpath "$file" 2>/dev/null || echo "$file")" != "$(realpath "$CANONICAL_EA_PATH" 2>/dev/null || echo "$CANONICAL_EA_PATH")" ]; then
        # タイムスタンプ付きで安全に移動
        timestamp=$(date +%Y%m%d_%H%M%S)
        safe_name="$(basename "$file").${timestamp}"
        
        if mv "$file" "${TRASH_DIR}/${safe_name}" 2>/dev/null; then
            log_info "移動: $file -> ${TRASH_DIR}/${safe_name}"
            ((duplicate_count++))
        else
            log_warning "移動失敗: $file"
        fi
    fi
done < <(find . -type f -name "*JamesORB*.mq5" -print0 2>/dev/null || true)

# MT5ディレクトリ内での重複検索
if [ -d "$MT5_EA_DIR" ]; then
    while IFS= read -r -d '' file; do
        if [ "$(basename "$file")" != "$CANONICAL_EA_NAME" ]; then
            timestamp=$(date +%Y%m%d_%H%M%S)
            safe_name="MT5_$(basename "$file").${timestamp}"
            
            if mv "$file" "${TRASH_DIR}/${safe_name}" 2>/dev/null; then
                log_info "MT5から移動: $file -> ${TRASH_DIR}/${safe_name}"
                ((duplicate_count++))
            else
                log_warning "MT5移動失敗: $file"
            fi
        fi
    done < <(find "$MT5_EA_DIR" -type f -name "*JamesORB*.mq5" -print0 2>/dev/null || true)
fi

echo "  📊 重複ファイル処理数: ${duplicate_count}個"

# ルール2: 正規ファイル存在確認
echo "2. 正規EAファイル確認..."
if [ -f "$CANONICAL_EA_PATH" ]; then
    log_info "正規ファイル存在: $CANONICAL_EA_PATH"
    # ファイルサイズチェック
    size=$(stat -f%z "$CANONICAL_EA_PATH" 2>/dev/null || stat -c%s "$CANONICAL_EA_PATH" 2>/dev/null || echo "0")
    log_info "ファイルサイズ: ${size} bytes"
else
    die "正規ファイルが存在しません: ${CANONICAL_EA_PATH}"
fi

# ルール3: VERSION_HISTORY存在確認
echo "3. バージョン履歴確認..."
if [ -f "$VERSION_FILE" ]; then
    log_info "バージョン履歴存在: $VERSION_FILE"
else
    log_warning "バージョン履歴不存在: $VERSION_FILE"
    # 自動作成
    cat > "$VERSION_FILE" << 'EOF'
# JamesORB EA Version History

## v2.01 (Auto-created)
**基本機能:**
- マジックナンバー追加: 20250727
- 自動バージョン管理対応

**注意:** このファイルは自動作成されました。手動で更新してください。
EOF
    log_info "バージョン履歴ファイル自動作成完了"
fi

# ルール4: MT5への安全なコピー
echo "4. MT5への正規ファイルコピー..."
if [ -d "$MT5_EA_DIR" ] || mkdir -p "$MT5_EA_DIR" 2>/dev/null; then
    # バックアップ作成
    if [ -f "${MT5_EA_DIR}${CANONICAL_EA_NAME}" ]; then
        backup_name="${CANONICAL_EA_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "${MT5_EA_DIR}${CANONICAL_EA_NAME}" "${TRASH_DIR}/${backup_name}" 2>/dev/null || true
        log_info "既存ファイルバックアップ: ${backup_name}"
    fi
    
    # 安全なコピー
    if cp -p "$CANONICAL_EA_PATH" "${MT5_EA_DIR}${CANONICAL_EA_NAME}"; then
        log_info "コピー完了: ${MT5_EA_DIR}${CANONICAL_EA_NAME}"
    else
        die "MT5へのファイルコピーに失敗しました"
    fi
else
    die "MT5 EAディレクトリにアクセスできません: ${MT5_EA_DIR}"
fi

# ルール5: Git状態確認（エラーでも継続）
echo "5. Git状態確認..."
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    if git status --porcelain 2>/dev/null | grep -q "MT5/EA/"; then
        echo "  📝 EA関連の変更が検出されました"
        git status --short -- "MT5/EA/" 2>/dev/null || true
    else
        log_info "Git状態はクリーンです"
    fi
else
    log_warning "Git環境が利用できません"
fi

# ルール6: 実行サマリー
echo "6. 実行サマリー..."
log_info "処理済み重複ファイル: ${duplicate_count}個"
log_info "ゴミ箱ディレクトリ: ${TRASH_DIR}"
log_info "正規EAファイル: ${CANONICAL_EA_PATH}"

# ゴミ箱クリーニング（30日以上古いファイル削除）
if [ -d "$TRASH_DIR" ]; then
    old_files=$(find "$TRASH_DIR" -type f -mtime +30 2>/dev/null | wc -l || echo "0")
    if [ "$old_files" -gt 0 ]; then
        find "$TRASH_DIR" -type f -mtime +30 -delete 2>/dev/null || true
        log_info "古いゴミ箱ファイル削除: ${old_files}個"
    fi
fi

echo "======================================================"
echo "✅ EAバージョン管理ルール実行完了（安全モード）"
echo "🗑️  削除されたファイルは ${TRASH_DIR} で確認できます"