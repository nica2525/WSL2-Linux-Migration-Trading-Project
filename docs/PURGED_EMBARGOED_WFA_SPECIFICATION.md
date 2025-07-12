# Purged & Embargoed Walk-Forward Analysis 実装仕様書

## 📋 概要
`ファイナンス機械学習`で提唱された、情報リークを防ぐPurged & Embargoed Cross-Validationを、ウォークフォワード分析に統合した実装仕様書。47EA失敗の根本原因である過学習を防ぐための技術的基盤。

---

## 🎯 設計目標

### 主要目的
1. **情報リーク完全阻止**: 未来データの訓練への混入防止
2. **時系列自己相関対応**: 金融データ特有の相関構造考慮
3. **現実的性能評価**: 実機環境により近い検証環境構築
4. **統計的有意性確保**: 偶然ではない真の優位性検出

### 従来WFAとの差異
| 項目 | 従来WFA | Purged & Embargoed WFA |
|------|---------|------------------------|
| **データ分割** | 単純な時系列分割 | Purge + Embargo期間設定 |
| **情報リーク** | 境界付近で発生 | 完全阻止 |
| **自己相関** | 未考慮 | 明示的に除去 |
| **統計的厳密性** | 基本的 | 高度な統計的補正 |

---

## 🔬 理論的基盤

### Purging（パージング）の必要性
```
問題: テスト期間の直前IS期間にリーク情報が混入

例: 20日移動平均を使用する戦略の場合
OOS期間: 2024/07/01-2024/07/31
IS期間: 2024/01/01-2024/06/30

しかし、7/1の20日MAは6/11-6/30の価格を含む
→ IS期間最終20日間はOOS情報を間接的に含有
→ 情報リーク発生
```

### Embargoing（エンバーゴ）の必要性
```
問題: 時系列データの自己相関による統計的非独立性

例: 月次WFAの場合
OOS1: 2024/07 → 結果がIS期間に影響
IS2: 2024/08-2025/01 → OOS1の結果が間接的に影響
→ 統計的独立性の破綻
```

---

## 🛠️ 技術仕様

### 1. データ構造設計

#### TimeSeriesData クラス
```python
class TimeSeriesData:
    def __init__(self, data, datetime_col='datetime'):
        self.data = data.sort_values(datetime_col)
        self.datetime_col = datetime_col
        
    def get_bars_for_period(self, start_date, end_date):
        """指定期間のバーデータを取得"""
        mask = (self.data[self.datetime_col] >= start_date) & \
               (self.data[self.datetime_col] <= end_date)
        return self.data[mask]
    
    def calculate_lookback_period(self, strategy_config):
        """戦略の最大ルックバック期間を計算"""
        max_periods = []
        
        # 移動平均期間
        if 'ma_periods' in strategy_config:
            max_periods.extend(strategy_config['ma_periods'])
        
        # ATR期間
        if 'atr_period' in strategy_config:
            max_periods.append(strategy_config['atr_period'])
        
        # その他のインジケーター期間
        if 'other_periods' in strategy_config:
            max_periods.extend(strategy_config['other_periods'])
        
        return max(max_periods) if max_periods else 20  # デフォルト20期間
```

#### WFAConfig クラス
```python
class WFAConfig:
    def __init__(self, 
                 is_months=24,           # IS期間（月）
                 oos_months=6,           # OOS期間（月）
                 step_months=6,          # ステップ間隔（月）
                 anchored=True,          # アンカード方式
                 purge_bars=None,        # Purge期間（自動計算推奨）
                 embargo_bars=None):     # Embargo期間（自動計算推奨）
        
        self.is_months = is_months
        self.oos_months = oos_months  
        self.step_months = step_months
        self.anchored = anchored
        self.purge_bars = purge_bars
        self.embargo_bars = embargo_bars
        
    def calculate_purge_embargo(self, strategy_config, timeframe='M5'):
        """戦略設定に基づくPurge/Embargo期間の自動計算"""
        lookback_period = self._get_max_lookback(strategy_config)
        
        # 時間足別の倍率設定
        timeframe_multipliers = {
            'M5': 1.0,
            'M15': 0.33,
            'M30': 0.16,
            'H1': 0.08,
            'H4': 0.02,
            'D1': 0.004
        }
        
        multiplier = timeframe_multipliers.get(timeframe, 1.0)
        
        # Purge期間: 最大ルックバック期間の1.5倍
        self.purge_bars = int(lookback_period * 1.5 * multiplier)
        
        # Embargo期間: Purge期間と同等
        self.embargo_bars = self.purge_bars
        
        return self.purge_bars, self.embargo_bars
```

### 2. コア実装クラス

#### PurgedEmbargoedWFA クラス
```python
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class PurgedEmbargoedWFA:
    def __init__(self, data, config, strategy_config):
        self.data = TimeSeriesData(data)
        self.config = config
        self.strategy_config = strategy_config
        
        # Purge/Embargo期間の自動計算
        if config.purge_bars is None or config.embargo_bars is None:
            config.calculate_purge_embargo(strategy_config)
            
        self.results = []
        
    def generate_folds(self):
        """WFAフォールドの生成（Purge & Embargo考慮）"""
        folds = []
        
        # データ期間の取得
        start_date = self.data.data[self.data.datetime_col].min()
        end_date = self.data.data[self.data.datetime_col].max()
        
        # 初回IS開始日
        current_is_start = start_date
        
        while True:
            # IS期間終了日
            is_end = current_is_start + relativedelta(months=self.config.is_months)
            
            # Purge期間（IS最終部分を除去）
            purge_start = is_end - timedelta(days=self._bars_to_days(self.config.purge_bars))
            actual_is_end = purge_start
            
            # OOS期間開始日（IS終了直後）
            oos_start = is_end
            # OOS期間終了日
            oos_end = oos_start + relativedelta(months=self.config.oos_months)
            
            # データ終了チェック
            if oos_end > end_date:
                break
                
            # Embargo期間（次回IS開始前の空白）
            embargo_days = self._bars_to_days(self.config.embargo_bars)
            next_is_start = oos_end + timedelta(days=embargo_days)
            
            fold = {
                'fold_id': len(folds) + 1,
                'is_start': current_is_start,
                'is_end': actual_is_end,
                'purge_start': purge_start,
                'purge_end': is_end,
                'oos_start': oos_start,
                'oos_end': oos_end,
                'embargo_start': oos_end,
                'embargo_end': next_is_start
            }
            
            folds.append(fold)
            
            # 次のフォールドの準備
            if self.config.anchored:
                # アンカード: IS開始は固定、IS期間延長
                current_is_start = start_date
                self.config.is_months += self.config.step_months
            else:
                # 非アンカード: IS期間固定、ウィンドウスライド
                current_is_start = next_is_start
                
        return folds
    
    def _bars_to_days(self, bars):
        """バー数を日数に変換（概算）"""
        # M5の場合: 1日 ≈ 288バー (24h * 60min / 5min)
        # 実際の取引時間を考慮した調整が必要
        bars_per_day = {
            'M5': 288,
            'M15': 96, 
            'M30': 48,
            'H1': 24,
            'H4': 6,
            'D1': 1
        }
        
        timeframe = self.strategy_config.get('timeframe', 'M5')
        daily_bars = bars_per_day.get(timeframe, 288)
        
        return max(1, bars // daily_bars)
```

### 3. 統計的検証統合

#### StatisticalValidator クラス
```python
class StatisticalValidator:
    def __init__(self, wfa_results):
        self.results = wfa_results
        
    def calculate_oos_consistency(self):
        """OOS期間の一貫性評価"""
        oos_returns = [fold['oos_return'] for fold in self.results]
        
        # 基本統計
        positive_periods = sum(1 for r in oos_returns if r > 0)
        total_periods = len(oos_returns)
        consistency_ratio = positive_periods / total_periods
        
        # t検定（OOSリターンが0より大きいかの検定）
        from scipy import stats
        t_stat, p_value = stats.ttest_1samp(oos_returns, 0)
        
        return {
            'consistency_ratio': consistency_ratio,
            'positive_periods': positive_periods,
            'total_periods': total_periods,
            't_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < 0.05
        }
    
    def calculate_wfa_efficiency(self):
        """ウォークフォワード効率の計算"""
        total_oos_return = sum(fold['oos_return'] for fold in self.results)
        total_is_return = sum(fold['is_return'] for fold in self.results)
        
        if total_is_return <= 0:
            return 0
            
        wfa_efficiency = total_oos_return / total_is_return
        return wfa_efficiency
    
    def calculate_deflated_sharpe_ratio(self):
        """DSR計算（複数フォールド考慮）"""
        oos_sharpe_ratios = [fold['oos_sharpe'] for fold in self.results]
        max_sharpe = max(oos_sharpe_ratios)
        
        # 試行回数 = フォールド数
        N = len(self.results)
        
        # DSR計算（簡易版）
        from math import sqrt, log
        import math
        
        euler_gamma = 0.5772156649
        z_inv_N = self._norm_ppf(1 - 1/N)
        z_inv_Ne = self._norm_ppf(1 - 1/(N * math.e))
        
        expected_max_sr = (1 - euler_gamma) * z_inv_N + euler_gamma * z_inv_Ne
        
        return {
            'observed_max_sr': max_sharpe,
            'expected_max_sr': expected_max_sr,
            'deflated_sr': max_sharpe - expected_max_sr,
            'is_significant': max_sharpe > expected_max_sr
        }
```

---

## 📊 実装例

### 使用例
```python
# データ準備
import pandas as pd

# EURUSD M5データの読み込み（例）
data = pd.read_csv('EURUSD_M5_2020_2024.csv')
data['datetime'] = pd.to_datetime(data['datetime'])

# 戦略設定
strategy_config = {
    'ma_periods': [20, 50],      # 移動平均期間
    'atr_period': 14,            # ATR期間
    'timeframe': 'M5',           # 時間足
    'other_periods': []          # その他のインジケーター期間
}

# WFA設定
wfa_config = WFAConfig(
    is_months=24,                # IS期間24ヶ月
    oos_months=6,                # OOS期間6ヶ月
    step_months=6,               # 6ヶ月ステップ
    anchored=True                # アンカード方式
)

# WFA実行
wfa = PurgedEmbargoedWFA(data, wfa_config, strategy_config)
folds = wfa.generate_folds()

# 各フォールドでの戦略実行（疑似コード）
results = []
for fold in folds:
    # IS期間でのパラメータ最適化
    is_data = wfa.data.get_bars_for_period(fold['is_start'], fold['is_end'])
    optimized_params = optimize_strategy(is_data, strategy_config)
    
    # OOS期間での検証
    oos_data = wfa.data.get_bars_for_period(fold['oos_start'], fold['oos_end'])
    oos_result = backtest_strategy(oos_data, optimized_params)
    
    results.append({
        'fold_id': fold['fold_id'],
        'is_return': calculate_is_return(is_data, optimized_params),
        'oos_return': oos_result['total_return'],
        'oos_sharpe': oos_result['sharpe_ratio'],
        'oos_pf': oos_result['profit_factor'],
        'trades': oos_result['total_trades']
    })

# 統計的検証
validator = StatisticalValidator(results)
consistency = validator.calculate_oos_consistency()
wfa_efficiency = validator.calculate_wfa_efficiency()
dsr_result = validator.calculate_deflated_sharpe_ratio()

print(f"OOS一貫性: {consistency['consistency_ratio']:.2%}")
print(f"WFA効率: {wfa_efficiency:.3f}")
print(f"統計的有意性: {consistency['is_significant']}")
```

---

## ⚙️ 設定パラメータ詳細

### 推奨設定値

#### 時間足別設定
| 時間足 | IS期間 | OOS期間 | ステップ | Purge/Embargo |
|--------|--------|---------|----------|---------------|
| **M5** | 24ヶ月 | 6ヶ月 | 6ヶ月 | 30-50バー |
| **M15** | 18ヶ月 | 6ヶ月 | 6ヶ月 | 10-20バー |
| **H1** | 12ヶ月 | 3ヶ月 | 3ヶ月 | 5-10バー |
| **H4** | 12ヶ月 | 3ヶ月 | 3ヶ月 | 2-5バー |

#### 戦略複雑度別設定
| 戦略タイプ | IS期間 | 最小取引数 | Purge倍率 |
|------------|--------|------------|-----------|
| **シンプル** | 18ヶ月 | 300 | 1.5x |
| **中程度** | 24ヶ月 | 500 | 2.0x |
| **複雑** | 36ヶ月 | 1000 | 2.5x |

---

## 🔍 品質保証

### 実装検証チェックリスト
- [ ] **データ分離確認**: IS/OOS期間の完全分離
- [ ] **Purge実装確認**: IS末尾の適切な除去
- [ ] **Embargo実装確認**: OOS後の空白期間設定
- [ ] **情報リーク検査**: 未来データの混入なし
- [ ] **統計計算確認**: t検定、DSRの正確な実装

### パフォーマンステスト
- [ ] **データサイズ**: 5年間M5データでの動作確認
- [ ] **処理速度**: 1フォールド5分以内の処理
- [ ] **メモリ使用量**: 8GB以内での動作
- [ ] **エラーハンドリング**: 異常データへの適切な対応

---

## 📈 出力仕様

### WFAレポート構成
```json
{
  "summary": {
    "total_folds": 8,
    "oos_consistency_ratio": 0.875,
    "wfa_efficiency": 0.67,
    "statistical_significance": true,
    "deflated_sharpe_ratio": 0.15
  },
  "fold_results": [
    {
      "fold_id": 1,
      "period": "2020-01 to 2022-06",
      "is_performance": {
        "profit_factor": 1.45,
        "sharpe_ratio": 0.82,
        "max_drawdown": 0.12
      },
      "oos_performance": {
        "profit_factor": 1.32,
        "sharpe_ratio": 0.75,
        "max_drawdown": 0.15,
        "total_trades": 145
      }
    }
  ],
  "statistical_tests": {
    "oos_t_test": {
      "t_statistic": 2.34,
      "p_value": 0.024,
      "is_significant": true
    },
    "parameter_stability": {
      "mean_parameter_change": 0.08,
      "max_parameter_change": 0.15,
      "stability_score": 0.92
    }
  }
}
```

---

## 🚀 実装ロードマップ

### Phase 1: 基盤実装（1週間）
- [ ] データ構造クラス実装
- [ ] WFA設定クラス実装
- [ ] 基本的なフォールド生成機能

### Phase 2: 核心機能実装（1週間）
- [ ] Purged & Embargoed分割ロジック
- [ ] 戦略実行インターフェース
- [ ] 基本的な結果集計機能

### Phase 3: 統計機能実装（1週間）
- [ ] 統計的検証クラス実装
- [ ] DSR計算機能
- [ ] レポート生成機能

### Phase 4: 最適化・検証（1週間）
- [ ] パフォーマンス最適化
- [ ] 品質保証テスト
- [ ] ドキュメント整備

---

**🎯 この仕様書に基づくWFA実装により、情報リークを完全に防ぎ、47EA失敗の根本原因を解決する堅牢な検証システムが構築されます。**