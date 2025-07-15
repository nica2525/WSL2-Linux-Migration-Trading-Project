# リアリティ追求フェーズ：理論的ガイダンス

対象：`minimal_wfa_results.json` の最新 WFA 検証結果  
参照：`3AI_DEVELOPMENT_CHARTER.md`、`DEVELOPMENT_STANDARDS.md`

---

## 1. 理論的背景

本手法はマルチタイムフレーム・ブレイクアウト戦略の実用性を検証し、  
リアル世界の取引コストやスリッページ、ドローダウン許容を組み込むための理論的枠組みです。  
金融工学では以下の点を重視します：

- **取引コスト** はリターンから差し引く「摩擦費用」  
- **スリッページ** は市場流動性に応じた価格乖離  
- **ドローダウン** は最大後退幅をリスク指標とする  

---

## 2. FX取引コストモデル

### 2.1 理論的背景  
- **スプレッド**: ブローカーが設定する売買価格差（1–2 pips が典型）  
- **約定手数料**: OANDA MT4 の場合、往復0.2–0.4 pips程度が目安  

### 2.2 実装コード例

```python
def apply_transaction_costs(trades, spread=0.0002, commission=0.00004):
    """
    trades: DataFrame with columns ['raw_return', 'num_trades']
    spread: 取引毎にかかるスプレッド（1pip=0.0001）
    commission: 取引毎の往復手数料
    """
    trades['net_return'] = trades['raw_return'] - (spread + commission) * trades['num_trades']
    return trades
```

### 2.3 パラメータ詳細

| パラメータ    | 推奨値            | 設定根拠・調整方法                         |
|---------------|-------------------|--------------------------------------------|
| `spread`      | 0.0001–0.0002     | OANDAのUSDJPY標準スプレッドを参照         |
| `commission`  | 0.00002–0.00004   | ブローカーの約定手数料を往復で合計         |
| `num_trades`  | 実行トレード数    | WFA結果の `oos_trades` を利用             |

### 2.4 限界・注意点

- スプレッドは時間帯・ニュース時に大きく変動  
- 手数料はロット数に依存する場合あり  
- 高頻度トレードではコストがリターンを圧迫しやすい  

### 2.5 評価基準

- **コスト後 PF** ≥ 1.10 で実用性あり  
- **コスト影響率** = (PF_raw − PF_net) / PF_raw ≤ 5％  

---

## 3. スリッページシミュレーション

### 3.1 理論的背景  
- **固定モデル**: 一律に価格乖離を想定  
- **流動性依存モデル**: 約定深度や気配幅と連動  

### 3.2 実装コード例

```python
import numpy as np

def simulate_slippage(trades, model='fixed', fixed_slippage=0.0001, liquidity_factor=0.5):
    """
    model: 'fixed' or 'liquidity'
    fixed_slippage: 一律スリッページ
    liquidity_factor: oos_trades数に応じた調整率
    """
    if model == 'fixed':
        trades['slippage'] = fixed_slippage
    else:
        trades['slippage'] = liquidity_factor * (trades['spread_observed'] / trades['oos_trades'])
    trades['net_return'] = trades['net_return'] - trades['slippage']
    return trades
```

### 3.3 パラメータ詳細

| モデル             | 推奨値／式                                         |
|--------------------|----------------------------------------------------|
| 固定スリッページ   | `fixed_slippage = 0.0001–0.0005`                   |
| 流動性依存モデル   | `liquidity_factor = 0.3–0.7`<br>`spread_observed` は実データ |

### 3.4 限界・注意点

- 気配幅データが必要（取得困難な場合は固定モデル推奨）  
- モデルの係数は市場環境で調整必須  

### 3.5 評価基準

- **PF変動幅** ≤ ±3％ 以内に収まるモデルを選択  

---

## 4. 最大ドローダウン分析

### 4.1 理論的背景  
- ドローダウンは「累積リターンのピークからの最大後退幅」  
- 金額ベース・%ベースの両面評価が必要  

### 4.2 実装コード例

```python
import pandas as pd

def compute_drawdown(equity_curve):
    """
    equity_curve: 累積リターンの時系列配列
    """
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    max_dd = drawdown.min()
    return drawdown, max_dd

# 各フォールドの最大ドローダウン集計例
results = {}
for fold in wfa_results:
    curve = pd.Series(fold['oos_return']).cumsum()
    _, max_dd = compute_drawdown(curve)
    results[fold['fold_id']] = max_dd
```

### 4.3 パラメータ詳細

| 指標              | 計算方法                                   |
|-------------------|--------------------------------------------|
| %ドローダウン     | `(equity - peak) / peak * 100`             |
| 期間ドローダウン  | ピークから立ち直るまでの日数・トレード数   |

### 4.4 限界・注意点

- トレード頻度が高いと短期間で大きく振れる  
- ドローダウン許容は投資家心理に依存  

### 4.5 評価基準

- **最大ドローダウン** ≤ 10％  
- **平均回復期間** ≤ 30トレード  

---

## 5. WFA 結果との照合サマリー

| Fold | oos_pf | oos_trades | avg_oos_return | 推奨モデル後 PF 期待値 |
|------|--------|------------|----------------|------------------------|
| 1    | 1.6026 | 44         | 0.0478         | 約1.52（コスト＆スリッページ反映後） |
| 2    | 1.5745 | 45         | 0.0160         | 約1.50                  |
| 3    | 1.2820 | 45         | 0.0137         | 約1.23                  |
| 4    | 1.5205 | 88         | 0.0511         | 約1.47                  |
| 5    | 1.6793 | 45         | 0.0570         | 約1.62                  |

---

以上の内容を Markdown 形式のファイルとして作成しました。