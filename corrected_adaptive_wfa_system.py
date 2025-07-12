#!/usr/bin/env python3
"""
WFA原則遵守 環境適応型システム (Gemini査読修正版)
作成日時: 2025-07-12 21:55 JST

Gemini指摘の致命的問題修正:
1. Look-ahead Bias完全排除
2. WFA各フォールドでの独立最適化
3. テスト期間データの完全分離
4. 実際のバックテスト結果使用
5. フォールド3特化排除
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from scipy import stats
from scipy.optimize import differential_evolution

from data_cache_system import DataCacheManager
from cost_resistant_strategy import CostResistantStrategy
from market_regime_detector import MarketRegimeDetector, MarketRegime

class WFACompliantOptimizer:
    """
    WFA原則遵守最適化器
    - 学習期間データのみ使用
    - テスト期間データ完全遮断
    - 実際のバックテスト評価
    """
    
    def __init__(self, learning_data: pd.DataFrame):
        self.learning_data = learning_data
        self.base_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,
            'stop_atr': 1.3,
            'min_break_pips': 5,
            'spread_pips': 1.5,
            'commission_pips': 0.3
        }
        
        # WFA原則遵守パラメータ範囲
        self.param_ranges = [
            (0.0001, 0.001),   # volatility_threshold_low
            (0.001, 0.003),    # volatility_threshold_high
            (0.1, 1.0),        # trend_strength_threshold
            (0.1, 0.8),        # range_efficiency_threshold
            (10, 30),          # atr_period
            (15, 40),          # range_period
            (30, 100)          # trend_period
        ]
    
    def execute_backtest_with_regime(self, detector_params: List[float]) -> Dict:
        """学習期間データのみでバックテスト実行"""
        try:
            # レジーム検出器作成
            detector = MarketRegimeDetector()
            detector.volatility_threshold_low = detector_params[0]
            detector.volatility_threshold_high = detector_params[1]
            detector.trend_strength_threshold = detector_params[2]
            detector.range_efficiency_threshold = detector_params[3]
            detector.atr_period = int(detector_params[4])
            detector.range_period = int(detector_params[5])
            detector.trend_period = int(detector_params[6])
            
            # レジーム検出実行
            regimes = detector.detect_regime(self.learning_data)
            
            # 適応型バックテスト実行
            return self._execute_adaptive_backtest(detector, regimes)
            
        except Exception as e:
            print(f"⚠️ バックテストエラー: {e}")
            return {'profit_factor': 0.1, 'sharpe_ratio': -999}
    
    def _execute_adaptive_backtest(self, detector: MarketRegimeDetector, 
                                 regimes: pd.Series) -> Dict:
        """環境適応型バックテスト（学習期間のみ）"""
        trades = []
        balance = 100000
        position = None
        
        for i in range(len(self.learning_data)):
            if i >= len(regimes):
                break
                
            current_bar = self.learning_data.iloc[i]
            current_regime = regimes.iloc[i]
            
            # レジーム別パラメータ取得
            regime_params = detector.get_strategy_parameters(current_regime)
            
            # 取引停止判定
            if not regime_params['active']:
                if position is not None:
                    # 強制決済
                    pnl = self._calculate_pnl(position, current_bar['close'])
                    balance += pnl
                    trades.append({
                        'pnl': pnl,
                        'exit_reason': 'REGIME_STOP'
                    })
                    position = None
                continue
            
            # 動的パラメータで戦略作成
            adaptive_params = self.base_params.copy()
            adaptive_params.update({
                'profit_atr': regime_params['profit_atr'],
                'stop_atr': regime_params['stop_atr'],
                'min_break_pips': regime_params['min_break_pips']
            })
            
            strategy = CostResistantStrategy(adaptive_params)
            
            # 過去データのみでシグナル生成（Look-ahead防止）
            signal = strategy.generate_signal(self.learning_data.iloc[:i+1])
            
            # ポジション管理
            if position is None and signal != 'HOLD':
                position = {
                    'direction': signal,
                    'entry_price': current_bar['close'],
                    'entry_time': current_bar.name,
                    'stop_loss': strategy.calculate_stop_loss(current_bar['close'], signal),
                    'take_profit': strategy.calculate_take_profit(current_bar['close'], signal),
                    'position_size': regime_params['position_size']
                }
            
            elif position is not None:
                # 決済判定
                exit_signal, exit_reason = strategy.check_exit_conditions(
                    position, current_bar, self.learning_data.iloc[:i+1]
                )
                
                if exit_signal:
                    pnl = self._calculate_pnl(position, current_bar['close'])
                    adjusted_pnl = pnl * position['position_size']
                    balance += adjusted_pnl
                    
                    trades.append({
                        'pnl': adjusted_pnl,
                        'exit_reason': exit_reason
                    })
                    
                    position = None
        
        # パフォーマンス計算
        if not trades:
            return {'profit_factor': 1.0, 'sharpe_ratio': 0.0, 'total_trades': 0}
        
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 2.0
        
        # シャープレシオ計算
        pnl_series = np.array([t['pnl'] for t in trades])
        sharpe_ratio = np.mean(pnl_series) / np.std(pnl_series) if np.std(pnl_series) > 0 else 0
        
        return {
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(trades),
            'win_rate': len(winning_trades) / len(trades)
        }
    
    def _calculate_pnl(self, position: Dict, exit_price: float) -> float:
        """PnL計算"""
        if position['direction'] == 'BUY':
            return (exit_price - position['entry_price']) * 10000
        else:
            return (position['entry_price'] - exit_price) * 10000
    
    def objective_function(self, params: List[float]) -> float:
        """WFA準拠目的関数（汎用的パフォーマンス指標）"""
        result = self.execute_backtest_with_regime(params)
        
        # 汎用的複合スコア（フォールド特化なし）
        pf = result['profit_factor']
        sharpe = result['sharpe_ratio']
        trades = result['total_trades']
        
        # 取引数不足ペナルティ
        trade_penalty = 1.0 if trades >= 50 else trades / 50.0
        
        # PF重視、シャープレシオ補正、取引数確保
        score = (
            np.log(max(pf, 0.1)) * 0.6 +     # PF（対数変換で安定化）
            max(sharpe, -2.0) * 0.3 +        # シャープレシオ
            trade_penalty * 0.1              # 取引数確保
        )
        
        return -score  # 最小化問題なので符号反転
    
    def optimize(self, max_iterations: int = 50) -> Tuple[List[float], float]:
        """学習期間データのみで最適化"""
        print(f"   🧬 学習期間最適化実行（データ数: {len(self.learning_data)}バー）")
        
        result = differential_evolution(
            self.objective_function,
            self.param_ranges,
            maxiter=max_iterations,
            popsize=15,
            seed=42,
            disp=False
        )
        
        best_score = -result.fun  # 符号を戻す
        print(f"   ✅ 最適化完了（スコア: {best_score:.4f}）")
        
        return result.x, best_score

class CorrectedAdaptiveWFASystem:
    """
    修正版環境適応型WFAシステム
    - WFA原則完全遵守
    - Look-ahead Bias完全排除
    - 各フォールドで独立最適化
    """
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
        # WFAフォールド設定（学習:テスト = 3:1比率）
        self.wfa_config = [
            {
                'fold_id': 1,
                'learning_period': ('2019-01-01', '2019-10-01'),
                'test_period': ('2019-10-01', '2020-01-01')
            },
            {
                'fold_id': 2,
                'learning_period': ('2019-04-01', '2020-01-01'),
                'test_period': ('2020-01-01', '2020-04-01')
            },
            {
                'fold_id': 3,
                'learning_period': ('2019-07-01', '2021-01-01'),
                'test_period': ('2021-01-01', '2021-07-01')
            },
            {
                'fold_id': 4,
                'learning_period': ('2020-01-01', '2022-01-01'),
                'test_period': ('2022-01-01', '2022-07-01')
            },
            {
                'fold_id': 5,
                'learning_period': ('2020-07-01', '2023-01-01'),
                'test_period': ('2023-01-01', '2023-07-01')
            }
        ]
        
        self.results = {'corrected_wfa': [], 'summary': None}
    
    def load_market_data(self) -> pd.DataFrame:
        """市場データ読み込み"""
        print("📊 市場データ読み込み中...")
        raw_data = self.cache_manager.load_cached_data()
        
        data = pd.DataFrame(raw_data)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        
        print(f"   データ期間: {data.index[0]} 〜 {data.index[-1]}")
        return data
    
    def extract_period_data(self, data: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        """期間データ抽出"""
        mask = (data.index >= start) & (data.index < end)
        return data[mask].copy()
    
    def run_corrected_wfa(self) -> Dict:
        """修正版WFA実行"""
        print("🛡️ WFA原則遵守 環境適応型分析開始")
        print(f"⏰ 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')}")
        
        # データ読み込み
        data = self.load_market_data()
        fold_results = []
        
        for fold_config in self.wfa_config:
            fold_id = fold_config['fold_id']
            print(f"\n📈 フォールド {fold_id} 実行中...")
            
            # 学習期間・テスト期間データ抽出
            learning_data = self.extract_period_data(
                data, fold_config['learning_period'][0], fold_config['learning_period'][1]
            )
            test_data = self.extract_period_data(
                data, fold_config['test_period'][0], fold_config['test_period'][1]
            )
            
            if len(learning_data) == 0 or len(test_data) == 0:
                print(f"   ⚠️ フォールド {fold_id}: データ不足")
                continue
            
            print(f"   学習期間: {len(learning_data)}バー ({fold_config['learning_period']})")
            print(f"   テスト期間: {len(test_data)}バー ({fold_config['test_period']})")
            
            # 学習期間のみで最適化
            optimizer = WFACompliantOptimizer(learning_data)
            best_params, learning_score = optimizer.optimize()
            
            # 最適化されたパラメータでテスト期間評価
            test_result = self._evaluate_on_test_period(best_params, test_data)
            
            fold_result = {
                'fold_id': fold_id,
                'learning_score': learning_score,
                'test_pf': test_result['profit_factor'],
                'test_trades': test_result['total_trades'],
                'test_win_rate': test_result['win_rate'],
                'optimized_params': best_params.tolist(),
                'periods': fold_config
            }
            
            fold_results.append(fold_result)
            print(f"   ✅ フォールド {fold_id} 完了")
            print(f"      学習スコア: {learning_score:.4f}")
            print(f"      テストPF: {test_result['profit_factor']:.3f}")
            print(f"      テスト取引数: {test_result['total_trades']}")
        
        # 統計的有意性計算
        test_pf_values = [r['test_pf'] for r in fold_results]
        p_value = self._calculate_statistical_significance(test_pf_values)
        
        summary = {
            'total_folds': len(fold_results),
            'avg_test_pf': np.mean(test_pf_values),
            'std_test_pf': np.std(test_pf_values),
            'positive_folds': sum(1 for pf in test_pf_values if pf > 1.0),
            'p_value': p_value,
            'statistical_significance': p_value < 0.05
        }
        
        self.results = {
            'corrected_wfa': fold_results,
            'summary': summary
        }
        
        print(f"\n🎯 WFA原則遵守分析完了:")
        print(f"   平均テストPF: {summary['avg_test_pf']:.3f}")
        print(f"   p値: {summary['p_value']:.4f}")
        print(f"   統計的有意性: {summary['statistical_significance']}")
        print(f"   プラスフォールド: {summary['positive_folds']}/{summary['total_folds']}")
        
        return self.results
    
    def _evaluate_on_test_period(self, params: np.ndarray, test_data: pd.DataFrame) -> Dict:
        """テスト期間での評価（パラメータ固定）"""
        optimizer = WFACompliantOptimizer(test_data)
        return optimizer.execute_backtest_with_regime(params.tolist())
    
    def _calculate_statistical_significance(self, pf_values: List[float]) -> float:
        """統計的有意性計算"""
        if len(pf_values) < 2:
            return 1.0
        
        # H0: PF = 1.0 vs H1: PF > 1.0
        t_stat, p_value = stats.ttest_1samp(pf_values, 1.0)
        one_tailed_p = p_value / 2 if t_stat > 0 else 1.0 - (p_value / 2)
        
        return one_tailed_p
    
    def save_results(self):
        """結果保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'corrected_adaptive_wfa_results_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"💾 修正版結果保存: {filename}")

if __name__ == "__main__":
    print("🛡️ WFA原則遵守 環境適応型システム")
    print("作成日時: 2025-07-12 21:55 JST")
    print("Gemini査読修正版 - Look-ahead Bias完全排除")
    
    system = CorrectedAdaptiveWFASystem()
    results = system.run_corrected_wfa()
    system.save_results()
    
    if 'summary' in results and results['summary']:
        summary = results['summary']
        print(f"\n🎊 最終結果:")
        print(f"   統計的有意性達成: {summary['statistical_significance']}")
        print(f"   p値: {summary['p_value']:.4f}")
        print(f"   平均PF: {summary['avg_test_pf']:.3f}")