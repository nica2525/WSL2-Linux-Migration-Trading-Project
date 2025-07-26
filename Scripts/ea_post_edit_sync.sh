#!/bin/bash
# EAファイル編集後の自動同期スクリプト

EA_FILE="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/EA/JamesORB_v1.0.mq5"
MT5_EA_PATH="/home/trader/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/JamesORB_v1.0.mq5"

echo "🔄 EA編集後自動同期実行"
echo "======================"

# 1. EAファイル編集検出
if [ -f "$EA_FILE" ]; then
    # 2. MT5への自動同期
    echo "📋 MT5への同期中..."
    cp "$EA_FILE" "$MT5_EA_PATH"
    echo "  ✅ 同期完了: $MT5_EA_PATH"
    
    # 3. Git状態確認
    cd "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
    if git status --porcelain | grep -q "MT5/EA/"; then
        echo "📝 Git変更検出:"
        git status --porcelain | grep "MT5/EA/"
        echo "  💡 commit推奨: git add MT5/EA/ && git commit -m 'EA update'"
    fi
    
    # 4. バージョン履歴確認
    if git status --porcelain | grep -q "VERSION_HISTORY.md"; then
        echo "📚 バージョン履歴更新検出"
    else
        echo "⚠️  バージョン履歴未更新 - VERSION_HISTORY.md の更新を推奨"
    fi
    
else
    echo "❌ 正規EAファイルが見つかりません: $EA_FILE"
fi

echo "======================"
echo "✅ 同期処理完了"