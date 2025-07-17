#!/bin/bash

# セッション記録ルール参照スクリプト
# Gemini改善: パス動的解決対応

# パス動的解決
source "$(dirname "$0")/path_resolver.sh"
PROJECT_DIR="$(get_project_dir)"
CLAUDE_MD="$(get_config_file "CLAUDE.md")"
RECORD_DIR="$PROJECT_DIR/文書/記録"

# 引数から操作を判定
OPERATION="$1"
TOOL_NAME="$2"

# セッション記録関連ツール使用時のみ動作
if [[ "$TOOL_NAME" == "Write" && "$*" == *"セッション記録"* ]]; then
    
    echo "🔍 セッション記録ルール確認中..."
    
    # 当日の既存ファイル確認
    TODAY=$(date +%Y-%m-%d)
    EXISTING_FILE=$(find "$RECORD_DIR" -name "*${TODAY}*.md" 2>/dev/null | head -1)
    
    if [[ -n "$EXISTING_FILE" ]]; then
        echo "📝 同日ファイル発見: $(basename "$EXISTING_FILE")"
        echo "💡 ルール: 既存ファイルに「## 追加セッション」として追記してください"
        echo "📋 参照: CLAUDE.md 「📝 セッション記録基本ルール」セクション"
        
        # CLAUDE.mdのルール部分を表示
        if [[ -f "$CLAUDE_MD" ]]; then
            echo ""
            echo "📖 適用ルール:"
            grep -A 5 "## 📝 セッション記録基本ルール" "$CLAUDE_MD" | head -6
        fi
    else
        echo "📁 当日初回セッション: 新規ファイル作成OK"
    fi
    
    echo "✅ ルール確認完了"
fi

exit 0