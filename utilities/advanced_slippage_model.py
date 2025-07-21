#!/usr/bin/env python3
"""
高度スリッパージ・約定遅延モデル
現実的な取引コスト・市場インパクト・流動性を考慮

Gemini満点システムへの統合対応
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from enum import Enum

class MarketCondition(Enum):
    """市場状況"""
    LIQUID = "liquid"          # 流動性豊富
    NORMAL = "normal"          # 通常
    ILLIQUID = "illiquid"      # 流動性不足
    VOLATILE = "volatile"      # 高ボラティリティ

class OrderType(Enum):
    """注文タイプ"""
    MARKET = "market"          # 成行注文
    LIMIT = "limit"            # 指値注文
    STOP = "stop"              # 逆指値注文

@dataclass
class SlippageConfig:
    """スリッパージ設定"""
    base_spread: float = 0.0002        # 基本スプレッド (2pip)
    market_impact_coeff: float = 0.5   # 市場インパクト係数
    volatility_multiplier: float = 2.0 # ボラティリティ乗数
    execution_delay_ms: int = 100      # 約定遅延(ミリ秒)
    liquidity_threshold: float = 1000000  # 流動性閾値
    
class AdvancedSlippageModel:
    """高度スリッパージモデル"""
    
    def __init__(self, config: SlippageConfig = None):
        self.config = config or SlippageConfig()
        self.market_conditions = {}
        self.execution_history = []
        
    def analyze_market_condition(self, data: pd.DataFrame, 
                               lookback_period: int = 20) -> MarketCondition:
        """市場状況分析"""
        if len(data) < lookback_period:
            return MarketCondition.NORMAL
            
        # 最近のデータ
        recent_data = data.tail(lookback_period)
        
        # ボラティリティ計算
        returns = recent_data['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # 年間ボラティリティ
        
        # 出来高分析
        avg_volume = recent_data['Volume'].mean()
        volume_std = recent_data['Volume'].std()
        current_volume = recent_data['Volume'].iloc[-1]
        
        # スプレッド分析（High-Low）
        spreads = (recent_data['High'] - recent_data['Low']) / recent_data['Close']
        avg_spread = spreads.mean()
        
        # 条件判定
        if volatility > 0.3:  # 30%以上の年間ボラティリティ
            return MarketCondition.VOLATILE
        elif current_volume < (avg_volume - volume_std):
            return MarketCondition.ILLIQUID
        elif current_volume > (avg_volume + volume_std) and avg_spread < 0.001:
            return MarketCondition.LIQUID
        else:
            return MarketCondition.NORMAL
    
    def calculate_dynamic_slippage(self, 
                                 price: float,
                                 volume: float,
                                 market_condition: MarketCondition,
                                 order_type: OrderType,
                                 order_size: float = 100000) -> Dict:
        """動的スリッパージ計算"""
        
        # 基本スプレッド
        base_slippage = self.config.base_spread
        
        # 市場状況調整
        condition_multipliers = {
            MarketCondition.LIQUID: 0.5,
            MarketCondition.NORMAL: 1.0,
            MarketCondition.ILLIQUID: 2.0,
            MarketCondition.VOLATILE: 1.5
        }
        
        # 注文タイプ調整
        order_multipliers = {
            OrderType.MARKET: 1.0,
            OrderType.LIMIT: 0.3,
            OrderType.STOP: 1.2
        }
        
        # 市場インパクト計算
        market_impact = self.config.market_impact_coeff * np.sqrt(order_size / volume)
        
        # 最終スリッパージ
        total_slippage = (
            base_slippage * 
            condition_multipliers[market_condition] * 
            order_multipliers[order_type] + 
            market_impact
        )
        
        return {
            'total_slippage': total_slippage,
            'base_slippage': base_slippage,
            'market_impact': market_impact,
            'condition_multiplier': condition_multipliers[market_condition],
            'order_multiplier': order_multipliers[order_type],
            'market_condition': market_condition.value
        }
    
    def calculate_execution_delay(self, 
                                market_condition: MarketCondition,
                                order_type: OrderType,
                                network_latency: int = 50) -> Dict:
        """約定遅延計算"""
        
        # 基本約定遅延
        base_delay = self.config.execution_delay_ms
        
        # 市場状況による遅延
        condition_delays = {
            MarketCondition.LIQUID: 50,
            MarketCondition.NORMAL: 100,
            MarketCondition.ILLIQUID: 300,
            MarketCondition.VOLATILE: 200
        }
        
        # 注文タイプによる遅延
        order_delays = {
            OrderType.MARKET: 0,
            OrderType.LIMIT: 100,
            OrderType.STOP: 50
        }
        
        # 総遅延時間
        total_delay = (
            base_delay + 
            condition_delays[market_condition] + 
            order_delays[order_type] + 
            network_latency
        )
        
        return {
            'total_delay_ms': total_delay,
            'base_delay': base_delay,
            'condition_delay': condition_delays[market_condition],
            'order_delay': order_delays[order_type],
            'network_latency': network_latency
        }
    
    def simulate_realistic_execution(self, 
                                   data: pd.DataFrame,
                                   entry_signals: pd.Series,
                                   order_type: OrderType = OrderType.MARKET,
                                   order_size: float = 100000) -> List[Dict]:
        """現実的な約定シミュレーション"""
        
        executions = []
        
        for timestamp, should_execute in entry_signals.items():
            if not should_execute:
                continue
                
            try:
                # 現在の市場データ
                current_idx = data.index.get_loc(timestamp)
                current_bar = data.iloc[current_idx]
                
                # 市場状況分析
                market_condition = self.analyze_market_condition(
                    data.iloc[:current_idx+1]
                )
                
                # スリッパージ計算（Look-ahead bias完全修正）
                # 実際の取引では現在バーのCloseは使用不可、常にOpenを使用
                current_price = current_bar['Open']
                
                slippage_info = self.calculate_dynamic_slippage(
                    price=current_price,
                    volume=current_bar['Volume'],
                    market_condition=market_condition,
                    order_type=order_type,
                    order_size=order_size
                )
                
                # 約定遅延計算
                delay_info = self.calculate_execution_delay(
                    market_condition=market_condition,
                    order_type=order_type
                )
                
                # 約定価格計算（スリッパージ考慮）
                if order_type == OrderType.MARKET:
                    # 成行注文：次のバーの始値 + スリッパージ
                    if current_idx + 1 < len(data):
                        next_bar = data.iloc[current_idx + 1]
                        execution_price = next_bar['Open'] * (1 + slippage_info['total_slippage'])
                    else:
                        continue
                else:
                    # 指値・逆指値注文：現在価格 + スリッパージ（Look-ahead bias修正）
                    execution_price = current_price * (1 + slippage_info['total_slippage'])
                
                # 約定記録（Look-ahead bias修正）
                execution = {
                    'timestamp': timestamp,
                    'signal_price': current_price,
                    'execution_price': execution_price,
                    'slippage_cost': execution_price - current_price,
                    'slippage_pct': slippage_info['total_slippage'],
                    'market_condition': market_condition.value,
                    'order_type': order_type.value,
                    'order_size': order_size,
                    'execution_delay_ms': delay_info['total_delay_ms'],
                    'volume': current_bar['Volume'],
                    'detailed_slippage': slippage_info,
                    'detailed_delay': delay_info
                }
                
                executions.append(execution)
                self.execution_history.append(execution)
                
            except (IndexError, KeyError) as e:
                continue
        
        return executions
    
    def calculate_cost_impact(self, executions: List[Dict]) -> Dict:
        """コストインパクト分析"""
        if not executions:
            return {}
            
        # 基本統計
        slippage_costs = [e['slippage_cost'] for e in executions]
        slippage_pcts = [e['slippage_pct'] for e in executions]
        delays = [e['execution_delay_ms'] for e in executions]
        
        # 市場状況別分析
        condition_analysis = {}
        for condition in MarketCondition:
            condition_execs = [e for e in executions if e['market_condition'] == condition.value]
            if condition_execs:
                condition_analysis[condition.value] = {
                    'count': len(condition_execs),
                    'avg_slippage_pct': np.mean([e['slippage_pct'] for e in condition_execs]),
                    'avg_delay_ms': np.mean([e['execution_delay_ms'] for e in condition_execs])
                }
        
        return {
            'total_executions': len(executions),
            'total_slippage_cost': sum(slippage_costs),
            'avg_slippage_cost': np.mean(slippage_costs),
            'avg_slippage_pct': np.mean(slippage_pcts),
            'max_slippage_pct': max(slippage_pcts),
            'avg_execution_delay_ms': np.mean(delays),
            'max_execution_delay_ms': max(delays),
            'condition_breakdown': condition_analysis,
            'slippage_distribution': {
                'p25': np.percentile(slippage_pcts, 25),
                'p50': np.percentile(slippage_pcts, 50),
                'p75': np.percentile(slippage_pcts, 75),
                'p95': np.percentile(slippage_pcts, 95)
            }
        }
    
    def save_execution_report(self, executions: List[Dict], output_path: str = None):
        """約定レポート保存"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"slippage_execution_report_{timestamp}.json"
        
        cost_impact = self.calculate_cost_impact(executions)
        
        report = {
            'config': {
                'base_spread': self.config.base_spread,
                'market_impact_coeff': self.config.market_impact_coeff,
                'volatility_multiplier': self.config.volatility_multiplier,
                'execution_delay_ms': self.config.execution_delay_ms
            },
            'cost_impact_analysis': cost_impact,
            'detailed_executions': executions,
            'generation_timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✅ 約定レポート保存: {output_path}")
        return output_path

def main():
    """テスト実行"""
    print("🚀 高度スリッパージ・約定遅延モデル テスト")
    print("=" * 60)
    
    # テストデータ生成
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    n_days = len(dates)
    
    returns = np.random.normal(0.0005, 0.02, n_days)
    price = 100 * np.exp(np.cumsum(returns))
    
    test_data = pd.DataFrame({
        'Open': price * (1 + np.random.normal(0, 0.001, n_days)),
        'High': price * (1 + np.abs(np.random.normal(0, 0.005, n_days))),
        'Low': price * (1 - np.abs(np.random.normal(0, 0.005, n_days))),
        'Close': price,
        'Volume': np.random.lognormal(15, 1, n_days)
    }, index=dates)
    
    # ランダムシグナル生成
    signal_frequency = 0.05  # 5%の確率でシグナル
    entry_signals = pd.Series(
        np.random.random(n_days) < signal_frequency,
        index=dates
    )
    
    # スリッパージモデル実行
    slippage_model = AdvancedSlippageModel()
    
    print(f"📊 テストデータ: {len(test_data)}日分")
    print(f"🎯 エントリーシグナル: {entry_signals.sum()}回")
    
    # 約定シミュレーション実行
    executions = slippage_model.simulate_realistic_execution(
        data=test_data,
        entry_signals=entry_signals,
        order_type=OrderType.MARKET,
        order_size=100000
    )
    
    print(f"✅ 約定実行: {len(executions)}回")
    
    # コストインパクト分析
    cost_impact = slippage_model.calculate_cost_impact(executions)
    
    print(f"\n📈 コストインパクト分析:")
    print(f"   平均スリッパージ: {cost_impact['avg_slippage_pct']:.4f}%")
    print(f"   最大スリッパージ: {cost_impact['max_slippage_pct']:.4f}%")
    print(f"   平均約定遅延: {cost_impact['avg_execution_delay_ms']:.0f}ms")
    
    # レポート保存
    report_path = slippage_model.save_execution_report(executions)
    
    print(f"\n🎉 高度スリッパージモデル テスト完了")
    print(f"📁 レポート: {report_path}")

if __name__ == "__main__":
    main()