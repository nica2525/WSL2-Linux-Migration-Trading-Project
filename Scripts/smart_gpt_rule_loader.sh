#!/bin/bash
# Smart GPT Rule Loader - JSON Hook対応版
# HookのJSON入力からGPT作業を検出

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
TRIGGER_GPT_RULES=false

# Hook JSON入力読み取り（stdin経由）
HOOK_INPUT=""
if [ -t 0 ]; then
    # TTYからの実行（テスト時）
    echo "📋 テストモード: Hook JSON入力なし"
else
    # 実際のHook実行時
    HOOK_INPUT=$(cat)
fi

# Python JSONパーサー（jq代替）
parse_json() {
    python3 -c "
import json, sys
try:
    data = json.load(sys.stdin) if sys.stdin.isatty() == False else json.loads('$1')
    keys = '$2'.split('.')
    result = data
    for key in keys:
        if key and isinstance(result, dict):
            result = result.get(key, '')
    print(result if result is not None else '')
except:
    pass
"
}

# 1. Geminiの応答チェック（mcp__gemini-cli__chat実行時）
TOOL_NAME=$(echo "$HOOK_INPUT" | parse_json "" "tool_name")
if [ "$TOOL_NAME" = "mcp__gemini-cli__chat" ]; then
    GEMINI_RESPONSE=$(echo "$HOOK_INPUT" | parse_json "" "tool_response.response")
    if echo "$GEMINI_RESPONSE" | grep -q "\[GPT_TASK_REQUIRED\]"; then
        TRIGGER_GPT_RULES=true
        echo "🤖 Geminiが明示的にGPT作業を推奨"
    fi
fi

# 2. Claude作業パターン検出（transcript_path解析）
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | parse_json "" "transcript_path")
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    # 最新の20行からGPT関連パターンを検索
    RECENT_CONTENT=$(tail -20 "$TRANSCRIPT_PATH" 2>/dev/null | tail -10)
    if echo "$RECENT_CONTENT" | grep -iE "(GPT.*依頼|ChatGPT.*送信|実装依頼|依頼文.*作成|プロンプト.*作成|GPT.*で.*実装|3AI.*collaboration|to_chatgpt)" > /dev/null; then
        TRIGGER_GPT_RULES=true
        echo "🤖 Claude発言でGPT作業パターンを検出"
    fi
fi

# 3. ファイル操作パターン検出（Write/Edit時の3AI_collaborationフォルダ）
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
    FILE_PATH=$(echo "$HOOK_INPUT" | parse_json "" "tool_input.file_path")
    if echo "$FILE_PATH" | grep -E "3AI_collaboration|to_chatgpt|gpt.*request" > /dev/null; then
        TRIGGER_GPT_RULES=true
        echo "🤖 GPT関連ファイル操作を検出"
    fi
fi

# 4. GPTルール読み込み実行
if [ "$TRIGGER_GPT_RULES" = true ]; then
    echo ""
    echo "📋 =============================================="
    echo "🎯 GPT依頼作業が検出されました"
    echo "📋 GPT依頼ルール自動読み込み実行中..."
    echo "📋 =============================================="
    echo ""

    # GPTルール表示
    echo "📋 GPT依頼プロトコル（重要部分）:"
    head -30 "$PROJECT_DIR/文書/核心/GPT依頼プロトコル.md"

    echo ""
    echo "🔍 現在の品質状況:"
    python3 "$PROJECT_DIR/Scripts/quality_checker.py" | head -15

    echo ""
    echo "💡 依頼文作成時の必須確認:"
    echo "1. 具体的な目的・背景の明示"
    echo "2. 期待する結果の詳細仕様"
    echo "3. 品質基準・検証方法の定義"
    echo "4. 学習目的時は改善理由説明"
    echo ""
    echo "⚠️ 依頼文に不備があれば修正してください"
    echo "📋 =============================================="

    # 実行記録
    echo "$(date '+%Y-%m-%d %H:%M:%S') - GPTルール自動読み込み実行 (D案)" >> "$PROJECT_DIR/.gpt_rules_auto_load.log"
else
    echo "📖 Gemini単体作業 - GPTルール読み込みスキップ"
fi
