#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from scipy import stats
from functools import lru_cache
import numpy as np
from typing import Dict, List, Tuple

class CorrectedAdaptiveWFA:

    def extract_period_data(self, data: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        """期間データ抽出 — pandas の .loc を直接使うことで内部で高速化"""
        return data.loc[start:end].copy()

    def run_corrected_wfa(self) -> Dict:
        data = self.load_market_data()
        regimes = MarketRegimeDetector().detect_regime(data)
        for cfg in self.wfa_config:
            learn = self.extract_period_data(data, *cfg['learning_period'])
            test  = self.extract_period_data(data, *cfg['test_period'])
            slice_regimes = regimes.loc[learn.index]
            optimizer = WFACompliantOptimizer(learn, slice_regimes)
            # ...

    def _force_exit_all(self, df: pd.DataFrame, position: Dict) -> float:
        """最後のバーで一括決済したときのPnLをベクトル化して算出"""
        last_price = df['close'].iat[-1]
        direction = 1 if position['direction']=='BUY' else -1
        return (last_price - position['entry_price']) * 10000 * direction

    def _calculate_statistical_significance(self, pf_values: List[float]) -> float:
        """ワンテールt検定をSciPyで実行"""
        if len(pf_values) < 2:
            return 1.0
        _, p_value = stats.ttest_1samp(pf_values, 1.0, alternative='greater')
        return p_value

    @lru_cache(maxsize=32)
    def execute_backtest_with_regime(self, detector_params: Tuple[float,...]) -> Dict:
        """パラメータセットをキーにバックテスト結果をキャッシュ"""
        result = {}  # 実装例
        return result

    def objective_function(self, params: Tuple[float,...]) -> float:
        """キャッシュ化を活用するため tuple キーを利用"""
        result = self.execute_backtest_with_regime(tuple(params))
        pf = result.get('profit_factor', 0.0)
        sharpe = result.get('sharpe_ratio', 0.0)
        trades = result.get('total_trades', 0)
        penalty = 1.0 if trades >= 50 else trades / 50.0
        return -(
            np.log(max(pf, 0.1))*0.6 +
            max(sharpe, -2.0)*0.3 +
            penalty*0.1
        )
