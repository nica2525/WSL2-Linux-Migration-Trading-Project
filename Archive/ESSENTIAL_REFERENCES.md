# 必須参照ファイル一覧（コンパクト版）

**作成日時: 2025-07-12 22:30 JST**

## 🗺️ 参照マップ（記憶システム統合版）

### ⚡ 効率的記憶更新方式
**従来**: 4-6ファイル個別読み込み → **新方式**: このマップ1回確認
**利点**: 記憶負荷軽減・必要情報のみ選択・更新管理一元化

### 🚨 絶対に必要な参照ファイル

#### レベル1: 記憶システム（必須）
- `ESSENTIAL_REFERENCES.md` ← **このファイル（参照マップ）**
- `PROJECT_STATUS_COMPACT.md` ← **現状把握（コンパクト版）**
- `CLAUDE_MEMORY_SYSTEM.md` ← **記憶システム詳細**

#### レベル2: 作業時確認（選択的）
- `docs/CHATGPT_TASK_REQUEST.md` ← **ChatGPT依頼形式**
- `docs/MANAGER_LEARNING_LOG.md` ← **学習履歴・失敗教訓**
- `3AI_DEVELOPMENT_CHARTER.md` ← **3AI協働ルール**

#### レベル3: システム確認（必要時）
- `CLAUDE.md` ← **基本設定**
- `DEVELOPMENT_STANDARDS.md` ← **開発標準**

### 作業時必須参照
- `docs/CHATGPT_TASK_REQUEST.md` - ChatGPT依頼形式（統一済み）
- `docs/MANAGER_LEARNING_LOG.md` - 過去学習・失敗教訓
- `PROJECT_STATUS_COMPACT.md` - 現状把握（このファイルと同階層）

### Git・システム確認
```bash
Scripts/start_auto_git.sh status          # 自動保存確認
git log --oneline -5                      # 最新履歴
ls -la docs/MEMORY_EXECUTION_HISTORY.md   # 記憶実行履歴
```

## 📋 重要ルール（忘れがち）

### ChatGPT依頼
- **場所**: `docs/CHATGPT_TASK_REQUEST.md`
- **形式**: 既存ファイル完全準拠（過去成功例参照必須）
- **新規作成前**: 必ず既存形式確認

### 命名規則
- **統一済み**: CHATGPT_TASK_REQUEST.md 形式
- **日時記載**: 全mdファイルに日本時間必須
- **保存場所**: `3AI_collaboration/from_chatgpt/` (成果物)

### 3AI役割分担
- **Claude Code**: 統合管理・実装・品質管理
- **Gemini**: 客観監査・技術検証・バイアス検出
- **ChatGPT**: 戦略立案・実装支援・最適化

## 🔄 定期実行（記憶システム）
- **30分毎**: 記憶システム確認
- **30アクション毎**: 自動アラート（Hooks機能）
- **重要作業前**: 基本ルール再確認

---
**このファイルで主要参照先を一元管理し、記憶負荷を軽減**