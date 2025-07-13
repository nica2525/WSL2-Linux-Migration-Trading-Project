# Claude設定

## ⚡ Hooks自動化システム
- **言語設定**: セッション開始時に日本語モード自動確認
- **プロジェクト開始**: 必須ファイル確認・品質基準チェック自動実行
- **作業記録**: セッション終了時に自動保存
- **設定場所**: ~/.claude/settings.json

## 🚨 最重要 - systemd自動化システム確認プロトコル
**セッション開始時に必ず実行:**
```bash
systemctl --user list-timers
systemctl --user status git-auto-save.timer memory-tracker.timer
```

**停止していたら即座に:**
```bash
systemctl --user start git-auto-save.timer memory-tracker.timer
```

**⚡ 重要: 旧デーモン方式は完全廃止済み**
- `start_auto_git.sh` → 使用禁止（.DISABLED化済み）
- `start_memory_tracker.sh` → 使用禁止（.DISABLED化済み）
- **systemdタイマーが唯一の正式な自動実行方法**

## systemd自動化システム仕様
- 📁 **Git自動保存**: 3分間隔、flock排他制御付き
- 🧠 **記憶追跡**: 30分間隔、systemd標準管理
- ⏰ **管理方式**: systemdタイマー（OS級の安定性）
- 💰 **料金**: 0円 (100%ローカル処理)
- 🔄 **復旧**: systemd自動復旧、WSL systemd対応
- 🛑 **制御方法**: systemctl --user コマンド
- 📋 **ログ確認**: journalctl -u サービス名

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
- `Scripts/git_simple_commit.py` - Git自動保存の中核システム
- `Scripts/memory_simple_update.py` - 記憶追跡の中核システム
- `systemd/git-auto-save.timer` - Git自動保存タイマー設定
- `systemd/memory-tracker.timer` - 記憶追跡タイマー設定
- `systemd/*.service` - systemdサービス定義

**ファイル整理・大規模変更時の必須手順:**
1. 必ず事前に `systemctl --user list-timers` で動作確認
2. 変更後に即座に `systemctl --user daemon-reload` 実行
3. systemdタイマー停止は絶対に許可されない
4. 旧デーモン方式（.DISABLED）の復活は厳禁

## 絶対に忘れてはいけないこと
1. **systemdタイマー確認が最優先** (Git自動保存・記憶追跡)
2. セッション開始時のGitログ確認（過去作業把握）
3. **セッション開始時のマネージャー学習ログ確認**
4. 重要な設計変更時の即時記録
5. ⚡ Hooks自動化により作業記録は自動実行
6. **🚨 systemd重要ファイル保護の絶対遵守**
7. **旧デーモン方式は完全廃止 - systemdタイマーのみ使用**
