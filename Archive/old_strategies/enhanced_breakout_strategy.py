#!/usr/bin/env python3
"""
強化ブレイクアウト戦略
リスク管理システムを統合したマルチタイムフレームブレイクアウト戦略
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
from risk_management_system import AdaptiveRiskManager, RiskParameters

@dataclass
class EnhancedTradeSignal:
    """強化トレードシグナル"""
    timestamp: datetime
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'
    risk_assessment: str
    market_environment: Dict
    original_signal: Dict

class EnhancedBreakoutStrategy:
    """強化ブレイクアウト戦略"""
    
    def __init__(self, base_params: Dict):
        self.base_params = base_params
        self.base_strategy = MultiTimeframeBreakoutStrategy(base_params)
        self.risk_manager = AdaptiveRiskManager(base_params)
        
        # 統合設定
        self.enable_adaptive_risk = True
        self.enable_market_filter = True
        self.enable_volatility_filter = True
        
        # 統計
        self.signals_generated = 0
        self.signals_filtered = 0
        self.trades_executed = 0
        
    def generate_enhanced_signal(self, 
                               mtf_data: MultiTimeframeData,
                               current_time: datetime,
                               current_drawdown: float = 0.0,
                               daily_loss: float = 0.0,
                               open_positions: int = 0) -> Optional[EnhancedTradeSignal]:
        """強化シグナル生成"""
        
        # 元の戦略シグナル取得（簡易版）
        original_signal = self._get_simple_signal(mtf_data, current_time)
        
        if not original_signal or original_signal['action'] == 'HOLD':
            return None
        
        self.signals_generated += 1
        
        # 市場環境分析
        h1_data = mtf_data.get_h1_data()
        price_data = []
        for bar in h1_data[-300:]:
            if isinstance(bar, dict):
                # 辞書形式のデータ
                price_data.append({
                    'datetime': bar['datetime'],
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'volume': bar.get('volume', 1000)
                })
            else:
                # オブジェクト形式のデータ
                price_data.append({
                    'datetime': bar.datetime,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': getattr(bar, 'volume', 1000)
                })
        
        market_analysis = self.risk_manager.get_market_analysis(price_data, current_time)
        
        # トレード実行判定
        can_trade, reason = self.risk_manager.should_enter_trade(
            price_data, current_time, current_drawdown, daily_loss, open_positions
        )
        
        if not can_trade:
            self.signals_filtered += 1
            print(f"   シグナルフィルタリング: {reason}")
            return None
        
        # 適応的リスク管理パラメータ
        risk_params = self.risk_manager.calculate_adaptive_risk_parameters(
            price_data, current_time, current_drawdown
        )
        
        # エントリー価格調整
        current_price = h1_data[-1]['close'] if isinstance(h1_data[-1], dict) else h1_data[-1].close
        
        if original_signal['action'] == 'BUY':
            entry_price = current_price
            stop_loss = current_price - (risk_params.stop_loss_pips / 10000)
            take_profit = current_price + (risk_params.take_profit_pips / 10000)
        else:  # SELL
            entry_price = current_price
            stop_loss = current_price + (risk_params.stop_loss_pips / 10000)
            take_profit = current_price - (risk_params.take_profit_pips / 10000)
        
        # 信頼度評価
        confidence = self._assess_signal_confidence(original_signal, market_analysis)
        
        # 強化シグナル作成
        enhanced_signal = EnhancedTradeSignal(
            timestamp=current_time,
            direction=original_signal['action'],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=risk_params.position_size,
            confidence=confidence,
            risk_assessment=market_analysis['trading_conditions']['risk_assessment'],
            market_environment=market_analysis['market_environment'],
            original_signal=original_signal
        )
        
        self.trades_executed += 1
        return enhanced_signal
    
    def _get_simple_signal(self, mtf_data: MultiTimeframeData, current_time: datetime) -> Optional[Dict]:
        """簡易シグナル生成（ATRボラティリティフィルター強化版）"""
        try:
            h1_data = mtf_data.get_h1_data()
            h4_data = mtf_data.get_h4_data()
            
            if len(h1_data) < 50 or len(h4_data) < 50:
                return None
            
            # 現在価格
            current_h1 = h1_data[-1]
            current_price = current_h1['close']
            
            # ATRベースボラティリティフィルター
            atr_analysis = self._calculate_atr_volatility_filter(h1_data)
            
            # 低ボラティリティ環境での取引停止
            if atr_analysis['volatility_level'] == 'LOW':
                return {'action': 'HOLD', 'filter_reason': 'LOW_VOLATILITY'}
            
            # 異常高ボラティリティでの取引停止
            if atr_analysis['volatility_level'] == 'EXTREME':
                return {'action': 'HOLD', 'filter_reason': 'EXTREME_VOLATILITY'}
            
            # 簡易ブレイクアウト判定
            # H4の高値・安値ブレイク
            h4_high = max(bar['high'] for bar in h4_data[-self.base_params['h4_period']:])
            h4_low = min(bar['low'] for bar in h4_data[-self.base_params['h4_period']:])
            
            # H1の高値・安値ブレイク
            h1_high = max(bar['high'] for bar in h1_data[-self.base_params['h1_period']:])
            h1_low = min(bar['low'] for bar in h1_data[-self.base_params['h1_period']:])
            
            # ATR正規化ブレイクアウト強度
            current_atr = atr_analysis['current_atr']
            h4_break_strength = 0.0
            h1_break_strength = 0.0
            
            # ブレイクアウト判定と強度計算
            if current_price > h4_high and current_price > h1_high:
                h4_break_strength = (current_price - h4_high) / current_atr
                h1_break_strength = (current_price - h1_high) / current_atr
                
                # 最小ブレイクアウト強度チェック
                if h4_break_strength < 0.5 or h1_break_strength < 0.3:
                    return {'action': 'HOLD', 'filter_reason': 'WEAK_BREAKOUT'}
                
                return {
                    'action': 'BUY',
                    'breakout_strength': min(h4_break_strength, h1_break_strength),
                    'trend_alignment': atr_analysis['trend_strength'],
                    'volume_confirmation': atr_analysis['volume_factor'],
                    'volatility_level': atr_analysis['volatility_level'],
                    'atr_info': atr_analysis,
                    'signal_time': current_time.isoformat()
                }
            elif current_price < h4_low and current_price < h1_low:
                h4_break_strength = (h4_low - current_price) / current_atr
                h1_break_strength = (h1_low - current_price) / current_atr
                
                # 最小ブレイクアウト強度チェック
                if h4_break_strength < 0.5 or h1_break_strength < 0.3:
                    return {'action': 'HOLD', 'filter_reason': 'WEAK_BREAKOUT'}
                
                return {
                    'action': 'SELL',
                    'breakout_strength': min(h4_break_strength, h1_break_strength),
                    'trend_alignment': atr_analysis['trend_strength'],
                    'volume_confirmation': atr_analysis['volume_factor'],
                    'volatility_level': atr_analysis['volatility_level'],
                    'atr_info': atr_analysis,
                    'signal_time': current_time.isoformat()
                }
            
            return {'action': 'HOLD'}
            
        except Exception as e:
            print(f"   シグナル生成エラー: {str(e)}")
            return None
    
    def _calculate_atr_volatility_filter(self, h1_data: List) -> Dict:
        """ATRベースボラティリティフィルター計算"""
        try:
            atr_period = self.base_params.get('atr_period', 14)
            
            if len(h1_data) < atr_period + 10:
                return {
                    'current_atr': 0.0001,
                    'volatility_level': 'MEDIUM',
                    'trend_strength': 0.5,
                    'volume_factor': 0.5
                }
            
            # ATR計算
            atr_values = []
            for i in range(atr_period, len(h1_data)):
                true_ranges = []
                for j in range(i - atr_period + 1, i + 1):
                    bar = h1_data[j]
                    prev_bar = h1_data[j - 1]
                    
                    if isinstance(bar, dict):
                        high = bar['high']
                        low = bar['low']
                        prev_close = prev_bar['close']
                    else:
                        high = bar.high
                        low = bar.low
                        prev_close = prev_bar.close
                    
                    tr = max(
                        high - low,
                        abs(high - prev_close),
                        abs(low - prev_close)
                    )
                    true_ranges.append(tr)
                
                atr = sum(true_ranges) / len(true_ranges)
                atr_values.append(atr)
            
            if not atr_values:
                current_atr = 0.0001
                atr_percentile = 50
            else:
                current_atr = atr_values[-1]
                # ATRパーセンタイル計算
                sorted_atr = sorted(atr_values[-100:])  # 直近100期間
                atr_percentile = (sorted_atr.index(min(sorted_atr, key=lambda x: abs(x - current_atr))) + 1) / len(sorted_atr) * 100
            
            # ボラティリティレベル判定
            if atr_percentile < 20:
                volatility_level = 'LOW'
            elif atr_percentile < 40:
                volatility_level = 'MEDIUM_LOW'
            elif atr_percentile < 60:
                volatility_level = 'MEDIUM'
            elif atr_percentile < 80:
                volatility_level = 'MEDIUM_HIGH'
            elif atr_percentile < 95:
                volatility_level = 'HIGH'
            else:
                volatility_level = 'EXTREME'
            
            # トレンド強度計算（移動平均ベース）
            recent_prices = []
            for bar in h1_data[-20:]:
                price = bar['close'] if isinstance(bar, dict) else bar.close
                recent_prices.append(price)
            
            if len(recent_prices) >= 10:
                short_ma = sum(recent_prices[-10:]) / 10
                long_ma = sum(recent_prices) / len(recent_prices)
                trend_strength = abs(short_ma - long_ma) / current_atr
                trend_strength = min(trend_strength, 1.0)  # 0-1正規化
            else:
                trend_strength = 0.5
            
            # ボリューム係数（簡易版）
            volume_factor = 0.7 if volatility_level in ['MEDIUM', 'MEDIUM_HIGH', 'HIGH'] else 0.3
            
            return {
                'current_atr': current_atr,
                'atr_percentile': atr_percentile,
                'volatility_level': volatility_level,
                'trend_strength': trend_strength,
                'volume_factor': volume_factor,
                'atr_values_count': len(atr_values)
            }
            
        except Exception as e:
            print(f"   ATRフィルター計算エラー: {str(e)}")
            return {
                'current_atr': 0.0001,
                'volatility_level': 'MEDIUM',
                'trend_strength': 0.5,
                'volume_factor': 0.5
            }
    
    def _assess_signal_confidence(self, 
                                original_signal: Dict,
                                market_analysis: Dict) -> str:
        """シグナル信頼度評価"""
        
        confidence_factors = {
            'breakout_strength': original_signal.get('breakout_strength', 0.5),
            'market_volatility': 1.0 if market_analysis['market_environment']['volatility_level'] == 'medium' else 0.5,
            'trend_alignment': original_signal.get('trend_alignment', 0.5),
            'volume_confirmation': original_signal.get('volume_confirmation', 0.5)
        }
        
        avg_confidence = sum(confidence_factors.values()) / len(confidence_factors)
        
        if avg_confidence >= 0.75:
            return 'HIGH'
        elif avg_confidence >= 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def backtest_enhanced_strategy(self, 
                                 mtf_data: MultiTimeframeData,
                                 start_date: datetime,
                                 end_date: datetime) -> Dict:
        """強化戦略バックテスト"""
        
        print(f"🚀 強化戦略バックテスト開始")
        print(f"   期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        
        # 統計初期化
        self.signals_generated = 0
        self.signals_filtered = 0
        self.trades_executed = 0
        
        trades = []
        equity_curve = []
        
        # 初期設定
        initial_balance = 100000
        current_balance = initial_balance
        current_drawdown = 0.0
        daily_loss = 0.0
        open_positions = 0
        max_drawdown = 0.0
        
        # 日次リセット用
        last_date = start_date.date()
        
        # バックテスト実行
        h1_data = mtf_data.get_h1_data()
        
        for i, bar in enumerate(h1_data):
            bar_time = bar['datetime'] if isinstance(bar, dict) else bar.datetime
            if bar_time < start_date or bar_time > end_date:
                continue
            
            current_time = bar_time
            
            # 日次リセット
            if current_time.date() != last_date:
                daily_loss = 0.0
                last_date = current_time.date()
            
            # 強化シグナル生成
            enhanced_signal = self.generate_enhanced_signal(
                mtf_data, current_time, current_drawdown, daily_loss, open_positions
            )
            
            if enhanced_signal:
                # トレード実行
                trade_result = self._execute_trade(enhanced_signal, h1_data[i:i+100])
                
                if trade_result:
                    trades.append(trade_result)
                    
                    # 残高更新
                    current_balance += trade_result['pnl']
                    daily_loss += max(0, -trade_result['pnl'])
                    
                    # ドローダウン計算
                    if current_balance < initial_balance:
                        current_drawdown = (initial_balance - current_balance) / initial_balance
                        max_drawdown = max(max_drawdown, current_drawdown)
                    else:
                        current_drawdown = 0.0
            
            # エクイティカーブ記録
            if i % 24 == 0:  # 1日おき
                equity_curve.append({
                    'timestamp': current_time.isoformat(),
                    'balance': current_balance,
                    'drawdown': current_drawdown
                })
        
        # 結果分析
        results = self._analyze_enhanced_results(trades, equity_curve, initial_balance)
        
        # 統計情報追加
        results['signal_statistics'] = {
            'signals_generated': self.signals_generated,
            'signals_filtered': self.signals_filtered,
            'trades_executed': self.trades_executed,
            'filter_ratio': self.signals_filtered / self.signals_generated if self.signals_generated > 0 else 0,
            'execution_ratio': self.trades_executed / self.signals_generated if self.signals_generated > 0 else 0
        }
        
        print(f"   生成シグナル: {self.signals_generated}")
        print(f"   フィルタリング: {self.signals_filtered}")
        print(f"   実行取引: {self.trades_executed}")
        print(f"   フィルタリング率: {results['signal_statistics']['filter_ratio']:.1%}")
        
        return results
    
    def _execute_trade(self, signal: EnhancedTradeSignal, future_data: List) -> Optional[Dict]:
        """トレード実行シミュレーション"""
        
        if len(future_data) < 10:
            return None
        
        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit
        position_size = signal.position_size
        
        # 最大保有期間
        max_holding_bars = 48  # 48時間
        
        for i, bar in enumerate(future_data[:max_holding_bars]):
            # データ形式統一
            if isinstance(bar, dict):
                bar_time = bar['datetime']
                bar_low = bar['low']
                bar_high = bar['high']
                bar_close = bar['close']
            else:
                bar_time = bar.datetime
                bar_low = bar.low
                bar_high = bar.high
                bar_close = bar.close
            
            if signal.direction == 'BUY':
                # ロング
                if bar_low <= stop_loss:
                    # ストップロス
                    exit_price = stop_loss
                    pnl = (exit_price - entry_price) * position_size * 100000
                    return {
                        'entry_time': signal.timestamp.isoformat(),
                        'exit_time': bar_time.isoformat(),
                        'direction': 'BUY',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position_size': position_size,
                        'pnl': pnl,
                        'exit_reason': 'STOP_LOSS',
                        'holding_bars': i + 1,
                        'confidence': signal.confidence
                    }
                elif bar_high >= take_profit:
                    # テイクプロフィット
                    exit_price = take_profit
                    pnl = (exit_price - entry_price) * position_size * 100000
                    return {
                        'entry_time': signal.timestamp.isoformat(),
                        'exit_time': bar_time.isoformat(),
                        'direction': 'BUY',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position_size': position_size,
                        'pnl': pnl,
                        'exit_reason': 'TAKE_PROFIT',
                        'holding_bars': i + 1,
                        'confidence': signal.confidence
                    }
            else:  # SELL
                # ショート
                if bar_high >= stop_loss:
                    # ストップロス
                    exit_price = stop_loss
                    pnl = (entry_price - exit_price) * position_size * 100000
                    return {
                        'entry_time': signal.timestamp.isoformat(),
                        'exit_time': bar_time.isoformat(),
                        'direction': 'SELL',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position_size': position_size,
                        'pnl': pnl,
                        'exit_reason': 'STOP_LOSS',
                        'holding_bars': i + 1,
                        'confidence': signal.confidence
                    }
                elif bar_low <= take_profit:
                    # テイクプロフィット
                    exit_price = take_profit
                    pnl = (entry_price - exit_price) * position_size * 100000
                    return {
                        'entry_time': signal.timestamp.isoformat(),
                        'exit_time': bar_time.isoformat(),
                        'direction': 'SELL',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position_size': position_size,
                        'pnl': pnl,
                        'exit_reason': 'TAKE_PROFIT',
                        'holding_bars': i + 1,
                        'confidence': signal.confidence
                    }
        
        # 最大保有期間で強制決済
        last_bar = future_data[max_holding_bars - 1]
        exit_price = last_bar['close'] if isinstance(last_bar, dict) else last_bar.close
        last_bar_time = last_bar['datetime'] if isinstance(last_bar, dict) else last_bar.datetime
        
        if signal.direction == 'BUY':
            pnl = (exit_price - entry_price) * position_size * 100000
        else:
            pnl = (entry_price - exit_price) * position_size * 100000
        
        return {
            'entry_time': signal.timestamp.isoformat(),
            'exit_time': last_bar_time.isoformat(),
            'direction': signal.direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'position_size': position_size,
            'pnl': pnl,
            'exit_reason': 'TIME_EXIT',
            'holding_bars': max_holding_bars,
            'confidence': signal.confidence
        }
    
    def _analyze_enhanced_results(self, trades: List[Dict], equity_curve: List[Dict], initial_balance: float) -> Dict:
        """強化結果分析"""
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            }
        
        # 基本統計
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in trades)
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # ドローダウン計算
        max_drawdown = 0.0
        running_max = initial_balance
        
        for point in equity_curve:
            running_max = max(running_max, point['balance'])
            drawdown = (running_max - point['balance']) / running_max
            max_drawdown = max(max_drawdown, drawdown)
        
        # シャープ比
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                prev_balance = equity_curve[i-1]['balance']
                curr_balance = equity_curve[i]['balance']
                returns.append((curr_balance - prev_balance) / prev_balance)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                return_std = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
                sharpe_ratio = avg_return / return_std if return_std > 0 else 0
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # 信頼度別分析
        confidence_analysis = {}
        for confidence in ['HIGH', 'MEDIUM', 'LOW']:
            conf_trades = [t for t in trades if t['confidence'] == confidence]
            if conf_trades:
                conf_win_rate = len([t for t in conf_trades if t['pnl'] > 0]) / len(conf_trades)
                conf_pnl = sum(t['pnl'] for t in conf_trades)
                confidence_analysis[confidence] = {
                    'trades': len(conf_trades),
                    'win_rate': conf_win_rate,
                    'total_pnl': conf_pnl,
                    'avg_pnl': conf_pnl / len(conf_trades)
                }
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_pnl': total_pnl / total_trades,
            'confidence_analysis': confidence_analysis,
            'final_balance': initial_balance + total_pnl
        }

def main():
    """メイン実行"""
    print("🚀 強化ブレイクアウト戦略テスト開始")
    
    # パラメータ設定
    base_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,
        'stop_atr': 1.3,
        'min_break_pips': 5
    }
    
    # 強化戦略初期化
    enhanced_strategy = EnhancedBreakoutStrategy(base_params)
    
    print(f"   基本パラメータ: {base_params}")
    print(f"   適応的リスク管理: {enhanced_strategy.enable_adaptive_risk}")
    print(f"   市場フィルター: {enhanced_strategy.enable_market_filter}")
    
    print("✅ 強化ブレイクアウト戦略テスト完了")

if __name__ == "__main__":
    main()