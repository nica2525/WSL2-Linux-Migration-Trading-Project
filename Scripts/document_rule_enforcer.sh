#!/bin/bash
# ドキュメント管理強制システム（リファクタリング版）
# 2025-07-26 実装・修正・リファクタリング版
# 参考: anthropics/claude-code#3573, disler/claude-code-hooks-mastery
# Gemini査読 + 不具合修正 + パフォーマンス改善 + ファイルベースロック実装

readonly SCRIPT_NAME="document_rule_enforcer"
readonly SCRIPT_DIR=$(dirname "$(realpath "$0")")
readonly PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
readonly LOCK_DIR="$PROJECT_ROOT/.cache/doc_hook.lock"

# 安全な実行のための設定
set -euo pipefail

# ===============================
# ユーティリティ関数
# ===============================

# ログ出力（デバッグ用）
log_debug() {
    [ "${DEBUG:-0}" = "1" ] && echo "[DEBUG] $*" >&2
}

# JSON レスポンス生成
json_response() {
    local continue_flag="$1"
    local reason="${2:-}"

    if [ "$continue_flag" = "true" ]; then
        echo '{"continue": true}'
    else
        cat << EOF
{
    "continue": false,
    "stopReason": "$reason",
    "suppressOutput": false
}
EOF
    fi
}

# 多重実行防止チェック（ファイルベースロック）
acquire_lock() {
    # .cacheディレクトリを作成（必要に応じて）
    mkdir -p "$(dirname "$LOCK_DIR")" 2>/dev/null || true

    if mkdir "$LOCK_DIR" 2>/dev/null; then
        log_debug "Lock acquired: $LOCK_DIR"
        return 0
    else
        log_debug "Lock directory exists, another instance is running"
        return 1
    fi
}

# クリーンアップ処理
cleanup() {
    log_debug "Cleanup: removing lock directory"
    rmdir "$LOCK_DIR" 2>/dev/null || true
}

# 安全な終了
safe_exit() {
    local exit_code="${1:-0}"
    cleanup
    exit "$exit_code"
}

# ===============================
# ファイル検証関数
# ===============================

# .mdファイルかチェック
is_markdown_file() {
    local file="$1"
    [[ "$file" == *.md ]]
}

# ファイル存在チェック（安全版）
file_exists_safely() {
    local file="$1"
    [ -f "$file" ] && [ ! -L "$file" ]  # 通常ファイルのみ、シンボリックリンク除外
}

# 命名規則チェック
check_naming_convention() {
    local filename="$1"
    # 改良版正規表現: 日本語・英数字・アンダースコア対応
    [[ "$filename" =~ ^[A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+_[A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+_[A-Za-z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+\.md$ ]]
}

# 推奨ファイル検索
find_suggested_files() {
    local target_name="$1"
    local suggestions=()

    # プロジェクトから関連ファイルを動的検索
    if [[ "$target_name" == *"JamesORB"* ]]; then
        suggestions+=("JamesORB_バックテスト分析レポート_2025-07-24.md")
    fi

    # システム系ファイル
    suggestions+=("システム・MCP・拡張機能統合ロードマップ.md")

    # 存在するファイルのみ返す
    local existing_files=()
    for file in "${suggestions[@]}"; do
        if file_exists_safely "$PROJECT_ROOT/$file" || file_exists_safely "$file"; then
            existing_files+=("$file")
        fi
    done

    printf '%s\n' "${existing_files[@]}"
}

# ===============================
# メイン処理関数
# ===============================

# 新規Markdownファイル作成の処理
handle_new_markdown() {
    local target_file="$1"
    local filename
    filename=$(basename "$target_file")

    log_debug "Blocking new markdown file creation: $filename"

    # 推奨ファイルを動的に検索
    local suggested_files
    suggested_files=$(find_suggested_files "$filename")

    local suggestion_text=""
    if [ -n "$suggested_files" ]; then
        suggestion_text="\n\n📂 推奨既存ファイル:\n$(echo "$suggested_files" | sed 's/^/- /')"
    fi

    local stop_reason="🚨 新規Markdownファイル作成は禁止されています

❌ 禁止理由:
• ファイル散乱防止
• Git履歴の清潔性保持
• 開発効率向上

✅ 対応方法:
1. 既存の関連ファイルを特定
2. Edit操作で既存ファイルに追記
3. 命名規則: {プロジェクト}_{対象}_{内容}.md

🔧 新規作成が本当に必要な場合:
• Claudeからユーザーに理由説明・承認依頼
• 承認後に適切な手順で作成
• 作成理由をセッション記録に必須記載$suggestion_text"

    json_response "false" "$stop_reason"
    safe_exit 2
}

# 命名規則警告の処理
handle_naming_warning() {
    local filename="$1"

    echo "⚠️ 命名規則推奨: $filename"
    echo "推奨形式: {プロジェクト}_{対象}_{内容}.md"
    echo "例: JamesORB_統計分析.md, MT5システム_データ構造.md"
}

# メイン処理
main() {
    # 多重実行防止
    if ! acquire_lock; then
        exit 0  # 他のインスタンスが実行中
    fi

    # 異常終了時のクリーンアップ設定
    trap cleanup EXIT INT TERM

    # 引数チェック
    if [ $# -eq 0 ]; then
        log_debug "No arguments provided"
        json_response "true"
        safe_exit 0
    fi

    local target_file="$1"
    local filename
    filename=$(basename "$target_file")

    log_debug "Processing file: $target_file"

    # Markdownファイルの場合のみ処理
    if is_markdown_file "$target_file"; then
        log_debug "Markdown file detected"

        # 新規ファイル作成チェック
        if ! file_exists_safely "$target_file"; then
            handle_new_markdown "$target_file"
            # この時点で exit される
        fi

        # 既存ファイルの命名規則チェック（警告のみ）
        if ! check_naming_convention "$filename"; then
            handle_naming_warning "$filename"
        fi
    else
        log_debug "Non-markdown file, skipping"
    fi

    # 正常終了
    log_debug "Processing completed successfully"
    json_response "true"
    safe_exit 0
}

# ===============================
# エントリーポイント
# ===============================

# メイン処理実行
main "$@"
