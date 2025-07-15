# Claude設定

## ⚡ Hooks自動化システム
- **言語設定**: セッション開始時に日本語モード自動確認
- **プロジェクト開始**: 必須ファイル確認・品質基準チェック自動実行
- **作業記録**: セッション終了時に自動保存
- **設定場所**: ~/.claude/settings.json

## 🚨 最重要 - cron自動化システム確認プロトコル
**セッション開始時に必ず実行:**
```bash
crontab -l
ps aux | grep cron
```

**cron自動化システム確認:**
```bash
tail -10 .cron_git_auto_save.log
tail -10 .cron_monitor.log
```

**⚡ 重要: systemd方式は完全廃止済み**
- `systemd/*.timer` → 使用禁止（cron移行済み）
- `start_auto_git.sh` → 使用禁止（.DISABLED化済み）
- `start_memory_tracker.sh` → 使用禁止（.DISABLED化済み）
- **cronが唯一の正式な自動実行方法**

## cron自動化システム仕様
- 📁 **Git自動保存**: 3分間隔、flock排他制御付き（cron_git_auto_save.py）
- 🧠 **システム監視**: 5分間隔、cron標準管理（cron_system_monitor.py）
- ⏰ **管理方式**: cron（WSL最適化・自己修復機能付き）
- 💰 **料金**: 0円 (100%ローカル処理)
- 🔄 **復旧**: 自己修復機能内蔵、WSL完全対応
- 🛑 **制御方法**: crontab コマンド
- 📋 **ログ確認**: .cron_*.log ファイル

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

## 🛡️ 品質状況確認プロトコル
**セッション開始時必須確認:**
```bash
cat CURRENT_QUALITY_STATUS.md
```

**品質チェック手動実行:**
```bash
python3 Scripts/quality_checker.py
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
cat GPT_REQUEST_PROTOCOL.md
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
- `Scripts/cron_git_auto_save.py` - Git自動保存の中核システム
- `Scripts/cron_system_monitor.py` - システム監視の中核システム
- `Scripts/git_simple_commit.py` - Git自動保存の中核システム（旧版・予備）
- `Scripts/memory_simple_update.py` - 記憶追跡の中核システム（旧版・予備）

**ファイル整理・大規模変更時の必須手順:**
1. 必ず事前に `crontab -l` でcron動作確認
2. 変更後に即座に `crontab -l` で設定確認
3. cron自動化停止は絶対に許可されない
4. systemd方式・旧デーモン方式の復活は厳禁

## 💬 回答方式の使い分け
### 簡潔回答（4行以内）
- **簡単な質問・確認**: 「現在の状態は？」「ファイルある？」
- **Yes/No質問**: 「動作している？」「問題ない？」
- **単純な説明**: 「これは何？」「意味は？」

### 詳細回答（制限なし）
- **技術的説明**: EA開発・戦略分析・システム設計
- **コード実装**: 実装手順・コード解説・トラブル対応
- **複雑な作業**: 多段階プロセス・設定変更・品質分析
- **学習・教育**: 概念説明・ベストプラクティス

**📋 判断基準**: 開発効率を最優先。必要な情報を適切な長さで提供。

## 絶対に忘れてはいけないこと
1. **cron自動化確認が最優先** (Git自動保存・システム監視)
2. セッション開始時のGitログ確認（過去作業把握）
3. **セッション開始時のマネージャー学習ログ確認**
4. **GPT依頼文作成時のプロトコル遵守** (GPT_REQUEST_PROTOCOL.md)
5. 重要な設計変更時の即時記録
6. ⚡ Hooks自動化により作業記録は自動実行
7. **🚨 cron重要ファイル保護の絶対遵守**
8. **systemd・旧デーモン方式は完全廃止 - cronのみ使用**
