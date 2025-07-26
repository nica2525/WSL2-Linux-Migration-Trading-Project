# MT5リアルタイム取引監視システム技術仕様書

## 概要

JamesORBデモ取引（300万円、EURUSD、0.01ロット固定）のリアルタイム監視システム。

## 1. システム要件

### 1.1 基本仕様
- **対象EA**: JamesORB
- **監視通貨**: EURUSD
- **初期残高**: 300万円
- **固定ロット**: 0.01
- **更新間隔**: 5秒（調整可能）

### 1.2 技術要件
- **Python**: 3.7以上
- **主要ライブラリ**:
  - MetaTrader5 (最新版)
  - pandas, numpy
  - psutil (システム監視)
  - threading (並行処理)

## 2. MT5 Python API仕様

### 2.1 リアルタイムデータ取得方法

#### 2.1.1 アカウント情報取得
```python
account_info = mt5.account_info()
# 取得データ: balance, equity, margin, profit等
```

#### 2.1.2 ポジション監視
```python
positions = mt5.positions_get(symbol="EURUSD")
# 取得データ: ticket, volume, price_open, profit等
```

#### 2.1.3 取引履歴取得
```python
history = mt5.history_deals_get(from_date, to_date, group="EURUSD")
# 取得データ: 完了取引の詳細情報
```

#### 2.1.4 ティックデータ取得
```python
ticks = mt5.copy_ticks_from(symbol, from_date, count, mt5.COPY_TICKS_ALL)
# 高頻度価格データ（必要時のみ使用）
```

### 2.2 データ取得頻度と効率化

#### 2.2.1 推奨更新間隔
- **基本監視**: 5秒間隔
- **詳細分析**: 1分間隔
- **履歴更新**: 1時間間隔

#### 2.2.2 効率化手法
- **データフィルタリング**: シンボル指定による限定取得
- **履歴保持**: deque(maxlen=1000)による自動メモリ管理
- **バッチ処理**: 複数データの一括取得

## 3. リアルタイム統計計算

### 3.1 基本統計
- **現在残高**: account_info.balance
- **評価額**: account_info.equity
- **未実現損益**: sum(position.profit)
- **利益率**: (current_equity - initial_balance) / initial_balance * 100

### 3.2 リスク指標
- **最大ドローダウン**: (peak_equity - current_equity) / peak_equity * 100
- **現在ドローダウン**: リアルタイム計算
- **ポジション数**: len(positions)

### 3.3 統計更新方式
```python
def calculate_statistics(account_info, positions):
    # ピーク残高更新
    if current_equity > peak_balance:
        peak_balance = current_equity
    
    # ドローダウン計算
    current_dd = (peak_balance - current_equity) / peak_balance * 100
    
    return statistics
```

## 4. アラート・通知システム

### 4.1 アラート条件
| 種類 | 条件 | アクション |
|------|------|-----------|
| 危険DD | >20% | ⚠️ 危険アラート |
| 注意DD | >10% | ⚠️ 注意アラート |
| 利益達成 | >5% | 🎉 利益通知 |
| ポジション過多 | >5個 | ⚠️ ポジション警告 |

### 4.2 通知方法
- **ログ出力**: WARNING/ERROR レベル
- **ファイル保存**: JSON形式でアラート履歴保存
- **コンソール表示**: リアルタイム表示

## 5. パフォーマンス監視とメモリ最適化

### 5.1 システム監視指標
```python
import psutil

# CPU使用率
cpu_percent = process.cpu_percent()

# メモリ使用量
memory_mb = process.memory_info().rss / 1024 / 1024
```

### 5.2 メモリ最適化手法

#### 5.2.1 データ構造最適化
- **deque使用**: 固定長キューによる自動メモリ管理
```python
self.position_history = deque(maxlen=1000)  # 最新1000件のみ保持
self.balance_history = deque(maxlen=1000)
```

#### 5.2.2 CPU負荷軽減
- **適切な更新間隔**: 5秒間隔でバランス調整
- **スレッド分離**: メイン処理と監視処理の分離
- **例外処理**: エラー時の継続実行

### 5.3 パフォーマンス基準
- **CPU使用率**: <5% (平均)
- **メモリ使用量**: <100MB
- **応答時間**: <1秒 (データ取得)

## 6. エラーハンドリング・接続断対応

### 6.1 接続エラー対応

#### 6.1.1 一般的なエラー
```python
# IPC timeout エラー (-10005)
if not mt5.initialize(timeout=60000):
    error = mt5.last_error()
    logger.error(f"初期化失敗: {error}")
```

#### 6.1.2 再接続メカニズム
```python
def connect_with_retry(max_retries=3):
    for attempt in range(max_retries):
        if mt5.initialize():
            return True
        time.sleep(5)
    return False
```

### 6.2 pymt5adapter使用による強化
```python
import pymt5adapter as mt5

# 自動エラーハンドリング
mt5_connected = mt5.connected(
    timeout=5000,
    raise_on_errors=True,
    ensure_trade_enabled=True
)

with mt5_connected as conn:
    # 安全な取引処理
    pass
```

### 6.3 エラー分類と対応

| エラー種類 | エラーコード | 対応方法 |
|-----------|-------------|----------|
| IPC timeout | -10005 | 再初期化、timeout調整 |
| Login failed | -10003 | 認証情報確認、サーバー確認 |
| Connection lost | - | 自動再接続、ログ記録 |

## 7. JamesORBデモ監視仕様

### 7.1 監視対象詳細
- **EA名**: JamesORB
- **アカウント**: デモ口座
- **資金**: 300万円（3,000,000 JPY）
- **通貨ペア**: EURUSD
- **ロットサイズ**: 0.01固定
- **開始日時**: 2025-07-24 23:47

### 7.2 専用監視項目
- **エントリー検出**: ブレイクアウト条件の確認
- **エグジット追跡**: 利確・損切りの実行確認
- **時間軸分析**: 取引時間帯の分析
- **スプレッド影響**: 実行価格とシグナル価格の比較

### 7.3 レポート出力
```python
def generate_james_orb_report():
    return {
        'ea_performance': {
            'total_trades': len(completed_trades),
            'win_rate': wins / total_trades * 100,
            'profit_factor': gross_profit / gross_loss,
            'avg_trade_duration': avg_duration
        },
        'risk_analysis': {
            'max_drawdown': max_dd,
            'sharpe_ratio': calculate_sharpe(),
            'var_95': value_at_risk_95()
        }
    }
```

## 8. 実装コードの詳細

### 8.1 主要クラス: MT5RealtimeMonitor
- **初期化**: パラメータ設定、ログ設定
- **接続管理**: connect_mt5(), disconnect_mt5()
- **データ取得**: get_account_info(), get_positions(), get_trade_history()
- **統計計算**: calculate_statistics()
- **監視ループ**: monitoring_loop() (別スレッド実行)

### 8.2 実行フロー
1. **初期化**: システム設定、MT5接続
2. **監視開始**: 別スレッドで監視ループ開始
3. **データ収集**: 5秒間隔でデータ取得・統計計算
4. **アラート**: 条件に応じたアラート発行
5. **データ保存**: JSON形式でリアルタイムデータ保存
6. **レポート**: 監視終了時に最終レポート生成

### 8.3 ファイル出力
- **リアルタイムデータ**: `MT5_Results/realtime_monitor_YYYYMMDD_HHMMSS.json`
- **最終レポート**: `MT5_Results/final_monitoring_report.json`
- **ログファイル**: `mt5_realtime_monitor.log`

## 9. 運用ガイドライン

### 9.1 システム起動手順
1. MT5ターミナル起動・ログイン
2. JamesORB EAの稼働確認
3. 監視システム実行: `python Scripts/mt5_realtime_monitoring_system.py`

### 9.2 監視項目チェックリスト
- [ ] MT5接続状態
- [ ] EA稼働状態
- [ ] ポジション状況
- [ ] ドローダウン水準
- [ ] システムリソース使用状況

### 9.3 異常時対応
- **接続断**: 自動再接続機能
- **EA停止**: 手動確認・再開
- **システム過負荷**: 更新間隔調整
- **メモリ不足**: システム再起動

## 10. 今後の拡張計画

### 10.1 機能拡張
- **Web UI**: ブラウザベースの監視画面
- **データベース**: 履歴データの永続化
- **機械学習**: パターン認識・予測機能
- **通知強化**: Email/Slack通知

### 10.2 パフォーマンス改善
- **非同期処理**: asyncio導入
- **キャッシュ機能**: 重複データ取得の削減
- **分散処理**: 複数EA同時監視

この技術仕様書に基づいて、JamesORBデモ取引の包括的なリアルタイム監視システムが実装されています。