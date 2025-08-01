# JamesORB pips分析補足
**作成日**: 2025年7月25日

## 🚨 重要な修正点

### pips計算の修正
EURUSDの場合、小数点以下5桁目が1pipとなります：
- **誤**: 1.17407 → 1.17498 = 91pips
- **正**: 1.17407 → 1.17498 = 9.1pips

### 実際のリスク管理パラメータ
- **ストップロス**: 9.1pips
- **テイクプロフィット**: 5.6pips
- **リスクリワード比**: 0.62

## 📊 この設定の特徴と課題

### 1. **非常にタイトな設定**
- SL 9.1pips、TP 5.6pipsは**スキャルピング戦略**
- スプレッド5-6pipsを考慮すると、実質的な利益幅は非常に狭い
- 高頻度取引により小さな利益を積み重ねる戦略

### 2. **スプレッドの影響（修正版）**
```
実質的な状況：
- エントリー時のスプレッドコスト: 0.5-0.6pips（実測値）
- TP 5.6pipsなら、実質利益は約5.0pips
- 十分に利益が取れる条件
```

### 3. **バックテストとの乖離要因（修正）**
- バックテスト: スプレッド0pips
- 実取引: スプレッド0.5-0.6pips
- **影響は限定的（優良な取引環境）**

## 🎯 新EA開発への重要な示唆

### 1. **より現実的なTP/SL設定**
```
推奨設定例：
- TP: 20-30pips
- SL: 15-20pips
- RR比: 1.3-1.5
```

### 2. **スプレッドを考慮した戦略**
- 最低でもTP > スプレッド×2 が必要
- 朝方のスプレッド拡大時間帯の回避
- ECN口座での低スプレッド環境推奨

### 3. **時間軸の見直し**
- 現在のM5（5分足）から、より大きな時間軸への移行検討
- H1（1時間足）やH4（4時間足）でのスイングトレード
- より大きなpips幅での取引

## 💡 結論

現在のJamesORBは**超短期スキャルピングEA**として動作しており、以下の課題があります：

1. **スプレッドに対してTPが小さすぎる**
2. **リスクリワード比が不利（0.62）**
3. **高頻度取引による手数料負担**

新EA開発では、より健全なリスクリワード比と、スプレッドの影響を最小化できる設計が必要です。

---
**作成者**: Claude Code（実装担当）
