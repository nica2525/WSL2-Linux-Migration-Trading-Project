#!/usr/bin/env python3
"""
統合WFA戦略システム
最小実行可能戦略とPurged & Embargoed WFAの統合実装
"""

import math
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class MinimalViableStrategy:
    """最小実行可能戦略（時間的ブレイクアウト）"""
    
    def __init__(self, params=None):
        """
        初期化
        
        Args:
            params: パラメータ辞書 {'break_pips': 20, 'profit_pips': 30, 'stop_pips': 20}
        """
        self.params = params or {
            'break_pips': 20,
            'profit_pips': 30,
            'stop_pips': 20
        }
        
    def is_trade_time(self, dt):
        """取引時間判定（日本時間09:00-11:00）"""
        hour = dt.hour
        return 9 <= hour < 11
    
    def get_previous_day_range(self, data, current_idx):
        """前日高値・安値の取得"""
        if current_idx < 1:
            return None, None
            
        # 前日のデータを検索（簡易実装）
        current_date = data[current_idx]['datetime'].date()
        prev_date = current_date - timedelta(days=1)
        
        # 前日のデータを検索
        prev_day_bars = []
        for i in range(max(0, current_idx - 300), current_idx):  # 最大300バー遡る
            if data[i]['datetime'].date() == prev_date:
                prev_day_bars.append(data[i])
        
        if not prev_day_bars:
            return None, None
            
        prev_high = max(bar['high'] for bar in prev_day_bars)
        prev_low = min(bar['low'] for bar in prev_day_bars)
        
        return prev_high, prev_low
    
    def generate_signals(self, data, start_idx=0, end_idx=None):
        """
        シグナル生成（バックテスト用）
        
        Args:
            data: OHLC時系列データ
            start_idx: 開始インデックス
            end_idx: 終了インデックス
        
        Returns:
            list: シグナルリスト
        """
        if end_idx is None:
            end_idx = len(data)
            
        signals = []
        
        for i in range(start_idx, end_idx):
            current_bar = data[i]
            
            # 取引時間チェック
            if not self.is_trade_time(current_bar['datetime']):
                continue
                
            # 前日高値・安値取得
            prev_high, prev_low = self.get_previous_day_range(data, i)
            if prev_high is None or prev_low is None:
                continue
            
            # ブレイクアウト判定（Look-ahead bias修正）
            break_pips = self.params['break_pips'] * 0.0001
            current_high = current_bar['high']
            current_low = current_bar['low']
            
            signal = None
            
            # ロングシグナル（高値がブレイクアウトレベルを超えた場合）
            if current_high > prev_high + break_pips:
                # エントリー価格はブレイクアウトレベル（実現可能な価格）
                entry_price = prev_high + break_pips
                signal = {
                    'type': 'long',
                    'datetime': current_bar['datetime'],
                    'entry_price': entry_price,
                    'profit_target': entry_price + self.params['profit_pips'] * 0.0001,
                    'stop_loss': entry_price - self.params['stop_pips'] * 0.0001,
                    'prev_high': prev_high,
                    'prev_low': prev_low
                }
            
            # ショートシグナル（安値がブレイクアウトレベルを下回った場合）
            elif current_low < prev_low - break_pips:
                # エントリー価格はブレイクアウトレベル（実現可能な価格）
                entry_price = prev_low - break_pips
                signal = {
                    'type': 'short',
                    'datetime': current_bar['datetime'],
                    'entry_price': entry_price,
                    'profit_target': entry_price - self.params['profit_pips'] * 0.0001,
                    'stop_loss': entry_price + self.params['stop_pips'] * 0.0001,
                    'prev_high': prev_high,
                    'prev_low': prev_low
                }
            
            if signal:
                signals.append(signal)
                
        return signals
    
    def backtest(self, data, start_idx=0, end_idx=None):
        """
        バックテスト実行
        
        Args:
            data: OHLC時系列データ
            start_idx: 開始インデックス
            end_idx: 終了インデックス
            
        Returns:
            dict: バックテスト結果
        """
        signals = self.generate_signals(data, start_idx, end_idx)
        
        trades = []
        for signal_idx, signal in enumerate(signals):
            # 実際の価格追跡による取引結果計算
            exit_price, result = self._track_trade_outcome(signal, data, start_idx, end_idx)
            
            # PnL計算
            if signal['type'] == 'long':
                pnl = exit_price - signal['entry_price']
            else:  # short
                pnl = signal['entry_price'] - exit_price
            
            trades.append({
                'datetime': signal['datetime'],
                'type': signal['type'],
                'entry_price': signal['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'result': result
            })
        
        # パフォーマンス計算
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade['result'] == 'win')
        win_rate = winning_trades / total_trades
        
        gross_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
        gross_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] < 0))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        total_pnl = sum(trade['pnl'] for trade in trades)
        
        # 簡易的なドローダウン計算
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            cumulative_pnl += trade['pnl']
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # シャープレシオ計算
        returns = [trade['pnl'] for trade in trades]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_return = math.sqrt(variance) if variance > 0 else 0
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'trades': trades
        }
    
    def _track_trade_outcome(self, signal, data, start_idx, end_idx):
        """
        実際の価格追跡による取引結果計算
        
        Args:
            signal: 取引シグナル
            data: OHLC時系列データ
            start_idx: 開始インデックス
            end_idx: 終了インデックス
            
        Returns:
            tuple: (exit_price, result)
        """
        if end_idx is None:
            end_idx = len(data)
            
        signal_time = signal['datetime']
        signal_type = signal['type']
        entry_price = signal['entry_price']
        profit_target = signal['profit_target']
        stop_loss = signal['stop_loss']
        
        # シグナル発生時のインデックスを検索
        signal_idx = None
        for i in range(start_idx, end_idx):
            if i < len(data) and data[i]['datetime'] >= signal_time:
                signal_idx = i
                break
        
        if signal_idx is None:
            # シグナルが見つからない場合は小さな損失で終了
            return entry_price - 0.0001, 'loss'
        
        # シグナル後の価格を追跡
        for i in range(signal_idx + 1, min(signal_idx + 100, end_idx)):
            if i >= len(data):
                break
                
            current_bar = data[i]
            high = current_bar['high']
            low = current_bar['low']
            
            if signal_type == 'long':
                # ロングポジション
                if high >= profit_target:
                    # 利確達成
                    return profit_target, 'win'
                elif low <= stop_loss:
                    # ストップロス到達
                    return stop_loss, 'loss'
            else:
                # ショートポジション
                if low <= profit_target:
                    # 利確達成
                    return profit_target, 'win'
                elif high >= stop_loss:
                    # ストップロス到達
                    return stop_loss, 'loss'
        
        # 追跡期間内に決着がつかない場合はエントリー価格で決済
        return entry_price, 'timeout'

class IntegratedWFASystem:
    """統合WFAシステム"""
    
    def __init__(self, data, wfa_config, strategy_params):
        """
        初期化
        
        Args:
            data: 時系列データ
            wfa_config: WFA設定
            strategy_params: 戦略パラメータ
        """
        from wfa_prototype import TimeSeriesData, WFAConfig, PurgedEmbargoedWFA
        
        self.data = TimeSeriesData(data) if not isinstance(data, TimeSeriesData) else data
        self.wfa_config = wfa_config
        self.strategy_params = strategy_params
        
        # WFA設定
        strategy_config = {
            'ma_periods': [20],  # 最小限の設定
            'timeframe': 'M5',
            'other_periods': []
        }
        
        # WFAエンジン初期化
        self.wfa_engine = PurgedEmbargoedWFA(
            self.data.data, 
            wfa_config, 
            strategy_config
        )
        
        # 戦略インスタンス
        self.strategy = MinimalViableStrategy(strategy_params)
        
    def run_full_wfa(self):
        """完全WFA実行"""
        print("🚀 統合WFA実行開始")
        
        # フォールド生成
        folds = self.wfa_engine.generate_folds()
        
        results = []
        
        for fold_idx, fold in enumerate(folds, 1):
            print(f"\n📊 フォールド {fold_idx}/{len(folds)} 処理中...")
            
            # フォールドデータ取得
            fold_data = self.wfa_engine.get_fold_data(fold_idx)
            
            is_data = fold_data['is_data']
            oos_data = fold_data['oos_data']
            
            print(f"   IS期間: {len(is_data)}バー")
            print(f"   OOS期間: {len(oos_data)}バー")
            
            # IS期間でのパラメータ最適化（簡易実装）
            best_params = self.optimize_parameters(is_data)
            print(f"   最適パラメータ: {best_params}")
            
            # 最適パラメータでIS期間の性能確認
            optimized_strategy = MinimalViableStrategy(best_params)
            is_result = optimized_strategy.backtest(is_data)
            
            # OOS期間での検証
            oos_result = optimized_strategy.backtest(oos_data)
            
            # 結果記録
            fold_result = {
                'fold_id': fold_idx,
                'fold_info': fold,
                'optimized_params': best_params,
                'is_performance': is_result,
                'oos_performance': oos_result,
                'is_return': is_result['total_pnl'],
                'oos_return': oos_result['total_pnl'],
                'oos_sharpe': oos_result['sharpe_ratio'],
                'oos_pf': oos_result['profit_factor'],
                'trades': oos_result['total_trades']
            }
            
            results.append(fold_result)
            
            print(f"   IS PF: {is_result['profit_factor']:.3f}")
            print(f"   OOS PF: {oos_result['profit_factor']:.3f}")
            print(f"   取引数: {oos_result['total_trades']}")
        
        return results
    
    def optimize_parameters(self, data):
        """パラメータ最適化（グリッドサーチ）"""
        
        # パラメータ範囲
        break_pips_range = [15, 20, 25]
        profit_pips_range = [25, 30, 35]
        stop_pips_range = [15, 20, 25]
        
        best_params = None
        best_score = -999999
        
        # グリッドサーチ
        for break_pips in break_pips_range:
            for profit_pips in profit_pips_range:
                for stop_pips in stop_pips_range:
                    
                    params = {
                        'break_pips': break_pips,
                        'profit_pips': profit_pips,
                        'stop_pips': stop_pips
                    }
                    
                    strategy = MinimalViableStrategy(params)
                    result = strategy.backtest(data)
                    
                    # スコア計算（プロフィットファクター基準）
                    score = result['profit_factor']
                    
                    if score > best_score and result['total_trades'] >= 10:
                        best_score = score
                        best_params = params
        
        return best_params or self.strategy_params
    
    def generate_report(self, results):
        """WFAレポート生成"""
        from wfa_prototype import StatisticalValidator
        
        print("\n📈 WFA結果レポート生成")
        
        # 統計的検証
        validator = StatisticalValidator(results)
        consistency = validator.calculate_oos_consistency()
        wfa_efficiency = validator.calculate_wfa_efficiency()
        
        # 基本統計
        total_folds = len(results)
        positive_folds = sum(1 for r in results if r['oos_return'] > 0)
        consistency_ratio = positive_folds / total_folds if total_folds > 0 else 0
        
        # 平均パフォーマンス
        if results:
            avg_oos_pf = sum(r['oos_pf'] for r in results) / len(results)
            avg_oos_trades = sum(r['trades'] for r in results) / len(results)
        else:
            avg_oos_pf = 0
            avg_oos_trades = 0
        
        report = {
            'summary': {
                'total_folds': total_folds,
                'positive_folds': positive_folds,
                'consistency_ratio': consistency_ratio,
                'avg_oos_pf': avg_oos_pf,
                'avg_oos_trades': avg_oos_trades,
                'wfa_efficiency': wfa_efficiency,
                'statistical_significance': consistency.get('is_significant', False),
                'p_value': consistency.get('p_value', 1.0)
            },
            'detailed_results': results,
            'statistical_tests': consistency
        }
        
        # レポート表示
        print(f"\n🎯 WFA結果サマリー:")
        print(f"   総フォールド数: {total_folds}")
        print(f"   正の結果: {positive_folds}/{total_folds} ({consistency_ratio:.1%})")
        print(f"   平均OOS PF: {avg_oos_pf:.3f}")
        print(f"   平均取引数: {avg_oos_trades:.0f}")
        print(f"   WFA効率: {wfa_efficiency:.3f}")
        print(f"   統計的有意性: {'あり' if consistency.get('is_significant') else 'なし'}")
        print(f"   p値: {consistency.get('p_value', 1.0):.4f}")
        
        # 判定結果
        if consistency.get('is_significant') and avg_oos_pf >= 1.1:
            print(f"\n✅ 戦略合格: 統計的優位性確認")
        else:
            print(f"\n❌ 戦略不合格: 統計的優位性未確認")
        
        return report

def create_sample_data():
    """サンプルデータ生成（テスト用）"""
    import random
    
    base_date = datetime(2020, 1, 1)
    data = []
    
    # 5年間のM5データを疑似生成
    current_date = base_date
    price = 1.1000
    
    for i in range(200000):  # 約4年分（フォールド生成に十分）
        # 価格をランダムウォーク
        price += random.gauss(0, 0.0001)
        price = max(0.9000, min(1.3000, price))
        
        data.append({
            'datetime': current_date,
            'open': price,
            'high': price + random.uniform(0, 0.0005),
            'low': price - random.uniform(0, 0.0005),
            'close': price + random.gauss(0, 0.0002),
            'volume': random.randint(50, 200)
        })
        
        current_date += timedelta(minutes=5)
        
        # 週末はスキップ
        if current_date.weekday() >= 5:
            current_date += timedelta(days=2)
    
    return data

def main():
    """メイン実行関数"""
    print("🚀 統合WFA戦略システム実行開始")
    
    # サンプルデータ生成
    print("📊 サンプルデータ生成中...")
    data = create_sample_data()
    print(f"   生成データ数: {len(data)}バー")
    
    # WFA設定
    from wfa_prototype import WFAConfig
    wfa_config = WFAConfig(
        is_months=24,      # IS期間24ヶ月
        oos_months=6,      # OOS期間6ヶ月
        step_months=6,     # 6ヶ月ステップ
        anchored=True      # アンカード方式
    )
    
    # 戦略パラメータ
    strategy_params = {
        'break_pips': 20,
        'profit_pips': 30,
        'stop_pips': 20
    }
    
    # 統合WFAシステム初期化
    wfa_system = IntegratedWFASystem(data, wfa_config, strategy_params)
    
    # 完全WFA実行
    results = wfa_system.run_full_wfa()
    
    # レポート生成
    report = wfa_system.generate_report(results)
    
    print(f"\n✅ 統合WFA実行完了！")
    print(f"   フェーズ2-1: WFA実装と戦略統合完了")
    print(f"   次のステップ: 統計的検証と合格判定")
    
    return wfa_system, results, report

if __name__ == "__main__":
    system, results, report = main()