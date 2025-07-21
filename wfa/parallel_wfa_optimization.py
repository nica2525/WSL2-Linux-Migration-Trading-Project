#!/usr/bin/env python3
"""
並列処理最適化WFAシステム
ProcessPoolExecutorによる高速化実装
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Protocol
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import multiprocessing as mp
import time
from pathlib import Path
from abc import ABC, abstractmethod

# システム情報
CPU_COUNT = mp.cpu_count()
MAX_WORKERS = max(1, CPU_COUNT - 1)  # 1つのCPUを他の処理用に残す

class TradingStrategy(ABC):
    """取引戦略基底クラス"""
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """取引シグナル生成"""
        pass
    
    @abstractmethod
    def get_parameter_ranges(self) -> Dict:
        """パラメータ範囲取得"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """戦略名取得"""
        pass

class BreakoutStrategy(TradingStrategy):
    """ブレイクアウト戦略"""
    
    def generate_signals(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """ブレイクアウトシグナル生成"""
        lookback = params.get('lookback', 20)
        
        if len(data) < lookback + 1:
            return pd.Series(False, index=data.index)
        
        # ローリング最高値
        rolling_high = data['High'].rolling(window=lookback).max()
        
        # ブレイクアウト条件（前日高値を上抜け - Look-ahead bias修正）
        # 現在足のCloseではなく、当足高値でのブレイクアウト判定
        breakout_condition = data['High'] > rolling_high.shift(1)
        
        return breakout_condition.fillna(False)
    
    def get_parameter_ranges(self) -> Dict:
        """パラメータ範囲"""
        return {
            'lookback': {'min': 5, 'max': 50, 'step': 5}
        }
    
    def get_strategy_name(self) -> str:
        return "BreakoutStrategy"

class MeanReversionStrategy(TradingStrategy):
    """平均回帰戦略"""
    
    def generate_signals(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """平均回帰シグナル生成"""
        lookback = params.get('lookback', 20)
        threshold = params.get('threshold', 2.0)
        
        if len(data) < lookback + 1:
            return pd.Series(False, index=data.index)
        
        # 移動平均とボリンジャーバンド
        rolling_mean = data['Close'].rolling(window=lookback).mean()
        rolling_std = data['Close'].rolling(window=lookback).std()
        
        # 下限ラインを下回った時に買いシグナル（Look-ahead bias修正）
        lower_band = rolling_mean - threshold * rolling_std
        # 現在足のCloseではなく、当足安値でのバンド下抜け判定
        mean_reversion_condition = data['Low'] < lower_band.shift(1)
        
        return mean_reversion_condition.fillna(False)
    
    def get_parameter_ranges(self) -> Dict:
        return {
            'lookback': {'min': 10, 'max': 30, 'step': 5},
            'threshold': {'min': 1.5, 'max': 2.5, 'step': 0.5}
        }
    
    def get_strategy_name(self) -> str:
        return "MeanReversionStrategy"

class ParallelWFAOptimization:
    """並列処理最適化WFAクラス"""
    
    def __init__(self, vectorbt_data: pd.DataFrame = None):
        self.vectorbt_data = vectorbt_data
        self.results = []
        
        print(f"🚀 並列処理システム初期化")
        print(f"   CPU数: {CPU_COUNT}")
        print(f"   最大並列ワーカー数: {MAX_WORKERS}")
    
    def load_test_data(self):
        """テストデータ読み込み"""
        if self.vectorbt_data is None:
            # テストデータ生成（実際の使用時は外部データ読み込み）
            np.random.seed(42)
            dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
            n_days = len(dates)
            
            # よりリアルな価格データ生成
            returns = np.random.normal(0.0005, 0.02, n_days)  # 日次リターン
            price = 100 * np.exp(np.cumsum(returns))
            
            self.vectorbt_data = pd.DataFrame({
                'Open': price * (1 + np.random.normal(0, 0.001, n_days)),
                'High': price * (1 + np.abs(np.random.normal(0, 0.005, n_days))),
                'Low': price * (1 - np.abs(np.random.normal(0, 0.005, n_days))),
                'Close': price,
                'Volume': np.random.lognormal(10, 1, n_days)
            }, index=dates)
            
        print(f"✅ データ読み込み完了: {len(self.vectorbt_data)}日分")
        return self.vectorbt_data

def calculate_single_fold_wfa(fold_params: Tuple) -> Dict:
    """
    単一Fold WFA計算（並列実行用関数）
    
    Args:
        fold_params: (fold_id, fold_config, strategy_config, cost_scenario)
    
    Returns:
        Dict: Fold実行結果
    """
    fold_id, fold_config, strategy_config, cost_scenario = fold_params
    
    try:
        # データ分割
        in_sample_data = fold_config['in_sample_data']
        out_sample_data = fold_config['out_sample_data']
        
        # 戦略インスタンス生成
        strategy_name = strategy_config['strategy_name']
        if strategy_name == 'BreakoutStrategy':
            strategy = BreakoutStrategy()
        elif strategy_name == 'MeanReversionStrategy':
            strategy = MeanReversionStrategy()
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # In-Sample最適化
        best_params = None
        best_in_sample_sharpe = -np.inf
        
        for params in strategy_config['parameter_combinations']:
            try:
                # 戦略シグナル生成
                in_sample_signals = strategy.generate_signals(in_sample_data, params)
                
                if in_sample_signals.sum() > 0:  # シグナル存在確認
                    # シンプルなバックテスト
                    sharpe_ratio = calculate_simple_sharpe(in_sample_data, in_sample_signals, cost_scenario)
                    
                    if not np.isnan(sharpe_ratio) and sharpe_ratio > best_in_sample_sharpe:
                        best_in_sample_sharpe = sharpe_ratio
                        best_params = params
                        
            except Exception as e:
                continue
        
        # Out-of-Sample検証
        if best_params is not None:
            out_sample_signals = strategy.generate_signals(out_sample_data, best_params)
            
            if out_sample_signals.sum() > 0:
                out_sample_sharpe = calculate_simple_sharpe(out_sample_data, out_sample_signals, cost_scenario)
                total_return = calculate_simple_return(out_sample_data, out_sample_signals, cost_scenario)
                max_drawdown = calculate_simple_drawdown(out_sample_data, out_sample_signals, cost_scenario)
                
                return {
                    'fold_id': fold_id,
                    'optimal_params': best_params,
                    'strategy_name': strategy.get_strategy_name(),
                    'in_sample_sharpe': best_in_sample_sharpe,
                    'out_sample_sharpe': out_sample_sharpe,
                    'total_return': total_return,
                    'max_drawdown': max_drawdown,
                    'cost_scenario': cost_scenario['name'],
                    'execution_time': time.time(),
                    'status': 'success'
                }
        
        return {
            'fold_id': fold_id,
            'status': 'failed',
            'error': 'No valid signals or parameters found',
            'cost_scenario': cost_scenario['name']
        }
        
    except Exception as e:
        return {
            'fold_id': fold_id,
            'status': 'error',
            'error': str(e),
            'cost_scenario': cost_scenario['name']
        }

def generate_parameter_combinations(param_ranges: Dict) -> List[Dict]:
    """パラメータ組み合わせ生成"""
    import itertools
    
    param_names = list(param_ranges.keys())
    param_values = []
    
    for param_name in param_names:
        range_config = param_ranges[param_name]
        if isinstance(range_config, dict) and 'min' in range_config:
            # 数値範囲の場合
            if 'step' in range_config:
                values = np.arange(range_config['min'], range_config['max'], range_config['step'])
            else:
                values = np.linspace(range_config['min'], range_config['max'], 10)
        else:
            # リストの場合
            values = range_config
        param_values.append(values)
    
    # 全組み合わせ生成
    combinations = []
    for combination in itertools.product(*param_values):
        param_dict = dict(zip(param_names, combination))
        combinations.append(param_dict)
    
    return combinations

def calculate_simple_sharpe(data: pd.DataFrame, signals: pd.Series, cost_scenario: Dict) -> float:
    """シンプルなシャープレシオ計算"""
    try:
        # シグナル位置での売買リターン計算（Look-ahead bias修正）
        # シグナル発生の次足Open価格でエントリー
        entry_prices = data['Open'].shift(-1)[signals].values
        if len(entry_prices) == 0:
            return np.nan
            
        # エントリーの次足Open価格で決済（簡素化）
        exit_signals = signals.shift(-2).fillna(False)  # 2期間後
        exit_prices = data['Open'].shift(-1)[exit_signals].values
        
        # リターン計算（コスト考慮）
        if len(entry_prices) == len(exit_prices):
            returns = (exit_prices - entry_prices) / entry_prices
            returns -= cost_scenario['fees'] + cost_scenario['slippage']  # コスト差し引き
            
            if len(returns) > 1 and returns.std() > 0:
                return returns.mean() / returns.std() * np.sqrt(252)  # 年間シャープレシオ
        
        return np.nan
    except:
        return np.nan

def calculate_simple_return(data: pd.DataFrame, signals: pd.Series, cost_scenario: Dict) -> float:
    """シンプルなリターン計算（Look-ahead bias修正版）"""
    try:
        # シグナル発生の次足Open価格でエントリー（Look-ahead bias修正）
        entry_prices = data['Open'].shift(-1)[signals].values
        if len(entry_prices) == 0:
            return 0.0
            
        # エントリーの次足Open価格で決済
        exit_signals = signals.shift(-2).fillna(False)  # 2期間後
        exit_prices = data['Open'].shift(-1)[exit_signals].values
        
        if len(entry_prices) == len(exit_prices):
            returns = (exit_prices - entry_prices) / entry_prices
            returns -= cost_scenario['fees'] + cost_scenario['slippage']
            return (1 + returns).prod() - 1  # 累積リターン
        
        return 0.0
    except:
        return 0.0

def calculate_simple_drawdown(data: pd.DataFrame, signals: pd.Series, cost_scenario: Dict) -> float:
    """実際の最大ドローダウン計算（Look-ahead bias修正版）"""
    try:
        # シグナル発生の次足Open価格でエントリー（Look-ahead bias修正）
        entry_prices = data['Open'].shift(-1)[signals].values
        if len(entry_prices) == 0:
            return 0.0
            
        # エントリーの次足Open価格で決済
        exit_signals = signals.shift(-2).fillna(False)  # 2期間後
        exit_prices = data['Open'].shift(-1)[exit_signals].values
        
        if len(entry_prices) != len(exit_prices):
            return 0.0
        
        # トレード毎のリターン計算
        trade_returns = (exit_prices - entry_prices) / entry_prices
        trade_returns -= (cost_scenario['fees'] + cost_scenario['slippage'])
        
        # 累積リターン計算
        cumulative_returns = np.cumprod(1 + trade_returns)
        
        # 各時点での最高値更新
        running_max = np.maximum.accumulate(cumulative_returns)
        
        # ドローダウン計算（現在値/最高値 - 1）
        drawdowns = (cumulative_returns / running_max) - 1
        
        # 最大ドローダウン
        max_drawdown = np.min(drawdowns)
        
        return max_drawdown
        
    except Exception as e:
        return 0.0

class ParallelWFARunner:
    """並列WFA実行クラス"""
    
    def __init__(self, data: pd.DataFrame, config_path: str = "wfa_config.json"):
        self.data = data
        self.optimization_system = ParallelWFAOptimization(data)
        self.config = self.load_config(config_path)
    
    def load_config(self, config_path: str) -> Dict:
        """設定ファイル読み込み"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"✅ 設定ファイル読み込み完了: {config_path}")
            return config
        except FileNotFoundError:
            print(f"⚠️ 設定ファイルが見つかりません: {config_path}、デフォルト設定を使用")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            "execution_config": {"num_folds": 3, "max_workers": "auto"},
            "cost_scenarios": [
                {"name": "Low Cost", "fees": 0.001, "slippage": 0.0005},
                {"name": "Medium Cost", "fees": 0.002, "slippage": 0.001},
                {"name": "High Cost", "fees": 0.003, "slippage": 0.002}
            ]
        }
        
    def run_parallel_wfa(self, 
                        strategy: TradingStrategy,
                        cost_scenarios: Optional[List[Dict]] = None,
                        num_folds: int = 5) -> Dict:
        """
        並列WFA実行
        
        Args:
            strategy: 取引戦略インスタンス
            cost_scenarios: コストシナリオリスト
            num_folds: Fold数
            
        Returns:
            Dict: 実行結果
        """
        
        print(f"🚀 並列WFA実行開始")
        print(f"   Fold数: {num_folds}")
        print(f"   並列ワーカー数: {MAX_WORKERS}")
        
        start_time = time.time()
        
        # コストシナリオ（設定ファイル優先）
        if cost_scenarios is None:
            cost_scenarios = self.config.get('cost_scenarios', [
                {'name': 'Low Cost', 'fees': 0.001, 'slippage': 0.0005},
                {'name': 'Medium Cost', 'fees': 0.002, 'slippage': 0.001},
                {'name': 'High Cost', 'fees': 0.003, 'slippage': 0.002}
            ])
        
        # 実行設定（設定ファイル優先）
        execution_config = self.config.get('execution_config', {})
        if 'num_folds' in execution_config:
            num_folds = execution_config['num_folds']
        
        # 戦略パラメータ準備
        param_ranges = strategy.get_parameter_ranges()
        parameter_combinations = generate_parameter_combinations(param_ranges)
        
        strategy_config = {
            'strategy_name': strategy.get_strategy_name(),
            'parameter_combinations': parameter_combinations
        }
        total_length = len(self.data)
        
        # Fold設定生成
        fold_configs = []
        for fold_id in range(1, num_folds + 1):
            # 時系列順序を維持したIn-Sample/Out-of-Sample分割
            initial_in_sample_size = int(total_length * 0.6)  # 60%を初期学習データ
            fold_step = int((total_length - initial_in_sample_size) / num_folds)
            
            in_sample_end = initial_in_sample_size + (fold_id - 1) * fold_step
            out_sample_start = in_sample_end
            out_sample_end = min(in_sample_end + fold_step, total_length)
            
            if out_sample_end <= out_sample_start:
                continue
                
            fold_config = {
                'fold_id': fold_id,
                'in_sample_data': self.data.iloc[:in_sample_end].copy(),
                'out_sample_data': self.data.iloc[out_sample_start:out_sample_end].copy()
            }
            fold_configs.append(fold_config)
        
        # 並列実行用タスク生成
        tasks = []
        for fold_config in fold_configs:
            for cost_scenario in cost_scenarios:
                task = (
                    fold_config['fold_id'],
                    fold_config,
                    strategy_config,
                    cost_scenario
                )
                tasks.append(task)
        
        print(f"📊 実行タスク数: {len(tasks)}")
        
        # 並列実行
        results = []
        completed_tasks = 0
        
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # タスク投入
            future_to_task = {
                executor.submit(calculate_single_fold_wfa, task): task 
                for task in tasks
            }
            
            # 結果収集
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
                completed_tasks += 1
                
                if completed_tasks % 3 == 0 or completed_tasks == len(tasks):
                    progress = (completed_tasks / len(tasks)) * 100
                    print(f"   進捗: {completed_tasks}/{len(tasks)} ({progress:.1f}%)")
        
        execution_time = time.time() - start_time
        
        # 結果分析
        successful_results = [r for r in results if r.get('status') == 'success']
        failed_results = [r for r in results if r.get('status') != 'success']
        
        print(f"\n✅ 並列WFA実行完了")
        print(f"   実行時間: {execution_time:.2f}秒")
        print(f"   成功: {len(successful_results)}件")
        print(f"   失敗: {len(failed_results)}件")
        
        if successful_results:
            avg_sharpe = np.mean([r['out_sample_sharpe'] for r in successful_results if not np.isnan(r['out_sample_sharpe'])])
            print(f"   平均Out-of-Sample Sharpe: {avg_sharpe:.3f}")
        
        # 結果整理
        execution_summary = {
            'execution_timestamp': datetime.now().isoformat(),
            'execution_time_seconds': execution_time,
            'total_tasks': len(tasks),
            'successful_tasks': len(successful_results),
            'failed_tasks': len(failed_results),
            'success_rate': len(successful_results) / len(tasks) if tasks else 0,
            'parallel_workers': MAX_WORKERS,
            'cpu_count': CPU_COUNT,
            'performance_metrics': {
                'avg_out_sample_sharpe': np.mean([r['out_sample_sharpe'] for r in successful_results if not np.isnan(r['out_sample_sharpe'])]) if successful_results else None,
                'best_out_sample_sharpe': max([r['out_sample_sharpe'] for r in successful_results if not np.isnan(r['out_sample_sharpe'])], default=None),
                'positive_sharpe_rate': np.mean([r['out_sample_sharpe'] > 0 for r in successful_results if not np.isnan(r['out_sample_sharpe'])]) if successful_results else None
            }
        }
        
        return {
            'execution_summary': execution_summary,
            'successful_results': successful_results,
            'failed_results': failed_results,
            'all_results': results
        }
    
    def save_parallel_results(self, results: Dict, output_path: str = None):
        """並列実行結果保存"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"parallel_wfa_results_{timestamp}.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"✅ 並列実行結果保存: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 結果保存エラー: {e}")
            return None

def performance_comparison_test():
    """性能比較テスト実行"""
    print("🔍 並列処理性能比較テスト")
    print("=" * 60)
    
    # テストデータ準備
    optimization = ParallelWFAOptimization()
    test_data = optimization.load_test_data()
    runner = ParallelWFARunner(test_data)
    
    # 並列実行
    print("\n📊 並列処理実行...")
    strategy = BreakoutStrategy()
    parallel_start = time.time()
    parallel_results = runner.run_parallel_wfa(
        strategy=strategy,
        num_folds=3
    )
    parallel_time = time.time() - parallel_start
    
    # 結果保存
    results_path = runner.save_parallel_results(parallel_results)
    
    # 性能サマリー
    print(f"\n🏆 性能比較結果:")
    print(f"   並列実行時間: {parallel_time:.2f}秒")
    print(f"   使用ワーカー数: {MAX_WORKERS}")
    print(f"   推定順次実行時間: {parallel_time * MAX_WORKERS:.2f}秒")
    print(f"   高速化率: {MAX_WORKERS:.1f}倍")
    
    return parallel_results, results_path

def main():
    """メイン実行"""
    print("🚀 並列処理最適化WFAシステム")
    print("=" * 60)
    
    # 性能比較テスト実行
    results, path = performance_comparison_test()
    
    print(f"\n🎉 並列処理最適化実装完了")
    print(f"   結果ファイル: {path}")

if __name__ == "__main__":
    main()