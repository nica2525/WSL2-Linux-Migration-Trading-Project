# MT4-Python統合ガイド

## 概要
MT4とPython戦略システムの統合実装ガイド。CSV通信から始まりZeroMQへの段階的移行を行う。

## 実装アーキテクチャ

### Stage 1: CSV通信プロトタイプ（現在完了）
- **目的**: 安全・確実な統合テスト
- **メリット**: 実装簡単、プラットフォーム独立、外部依存なし
- **用途**: 基本動作確認、ロジック検証

### Stage 2: ZeroMQ高性能実装（次段階）
- **目的**: 低遅延・高信頼性統合
- **メリット**: マイクロ秒レベル遅延、非同期処理、スケーラブル
- **用途**: プロダクション運用

## ファイル構成

```
MT4_Integration/
├── csv_communication_prototype.py     # Python側CSV通信
├── MT4_CSV_Communicator.mq4          # MT4側CSV通信EA
├── test_csv_integration.py           # 統合テストスクリプト
├── README_Integration_Guide.md       # このファイル
└── MT4_Data/                         # 通信データディレクトリ
    ├── price_data.csv                # 価格データ
    ├── trading_signals.csv           # 取引シグナル
    └── connection_status.csv         # 接続ステータス
```

## CSV通信仕様

### 価格データ（MT4 → Python）
```csv
timestamp,symbol,bid,ask,volume
1641563400,EURUSD,1.13456,1.13458,1250
```

### 取引シグナル（Python → MT4）
```csv
timestamp,symbol,action,price,confidence,volume,stop_loss,take_profit
2025-07-20T09:30:00,EURUSD,BUY,1.13456,0.85,0.1,1.13256,1.13656
```

### 接続ステータス（双方向）
```csv
timestamp,status,heartbeat
2025-07-20T09:30:00,MT4_STARTED,1641563400
```

## 使用方法

### 1. Python側起動
```bash
cd MT4_Integration
python3 csv_communication_prototype.py
```

### 2. MT4側設定
1. MT4_CSV_Communicator.mq4をMT4に読み込み
2. エキスパートアドバイザー有効化
3. 自動売買許可

### 3. 統合テスト実行
```bash
python3 test_csv_integration.py --duration 5 --simulate-price
```

## ブレイクアウト判定ロジック

### Python側実装
```python
def _check_breakout_signal(self, current_tick: Dict):
    # 過去20期間の高値・安値取得
    high_20 = max(prices[-20:])
    low_20 = min(prices[-20:])
    current_price = current_tick['bid']
    
    # 上方ブレイクアウト
    if current_price > high_20 * 1.0005:  # 0.05% above
        signal = "BUY"
        confidence = calculate_confidence(...)
    
    # 下方ブレイクアウト
    elif current_price < low_20 * 0.9995:  # 0.05% below
        signal = "SELL"
        confidence = calculate_confidence(...)
```

### MT4側実装
```mql4
void ProcessPythonSignal(string signalData) {
    // CSV解析
    string parts[];
    StringSplit(signalData, ',', parts);
    
    // 注文実行
    if(confidence > 0.3 && spread < MaxSpreadPips) {
        ExecuteOrder(action, volume, stopLoss, takeProfit);
    }
}
```

## パフォーマンス特性

### CSV通信
- **遅延**: 100ms - 1秒
- **スループット**: 10-100 signals/秒
- **安定性**: 高（ファイルI/O）
- **リソース**: 低

### ZeroMQ通信（計画）
- **遅延**: 1-10ms
- **スループット**: 1000+ signals/秒
- **安定性**: 高（TCP/IPC）
- **リソース**: 中

## エラーハンドリング

### 接続監視
- ハートビート機能（10秒間隔）
- タイムアウト検出（30秒）
- 自動復旧機能

### データ検証
- 必須フィールド確認
- 価格データ妥当性チェック
- シグナル信頼度フィルタリング

### 注文実行安全性
- スプレッドチェック
- ロットサイズ検証
- 市場時間確認

## 次段階: ZeroMQ実装

### 必要な準備
1. libzmq.dll配置
2. Visual C++ 2015ランタイム
3. MQL4 ZeroMQライブラリ

### 実装計画
```
Phase 1: CSV動作確認 ✅
Phase 2: ZeroMQ基本実装
Phase 3: 高度な機能統合
Phase 4: プロダクション最適化
```

## トラブルシューティング

### よくある問題
1. **ファイルアクセス権限**: MT4のファイルパス確認
2. **データ形式エラー**: CSV形式の検証
3. **タイミング問題**: ファイル更新間隔調整

### デバッグ方法
```bash
# ログ確認
tail -f MT4_Data/*.csv

# テスト実行
python3 test_csv_integration.py --duration 1
```

## Gemini査読準備事項

### 技術的検証点
- [ ] Look-ahead bias完全排除
- [ ] リアルタイム約定ロジック
- [ ] エラーハンドリング妥当性
- [ ] パフォーマンス最適化余地

### アーキテクチャ検証点
- [ ] 段階的実装戦略の妥当性
- [ ] スケーラビリティ対応
- [ ] セキュリティ考慮事項
- [ ] 運用保守性

### コード品質検証点
- [ ] 命名規則統一
- [ ] 例外処理網羅性
- [ ] ログ出力適切性
- [ ] テストケース充実度