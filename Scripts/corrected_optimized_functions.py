#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional
from cost_resistant_strategy import CostResistantStrategy
from market_regime_detector import MarketRegimeDetector


class SecureWFA:
    def __init__(self, learning_data: pd.DataFrame):
        self.learning_data = learning_data

    def execute_backtest_with_regime(self, detector_params: List[float]) -> Dict:
        detector = MarketRegimeDetector()
        detector.volatility_threshold_low = detector_params[0]
        detector.volatility_threshold_high = detector_params[1]
        detector.trend_strength_threshold = detector_params[2]
        detector.range_efficiency_threshold = detector_params[3]
        detector.atr_period = int(detector_params[4])
        detector.range_period = int(detector_params[5])
        detector.trend_period = int(detector_params[6])

        regimes = detector.detect_regime(self.learning_data)

        trades = []
        balance = 100000
        position = None

        for i in range(len(self.learning_data)):
            if i >= len(regimes):
                break

            bar = self.learning_data.iloc[i]
            current_regime = regimes.iloc[i]
            params = detector.get_strategy_parameters(current_regime)

            if not params['active']:
                if position is not None:
                    balance += self._close_position(position, bar['close'], trades, reason="REGIME_STOP")
                    position = None
                continue

            strategy = CostResistantStrategy(self._build_adaptive_params(params))
            signal = strategy.generate_signal(self.learning_data.iloc[:i+1])

            if position is None and signal != "HOLD":
                position = {
                    'direction': signal,
                    'entry_price': bar['close'],
                    'stop_loss': strategy.calculate_stop_loss(bar['close'], signal),
                    'take_profit': strategy.calculate_take_profit(bar['close'], signal),
                    'position_size': params['position_size']
                }

            elif position is not None:
                exit_signal, reason = strategy.check_exit_conditions(position, bar, self.learning_data.iloc[:i+1])
                if exit_signal:
                    balance += self._close_position(position, bar['close'], trades, reason)
                    position = None

        return self._evaluate_performance(trades)

    def _build_adaptive_params(self, regime_params: Dict) -> Dict:
        return {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': regime_params['profit_atr'],
            'stop_atr': regime_params['stop_atr'],
            'min_break_pips': regime_params['min_break_pips'],
            'spread_pips': 1.5,
            'commission_pips': 0.3
        }

    def _close_position(self, position: Dict, exit_price: float, trades: List[Dict], reason: str) -> float:
        pnl = ((exit_price - position['entry_price']) if position['direction'] == 'BUY'
               else (position['entry_price'] - exit_price)) * 10000 * position['position_size']
        trades.append({'pnl': pnl, 'exit_reason': reason})
        return pnl

    def _evaluate_performance(self, trades: List[Dict]) -> Dict:
        if not trades:
            return {'profit_factor': 1.0, 'sharpe_ratio': 0.0, 'total_trades': 0}

        pnl = [t['pnl'] for t in trades]
        profits = [p for p in pnl if p > 0]
        losses = [-p for p in pnl if p <= 0]
        pf = sum(profits) / sum(losses) if losses else 2.0
        sharpe = np.mean(pnl) / np.std(pnl) if np.std(pnl) > 0 else 0.0

        return {
            'profit_factor': pf,
            'sharpe_ratio': sharpe,
            'total_trades': len(trades),
            'win_rate': len(profits) / len(trades)
        }
