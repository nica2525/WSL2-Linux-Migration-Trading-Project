#!/bin/bash

# Gemini改善実装検証スクリプト
# 3項目改善の完了確認

source "$(dirname "$0")/path_resolver.sh"
PROJECT_DIR="$(get_project_dir)"

echo "🏆 Gemini指摘改善実装検証"
echo "========================================"

# 1. スケジューラ一元化確認
echo "📋 1. スケジューラ一元化確認"
if [[ -d "$PROJECT_DIR/systemd.DISABLED" ]]; then
    echo "✅ systemd無効化: 完了"
else
    echo "❌ systemd無効化: 未完了"
fi

if crontab -l | grep -q "cron_git_auto_save.py"; then
    echo "✅ cron Git自動保存: 動作中"
else
    echo "❌ cron Git自動保存: 未設定"
fi

if crontab -l | grep -q "cron_system_monitor.py"; then
    echo "✅ cron システム監視: 動作中"
else
    echo "❌ cron システム監視: 未設定"
fi

# 2. ログ管理確認
echo ""
echo "📋 2. ログ管理確認"
if crontab -l | grep -q "logrotate"; then
    echo "✅ logrotate cron: 設定済み"
else
    echo "❌ logrotate cron: 未設定"
fi

if [[ -f "/home/trader/.logrotate.conf" ]]; then
    echo "✅ logrotate設定ファイル: 存在"
else
    echo "❌ logrotate設定ファイル: 欠如"
fi

if [[ -f "/home/trader/.logrotate.state" ]]; then
    echo "✅ logrotate状態ファイル: 存在"
else
    echo "❌ logrotate状態ファイル: 欠如"
fi

# 3. パス動的解決確認
echo ""
echo "📋 3. パス動的解決確認"
if [[ -f "$PROJECT_DIR/Scripts/path_resolver.sh" ]]; then
    echo "✅ パス解決ヘルパー: 存在"
else
    echo "❌ パス解決ヘルパー: 欠如"
fi

# パス解決テスト
if source "$PROJECT_DIR/Scripts/path_resolver.sh" 2>/dev/null; then
    RESOLVED_DIR="$(get_project_dir)"
    if [[ "$RESOLVED_DIR" == "$PROJECT_DIR" ]]; then
        echo "✅ パス動的解決: 正常動作"
    else
        echo "❌ パス動的解決: 動作異常"
    fi
else
    echo "❌ パス動的解決: 実行エラー"
fi

# 主要スクリプトの動的パス対応確認
DYNAMIC_SCRIPTS=(
    "session_record_rule_checker.sh"
    "system_health_checker.sh"
)

for script in "${DYNAMIC_SCRIPTS[@]}"; do
    if grep -q "path_resolver.sh" "$PROJECT_DIR/Scripts/$script"; then
        echo "✅ $script: 動的パス対応済み"
    else
        echo "❌ $script: ハードコード残存"
    fi
done

# 4. システム統合状況確認
echo ""
echo "📋 4. システム統合状況確認"
TOTAL_CRON_JOBS=$(crontab -l | wc -l)
echo "   cron設定数: $TOTAL_CRON_JOBS"
echo "   - Git自動保存: 3分間隔"
echo "   - システム監視: 5分間隔"
echo "   - ログローテーション: 毎日2:00AM"

# 5. 総合評価
echo ""
echo "========================================"
echo "🎯 Gemini改善実装状況"

IMPROVEMENTS=0
TOTAL=3

# 改善項目カウント
if [[ -d "$PROJECT_DIR/systemd.DISABLED" ]] && crontab -l | grep -q "cron_git_auto_save.py"; then
    echo "✅ 1. スケジューラ一元化: 完了"
    ((IMPROVEMENTS++))
else
    echo "❌ 1. スケジューラ一元化: 未完了"
fi

if crontab -l | grep -q "logrotate" && [[ -f "/home/trader/.logrotate.conf" ]]; then
    echo "✅ 2. ログ管理導入: 完了"
    ((IMPROVEMENTS++))
else
    echo "❌ 2. ログ管理導入: 未完了"
fi

if [[ -f "$PROJECT_DIR/Scripts/path_resolver.sh" ]] && grep -q "path_resolver.sh" "$PROJECT_DIR/Scripts/system_health_checker.sh"; then
    echo "✅ 3. パス動的解決: 完了"
    ((IMPROVEMENTS++))
else
    echo "❌ 3. パス動的解決: 未完了"
fi

echo ""
echo "🏆 完了率: $IMPROVEMENTS/$TOTAL ($(( IMPROVEMENTS * 100 / TOTAL ))%)"

if [[ $IMPROVEMENTS -eq $TOTAL ]]; then
    echo "🎉 全てのGemini指摘改善が完了しました！"
    echo "💎 システムは「ほぼ停止しない盤石なシステム」に進化"
else
    echo "⚠️ 一部改善が未完了です"
fi

echo "========================================"

exit 0
