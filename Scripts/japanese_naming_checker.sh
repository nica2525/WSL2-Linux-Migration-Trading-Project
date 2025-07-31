#!/bin/bash
# 日本語化ルール遵守チェッカー
# PostToolUse Hookで自動実行

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"

echo "📝 日本語化ルール遵守チェック実行中..."

# 1. ルートディレクトリの英語MDファイルチェック
ENGLISH_MD_IN_ROOT=$(find "$PROJECT_DIR" -maxdepth 1 -name "*.md" -not -name "README.md" -not -name "CLAUDE.md" -not -name "現在の品質状況.md" | grep -E "[A-Z_]")

if [ -n "$ENGLISH_MD_IN_ROOT" ]; then
    echo "🚨 ルートディレクトリに英語名のMDファイルが発見されました:"
    echo "$ENGLISH_MD_IN_ROOT"
    echo "💡 文書/以下の適切なフォルダに日本語名で移動してください"
    echo ""
fi

# 2. 文書フォルダ外の文書ファイルチェック
DOCS_OUTSIDE=$(find "$PROJECT_DIR" -name "*.md" -not -path "*/文書/*" -not -path "*/node_modules/*" -not -path "*/miniconda3/*" -not -path "*/.wine/*" -not -name "README.md" -not -name "CLAUDE.md" -not -name "現在の品質状況.md")

if [ -n "$DOCS_OUTSIDE" ]; then
    echo "📁 文書フォルダ外に配置されているMDファイル:"
    echo "$DOCS_OUTSIDE"
    echo "💡 文書/以下に移動してください"
    echo ""
fi

# 3. 文書フォルダ内の英語名ファイルチェック
ENGLISH_IN_DOCS=$(find "$PROJECT_DIR/文書" -name "*.md" 2>/dev/null | grep -E "[A-Z_]")

if [ -n "$ENGLISH_IN_DOCS" ]; then
    echo "🔤 文書フォルダ内に英語名ファイルが発見されました:"
    echo "$ENGLISH_IN_DOCS"
    echo "💡 日本語名に変更してください"
    echo ""
fi

# 4. 分類されていないファイルチェック
UNCATEGORIZED=$(find "$PROJECT_DIR/文書" -maxdepth 1 -name "*.md" 2>/dev/null)

if [ -n "$UNCATEGORIZED" ]; then
    echo "📂 未分類の文書ファイル:"
    echo "$UNCATEGORIZED"
    echo "💡 核心/技術/管理/代替案 のいずれかに分類してください"
    echo ""
fi

# 5. 正常状態の確認
if [ -z "$ENGLISH_MD_IN_ROOT" ] && [ -z "$DOCS_OUTSIDE" ] && [ -z "$ENGLISH_IN_DOCS" ] && [ -z "$UNCATEGORIZED" ]; then
    echo "✅ 日本語化ルール遵守状況: 良好"
else
    echo "⚠️ 日本語化ルールの違反が発見されました"
    echo "📋 詳細は上記を確認してください"
fi

echo ""
echo "📋 日本語化ルール詳細: cat 文書/核心/日本語化ルール.md"
