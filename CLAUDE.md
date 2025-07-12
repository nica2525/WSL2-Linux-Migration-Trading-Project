# Claude設定

## ⚡ Hooks自動化システム
- **言語設定**: セッション開始時に日本語モード自動確認
- **プロジェクト開始**: 必須ファイル確認・品質基準チェック自動実行
- **作業記録**: セッション終了時に自動保存
- **設定場所**: ~/.claude/settings.json

## 🚨 最重要 - 自動Git保存確認プロトコル
**セッション開始時に必ず実行:**
```bash
Scripts/start_auto_git.sh status
```

**もし停止していたら即座に:**
```bash
Scripts/start_auto_git.sh start
```

**PCが再起動された場合も自動復旧済み（WSL設定完了）**

## 自動保存システム仕様
- 📁 **監視対象**: *.mq4, *.py, *.md, *.json等
- ⏰ **実行間隔**: 3分毎の自動チェック  
- 💰 **料金**: 0円 (100%ローカル処理)
- 🔄 **復旧**: PC再起動後も自動開始
- 🛑 **停止方法**: Scripts/start_auto_git.sh stop

## 🔍 Gitログ参照プロトコル
**セッション開始時必須確認:**
```bash
git log --oneline -10
```

**詳細履歴確認:**
```bash
git log --graph --pretty=format:'%h - %an, %ar : %s' -10
```

**特定キーワード検索:**
```bash
git log --grep="MCP\|Gemini\|Phase" --oneline -20
```

## 🤖 MCP-Gemini vs 自己実装ツール使い分け戦略
**セッション開始時必須参照:**
```
MCP_VS_SELF_IMPLEMENTATION_STRATEGY.md
```

**基本方針:**
- **複雑分析・新戦略開発**: MCP-Gemini使用
- **定型処理・自動化**: 自己実装Gemini使用  
- **コスト最適化**: タスク性質により適切選択

## 📚 マネージャー学習システム
**セッション開始時必須確認:**
```bash
cat docs/MANAGER_LEARNING_LOG.md
cat 3AI_DEVELOPMENT_CHARTER.md
cat DEVELOPMENT_STANDARDS.md
cat MANDATORY_VERIFICATION_PROTOCOL.md
```

**🎯 品質管理チェックリスト:**
- [ ] 前回学習事項の確認と適用
- [ ] 3AI協働ルール・役割分担の確認
- [ ] 実装品質への過信排除
- [ ] 異常結果への懐疑的検証
- [ ] 意思決定プロセスの遵守
- [ ] Gemini監査の必須実行

## 🚨 絶対に削除・変更禁止ファイル - 重要システム保護
**以下ファイルを削除・移動した場合、即座にプロジェクトから退場:**
- `Scripts/auto_git_commit.py` - 自動Git保存の中核システム
- `Scripts/start_auto_git.sh` - 自動Git保存制御スクリプト
- `Scripts/auto_git_commit.py.backup` - バックアップ版（復旧用）

**ファイル整理・大規模変更時の必須手順:**
1. 必ず事前に `Scripts/start_auto_git.sh status` で動作確認
2. 変更後に即座に再確認・復旧テスト実行
3. 自動保存システム停止は絶対に許可されない

## 絶対に忘れてはいけないこと
1. セッション開始時の自動Git保存確認
2. セッション開始時のGitログ確認（過去作業把握）
3. **セッション開始時のマネージャー学習ログ確認**
4. 重要な設計変更時の即時記録
5. ⚡ Hooks自動化により作業記録は自動実行
6. **🚨 重要システムファイル保護の絶対遵守**