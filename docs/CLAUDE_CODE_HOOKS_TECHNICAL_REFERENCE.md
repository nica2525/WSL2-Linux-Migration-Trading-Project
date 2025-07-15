# 🔧 Claude Code Hooks 技術資料

## 📋 概要
Claude Code Hooksは、Claude Codeのライフサイクルの特定のタイミングで自動実行されるシェルスクリプトシステム。

## 🎯 Hook種類と発動タイミング

### 1. PreToolUse - ツール実行前
```json
"PreToolUse": [
  {
    "matcher": ".*",
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/pre_tool_script.sh"]
      }
    ]
  }
]
```
**特徴:**
- ツール実行**前**に発動
- **アクションブロック可能**（exit code非0で中断）
- GPT依頼前の自動ルール読み込みに最適
- ファイル編集前の事前チェックに使用

### 2. PostToolUse - ツール実行後
```json
"PostToolUse": [
  {
    "matcher": ".*",
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/post_tool_script.sh"]
      }
    ]
  }
]
```
**特徴:**
- ツール実行**後**に発動
- 後処理・ログ記録・状態更新に使用
- **現在使用中**（memory_tracker_hook.sh）

### 3. Start - セッション開始時
```json
"Start": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/session_start_script.sh"]
      }
    ]
  }
]
```
**特徴:**
- Claude Codeセッション開始時に発動
- 環境初期化・設定確認に使用
- **現在使用中**（session_start_memory.sh）

### 4. Notification - 通知時
```json
"Notification": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/notification_script.sh"]
      }
    ]
  }
]
```
**特徴:**
- 通知・入力要求時に発動
- ユーザーインタラクション監視に使用
- **今後活用予定**

### 5. Stop - 応答完了時
```json
"Stop": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/stop_script.sh"]
      }
    ]
  }
]
```
**特徴:**
- Claude Code応答完了時に発動
- セッション終了処理・最終状態保存に使用
- **今後活用予定**

## 🔧 設定レベル

### 1. グローバル設定
**場所:** `~/.claude/settings.json`
**適用範囲:** 全プロジェクト

### 2. プロジェクト設定
**場所:** `[プロジェクト]/.claude/settings.json`
**適用範囲:** 特定プロジェクト

### 3. ローカル設定
**場所:** `[プロジェクト]/.claude/settings.local.json`
**適用範囲:** ローカルのみ（Git管理対象外）

## 🎯 matcher設定

### 基本パターン
```json
"matcher": ".*"              // 全ツール
"matcher": "Edit|Write"      // Edit・Writeツールのみ
"matcher": "Bash"            // Bashツールのみ
"matcher": "mcp__.*"         // MCPツールのみ
```

## 💡 実用例

### GPT依頼前の自動ルール読み込み
```json
"PreToolUse": [
  {
    "matcher": "mcp__gemini-cli__.*",
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/gpt_rules_loader.sh"]
      }
    ]
  }
]
```

### ファイル編集前の品質チェック
```json
"PreToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/quality_check.sh"]
      }
    ]
  }
]
```

### Git操作前の状態確認
```json
"PreToolUse": [
  {
    "matcher": "Bash.*git.*",
    "hooks": [
      {
        "type": "command",
        "command": "/bin/bash",
        "args": ["/path/to/git_pre_check.sh"]
      }
    ]
  }
]
```

## 🚨 重要な仕様

### 実行制約
- **制約なし**: 30アクション毎などの制約はない
- **即座発動**: 指定イベントで即座に実行
- **並列実行**: 複数hookが設定されている場合は順次実行

### エラーハンドリング
- **PreToolUse**: exit code非0でツール実行中断
- **PostToolUse**: exit code関係なく続行
- **Start/Stop**: exit code関係なく続行

### 環境変数
- スクリプト実行時にClaude Codeの環境変数が継承される
- プロジェクトディレクトリ情報などが利用可能

## 🎯 今後の活用計画

### 1. PreToolUse実装
- **GPT依頼前の自動ルール読み込み**
- **ファイル編集前の品質チェック**
- **危険操作のブロック**

### 2. Notification活用
- **ユーザーインタラクション監視**
- **重要な通知の記録**

### 3. Stop活用
- **セッション終了時の自動保存**
- **最終状態の記録**

## 📝 設定例テンプレート

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__gemini-cli__.*",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash",
            "args": ["/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/gpt_rules_loader.sh"]
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash",
            "args": ["/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/memory_tracker_hook.sh"]
          }
        ]
      }
    ],
    "Start": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/bin/bash",
            "args": ["/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/session_start_memory.sh"]
          }
        ]
      }
    ]
  }
}
```

---

**作成日時:** 2025-07-15  
**更新日時:** 2025-07-15  
**参考資料:** https://syu-m-5151.hatenablog.com/entry/2025/07/14/105812