# 🔄 GPT依頼ルール管理（2025年版）

## 🎯 現在の統合状況（2025-07-25更新）
**統合完了**: GPT依頼統合プロトコル.mdに全手順統合済み
**ルール管理**: 文書/核心/GPT依頼統合プロトコル.md で一元管理
**現在の課題**: JamesORBデモ監視中、新EA開発は一時保留

## 📋 現在の統合システム

### GPT依頼プロトコル統合完了
- **場所**: 文書/核心/GPT依頼統合プロトコル.md
- **内容**: テンプレート・品質管理・実行管理を統合
- **効果**: 164行で全手順を一元管理

### hooks自動化システム
- **セッション記録**: 自動生成・追記管理
- **記憶継承**: セッション開始時自動確認
- **設定場所**: ~/.claude/settings.json

## 💡 旧代替案（参考・削除予定）

### 1. 手動実行の改善（旧版）
**方法:** `Scripts/gpt_request_helper.sh check` の手動実行（現在は統合済み）
**メリット:**
- 完全に安全
- 必要時のみ実行
- エラー時の影響が限定的

**デメリット:**
- 手動実行が必要（忘れる可能性）
- 長時間セッションでの忘却問題は未解決

**改善案:**
```bash
# より簡単なエイリアス設定
alias gpt="Scripts/gpt_request_helper.sh check && echo 'GPT依頼準備完了'"
```

### 2. VSCode拡張機能によるリマインダー
**方法:** VSCode拡張機能でGPT依頼前の自動通知
**メリット:**
- Claude Codeに影響しない
- 視覚的なリマインダー
- カスタマイズ可能

**実装:**
- VSCode Extensionで特定キーワード検出
- GPT関連操作時に通知表示
- ワンクリックでルール読み込み

### 3. 定期的なルール表示 (PostToolUse改善)
**方法:** 既存のPostToolUseを改良し、定期的にルール表示
**メリット:**
- 既存システムの活用
- 安全性が確保済み
- 段階的な改善が可能

**実装:**
```bash
# memory_tracker_hook.sh の改良
if [ $((ACTION_COUNT % 10)) -eq 0 ]; then
    echo "📋 GPT依頼時はルール確認を忘れずに！"
    echo "実行: Scripts/gpt_request_helper.sh check"
fi
```

### 4. MCP-Gemini依頼時の自動プロンプト追加
**方法:** MCP-Gemini使用時に自動でルールを含むプロンプトを生成
**メリット:**
- 自動化が実現
- Claude Codeに影響しない
- GPT依頼時のみ動作

**実装:**
```bash
# mcp_gemini_wrapper.sh
#!/bin/bash
RULES=$(cat GPT_REQUEST_PROTOCOL.md)
PROMPT="$RULES\n\n--- 以下がユーザーの実際の依頼です ---\n\n$1"
# MCP-Geminiに送信
```

### 5. セッション開始時の強制表示強化
**方法:** Start Hookでの重要ルールの強制表示
**メリット:**
- 安全性が高い
- セッション開始時の意識付け
- 既存システムの活用

**実装:**
```bash
# session_start_memory.sh の改良
echo "🤖 GPT依頼時の必須チェック:"
echo "1. Scripts/gpt_request_helper.sh check"
echo "2. GPT_REQUEST_PROTOCOL.md 確認"
echo "3. 品質基準の明確化"
```

### 6. 外部ツールとの連携
**方法:** 別プロセスでの監視・通知システム
**メリット:**
- Claude Codeと完全分離
- 自由度が高い
- 安全性が確保

**実装:**
```bash
# 別プロセスでのファイル監視
inotifywait -m . -e modify --format '%w%f' | while read FILE; do
    if [[ "$FILE" == *"gpt"* ]]; then
        notify-send "GPT依頼準備" "ルール確認を実行してください"
    fi
done
```

## 🎯 推奨代替案の評価

### 最優先: 手動実行の改善
**実装内容:**
- エイリアス設定で簡単実行
- 定期的なリマインダー強化
- チェックリストの可視化

### 第二案: PostToolUse改善
**実装内容:**
- 10アクション毎にGPTルール確認メッセージ
- 重要タイミングでの強制表示
- 既存システムの安全な拡張

### 第三案: VSCode拡張機能
**実装内容:**
- GPT関連キーワード検出
- 自動通知システム
- ワンクリック実行

## 💡 段階的実装計画

### Phase 1: 即座実装可能 (安全)
```bash
# 1. エイリアス設定
echo 'alias gpt="Scripts/gpt_request_helper.sh check"' >> ~/.bashrc

# 2. PostToolUse改善
# memory_tracker_hook.sh にリマインダー追加

# 3. セッション開始時強化
# session_start_memory.sh にGPTルール表示
```

### Phase 2: 中期実装 (検討要)
- VSCode拡張機能開発
- MCP-Gemini wrapper実装
- 外部監視ツール構築

### Phase 3: 長期実装 (慎重)
- PreToolUse実装（十分な検証後）
- 高度な自動化システム

## 🔧 結論

**推奨アプローチ:**
1. **Phase 1の安全な改善**を即座に実装
2. **PreToolUse実装は延期**
3. **既存システムの漸進的改善**に注力

**理由:**
- 現在の安定システムを維持
- 段階的な改善で確実性を確保
- 高リスクな変更を回避

---

---

**🚀 2025年版更新**: GPT依頼プロトコル統合完了、hooks自動化により解決済み
**管理者**: Claude Code（実装担当）
**次回更新**: 新EA開発時のGPT依頼発生時
