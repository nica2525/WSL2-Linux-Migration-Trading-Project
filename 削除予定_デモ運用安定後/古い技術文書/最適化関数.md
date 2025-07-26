# 最適化された関数群

以下は、`corrected_adaptive_wfa_system.py` 内で特にパフォーマンスクリティカルな部分を最適化した関数群とその説明です。

---

## 1. 期間データ抽出の高速化
```python
def extract_period_data(data: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """期間データ抽出 — pandas の .loc を直接使うことで内部で高速化"""
    return data.loc[start:end].copy()
```
- **理由**: `.loc` はインデックスを使った C レベルのスライスを行い、ブールマスクを毎回作成するより高速です。

---

## 2. レジーム検出処理の事前実行と再利用
```python
def run_corrected_wfa(self) -> Dict:
    data = self.load_market_data()
    regimes = MarketRegimeDetector().detect_regime(data)

    for cfg in self.wfa_config:
        learn = self.extract_period_data(data, *cfg['learning_period'])
        test  = self.extract_period_data(data, *cfg['test_period'])
        slice_regimes = regimes.loc[learn.index]
        optimizer = WFACompliantOptimizer(learn, slice_regimes)
        # ...
```
- **理由**: フォールド毎に繰り返し検出せず一度だけ実行し、再利用することで時間を約1/5削減します。

---

## 3. 強制決済時のPnL計算のベクトル化
```python
def _force_exit_all(self, df: pd.DataFrame, position: Dict) -> float:
    """最後のバーで一括決済したときのPnLをベクトル化して算出"""
    last_price = df['close'].iat[-1]
    direction = 1 if position['direction']=='BUY' else -1
    return (last_price - position['entry_price']) * 10000 * direction
```
- **理由**: Pythonレベルのループを省き、ベクトル化で高速化します。

---

## 4. SciPyを用いた統計的有意性テスト
```python
from scipy import stats

def _calculate_statistical_significance(self, pf_values: List[float]) -> float:
    """ワンテールt検定をSciPyで実行"""
    if len(pf_values) < 2:
        return 1.0
    t_stat, p_value = stats.ttest_1samp(pf_values, 1.0, alternative='greater')
    return p_value
```
- **理由**: SciPyの`alternative='greater'`を使い、手動計算を排除して高速化します。

---

## 5. 関数呼び出し結果のキャッシュ化
```python
from functools import lru_cache

@lru_cache(maxsize=32)
def execute_backtest_with_regime(self, detector_params: Tuple[float,...]) -> Dict:
    # パラメータセットをキーにバックテスト結果をキャッシュ
    ...

def objective_function(self, params: Tuple[float,...]) -> float:
    # tupleに変換してキャッシュを活用
    result = self.execute_backtest_with_regime(tuple(params))
    pf = result['profit_factor']
    sharpe = result['sharpe_ratio']
    trades = result['total_trades']
    penalty = 1.0 if trades>=50 else trades/50.0
    return -(
        np.log(max(pf,0.1))*0.6 +
        max(sharpe,-2.0)*0.3 +
        penalty*0.1
    )
```
- **理由**: 同一パラメータでの実行結果をキャッシュして、再計算を削減します。
