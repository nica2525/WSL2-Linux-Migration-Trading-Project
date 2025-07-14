# 🚀 WSL完全移行手順書（初心者向け詳細版）

## 📋 移行概要
- **現在**: WSL(C:) ⟷ プロジェクト(E:) のクロスドライブ構成
- **移行後**: WSL(E:) ⟷ プロジェクト(E:) の同一ドライブ構成
- **効果**: I/O性能向上、システム安定性向上

## ⚠️ 重要な注意事項
- **移行中はWSL完全停止** → VSCode・Claude Code接続不可
- **所要時間**: 30分～1時間程度
- **失敗時の復旧**: 元のWSLは自動保持されるため安全

---

## 🔧 Phase 1: 移行前準備（WSL内で実行）

### 1-1. 現在の状態確認
```bash
# WSL状態確認
wsl --list --verbose

# 現在のディストリビューション名確認
echo $WSL_DISTRO_NAME

# プロジェクトの最新状態確認
git status
git log --oneline -5
```

### 1-2. 重要データの最終保存
```bash
# 未コミット変更があれば保存
git add .
git commit -m "WSL移行前の最終保存"

# cron設定のバックアップ
crontab -l > /mnt/e/Trading-Development/2.ブレイクアウト手法プロジェクト/backup_crontab.txt
```

---

## 🔄 Phase 2: WSL移行実行（Windows側で実行）

### 2-1. Windows PowerShell起動
1. `Win + X` → `Windows PowerShell (管理者)`
2. 管理者権限で実行

### 2-2. 現在のWSL状態確認
```powershell
wsl --list --verbose
```
**表示例**:
```
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
```

### 2-3. WSLのシャットダウン
```powershell
wsl --shutdown
```
**⚠️ この時点でVSCode・Claude Code接続が切れます（正常動作）**

### 2-4. WSLエクスポート実行
```powershell
wsl --export Ubuntu-22.04 E:\WSL\Ubuntu-22.04-backup.tar
```
**⏳ 時間がかかります（5-15分程度）**

### 2-5. 新WSL環境作成
```powershell
# 新しいWSL環境をEドライブに作成
wsl --import Ubuntu-E E:\WSL\Ubuntu-E E:\WSL\Ubuntu-22.04-backup.tar

# 新環境をデフォルトに設定
wsl --set-default Ubuntu-E
```

### 2-6. 新WSL環境の起動確認
```powershell
wsl --list --verbose
```
**表示例**:
```
  NAME            STATE           VERSION
* Ubuntu-E        Running         2
  Ubuntu-22.04    Stopped         2
```

---

## 🔧 Phase 3: 移行後設定復旧（新WSL内で実行）

### 3-1. 新WSL環境にログイン
```powershell
wsl -d Ubuntu-E
```

### 3-2. 基本設定の確認
```bash
# 現在のユーザー確認
whoami

# ホームディレクトリ確認
pwd
echo $HOME
```

### 3-3. プロジェクトの移行
```bash
# プロジェクトディレクトリをホームに移行
cp -r /mnt/e/Trading-Development ~/Trading-Development

# 移行先に移動
cd ~/Trading-Development/2.ブレイクアウト手法プロジェクト
```

### 3-4. cron設定の復旧
```bash
# バックアップから復旧（パス変更版）
cat > temp_crontab.txt << 'EOF'
*/3 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_git_auto_save.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_git_auto_save.log 2>&1
*/5 * * * * /usr/bin/python3 /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Scripts/cron_system_monitor.py >> /home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/.cron_monitor.log 2>&1
EOF

# cron設定適用
crontab temp_crontab.txt
rm temp_crontab.txt

# cron設定確認
crontab -l
```

### 3-5. Claude設定の更新
```bash
# Claude設定ファイルのパス更新
sed -i 's|/mnt/e/Trading-Development|/home/trader/Trading-Development|g' ~/.claude/settings.json

# 設定確認
cat ~/.claude/settings.json | grep Trading-Development
```

---

## 🧪 Phase 4: 移行後テスト

### 4-1. cron動作確認
```bash
# cron起動確認
ps aux | grep cron

# 3分後にログ確認
tail -f .cron_git_auto_save.log
```

### 4-2. Git動作確認
```bash
# Git状態確認
git status
git log --oneline -3

# テストコミット
echo "WSL移行完了テスト" > migration_test.txt
git add migration_test.txt
git commit -m "WSL移行完了テスト"
```

### 4-3. Claude Code再接続テスト
1. VSCodeを再起動
2. WSL Remote拡張で新環境に接続
3. Claude Codeが正常動作するか確認

---

## 🔥 Phase 5: 移行完了後の最終確認

### 5-1. 性能向上の確認
```bash
# ディスクI/O速度テスト
time ls -la

# Git操作速度テスト
time git status
```

### 5-2. システム安定性確認
```bash
# 全体システム動作確認
df -h
free -h
uptime
```

### 5-3. 旧WSL環境の削除（任意）
**⚠️ 完全に動作確認できてから実行**
```powershell
# Windows PowerShellで実行
wsl --unregister Ubuntu-22.04
```

---

## 🚨 トラブルシューティング

### エラー1: WSLエクスポートが失敗
**原因**: ディスク容量不足
**対処**: Eドライブの空き容量確認（最低20GB必要）

### エラー2: 新WSL環境が起動しない
**原因**: インポートファイル破損
**対処**: エクスポートからやり直し

### エラー3: cron設定が動作しない
**原因**: パス設定間違い
**対処**: 手順3-4を再実行

### エラー4: Claude Code接続不可
**原因**: VSCode設定の問題
**対処**: VSCode再起動、WSL Remote拡張再接続

---

## 📞 緊急時の復旧手順

### 完全失敗時の復旧
```powershell
# 新環境削除
wsl --unregister Ubuntu-E

# 元環境をデフォルトに復旧
wsl --set-default Ubuntu-22.04

# 元環境再起動
wsl
```

---

## ✅ 移行完了チェックリスト

- [ ] WSL新環境正常起動
- [ ] プロジェクトファイル移行完了
- [ ] cron自動化システム復旧
- [ ] Claude設定更新完了
- [ ] VSCode再接続成功
- [ ] Git動作確認完了
- [ ] Claude Code正常動作確認
- [ ] 性能向上確認完了

**移行完了後は、この手順書を参照してトラブルシューティングできます。**