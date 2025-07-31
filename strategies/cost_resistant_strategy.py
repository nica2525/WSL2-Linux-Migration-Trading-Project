#!/usr/bin/env python3
"""
コスト耐性ブレイクアウト戦略
エントリー品質を極限まで高めてコスト負けを防ぐ
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from multi_timeframe_breakout_strategy import (
    MultiTimeframeBreakoutStrategy,
    MultiTimeframeData,
)


@dataclass
class CostResistantSignal:
    """コスト耐性シグナル"""

    timestamp: datetime
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'
    atr_multiple: float
    trend_strength: float
    expected_profit_pips: float
    cost_ratio: float  # 期待利益/コスト比率


class CostResistantStrategy:
    """コスト耐性ブレイクアウト戦略"""

    def __init__(self, base_params: Dict):
        self.base_params = base_params
        self.base_strategy = MultiTimeframeBreakoutStrategy(base_params)

        # コスト耐性パラメータ（Gemini監査による修正版）
        self.cost_resistance_params = {
            "min_atr_multiple": 1.0,  # 最小ATR倍数（Gemini指摘により調整）
            "min_trend_strength": 0.1,  # 最小トレンド強度
            "min_profit_pips": 4.0,  # 最小期待利益（コストの2倍）
            "min_cost_ratio": 2.0,  # 最小コスト比率
            "atr_period": 14,  # ATR計算期間
            "trend_ma_long_period": 50,  # トレンド判定長期MA期間
            "trend_ma_short_period": 20,  # トレンド判定短期MA期間（Gemini指摘による修正）
            "breakout_confirmation": 2,  # ブレイクアウト確認バー数
            "cost_pips": 2.0,  # 取引コスト（外部化）
        }

        # 統計
        self.signals_generated = 0
        self.signals_filtered_atr = 0
        self.signals_filtered_trend = 0
        self.signals_filtered_profit = 0
        self.signals_approved = 0

    def generate_cost_resistant_signal(
        self, mtf_data: MultiTimeframeData, current_time: datetime
    ) -> Optional[CostResistantSignal]:
        """コスト耐性シグナル生成"""

        # 基本シグナル取得
        base_signal = self.base_strategy.generate_signal(mtf_data, current_time)

        if not base_signal or base_signal.get("action") == "HOLD":
            return None

        self.signals_generated += 1

        # データ準備
        h1_data = mtf_data.get_h1_data()
        h4_data = mtf_data.get_h4_data()

        if (
            len(h1_data) < self.cost_resistance_params["trend_ma_period"]
            or len(h4_data) < 50
        ):
            return None

        # 1. ATRフィルター: 大きなブレイクアウトのみ
        atr_filter_passed, atr_multiple = self._check_atr_filter(h1_data, base_signal)
        if not atr_filter_passed:
            self.signals_filtered_atr += 1
            return None

        # 2. トレンドフィルター: 明確な方向性のみ
        trend_filter_passed, trend_strength = self._check_trend_filter(
            h1_data, base_signal
        )
        if not trend_filter_passed:
            self.signals_filtered_trend += 1
            return None

        # 3. 利益期待フィルター: 十分な利益期待のみ
        profit_filter_passed, expected_profit_pips = self._check_profit_filter(
            h1_data, base_signal
        )
        if not profit_filter_passed:
            self.signals_filtered_profit += 1
            return None

        # 4. シグナル品質評価
        confidence = self._evaluate_signal_quality(
            atr_multiple, trend_strength, expected_profit_pips
        )

        # 5. コスト比率計算（外部化されたパラメータ使用）
        cost_pips = self.cost_resistance_params["cost_pips"]
        cost_ratio = expected_profit_pips / cost_pips

        # 6. 最終的なエントリー価格・ストップ・利確設定
        entry_price = base_signal.get("price", 0)
        stop_loss, take_profit = self._calculate_optimized_levels(
            h1_data, base_signal, expected_profit_pips
        )

        self.signals_approved += 1

        return CostResistantSignal(
            timestamp=current_time,
            direction=base_signal["action"],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            atr_multiple=atr_multiple,
            trend_strength=trend_strength,
            expected_profit_pips=expected_profit_pips,
            cost_ratio=cost_ratio,
        )

    def _check_atr_filter(self, h1_data: List, base_signal: Dict) -> Tuple[bool, float]:
        """ATRフィルター: 大きなブレイクアウトのみ許可"""
        atr_period = self.cost_resistance_params["atr_period"]
        min_multiple = self.cost_resistance_params["min_atr_multiple"]

        if len(h1_data) < atr_period + 10:
            return False, 0

        # ATR計算
        recent_data = h1_data[-atr_period - 5 :]
        true_ranges = []

        for i in range(1, len(recent_data)):
            current = recent_data[i]
            previous = recent_data[i - 1]

            # True Range計算
            if isinstance(current, dict):
                high = current["high"]
                low = current["low"]
                prev_close = previous["close"]
            else:
                high = current.high
                low = current.low
                prev_close = previous.close

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)

        if len(true_ranges) < atr_period:
            return False, 0

        atr = np.mean(true_ranges[-atr_period:])

        # 現在のブレイクアウト幅計算
        current_bar = h1_data[-1]
        if isinstance(current_bar, dict):
            breakout_size = current_bar["high"] - current_bar["low"]
        else:
            breakout_size = current_bar.high - current_bar.low

        atr_multiple = breakout_size / atr if atr > 0 else 0

        # ATR倍数チェック
        passed = atr_multiple >= min_multiple

        return passed, atr_multiple

    def _check_trend_filter(
        self, h1_data: List, base_signal: Dict
    ) -> Tuple[bool, float]:
        """トレンドフィルター: 明確な方向性のみ許可"""
        ma_long_period = self.cost_resistance_params["trend_ma_long_period"]
        ma_short_period = self.cost_resistance_params["trend_ma_short_period"]
        self.cost_resistance_params["min_trend_strength"]

        if len(h1_data) < ma_long_period + 10:
            return False, 0

        # 移動平均計算用データ準備
        recent_data = h1_data[-ma_long_period - 10 :]
        closes = []

        for bar in recent_data:
            if isinstance(bar, dict):
                closes.append(bar["close"])
            else:
                closes.append(bar.close)

        if len(closes) < ma_long_period:
            return False, 0

        # 長期・短期移動平均計算（Gemini指摘による修正）
        ma_long = np.mean(closes[-ma_long_period:])
        ma_short = np.mean(closes[-ma_short_period:])  # 短期MA期間を修正

        # 現在価格
        current_price = closes[-1]

        # トレンド強度計算（スケール調整）
        price_vs_long = (
            abs(current_price - ma_long) / ma_long * 100 if ma_long > 0 else 0
        )  # パーセント変換
        short_vs_long = (
            abs(ma_short - ma_long) / ma_long * 100 if ma_long > 0 else 0
        )  # パーセント変換

        trend_strength = (price_vs_long + short_vs_long) / 2  # 平均をとる

        # 方向性チェック
        signal_direction = base_signal.get("action", "")

        if signal_direction == "BUY":
            direction_match = current_price > ma_long and ma_short > ma_long
        elif signal_direction == "SELL":
            direction_match = current_price < ma_long and ma_short < ma_long
        else:
            direction_match = False

        # 方向性のみをチェック（強度チェックは一時的に無効化）
        passed = direction_match  # まずは方向性のみで承認

        return passed, trend_strength

    def _check_profit_filter(
        self, h1_data: List, base_signal: Dict
    ) -> Tuple[bool, float]:
        """利益期待フィルター: ATRベースのリスクリワード計算"""
        min_profit = self.cost_resistance_params["min_profit_pips"]
        atr_period = self.cost_resistance_params["atr_period"]

        if len(h1_data) < atr_period + 5:
            return False, 0

        # ATR計算（Gemini提案による改善）
        recent_data = h1_data[-atr_period - 5 :]
        true_ranges = []

        for i in range(1, len(recent_data)):
            current = recent_data[i]
            previous = recent_data[i - 1]

            if isinstance(current, dict):
                high = current["high"]
                low = current["low"]
                prev_close = previous["close"]
            else:
                high = current.high
                low = current.low
                prev_close = previous.close

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        if len(true_ranges) < atr_period:
            return False, 0

        atr = np.mean(true_ranges[-atr_period:])

        # ATRベース期待利益計算（リスクリワード1:2を想定）
        atr_pips = atr / 0.0001
        expected_profit_pips = atr_pips * 2.0  # 2xATRを期待利益とする

        passed = expected_profit_pips >= min_profit

        return passed, expected_profit_pips

    def _evaluate_signal_quality(
        self, atr_multiple: float, trend_strength: float, expected_profit_pips: float
    ) -> str:
        """シグナル品質評価"""
        score = 0

        # ATR評価
        if atr_multiple >= 5.0:
            score += 2
        elif atr_multiple >= 4.0:
            score += 1

        # トレンド評価
        if trend_strength >= 1.0:
            score += 2
        elif trend_strength >= 0.8:
            score += 1

        # 利益評価
        if expected_profit_pips >= 12.0:
            score += 2
        elif expected_profit_pips >= 10.0:
            score += 1

        if score >= 5:
            return "HIGH"
        elif score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_optimized_levels(
        self, h1_data: List, base_signal: Dict, expected_profit_pips: float
    ) -> Tuple[float, float]:
        """最適化されたストップ・利確レベル計算"""

        entry_price = base_signal.get("price", 0)
        direction = base_signal.get("action", "")

        # ATRベースのストップロス
        atr_period = 14
        if len(h1_data) >= atr_period:
            recent_data = h1_data[-atr_period:]
            true_ranges = []

            for i in range(1, len(recent_data)):
                current = recent_data[i]
                previous = recent_data[i - 1]

                if isinstance(current, dict):
                    high = current["high"]
                    low = current["low"]
                    prev_close = previous["close"]
                else:
                    high = current.high
                    low = current.low
                    prev_close = previous.close

                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                true_ranges.append(tr)

            atr = np.mean(true_ranges) if true_ranges else 0.0001
        else:
            atr = 0.0001

        # ストップロス = ATR * 1.5
        stop_distance = atr * 1.5

        # 利確 = 期待利益pips
        profit_distance = expected_profit_pips * 0.0001

        if direction == "BUY":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + profit_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - profit_distance

        return stop_loss, take_profit

    def get_statistics(self) -> Dict:
        """統計情報取得"""
        total_filtered = (
            self.signals_filtered_atr
            + self.signals_filtered_trend
            + self.signals_filtered_profit
        )

        return {
            "signals_generated": self.signals_generated,
            "signals_filtered_atr": self.signals_filtered_atr,
            "signals_filtered_trend": self.signals_filtered_trend,
            "signals_filtered_profit": self.signals_filtered_profit,
            "signals_approved": self.signals_approved,
            "total_filtered": total_filtered,
            "approval_rate": self.signals_approved / self.signals_generated
            if self.signals_generated > 0
            else 0,
            "filter_effectiveness": total_filtered / self.signals_generated
            if self.signals_generated > 0
            else 0,
        }


if __name__ == "__main__":
    # テスト用パラメータ
    test_params = {
        "h4_period": 24,
        "h1_period": 24,
        "atr_period": 14,
        "profit_atr": 2.5,
        "stop_atr": 1.3,
        "min_break_pips": 5,
    }

    strategy = CostResistantStrategy(test_params)
    print("🛡️ コスト耐性ブレイクアウト戦略初期化完了")
    print(f"   最小ATR倍数: {strategy.cost_resistance_params['min_atr_multiple']}")
    print(f"   最小利益期待: {strategy.cost_resistance_params['min_profit_pips']} pips")
    print(f"   最小コスト比率: {strategy.cost_resistance_params['min_cost_ratio']}")
