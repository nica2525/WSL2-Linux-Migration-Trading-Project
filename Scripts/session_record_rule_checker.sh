#!/bin/bash

# 🚨 セッション記録ルール絶対遵守システム 🚨
# CLAUDE.md準拠・違反時即座阻止

PROJECT_ROOT="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
RECORD_DIR="$PROJECT_ROOT/文書/記録"
TODAY=$(date +%Y-%m-%d)

# 緊急ルール表示関数
show_emergency_rules() {
    echo "🚨🚨🚨 セッション記録ルール絶対遵守 🚨🚨🚨"
    echo "=============================================="
    echo "【CLAUDE.md 必須ルール】"
    echo ""
    echo "✅ 同日追記対応（ファイル散らかり防止）:"
    echo "   - 同日セッション: 既存の当日ファイルに追記"
    echo "   - 「## 追加セッション」として追記"
    echo "   - 新規ファイル作成は絶対禁止"
    echo ""
    echo "✅ ファイル命名: セッション記録_YYYY-MM-DD_主要成果.md"
    echo ""
    echo "✅ 重複ファイル: 作成後即座に削除、既存ファイル統合"
    echo ""
    echo "✅ 場所: $RECORD_DIR/ 内のみ"
    echo ""
    echo "🚫 絶対禁止: プロジェクトルート直下への作成"
    echo "=============================================="
}

# 既存ファイル確認・強制表示
check_existing_files() {
    echo "🔍 既存セッション記録ファイル検索中..."
    echo "対象日: $TODAY"
    echo ""

    # プロジェクト全体から当日ファイル検索
    EXISTING_FILES=$(find "$PROJECT_ROOT" -name "セッション記録_${TODAY}_*.md" -type f 2>/dev/null)

    if [ -n "$EXISTING_FILES" ]; then
        echo "📋 既存の当日セッション記録発見:"
        echo "$EXISTING_FILES"
        echo ""
        echo "🚨 必須作業:"
        echo "1. Read操作で既存ファイル読み込み"
        echo "2. Edit操作で「## 追加セッション」追記"
        echo "3. Write操作による新規作成は絶対禁止"
        echo ""
        return 0
    else
        echo "📝 当日初回セッション - 新規ファイル作成可能"
        echo "作成場所: $RECORD_DIR/"
        echo ""
        return 1
    fi
}

# メイン実行
clear
echo "🤖 セッション記録ルール絶対遵守チェッカー"
echo "起動時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

show_emergency_rules
echo ""
check_existing_files

echo "⚠️  この画面を必ず確認してから作業を開始してください"
echo "✅ Enter キーで確認完了"
read
