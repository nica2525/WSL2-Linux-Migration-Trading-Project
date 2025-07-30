# WSL2 MCP最適化実行ガイド（Gemini査読版）

**実行日時**: 2025-07-30  
**目的**: Claude Code MCP・Sub-Agent機能完全活用  
**査読**: Gemini専門査読済み  

## 🚨 次に実行する手順（Windows側）

### 1. WSL2完全再起動（必須）
```cmd
# Windows PowerShellまたはコマンドプロンプトで実行
wsl --shutdown
wsl
```

### 2. Windows Firewall受信規則追加（セキュリティ強化）
Windows Defender Firewallで以下の受信規則を追加：

**手順**:
1. `Windows + R` → `wf.msc` → Enter
2. 「受信の規則」右クリック → 「新しい規則」
3. 規則の種類: 「ポート」
4. プロトコル: TCP
5. ポート: `3000-4000` (MCP通信範囲)
6. 操作: 「接続を許可する」
7. プロファイル: すべて選択
8. 名前: `WSL2-Claude-MCP-Servers`

### 3. 設定確認コマンド
WSL再起動後、以下で確認：
```bash
# ネットワーク設定確認
wsl.exe hostname -I

# mirrored mode動作確認
curl http://127.0.0.1:80 2>/dev/null && echo "✅ 127.0.0.1通信成功" || echo "❌ 通信失敗"
```

## 📋 Phase 1成功指標
- [ ] WSL2 mirrored mode有効化確認
- [ ] 127.0.0.1双方向通信成功
- [ ] Windows Firewall受信規則追加完了
- [ ] セキュリティ設定維持確認

## ⚠️ 注意事項
- `firewall=false`は使用禁止（Gemini査読指摘）
- Windows Firewall受信規則で安全に通信許可
- WSL再起動は必須（設定反映のため）

---
**次フェーズ**: Phase 2 - MCP設定最適化＋Docker積極採用