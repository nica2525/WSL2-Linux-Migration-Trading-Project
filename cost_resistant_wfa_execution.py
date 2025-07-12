#!/usr/bin/env python3
"""
コスト耐性戦略WFA実行
改善された戦略でフォールド間安定性を検証
"""

import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple

from cost_resistant_strategy import CostResistantStrategy
from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeData

class CostResistantWFAExecution:
    """コスト耐性戦略WFA実行クラス"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
        self.base_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,
            'stop_atr': 1.3,
            'min_break_pips': 5
        }
        
        self.strategy = CostResistantStrategy(self.base_params)
    
    def execute_cost_resistant_wfa(self) -> Dict:
        """コスト耐性戦略WFA実行"""
        print("🛡️ コスト耐性戦略WFA実行開始")
        
        # データ読み込み
        print(f"📊 データ読み込み中...")
        raw_data = self.cache_manager.get_full_data()
        
        if not raw_data or len(raw_data) < 1000:
            print(f"❌ データ不足: {len(raw_data) if raw_data else 0}バー")
            return {}
        
        print(f"   読み込み完了: {len(raw_data):,}バー")
        
        # 簡易WFA実行（5フォールド）
        print("🔄 ウォークフォワード分析実行中...")
        
        wfa_results = []
        fold_size = len(raw_data) // 5
        
        for fold_id in range(1, 6):
            print(f"\n📈 フォールド {fold_id} 実行中...")
            
            # テストデータ範囲
            test_start = (fold_id - 1) * fold_size
            test_end = fold_id * fold_size
            test_data = raw_data[test_start:test_end]
            
            print(f"   テストデータ: {len(test_data):,}バー")
            
            # データ形式確認
            first_bar = test_data[0]
            last_bar = test_data[-1]
            
            if isinstance(first_bar, dict):
                start_time = first_bar['datetime']
                end_time = last_bar['datetime']
            else:
                start_time = first_bar.datetime
                end_time = last_bar.datetime
                
            print(f"   期間: {start_time} - {end_time}")
            
            # アウトオブサンプルテスト実行
            oos_result = self._execute_oos_test(test_data, fold_id)
            
            if oos_result:
                wfa_results.append(oos_result)
                
                print(f"   ✅ フォールド {fold_id} 完了")
                print(f"      取引数: {oos_result['trades']}")
                print(f"      PF: {oos_result['profit_factor']:.3f}")
                print(f"      リターン: {oos_result['total_return']:.4f}")
                print(f"      勝率: {oos_result['win_rate']:.1%}")
            else:
                print(f"   ❌ フォールド {fold_id} 失敗")
        
        # 結果分析
        analysis_result = self._analyze_wfa_results(wfa_results)
        
        # 結果保存
        final_result = {
            'strategy_name': 'Cost Resistant Breakout',
            'execution_time': datetime.now().isoformat(),
            'base_parameters': self.base_params,
            'cost_resistance_parameters': self.strategy.cost_resistance_params,
            'wfa_results': wfa_results,
            'analysis': analysis_result,
            'data_info': {
                'total_bars': len(raw_data),
                'folds_executed': len(wfa_results)
            }
        }
        
        output_file = 'cost_resistant_wfa_results.json'
        with open(output_file, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        print(f"\n📄 結果保存: {output_file}")
        
        return final_result
    
    def _execute_oos_test(self, test_data: List, fold_id: int) -> Dict:
        """アウトオブサンプルテスト実行"""
        try:
            trades = []
            equity_curve = []
            initial_balance = 100000
            current_balance = initial_balance
            
            # 戦略統計リセット
            self.strategy.signals_generated = 0
            self.strategy.signals_filtered_atr = 0
            self.strategy.signals_filtered_trend = 0
            self.strategy.signals_filtered_profit = 0
            self.strategy.signals_approved = 0
            
            for i, bar in enumerate(test_data[50:]):  # 最初の50バーはスキップ
                try:
                    if isinstance(bar, dict):
                        current_time = bar['datetime']
                    else:
                        current_time = bar.datetime
                    
                    # 過去データ準備
                    historical_data = test_data[:50+i+1]
                    
                    # 簡易シグナル生成（テスト用）
                    signal = self._generate_simple_signal(historical_data, current_time)
                    
                    if signal:
                        # 簡易取引実行
                        trade_result = self._execute_simple_trade(signal, test_data[50+i:50+i+48])
                        
                        if trade_result:
                            trades.append(trade_result)
                            current_balance += trade_result['pnl']
                    
                    # エクイティ記録（1日毎）
                    if i % 24 == 0:
                        equity_curve.append({
                            'timestamp': current_time.isoformat(),
                            'balance': current_balance
                        })
                
                except Exception as e:
                    continue
            
            if not trades:
                return None
            
            # 結果計算
            total_return = (current_balance - initial_balance) / initial_balance
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / len(trades)
            gross_profit = sum(t['pnl'] for t in winning_trades)
            gross_loss = abs(sum(t['pnl'] for t in losing_trades))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # シャープ比計算
            if len(equity_curve) > 1:
                returns = []
                for i in range(1, len(equity_curve)):
                    prev_balance = equity_curve[i-1]['balance']
                    curr_balance = equity_curve[i]['balance']
                    returns.append((curr_balance - prev_balance) / prev_balance)
                
                if returns:
                    avg_return = np.mean(returns)
                    return_std = np.std(returns)
                    sharpe_ratio = avg_return / return_std if return_std > 0 else 0
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0
            
            # 戦略統計
            strategy_stats = self.strategy.get_statistics()
            
            return {
                'fold_id': fold_id,
                'trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'total_return': total_return,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe_ratio,
                'final_balance': current_balance,
                'avg_trade_pnl': sum(t['pnl'] for t in trades) / len(trades),
                'strategy_stats': strategy_stats,
                'trades_detail': trades[:10]  # 最初の10取引のみ保存
            }
            
        except Exception as e:
            print(f"   ⚠️ フォールド{fold_id}エラー: {e}")
            return None
    
    def _generate_simple_signal(self, historical_data: List, current_time: datetime) -> Dict:
        """簡易シグナル生成"""
        try:
            if len(historical_data) < 50:
                return None
            
            # 現在価格
            current_bar = historical_data[-1]
            if isinstance(current_bar, dict):
                current_price = current_bar['close']
            else:
                current_price = current_bar.close
            
            # 簡易ブレイクアウト判定
            lookback = 24
            if len(historical_data) < lookback + 1:
                return None
            
            # 価格データ取得
            highs = []
            lows = []
            
            for bar in historical_data[-lookback-1:-1]:
                if isinstance(bar, dict):
                    highs.append(bar['high'])
                    lows.append(bar['low'])
                else:
                    highs.append(bar.high)
                    lows.append(bar.low)
            
            if not highs or not lows:
                return None
            
            resistance = max(highs)
            support = min(lows)
            
            base_signal = None
            
            if current_price > resistance:
                base_signal = {
                    'action': 'BUY',
                    'price': current_price,
                    'timestamp': current_time
                }
            elif current_price < support:
                base_signal = {
                    'action': 'SELL',
                    'price': current_price,
                    'timestamp': current_time
                }
            
            if not base_signal:
                return None
            
            # フィルタリング適用
            self.strategy.signals_generated += 1
            
            # ATRフィルター
            atr_passed, atr_multiple = self.strategy._check_atr_filter(historical_data, base_signal)
            if not atr_passed:
                self.strategy.signals_filtered_atr += 1
                return None
            
            # トレンドフィルター
            trend_passed, trend_strength = self.strategy._check_trend_filter(historical_data, base_signal)
            if not trend_passed:
                self.strategy.signals_filtered_trend += 1
                return None
            
            # 利益フィルター
            profit_passed, expected_profit = self.strategy._check_profit_filter(historical_data, base_signal)
            if not profit_passed:
                self.strategy.signals_filtered_profit += 1
                return None
            
            # 承認
            self.strategy.signals_approved += 1
            
            # ストップ・利確計算
            stop_loss, take_profit = self.strategy._calculate_optimized_levels(
                historical_data, base_signal, expected_profit
            )
            
            return {
                'action': base_signal['action'],
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': current_time,
                'atr_multiple': atr_multiple,
                'trend_strength': trend_strength,
                'expected_profit': expected_profit
            }
            
        except Exception as e:
            return None
    
    def _execute_simple_trade(self, signal: Dict, future_data: List) -> Dict:
        """簡易取引実行"""
        try:
            if not future_data or len(future_data) < 5:
                return None
            
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            direction = signal['action']
            
            for i, bar in enumerate(future_data[:48]):  # 最大48時間保有
                
                # バーデータアクセス
                if isinstance(bar, dict):
                    bar_low = bar['low']
                    bar_high = bar['high']
                    bar_close = bar['close']
                    bar_time = bar['datetime']
                else:
                    bar_low = bar.low
                    bar_high = bar.high
                    bar_close = bar.close
                    bar_time = bar.datetime
                
                if direction == 'BUY':
                    if bar_low <= stop_loss:
                        # ストップロス
                        exit_price = stop_loss
                        pnl = (exit_price - entry_price) * 100000  # 1ロット
                        return {
                            'entry_time': signal['timestamp'].isoformat(),
                            'exit_time': bar_time.isoformat(),
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'STOP_LOSS',
                            'holding_hours': i + 1
                        }
                    elif bar_high >= take_profit:
                        # 利確
                        exit_price = take_profit
                        pnl = (exit_price - entry_price) * 100000
                        return {
                            'entry_time': signal['timestamp'].isoformat(),
                            'exit_time': bar_time.isoformat(),
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'TAKE_PROFIT',
                            'holding_hours': i + 1
                        }
                else:  # SELL
                    if bar_high >= stop_loss:
                        # ストップロス
                        exit_price = stop_loss
                        pnl = (entry_price - exit_price) * 100000
                        return {
                            'entry_time': signal['timestamp'].isoformat(),
                            'exit_time': bar_time.isoformat(),
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'STOP_LOSS',
                            'holding_hours': i + 1
                        }
                    elif bar_low <= take_profit:
                        # 利確
                        exit_price = take_profit
                        pnl = (entry_price - exit_price) * 100000
                        return {
                            'entry_time': signal['timestamp'].isoformat(),
                            'exit_time': bar_time.isoformat(),
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': 'TAKE_PROFIT',
                            'holding_hours': i + 1
                        }
            
            # 時間切れ決済
            last_bar = future_data[-1]
            if isinstance(last_bar, dict):
                exit_price = last_bar['close']
                last_bar_time = last_bar['datetime']
            else:
                exit_price = last_bar.close
                last_bar_time = last_bar.datetime
            
            if direction == 'BUY':
                pnl = (exit_price - entry_price) * 100000
            else:
                pnl = (entry_price - exit_price) * 100000
            
            return {
                'entry_time': signal['timestamp'].isoformat(),
                'exit_time': last_bar_time.isoformat(),
                'direction': direction,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'exit_reason': 'TIME_EXIT',
                'holding_hours': len(future_data)
            }
            
        except Exception as e:
            return None
    
    def _analyze_wfa_results(self, wfa_results: List) -> Dict:
        """WFA結果分析"""
        if not wfa_results:
            return {'error': 'No valid results'}
        
        # 基本統計
        profit_factors = [r['profit_factor'] for r in wfa_results]
        returns = [r['total_return'] for r in wfa_results]
        win_rates = [r['win_rate'] for r in wfa_results]
        sharpe_ratios = [r['sharpe_ratio'] for r in wfa_results]
        
        # 統計的検定準備
        positive_folds = len([r for r in returns if r > 0])
        profitable_folds = len([pf for pf in profit_factors if pf > 1.0])
        
        # 簡易p値計算（二項検定の近似）
        import math
        n = len(returns)
        k = positive_folds
        p_value = 0.5 ** n * sum(math.comb(n, i) for i in range(k, n+1))
        
        # t統計量の簡易計算
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            t_stat = mean_return / (std_return / math.sqrt(len(returns))) if std_return > 0 else 0
        else:
            t_stat = 0
        
        analysis = {
            'total_folds': len(wfa_results),
            'positive_folds': positive_folds,
            'profitable_folds': profitable_folds,
            'statistics': {
                'avg_profit_factor': np.mean(profit_factors),
                'std_profit_factor': np.std(profit_factors),
                'avg_return': np.mean(returns),
                'std_return': np.std(returns),
                'avg_win_rate': np.mean(win_rates),
                'avg_sharpe_ratio': np.mean(sharpe_ratios)
            },
            'statistical_tests': {
                'binomial_p_value': p_value,
                't_statistic': t_stat,
                'is_significant_5pct': p_value < 0.05,
                'is_significant_1pct': p_value < 0.01
            },
            'fold_consistency': {
                'min_profit_factor': min(profit_factors),
                'max_profit_factor': max(profit_factors),
                'profit_factor_range': max(profit_factors) - min(profit_factors),
                'folds_with_pf_above_1': profitable_folds,
                'consistency_ratio': profitable_folds / len(wfa_results)
            }
        }
        
        return analysis

def main():
    """メイン実行"""
    print("🛡️ コスト耐性戦略WFA実行開始")
    
    executor = CostResistantWFAExecution()
    results = executor.execute_cost_resistant_wfa()
    
    if results and 'analysis' in results:
        analysis = results['analysis']
        
        print(f"\n📊 WFA実行結果:")
        print(f"   実行フォールド数: {analysis['total_folds']}")
        print(f"   プラスフォールド: {analysis['positive_folds']}/{analysis['total_folds']}")
        print(f"   PF>1.0フォールド: {analysis['profitable_folds']}/{analysis['total_folds']}")
        print(f"   平均PF: {analysis['statistics']['avg_profit_factor']:.3f}")
        print(f"   平均リターン: {analysis['statistics']['avg_return']:.3f}")
        print(f"   統計的有意性: p={analysis['statistical_tests']['binomial_p_value']:.4f}")
        
        if analysis['statistical_tests']['is_significant_5pct']:
            print(f"   ✅ 5%水準で統計的有意")
        else:
            print(f"   ❌ 統計的有意性なし")
    
    print(f"\n🎯 コスト耐性戦略WFA完了")

if __name__ == "__main__":
    main()