#!/bin/bash

# WSL移行後の自動設定復旧スクリプト
# 使用方法: bash Scripts/wsl_migration_setup.sh

echo "🚀 WSL移行後設定復旧スクリプト開始"
echo "================================================="

# 現在のディレクトリ確認
if [[ ! -f "CLAUDE.md" ]]; then
    echo "❌ エラー: プロジェクトルートで実行してください"
    exit 1
fi

# 1. プロジェクトディレクトリの確認
echo "📁 プロジェクトディレクトリ確認中..."
PROJECT_DIR="$(pwd)"
echo "現在のプロジェクト: $PROJECT_DIR"

# 2. cron設定の自動復旧
echo "⏰ cron設定復旧中..."
cat > /tmp/new_crontab.txt << EOF
*/3 * * * * /usr/bin/python3 $PROJECT_DIR/Scripts/cron_git_auto_save.py >> $PROJECT_DIR/.cron_git_auto_save.log 2>&1
*/5 * * * * /usr/bin/python3 $PROJECT_DIR/Scripts/cron_system_monitor.py >> $PROJECT_DIR/.cron_monitor.log 2>&1
EOF

crontab /tmp/new_crontab.txt
rm /tmp/new_crontab.txt

echo "✅ cron設定復旧完了"
crontab -l

# 3. Claude設定の自動更新
echo "🤖 Claude設定更新中..."
if [[ -f "$HOME/.claude/settings.json" ]]; then
    # バックアップ作成
    cp "$HOME/.claude/settings.json" "$HOME/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)"
    
    # パス更新
    sed -i "s|/mnt/e/Trading-Development|$HOME/Trading-Development|g" "$HOME/.claude/settings.json"
    
    echo "✅ Claude設定更新完了"
else
    echo "⚠️  警告: Claude設定ファイルが見つかりません"
fi

# 4. 権限設定の確認
echo "🔐 権限設定確認中..."
find Scripts/ -name "*.sh" -exec chmod +x {} \;
find Scripts/ -name "*.py" -exec chmod +x {} \;
echo "✅ 権限設定完了"

# 5. Git設定の確認
echo "📝 Git設定確認中..."
git config --list | grep -E "(user.name|user.email)" || echo "⚠️  警告: Git設定が見つかりません"

# 6. 必要ディレクトリの作成
echo "📂 必要ディレクトリ作成中..."
mkdir -p logs
mkdir -p mcp_data
mkdir -p backup
echo "✅ ディレクトリ作成完了"

# 7. 環境変数の設定
echo "🌍 環境変数設定中..."
if ! grep -q "Trading-Development" "$HOME/.bashrc"; then
    echo "export TRADING_PROJECT_ROOT=\"$PROJECT_DIR\"" >> "$HOME/.bashrc"
    echo "✅ 環境変数追加完了"
else
    echo "✅ 環境変数は既に設定済み"
fi

# 8. 動作テスト
echo "🧪 動作テスト実行中..."

# cronプロセス確認
if ps aux | grep -q "[c]ron"; then
    echo "✅ cron動作確認: OK"
else
    echo "❌ cron動作確認: NG"
fi

# Git動作確認
if git status > /dev/null 2>&1; then
    echo "✅ Git動作確認: OK"
else
    echo "❌ Git動作確認: NG"
fi

# Python動作確認
if python3 --version > /dev/null 2>&1; then
    echo "✅ Python動作確認: OK"
else
    echo "❌ Python動作確認: NG"
fi

# 9. 最終確認
echo "================================================="
echo "🎉 WSL移行後設定復旧完了"
echo "================================================="
echo "📊 設定確認:"
echo "- プロジェクト: $PROJECT_DIR"
echo "- cron設定: $(crontab -l | wc -l) 行"
echo "- Claude設定: $(test -f ~/.claude/settings.json && echo "存在" || echo "不存在")"
echo "- Git状態: $(git status --porcelain | wc -l) 変更"
echo ""
echo "⚠️  重要: VSCodeを再起動してClaude Code接続を確認してください"
echo "================================================="

# 10. 次のステップガイド
echo "🎯 次のステップ:"
echo "1. VSCodeを再起動"
echo "2. WSL Remote拡張で新環境に接続"
echo "3. Claude Codeが正常動作するか確認"
echo "4. 3分後に 'tail -f .cron_git_auto_save.log' でcron動作確認"
echo "5. 性能向上を体感してください！"
echo ""
echo "🔧 トラブル時は WSL_MIGRATION_GUIDE.md を参照"