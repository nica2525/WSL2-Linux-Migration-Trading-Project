#!/bin/bash
# Smart GPT Rule Loader - D案実装
# Geminiの応答 + Claudeの発言パターンでGPT作業を検出

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
TRIGGER_GPT_RULES=false

# 1. Geminiの応答チェック（C案の残存機能）
if echo "$GEMINI_RESPONSE" | grep "\[GPT_TASK_REQUIRED\]" > /dev/null; then
    TRIGGER_GPT_RULES=true
    echo "🤖 Geminiが明示的にGPT作業を推奨"
fi

# 2. Claudeの発言パターンチェック（D案の核心）
# 直近の会話ログから私の発言をチェック
RECENT_CLAUDE_RESPONSE=$(tail -50 "$PROJECT_DIR/.claude_conversation.log" 2>/dev/null || echo "")

if echo "$RECENT_CLAUDE_RESPONSE" | grep -iE "(GPT.*依頼|ChatGPT.*送信|実装依頼|依頼文.*作成|プロンプト.*作成|GPT.*で.*実装)" > /dev/null; then
    TRIGGER_GPT_RULES=true
    echo "🤖 Claude発言でGPT作業パターンを検出"
fi

# 3. 追加パターン: 作業フロー関連
if echo "$RECENT_CLAUDE_RESPONSE" | grep -iE "(次.*GPT|続い.*GPT|GPT.*使用|GPT.*実行)" > /dev/null; then
    TRIGGER_GPT_RULES=true
    echo "🤖 GPT作業フローを検出"
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
    head -30 "$PROJECT_DIR/GPT_REQUEST_PROTOCOL.md"
    
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