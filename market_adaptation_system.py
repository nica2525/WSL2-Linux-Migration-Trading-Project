#!/usr/bin/env python3
"""
市場環境適応システム
動的パラメータ調整により市場環境変化に適応する
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class MarketRegime(Enum):
    """市場レジーム"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"
    BREAKOUT = "breakout"

@dataclass
class MarketState:
    """市場状態"""
    regime: MarketRegime
    volatility_level: str
    trend_strength: float
    volume_profile: str
    momentum: float
    mean_reversion_strength: float
    breakout_probability: float
    confidence: float

@dataclass
class AdaptiveParameters:
    """適応パラメータ"""
    h4_period: int
    h1_period: int
    atr_period: int
    profit_atr: float
    stop_atr: float
    min_break_pips: float
    position_size_multiplier: float
    entry_threshold: float
    exit_threshold: float
    time_filter_enabled: bool
    volatility_filter_enabled: bool

class MarketRegimeDetector:
    """市場レジーム検出器"""
    
    def __init__(self, lookback_period: int = 100):
        self.lookback_period = lookback_period
        
        # レジーム判定閾値
        self.thresholds = {
            'trend_strength': 0.6,
            'volatility_high': 1.5,
            'volatility_low': 0.5,
            'momentum_strong': 0.7,
            'range_width': 0.8
        }
    
    def detect_regime(self, price_data: List[Dict]) -> MarketState:
        """市場レジーム検出"""
        if len(price_data) < self.lookback_period:
            return self._default_market_state()
        
        recent_data = price_data[-self.lookback_period:]
        
        # 各指標計算
        trend_strength = self._calculate_trend_strength(recent_data)
        volatility_level = self._calculate_volatility_level(recent_data)
        momentum = self._calculate_momentum(recent_data)
        mean_reversion = self._calculate_mean_reversion_strength(recent_data)
        breakout_prob = self._calculate_breakout_probability(recent_data)
        volume_profile = self._analyze_volume_profile(recent_data)
        
        # レジーム判定
        regime = self._determine_regime(
            trend_strength, volatility_level, momentum, mean_reversion
        )
        
        # 信頼度計算
        confidence = self._calculate_confidence(
            trend_strength, volatility_level, momentum
        )
        
        return MarketState(
            regime=regime,
            volatility_level=volatility_level,
            trend_strength=trend_strength,
            volume_profile=volume_profile,
            momentum=momentum,
            mean_reversion_strength=mean_reversion,
            breakout_probability=breakout_prob,
            confidence=confidence
        )
    
    def _calculate_trend_strength(self, data: List[Dict]) -> float:
        """トレンド強度計算"""
        if len(data) < 20:
            return 0.5
        
        # 移動平均ベースのトレンド強度
        prices = [bar['close'] for bar in data]
        
        # 短期・長期移動平均
        short_ma = sum(prices[-10:]) / 10
        long_ma = sum(prices[-20:]) / 20
        
        # 価格分散
        price_std = math.sqrt(sum((p - long_ma)**2 for p in prices[-20:]) / 20)
        
        if price_std == 0:
            return 0.5
        
        # 正規化トレンド強度
        trend_strength = abs(short_ma - long_ma) / price_std
        return min(trend_strength, 1.0)
    
    def _calculate_volatility_level(self, data: List[Dict]) -> str:
        """ボラティリティレベル計算"""
        if len(data) < 14:
            return "medium"
        
        # ATR計算
        atr_values = []
        for i in range(1, len(data)):
            high = data[i]['high']
            low = data[i]['low']
            prev_close = data[i-1]['close']
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            atr_values.append(tr)
        
        if len(atr_values) < 14:
            return "medium"
        
        current_atr = sum(atr_values[-14:]) / 14
        historical_atr = sum(atr_values) / len(atr_values)
        
        if historical_atr == 0:
            return "medium"
        
        volatility_ratio = current_atr / historical_atr
        
        if volatility_ratio > self.thresholds['volatility_high']:
            return "high"
        elif volatility_ratio < self.thresholds['volatility_low']:
            return "low"
        else:
            return "medium"
    
    def _calculate_momentum(self, data: List[Dict]) -> float:
        """モメンタム計算"""
        if len(data) < 20:
            return 0.5
        
        # 価格変化率
        current_price = data[-1]['close']
        past_price = data[-20]['close']
        
        if past_price == 0:
            return 0.5
        
        price_change = (current_price - past_price) / past_price
        
        # 正規化（-1 to 1 → 0 to 1）
        momentum = (price_change + 1) / 2
        return max(0, min(1, momentum))
    
    def _calculate_mean_reversion_strength(self, data: List[Dict]) -> float:
        """平均回帰強度計算"""
        if len(data) < 30:
            return 0.5
        
        prices = [bar['close'] for bar in data]
        
        # 移動平均
        ma = sum(prices) / len(prices)
        
        # 価格の移動平均からの乖離
        deviations = [abs(p - ma) for p in prices]
        avg_deviation = sum(deviations) / len(deviations)
        
        # 乖離の減少傾向（平均回帰）
        recent_deviations = deviations[-10:]
        early_deviations = deviations[-20:-10]
        
        if not recent_deviations or not early_deviations:
            return 0.5
        
        recent_avg = sum(recent_deviations) / len(recent_deviations)
        early_avg = sum(early_deviations) / len(early_deviations)
        
        if early_avg == 0:
            return 0.5
        
        # 平均回帰強度（乖離の減少率）
        reversion_strength = (early_avg - recent_avg) / early_avg
        return max(0, min(1, reversion_strength))
    
    def _calculate_breakout_probability(self, data: List[Dict]) -> float:
        """ブレイクアウト確率計算"""
        if len(data) < 50:
            return 0.5
        
        # 価格レンジ分析
        highs = [bar['high'] for bar in data[-20:]]
        lows = [bar['low'] for bar in data[-20:]]
        
        range_high = max(highs)
        range_low = min(lows)
        range_width = range_high - range_low
        
        # 現在価格の位置
        current_price = data[-1]['close']
        
        # レンジ内での位置（0-1）
        if range_width == 0:
            return 0.5
        
        position_in_range = (current_price - range_low) / range_width
        
        # 端に近いほどブレイクアウト確率が高い
        breakout_probability = 2 * min(position_in_range, 1 - position_in_range)
        return 1 - breakout_probability  # 反転
    
    def _analyze_volume_profile(self, data: List[Dict]) -> str:
        """ボリューム分析"""
        if len(data) < 10:
            return "normal"
        
        volumes = [bar.get('volume', 1000) for bar in data[-10:]]
        avg_volume = sum(volumes) / len(volumes)
        recent_volume = volumes[-1]
        
        if recent_volume > avg_volume * 1.5:
            return "high"
        elif recent_volume < avg_volume * 0.7:
            return "low"
        else:
            return "normal"
    
    def _determine_regime(self, trend_strength: float, volatility_level: str, 
                         momentum: float, mean_reversion: float) -> MarketRegime:
        """レジーム判定"""
        
        # トレンド優先判定
        if trend_strength > self.thresholds['trend_strength']:
            return MarketRegime.TRENDING
        
        # ボラティリティベース判定
        if volatility_level == "high":
            if momentum > self.thresholds['momentum_strong']:
                return MarketRegime.BREAKOUT
            else:
                return MarketRegime.VOLATILE
        elif volatility_level == "low":
            return MarketRegime.QUIET
        
        # 平均回帰強度ベース判定
        if mean_reversion > 0.6:
            return MarketRegime.RANGING
        
        # デフォルト
        return MarketRegime.RANGING
    
    def _calculate_confidence(self, trend_strength: float, volatility_level: str, 
                            momentum: float) -> float:
        """判定信頼度計算"""
        confidence_factors = []
        
        # トレンド強度の明確性
        if trend_strength > 0.8 or trend_strength < 0.2:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # ボラティリティの明確性
        if volatility_level in ["high", "low"]:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # モメンタムの明確性
        if momentum > 0.8 or momentum < 0.2:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _default_market_state(self) -> MarketState:
        """デフォルト市場状態"""
        return MarketState(
            regime=MarketRegime.RANGING,
            volatility_level="medium",
            trend_strength=0.5,
            volume_profile="normal",
            momentum=0.5,
            mean_reversion_strength=0.5,
            breakout_probability=0.5,
            confidence=0.3
        )

class ParameterOptimizer:
    """パラメータ最適化器"""
    
    def __init__(self):
        # レジーム別最適パラメータ
        self.regime_parameters = {
            MarketRegime.TRENDING: {
                'h4_period': 20,
                'h1_period': 15,
                'profit_atr': 3.0,
                'stop_atr': 1.2,
                'min_break_pips': 8,
                'position_size_multiplier': 1.2,
                'entry_threshold': 0.6,
                'exit_threshold': 0.4,
                'time_filter_enabled': False,
                'volatility_filter_enabled': False
            },
            MarketRegime.RANGING: {
                'h4_period': 30,
                'h1_period': 20,
                'profit_atr': 1.8,
                'stop_atr': 1.5,
                'min_break_pips': 12,
                'position_size_multiplier': 0.8,
                'entry_threshold': 0.8,
                'exit_threshold': 0.3,
                'time_filter_enabled': True,
                'volatility_filter_enabled': True
            },
            MarketRegime.VOLATILE: {
                'h4_period': 15,
                'h1_period': 10,
                'profit_atr': 2.2,
                'stop_atr': 1.8,
                'min_break_pips': 5,
                'position_size_multiplier': 0.6,
                'entry_threshold': 0.7,
                'exit_threshold': 0.5,
                'time_filter_enabled': True,
                'volatility_filter_enabled': True
            },
            MarketRegime.QUIET: {
                'h4_period': 40,
                'h1_period': 30,
                'profit_atr': 1.5,
                'stop_atr': 1.0,
                'min_break_pips': 15,
                'position_size_multiplier': 1.5,
                'entry_threshold': 0.9,
                'exit_threshold': 0.2,
                'time_filter_enabled': True,
                'volatility_filter_enabled': False
            },
            MarketRegime.BREAKOUT: {
                'h4_period': 12,
                'h1_period': 8,
                'profit_atr': 4.0,
                'stop_atr': 1.0,
                'min_break_pips': 3,
                'position_size_multiplier': 1.0,
                'entry_threshold': 0.5,
                'exit_threshold': 0.6,
                'time_filter_enabled': False,
                'volatility_filter_enabled': False
            }
        }
    
    def optimize_parameters(self, market_state: MarketState, 
                          base_params: Dict) -> AdaptiveParameters:
        """パラメータ最適化"""
        
        # レジーム別パラメータ取得
        regime_params = self.regime_parameters[market_state.regime]
        
        # 信頼度による調整
        confidence_factor = market_state.confidence
        
        # 適応パラメータ計算
        adaptive_params = AdaptiveParameters(
            h4_period=int(regime_params['h4_period'] * (0.8 + 0.4 * confidence_factor)),
            h1_period=int(regime_params['h1_period'] * (0.8 + 0.4 * confidence_factor)),
            atr_period=base_params.get('atr_period', 14),
            profit_atr=regime_params['profit_atr'] * (0.8 + 0.4 * confidence_factor),
            stop_atr=regime_params['stop_atr'] * (1.2 - 0.4 * confidence_factor),
            min_break_pips=regime_params['min_break_pips'],
            position_size_multiplier=regime_params['position_size_multiplier'],
            entry_threshold=regime_params['entry_threshold'],
            exit_threshold=regime_params['exit_threshold'],
            time_filter_enabled=regime_params['time_filter_enabled'],
            volatility_filter_enabled=regime_params['volatility_filter_enabled']
        )
        
        return adaptive_params

class MarketAdaptationSystem:
    """市場適応システム"""
    
    def __init__(self, base_params: Dict):
        self.base_params = base_params
        self.regime_detector = MarketRegimeDetector()
        self.parameter_optimizer = ParameterOptimizer()
        
        # 状態履歴
        self.market_history = []
        self.adaptation_history = []
        
        # 学習機能
        self.learning_enabled = True
        self.adaptation_threshold = 0.7
    
    def adapt_to_market(self, price_data: List[Dict], 
                       current_time: datetime) -> Tuple[MarketState, AdaptiveParameters]:
        """市場適応"""
        
        # 市場状態検出
        market_state = self.regime_detector.detect_regime(price_data)
        
        # パラメータ最適化
        adaptive_params = self.parameter_optimizer.optimize_parameters(
            market_state, self.base_params
        )
        
        # 履歴記録
        self.market_history.append({
            'timestamp': current_time.isoformat(),
            'market_state': market_state,
            'confidence': market_state.confidence
        })
        
        self.adaptation_history.append({
            'timestamp': current_time.isoformat(),
            'regime': market_state.regime.value,
            'parameters': adaptive_params,
            'confidence': market_state.confidence
        })
        
        # 履歴サイズ制限
        if len(self.market_history) > 1000:
            self.market_history = self.market_history[-500:]
        if len(self.adaptation_history) > 1000:
            self.adaptation_history = self.adaptation_history[-500:]
        
        return market_state, adaptive_params
    
    def get_adaptation_summary(self) -> Dict:
        """適応サマリー"""
        if not self.market_history:
            return {"status": "no_data"}
        
        # 最新状態
        latest_state = self.market_history[-1]
        
        # レジーム分布
        regime_distribution = {}
        for record in self.market_history[-100:]:  # 直近100記録
            regime = record['market_state'].regime.value
            regime_distribution[regime] = regime_distribution.get(regime, 0) + 1
        
        # 平均信頼度
        avg_confidence = sum(r['confidence'] for r in self.market_history[-50:]) / min(50, len(self.market_history))
        
        return {
            'latest_regime': latest_state['market_state'].regime.value,
            'latest_confidence': latest_state['confidence'],
            'regime_distribution': regime_distribution,
            'average_confidence': avg_confidence,
            'adaptation_count': len(self.adaptation_history),
            'learning_enabled': self.learning_enabled
        }

def main():
    """メイン実行"""
    print("🌍 市場環境適応システムテスト開始")
    
    # テスト用データ生成
    test_data = []
    base_price = 1.1000
    base_date = datetime.now() - timedelta(hours=200)
    
    for i in range(200):
        # 時間的な価格変動パターン
        if i < 50:  # トレンド相場
            price_change = 0.0005 * (1 if i % 20 < 15 else -1)
        elif i < 100:  # レンジ相場
            price_change = 0.0002 * (1 if i % 10 < 5 else -1)
        elif i < 150:  # ボラティリティ相場
            price_change = 0.0015 * (1 if i % 5 < 2 else -1)
        else:  # 静寂相場
            price_change = 0.0001 * (1 if i % 30 < 15 else -1)
        
        base_price += price_change
        
        bar = {
            'datetime': base_date + timedelta(hours=i),
            'open': base_price,
            'high': base_price + abs(price_change) * 2,
            'low': base_price - abs(price_change) * 2,
            'close': base_price,
            'volume': 1000 + int(abs(price_change) * 100000)
        }
        
        test_data.append(bar)
    
    # 適応システム初期化
    base_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,
        'stop_atr': 1.3
    }
    
    adaptation_system = MarketAdaptationSystem(base_params)
    
    # 適応テスト
    print("\n適応テスト実行中...")
    
    for i in range(100, 200, 20):  # 20時間おきに5回テスト
        current_time = test_data[i]['datetime']
        market_data = test_data[:i+1]
        
        market_state, adaptive_params = adaptation_system.adapt_to_market(
            market_data, current_time
        )
        
        print(f"\n時刻: {current_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"レジーム: {market_state.regime.value}")
        print(f"信頼度: {market_state.confidence:.3f}")
        print(f"適応パラメータ:")
        print(f"  H4期間: {adaptive_params.h4_period}")
        print(f"  利益ATR: {adaptive_params.profit_atr:.1f}")
        print(f"  ストップATR: {adaptive_params.stop_atr:.1f}")
        print(f"  ポジションサイズ倍率: {adaptive_params.position_size_multiplier:.1f}")
    
    # サマリー
    summary = adaptation_system.get_adaptation_summary()
    print(f"\n適応サマリー:")
    print(f"  最新レジーム: {summary['latest_regime']}")
    print(f"  平均信頼度: {summary['average_confidence']:.3f}")
    print(f"  適応回数: {summary['adaptation_count']}")
    print(f"  レジーム分布: {summary['regime_distribution']}")
    
    print("\n✅ 市場環境適応システムテスト完了")

if __name__ == "__main__":
    main()