#!/bin/bash

# システム自動化ヘルスチェッカー
# hooks・cron・Git自動化の継続性監視
# Gemini改善: パス動的解決対応

# パス動的解決
source "$(dirname "$0")/path_resolver.sh"
PROJECT_DIR="$(get_project_dir)"
LOG_DIR="$PROJECT_DIR"
SETTINGS_FILE="/home/trader/.claude/settings.json"

echo "🔍 システム自動化ヘルスチェック実行中..."
echo "========================================"

# 1. cron動作確認
echo "📋 1. cron自動化システム確認"
if crontab -l | grep -q "cron_git_auto_save.py"; then
    echo "✅ Git自動保存cron: 動作中"
else
    echo "❌ Git自動保存cron: 停止"
fi

if crontab -l | grep -q "cron_system_monitor.py"; then
    echo "✅ システム監視cron: 動作中"
else
    echo "❌ システム監視cron: 停止"
fi

# 2. Git自動保存動作確認
echo ""
echo "📋 2. Git自動保存動作確認"
if [[ -f "$LOG_DIR/.cron_git_auto_save.log" ]]; then
    LAST_SAVE=$(tail -n 3 "$LOG_DIR/.cron_git_auto_save.log" | grep "処理終了" | tail -1)
    if [[ -n "$LAST_SAVE" ]]; then
        echo "✅ Git自動保存: 正常動作"
        echo "   最終実行: $LAST_SAVE"
    else
        echo "❌ Git自動保存: ログ異常"
    fi
else
    echo "❌ Git自動保存: ログファイル欠如"
fi

# 3. hooks設定確認
echo ""
echo "📋 3. Claude hooks設定確認"
if [[ -f "$SETTINGS_FILE" ]]; then
    if grep -q "session_record_rule_checker.sh" "$SETTINGS_FILE"; then
        echo "✅ セッション記録hooks: 設定済み"
    else
        echo "❌ セッション記録hooks: 未設定"
    fi
    
    if grep -q "memory_tracker_hook.sh" "$SETTINGS_FILE"; then
        echo "✅ メモリトラッカーhooks: 設定済み"
    else
        echo "❌ メモリトラッカーhooks: 未設定"
    fi
else
    echo "❌ Claude設定ファイル: 欠如"
fi

# 4. 重要スクリプト実行権限確認
echo ""
echo "📋 4. 重要スクリプト権限確認"
SCRIPTS=(
    "cron_git_auto_save.py"
    "cron_system_monitor.py"
    "session_record_rule_checker.sh"
    "memory_tracker_hook.sh"
)

for script in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="$PROJECT_DIR/Scripts/$script"
    if [[ -x "$SCRIPT_PATH" ]]; then
        echo "✅ $script: 実行権限OK"
    elif [[ -f "$SCRIPT_PATH" ]]; then
        echo "⚠️ $script: 実行権限なし"
    else
        echo "❌ $script: ファイル欠如"
    fi
done

# 5. システム依存関係確認
echo ""
echo "📋 5. システム依存関係確認"
if command -v git >/dev/null 2>&1; then
    echo "✅ Git: インストール済み"
else
    echo "❌ Git: 未インストール"
fi

if command -v python3 >/dev/null 2>&1; then
    echo "✅ Python3: インストール済み"
else
    echo "❌ Python3: 未インストール"
fi

# 6. 総合評価
echo ""
echo "========================================"
echo "🏆 システム自動化ヘルスチェック完了"
echo "📅 実行日時: $(date '+%Y-%m-%d %H:%M:%S JST')"
echo ""
echo "💡 問題発見時の対処法:"
echo "   - cron停止時: crontab -e で再設定"
echo "   - hooks停止時: ~/.claude/settings.json 確認"
echo "   - 権限問題時: chmod +x Scripts/*.sh で修復"
echo "========================================"

exit 0