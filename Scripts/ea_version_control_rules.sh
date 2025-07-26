#!/bin/bash
# EAファイル バージョン管理ルール強制実行スクリプト

EA_FILE="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/EA/JamesORB_v1.0.mq5"
VERSION_FILE="/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/EA/VERSION_HISTORY.md"
MT5_EA_PATH="/home/trader/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Experts/"

echo "🚫 EAファイル バージョン管理ルール強制実行"
echo "=================================="

# ルール1: 重複ファイル検索・削除
echo "1. 重複EAファイル検索・削除中..."
find . -name "*JamesORB*" -name "*.mq5" | grep -v "JamesORB_v1.0.mq5" | while read file; do
    if [ -f "$file" ]; then
        echo "  🗑️  削除: $file"
        rm "$file"
    fi
done

# ルール2: MT5ディレクトリ内の重複削除
echo "2. MT5ディレクトリ内重複削除..."
find "$MT5_EA_PATH" -name "*JamesORB*" -name "*.mq5" | grep -v "JamesORB_v1.0.mq5" | while read file; do
    if [ -f "$file" ]; then
        echo "  🗑️  MT5から削除: $file"
        rm "$file"
    fi
done

# ルール3: 正規ファイル存在確認
echo "3. 正規EAファイル確認..."
if [ -f "$EA_FILE" ]; then
    echo "  ✅ 正規ファイル存在: $EA_FILE"
else
    echo "  ❌ 正規ファイル不存在: $EA_FILE"
    exit 1
fi

# ルール4: VERSION_HISTORY存在確認
echo "4. バージョン履歴確認..."
if [ -f "$VERSION_FILE" ]; then
    echo "  ✅ バージョン履歴存在: $VERSION_FILE"
else
    echo "  ❌ バージョン履歴不存在: $VERSION_FILE"
    exit 1
fi

# ルール5: MT5への正規ファイルコピー
echo "5. MT5への正規ファイルコピー..."
cp "$EA_FILE" "$MT5_EA_PATH/JamesORB_v1.0.mq5"
echo "  ✅ コピー完了: $MT5_EA_PATH/JamesORB_v1.0.mq5"

# ルール6: Git状態確認
echo "6. Git状態確認..."
cd "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
if git status --porcelain | grep -q "MT5/EA/"; then
    echo "  📝 EA関連変更検出 - commit推奨"
    git status --porcelain | grep "MT5/EA/"
else
    echo "  ✅ Git状態クリーン"
fi

echo "=================================="
echo "✅ EAバージョン管理ルール実行完了"