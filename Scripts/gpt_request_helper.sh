#!/bin/bash
#
# GPT依頼文作成ヘルパースクリプト
# 簡単なコマンドでGPT依頼文自動化システムを使用
#

PROJECT_DIR="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
AUTOMATION_SCRIPT="$PROJECT_DIR/Scripts/gpt_request_automation.py"

show_help() {
    cat << EOF
🤖 GPT依頼文作成ヘルパー

使用方法:
  $0 check           # 依頼文作成前チェック実行
  $0 template TYPE   # テンプレート生成 (refactoring|analysis|implementation|general)
  $0 setup           # pre-commitフック設定
  $0 status          # 現在の状況確認

例:
  $0 check                    # 作業前チェック
  $0 template refactoring     # リファクタリング用テンプレート
  $0 template analysis        # 分析用テンプレート
EOF
}

case "$1" in
    "check")
        echo "🔍 GPT依頼文作成前チェック実行中..."
        cd "$PROJECT_DIR"
        python3 "$AUTOMATION_SCRIPT" --check-only
        ;;
    
    "template")
        if [ -z "$2" ]; then
            echo "❌ テンプレートタイプを指定してください"
            echo "使用可能: refactoring, analysis, implementation, general"
            exit 1
        fi
        
        echo "📝 $2 テンプレート生成中..."
        cd "$PROJECT_DIR"
        python3 "$AUTOMATION_SCRIPT" --template "$2"
        ;;
    
    "setup")
        echo "⚙️ pre-commitフック設定中..."
        cd "$PROJECT_DIR"
        python3 "$AUTOMATION_SCRIPT" --create-hook
        ;;
    
    "status")
        echo "📊 現在の状況:"
        cd "$PROJECT_DIR"
        echo "Git状況:"
        git status --porcelain | head -5
        echo -e "\n最近のGPT依頼文:"
        ls -la 3AI_collaboration/to_chatgpt/*.md 2>/dev/null | tail -3 || echo "なし"
        ;;
    
    "help"|"-h"|"--help"|"")
        show_help
        ;;
    
    *)
        echo "❌ 不明なコマンド: $1"
        show_help
        exit 1
        ;;
esac