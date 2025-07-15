# 🚨 PreToolUse実装リスク分析

## 📋 過去の実装失敗パターン分析

### 1. システム全体の動作不良
**問題:** PreToolUseスクリプトがすべてのツール実行前に動作するため、バグがあると全操作が不可能になる

**具体例:**
- スクリプトが無限ループ
- 必要なファイルが見つからずエラー
- 権限問題で実行できない

### 2. 性能劣化問題
**問題:** 毎回のツール実行前にスクリプトが実行されるため、応答速度が大幅に低下

**具体例:**
- GPT依頼でない操作でも毎回ルール読み込み
- ファイル読み込みで数秒の遅延が発生
- 連続操作時のストレス

### 3. 想定外の発動
**問題:** matcher設定が広すぎて予期しないタイミングで発動

**具体例:**
- 単純なファイル読み込みでもGPTルール読み込み
- 自動保存処理でも発動
- 内部処理まで影響を受ける

### 4. エラー時の復旧困難
**問題:** PreToolUseでエラーが発生すると、設定変更すらできなくなる

**具体例:**
- スクリプトが常にexit 1を返す
- 設定ファイル編集もブロックされる
- 復旧にはシステム外部からの操作が必要

## 🔧 具体的な問題発生シナリオ

### シナリオ1: GPTルール読み込みスクリプトの暴走
```bash
# gpt_rules_loader.sh が以下のような問題を持つ場合
while true; do
    # 無限ループ
    sleep 1
done
```
**結果:** Claude Code全体が応答しなくなる

### シナリオ2: 依存ファイルの不存在
```bash
# 必要なファイルが見つからない場合
cat /nonexistent/file.md
exit 1
```
**結果:** 全ツール実行がブロックされる

### シナリオ3: 権限問題
```bash
# 権限のないファイルにアクセス
sudo command
```
**結果:** 毎回権限エラーでツール実行不可

### シナリオ4: 過度な処理負荷
```bash
# 重い処理を毎回実行
find / -name "*.py" | xargs grep "pattern"
```
**結果:** 操作ごとに数十秒待機が発生

## 💡 リスク軽減策

### 1. 段階的実装
```bash
# Phase 1: 最小限の実装
echo "PreToolUse executed" >> /tmp/debug.log

# Phase 2: GPT関連のみ対象
if [[ "$TOOL_NAME" == *"gemini"* ]]; then
    # GPTルール読み込み
fi

# Phase 3: 完全実装
```

### 2. 安全な matcher 設定
```json
// 危険: 全ツール対象
"matcher": ".*"

// 安全: GPT関連のみ
"matcher": "mcp__gemini-cli__.*"

// より安全: 特定の操作のみ
"matcher": "mcp__gemini-cli__chat"
```

### 3. タイムアウト設定
```bash
# スクリプト内でタイムアウト設定
timeout 10s cat rules.md || exit 0
```

### 4. エラーハンドリング
```bash
# エラーが発生しても継続
set +e
load_rules() {
    # ルール読み込み処理
    return 0  # 常に成功扱い
}
```

### 5. 緊急停止機能
```bash
# 緊急停止ファイルの存在確認
if [[ -f "/tmp/disable_hooks" ]]; then
    exit 0
fi
```

## 🎯 推奨実装戦略

### Phase 1: 最小限テスト
```json
"PreToolUse": [
  {
    "matcher": "mcp__gemini-cli__chat",
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["-c", "echo 'PreToolUse test' >> /tmp/hook_test.log"]
      }
    ]
  }
]
```

### Phase 2: 条件付き実装
```bash
#!/bin/bash
# 条件チェック
if [[ ! -f "$GPT_RULES_FILE" ]]; then
    exit 0  # ファイルがなければ何もしない
fi

# 緊急停止チェック
if [[ -f "/tmp/disable_gpt_hooks" ]]; then
    exit 0
fi

# 実際の処理（タイムアウト付き）
timeout 5s cat "$GPT_RULES_FILE" || exit 0
```

### Phase 3: 完全実装
```bash
#!/bin/bash
# 完全なエラーハンドリング付き実装
```

## 🚨 復旧計画

### 1. 緊急停止方法
```bash
# Hook無効化
touch /tmp/disable_hooks

# 設定ファイル直接編集
vim ~/.claude/settings.json
```

### 2. 設定バックアップ
```bash
# 実装前にバックアップ
cp ~/.claude/settings.json ~/.claude/settings.json.backup
```

### 3. 段階的ロールバック
```bash
# Phase 1に戻す
# Phase 2に戻す
# 完全無効化
```

## 📊 実装前チェックリスト

- [ ] バックアップ作成済み
- [ ] 最小限の実装から開始
- [ ] エラーハンドリング実装
- [ ] タイムアウト設定
- [ ] 緊急停止機能
- [ ] テスト環境での動作確認
- [ ] 復旧手順の準備

## 💡 結論

PreToolUse実装は**高リスク**だが、適切な段階的実装により安全に導入可能。
最重要は**最小限から開始**し、各段階で十分なテストを行うこと。

---

**作成日時:** 2025-07-15  
**リスク評価:** 高リスク - 慎重な実装が必要