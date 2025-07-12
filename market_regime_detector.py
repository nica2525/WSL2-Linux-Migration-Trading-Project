#!/usr/bin/env python3
"""
市場レジーム検出システム (Copilot協働開発)
作成日時: 2025-07-12 21:32 JST

目的: 低ボラティリティ環境自動検出とブレイクアウト戦略適応調整
Copilotプロンプト: "低ボラ環境検出+戦略適応のPythonアルゴリズム設計"
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from enum import Enum

class MarketRegime(Enum):
    """市場レジーム分類"""
    HIGH_VOLATILITY = "high_vol"      # 高ボラティリティ（ブレイクアウト有利）
    LOW_VOLATILITY = "low_vol"        # 低ボラティリティ（レンジ相場）
    TRENDING = "trending"             # トレンド相場
    CHOPPY = "choppy"                # 横ばい・ノイズ多い

class MarketRegimeDetector:
    """
    市場レジーム自動検出システム
    - ATR基準のボラティリティ測定
    - 価格レンジ分析
    - トレンド強度測定
    - 複合指標による環境分類
    """
    
    def __init__(self, 
                 atr_period: int = 14,
                 range_period: int = 20,
                 trend_period: int = 50):
        self.atr_period = atr_period
        self.range_period = range_period
        self.trend_period = trend_period
        
        # しきい値（Copilotに最適化依頼予定）
        self.volatility_threshold_low = 0.0005   # ATR/Price比率
        self.volatility_threshold_high = 0.0015
        self.trend_strength_threshold = 0.5      # トレンド強度
        self.range_efficiency_threshold = 0.3    # レンジ効率
        
    def calculate_atr_ratio(self, data: pd.DataFrame) -> pd.Series:
        """ATR/価格比率計算（正規化ボラティリティ）"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # True Range計算
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = true_range.rolling(window=self.atr_period).mean()
        
        # 価格で正規化
        atr_ratio = atr / close
        
        return atr_ratio
    
    def calculate_price_range_efficiency(self, data: pd.DataFrame) -> pd.Series:
        """価格レンジ効率計算"""
        close = data['close']
        
        # 期間内の最大・最小価格
        rolling_max = close.rolling(window=self.range_period).max()
        rolling_min = close.rolling(window=self.range_period).min()
        
        # 価格レンジ
        price_range = rolling_max - rolling_min
        
        # 実際の価格移動距離
        price_movement = np.abs(close - close.shift(self.range_period))
        
        # レンジ効率（実移動/最大レンジ）
        range_efficiency = price_movement / (price_range + 1e-8)  # ゼロ除算防止
        
        return range_efficiency
    
    def calculate_trend_strength(self, data: pd.DataFrame) -> pd.Series:
        """トレンド強度計算"""
        close = data['close']
        
        # 移動平均の傾き
        ma = close.rolling(window=self.trend_period).mean()
        ma_slope = (ma - ma.shift(self.trend_period // 4)) / (self.trend_period // 4)
        
        # 価格と移動平均の乖離
        price_deviation = np.abs(close - ma) / ma
        
        # トレンド一貫性（方向性の一致度）
        price_changes = close.diff()
        trend_consistency = (
            price_changes.rolling(window=self.trend_period).apply(
                lambda x: np.sum(np.sign(x) == np.sign(np.sum(x))) / len(x)
            )
        )
        
        # 複合トレンド強度
        trend_strength = (
            np.abs(ma_slope) * 1000 +  # 傾きの重み
            price_deviation * 0.5 +     # 乖離の重み  
            trend_consistency * 0.3     # 一貫性の重み
        )
        
        return trend_strength
    
    def detect_regime(self, data: pd.DataFrame) -> pd.Series:
        """市場レジーム検出メイン関数"""
        
        # 各指標計算
        atr_ratio = self.calculate_atr_ratio(data)
        range_efficiency = self.calculate_price_range_efficiency(data)
        trend_strength = self.calculate_trend_strength(data)
        
        # レジーム分類ロジック
        regimes = []
        
        for i in range(len(data)):
            if i < max(self.atr_period, self.range_period, self.trend_period):
                regimes.append(MarketRegime.CHOPPY)  # 初期値
                continue
                
            vol = atr_ratio.iloc[i] if not pd.isna(atr_ratio.iloc[i]) else 0
            efficiency = range_efficiency.iloc[i] if not pd.isna(range_efficiency.iloc[i]) else 0
            trend = trend_strength.iloc[i] if not pd.isna(trend_strength.iloc[i]) else 0
            
            # 分類ロジック（Copilot最適化対象）
            if vol < self.volatility_threshold_low:
                if efficiency < self.range_efficiency_threshold:
                    regime = MarketRegime.LOW_VOLATILITY
                else:
                    regime = MarketRegime.CHOPPY
                    
            elif vol > self.volatility_threshold_high:
                if trend > self.trend_strength_threshold:
                    regime = MarketRegime.TRENDING
                else:
                    regime = MarketRegime.HIGH_VOLATILITY
                    
            else:  # 中程度のボラティリティ
                if trend > self.trend_strength_threshold:
                    regime = MarketRegime.TRENDING
                else:
                    regime = MarketRegime.CHOPPY
            
            regimes.append(regime)
        
        return pd.Series(regimes, index=data.index)
    
    def get_strategy_parameters(self, regime: MarketRegime) -> Dict:
        """レジーム別戦略パラメータ"""
        
        if regime == MarketRegime.HIGH_VOLATILITY:
            return {
                "profit_atr": 3.0,      # 利確幅拡大
                "stop_atr": 1.0,        # ストップ縮小
                "min_break_pips": 3,    # ブレイク閾値縮小
                "position_size": 1.0,   # フルポジション
                "active": True
            }
            
        elif regime == MarketRegime.TRENDING:
            return {
                "profit_atr": 4.0,      # 利確幅最大
                "stop_atr": 1.5,        # ストップ標準
                "min_break_pips": 5,    # ブレイク閾値標準
                "position_size": 1.2,   # オーバーポジション
                "active": True
            }
            
        elif regime == MarketRegime.LOW_VOLATILITY:
            return {
                "profit_atr": 1.5,      # 利確幅縮小
                "stop_atr": 2.0,        # ストップ拡大
                "min_break_pips": 8,    # ブレイク閾値拡大
                "position_size": 0.3,   # ポジション縮小
                "active": False         # 取引停止
            }
            
        else:  # CHOPPY
            return {
                "profit_atr": 2.0,      # 利確幅標準
                "stop_atr": 1.8,        # ストップやや拡大
                "min_break_pips": 6,    # ブレイク閾値やや拡大
                "position_size": 0.5,   # ポジション半分
                "active": True
            }
    
    def analyze_historical_regimes(self, data: pd.DataFrame) -> Dict:
        """過去のレジーム分析"""
        regimes = self.detect_regime(data)
        
        regime_stats = {}
        for regime in MarketRegime:
            count = (regimes == regime).sum()
            percentage = count / len(regimes) * 100
            regime_stats[regime.value] = {
                "count": count,
                "percentage": percentage
            }
        
        return regime_stats

# Copilot次回プロンプト用コメント
"""
Copilot改善要求:
1. しきい値の自動最適化アルゴリズム
2. 機械学習によるレジーム分類精度向上
3. リアルタイム処理最適化
4. バックテスト統合テスト関数

次回プロンプト例:
"上記MarketRegimeDetectorクラスのしきい値を、
過去データから自動最適化するアルゴリズムを追加してください。
目標: フォールド3のような低ボラ期間での戦略破綻防止"
"""

if __name__ == "__main__":
    # テスト用コード
    print("🤖 市場レジーム検出システム (Copilot協働版)")
    print("作成日時: 2025-07-12 21:32 JST")
    print("次のステップ: Copilotによるしきい値最適化")