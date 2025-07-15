#!/bin/bash
# セッション開始時記憶システム強制実行
# 作成日時: 2025-07-12 22:20 JST

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S JST')

echo "🧠 =================================="
echo "📅 Claude記憶システム強制実行開始"
echo "⏰ 実行時刻: $CURRENT_TIME"
echo "🧠 =================================="

# 日本語化ルール確認
echo "📝 日本語化ルール遵守確認:"
bash "$PROJECT_DIR/Scripts/japanese_naming_checker.sh"
echo ""

# セッション開始記録（Git管理対象）
echo "$CURRENT_TIME - セッション開始記憶確認実行" >> "$PROJECT_DIR/docs/MEMORY_EXECUTION_HISTORY.md"

echo "📋 記憶更新方式: 統合システム読み込み"
echo "  🎯 CLAUDE_UNIFIED_SYSTEM.md → 全情報一元化"
echo "  🗺️ ESSENTIAL_REFERENCES.md → 参照マップ（バックアップ）"
echo "  ⚡ 効率化: 9ファイル → 1ファイル統合完了"

echo ""
echo "🔄 記憶システム確認事項:"
echo "  • ChatGPT依頼: docs/CHATGPT_TASK_REQUEST.md"
echo "  • 命名規則: 統一済み"
echo "  • Git自動保存: Scripts/start_auto_git.sh status"
echo "  • 3AI役割: Claude統合、Gemini監査、ChatGPT実装"

echo ""
echo "⚡ 次回記憶更新:"
echo "  • 30分後: $(date -d '+30 minutes' '+%H:%M JST')"
echo "  • 30アクション後: アクション数監視中"

echo "🧠 =================================="

# アクションカウンターリセット（セッション開始時）
echo "1" > "$PROJECT_DIR/.action_count"