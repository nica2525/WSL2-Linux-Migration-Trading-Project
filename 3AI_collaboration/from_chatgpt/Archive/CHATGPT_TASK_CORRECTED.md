# リアリティ追求フェーズ：理論的ガイダンス（緊急修正版）

対象：`minimal_wfa_results.json` の最新 WFA 結果  
参照：`3AI_DEVELOPMENT_CHARTER.md`、`DEVELOPMENT_STANDARDS.md`

---

## 1. FX取引コストモデル

### 1.1 理論的背景
- **スプレッド**: 売買価格差（1 pip = 0.0001 USDJPY、典型値1–2 pips）  
- **約定手数料**: OANDA MT4 環境で往復約0.2–0.4 pips  

### 1.2 実装コード例
```python
def apply_transaction_costs(trades, spread_pips=1.5, commission_pips=0.3):
    """
    trades: DataFrame with columns ['raw_return', 'num_trades']
    spread_pips: スプレッド（pips単位）
    commission_pips: 往復手数料（pips単位）
    """
    # pipsを価格差に変換 (1 pip = 0.0001)
    cost_per_trade = (spread_pips + commission_pips) * 0.0001
    # 総コスト = 貿易数 × cost_per_trade
    trades['net_return'] = trades['raw_return'] - cost_per_trade * trades['num_trades']
    return trades
```

### 1.3 パラメータ詳細

| パラメータ           | 推奨値           | 設定根拠・調整方法                           |
|----------------------|------------------|----------------------------------------------|
| `spread_pips`        | 1.0–2.0 pips     | OANDA 提供のUSDJPYスプレッド平均を参照       |
| `commission_pips`    | 0.2–0.4 pips     | ブローカー約定手数料を往復で合算             |
| `num_trades`         | 実行トレード数   | WFA結果の `oos_trades` を使用                |

### 1.4 限界・注意点
- ニュース時や流動性低下時にスプレッドが広がる  
- 高頻度取引ではコスト影響大  
- コードでは**pips単位**→**価格単位**への変換を明示

### 1.5 評価基準
- **コスト後 PF** ≥ 1.10 で実用水準  
- **コスト影響率** = (PF_raw − PF_net) / PF_raw ≤ 5%

---

## 2. スリッページシミュレーション

### 2.1 理論的背景
- **市場インパクトモデル**: 注文量や流動性に応じた価格乖離  
- **固定モデル**: 定量的シンプル評価  

### 2.2 修正済み実装コード例
```python
def simulate_slippage(trades, model='fixed', fixed_slippage_pips=0.2, impact_coefficient=0.00001):
    """
    trades: DataFrame with columns ['net_return', 'volume'] 
    fixed_slippage_pips: 固定スリッページ（pips）
    impact_coefficient: 成行量×係数による変動スリッページ
    """
    if model == 'fixed':
        slippage = fixed_slippage_pips * 0.0001
    else:
        # volume: ロットや取引量に比例
        slippage = trades['volume'] * impact_coefficient
    # 各取引の総スリッページ
    trades['net_return'] = trades['net_return'] - slippage
    return trades
```

### 2.3 パラメータ詳細

| モデル               | 推奨値／式                                                |
|----------------------|-----------------------------------------------------------|
| 固定スリッページ     | `fixed_slippage_pips = 0.1–0.5`                           |
| 流動性依存モデル     | `impact_coefficient = 1e-5–5e-5`<br>`volume`はロット数等 |

### 2.4 修正点・注意事項
- **以前の誤り**: `spread_observed / oos_trades` では逆転現象発生  
- 新モデルは**取引量(volume)×係数**で比例関係を維持  
- pips→価格変換を明示  

### 2.5 評価基準
- **PF変動幅** ≤ ±3%以内に収まるモデルを選定  

---

## 3. 最大ドローダウン分析

### 3.1 理論的背景
- ドローダウンは累積リターンの**ピークからの最大後退幅**を示す  
- **金額ベース／%ベース**の2軸分析が必要

### 3.2 実装コード例
```python
import pandas as pd

def compute_drawdown(equity_series):
    """
    equity_series: 累積リターンの時系列 (Series of floats)
    """
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    max_dd = drawdown.min()
    return drawdown, max_dd

# 各フォールドの最大ドローダウン例
results = {}
for fold in wfa_results:
    series = pd.Series(fold['oos_return']).cumsum()
    _, max_dd = compute_drawdown(series)
    results[fold['fold_id']] = max_dd
```

### 3.3 指標詳細

| 指標               | 計算式                                    |
|--------------------|-------------------------------------------|
| %ドローダウン      | `(equity - peak) / peak * 100`            |
| 回復期間           | ピークから回復までの日数またはトレード数  |

### 3.4 限界・注意点
- ドローダウンと勝率のトレードオフを評価  
- 高頻度戦略では短期的揺れが大きい  

### 3.5 評価基準
- **最大ドローダウン** ≤ 10%  
- **平均回復期間** ≤ 30トレード  

---

## 4. WFA結果との照合

| Fold | oos_pf | oos_trades | avg_return | 予測PF後コスト反映 |
|------|--------|------------|------------|--------------------|
| 1    | 1.6026 | 44         | 4.78%      | 約1.52             |
| 2    | 1.5745 | 45         | 1.60%      | 約1.50             |
| 3    | 1.2820 | 45         | 1.37%      | 約1.23             |
| 4    | 1.5205 | 88         | 5.11%      | 約1.47             |
| 5    | 1.6793 | 45         | 5.70%      | 約1.62             |

---

*以上、緊急修正版として Markdown ファイルを作成しました。*