# EAファイル開発・管理プロトコル（厳格ルール）

## 🚫 絶対禁止事項
1. **新規EAファイル作成禁止**
   - `JamesORB_v1.0.mq5` 以外のファイル作成は厳禁
   - `*_with_magic.mq5`, `*_optimized.mq5` 等の派生ファイル作成禁止

2. **重複ファイル作成禁止**
   - 既存ファイルの複製・リネーム禁止
   - バックアップは Git の責任

## ✅ 必須実行ルール

### ルール1: 単一ファイル編集原則
```bash
# 正規ファイル
/MT5/EA/JamesORB_v1.0.mq5

# 編集方法
Edit tool で直接編集のみ
```

### ルール2: バージョン管理必須
```bash
# バージョン履歴ファイル
/MT5/EA/VERSION_HISTORY.md

# 更新必須項目
- バージョン番号
- 変更内容
- 実装日時
- 次期予定
```

### ルール3: MT5同期必須
```bash
# 編集後必須実行
cp /MT5/EA/JamesORB_v1.0.mq5 "/wine/MT5/MQL5/Experts/"
```

### ルール4: Git commit必須
```bash
# EA変更時は即座にcommit
git add MT5/EA/
git commit -m "EA v2.0X: 変更内容説明"
```

## 🤖 自動化Hook設定

### PreToolUse Hook
EAファイル編集前にルール確認スクリプト実行:
```bash
Scripts/ea_version_control_rules.sh
```

### PostToolUse Hook  
EAファイル編集後にMT5同期・Git確認:
```bash
Scripts/ea_post_edit_sync.sh
```

## 📋 開発ワークフロー

### 1. EA機能追加・修正
```bash
# 1. 重複ファイル削除確認
./Scripts/ea_version_control_rules.sh

# 2. 正規ファイル編集
Edit MT5/EA/JamesORB_v1.0.mq5

# 3. バージョン履歴更新
Edit MT5/EA/VERSION_HISTORY.md

# 4. MT5同期
cp MT5/EA/JamesORB_v1.0.mq5 "/wine/MT5/MQL5/Experts/"

# 5. Git commit
git add MT5/EA/ && git commit -m "EA vX.XX: 変更内容"
```

### 2. パラメータ最適化
```bash
# パラメータ変更のみ
Edit MT5/EA/JamesORB_v1.0.mq5 (input値のみ変更)
Edit MT5/EA/VERSION_HISTORY.md (記録)
同期・commit
```

### 3. 機能追加
```bash
# 新機能追加
Edit MT5/EA/JamesORB_v1.0.mq5 (関数・ロジック追加)
Edit MT5/EA/VERSION_HISTORY.md (詳細記録)
同期・commit
```

## ⚠️ 違反時の対処

### ファイル重複検出時
```bash
# 即座に重複削除
find . -name "*JamesORB*" -name "*.mq5" | grep -v "JamesORB_v1.0.mq5" | xargs rm
```

### ルール違反検出時
```bash
# 強制ルール実行
./Scripts/ea_version_control_rules.sh
```

## 🎯 品質保証

### チェックリスト
- [ ] 単一ファイル確認
- [ ] バージョン履歴更新
- [ ] MT5同期完了
- [ ] Git commit完了
- [ ] 重複ファイル削除確認

### 定期チェック
```bash
# 週次実行
./Scripts/ea_version_control_rules.sh
```

## 📄 ファイル一覧（許可）
```
MT5/EA/
├── JamesORB_v1.0.mq5          # 唯一の正規EA
├── VERSION_HISTORY.md         # バージョン管理
└── Backups/                   # Git管理外バックアップ
    ├── JamesORB_Dev_backup.mq5
    └── JamesORB_v1.0_backup.mq5
```

## 🚨 緊急時プロトコル
EA破損・消失時のみ、Backups/ からの復旧許可
復旧後、即座に正規ファイル名に変更・Git commit必須