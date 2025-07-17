#!/bin/bash

# パス動的解決ヘルパー
# Gemini指摘: ハードコード除去・環境変更への対応

# このスクリプトの場所から相対的にプロジェクトディレクトリを解決
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 動的パス解決関数
get_project_dir() {
    echo "$PROJECT_DIR"
}

get_scripts_dir() {
    echo "$SCRIPT_DIR"
}

get_log_file() {
    local log_name="$1"
    echo "$PROJECT_DIR/.${log_name}.log"
}

get_config_file() {
    local config_name="$1"
    echo "$PROJECT_DIR/${config_name}"
}

# 環境変数設定（他スクリプトでsource可能）
export TRADING_PROJECT_DIR="$PROJECT_DIR"
export TRADING_SCRIPTS_DIR="$SCRIPT_DIR"

# デバッグ用（環境変数DEBUG_PATHS=1で有効）
if [[ "$DEBUG_PATHS" == "1" ]]; then
    echo "🔍 パス解決結果:"
    echo "   PROJECT_DIR: $PROJECT_DIR"
    echo "   SCRIPT_DIR: $SCRIPT_DIR"
    echo "   Git自動保存ログ: $(get_log_file "cron_git_auto_save")"
    echo "   システム監視ログ: $(get_log_file "cron_monitor")"
fi