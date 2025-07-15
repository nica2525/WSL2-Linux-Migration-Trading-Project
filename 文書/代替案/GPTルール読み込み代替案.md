# 🔄 GPT依頼前ルール読み込み - 代替案検討

## 🚨 PreToolUse実装の問題点
- **無限ループリスク**: 記事でも警告されている
- **全システム停止**: 一度エラーが発生すると復旧困難
- **性能劣化**: 毎回のツール実行で遅延
- **想定外発動**: 単純操作でも重い処理実行

## 💡 代替案一覧

### 1. 手動実行の改善 (現在利用中)
**方法:** `Scripts/gpt_request_helper.sh check` の手動実行
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

**作成日時:** 2025-07-15  
**評価:** 安全性重視のアプローチを推奨