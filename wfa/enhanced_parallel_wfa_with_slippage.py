#!/usr/bin/env python3
"""
スリッパージ統合並列WFAシステム
Gemini満点システム + 高度スリッパージモデル統合
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import time
from pathlib import Path

# 既存システムのインポート
from parallel_wfa_optimization import (
    TradingStrategy, BreakoutStrategy, MeanReversionStrategy,
    ParallelWFARunner, generate_parameter_combinations
)
from advanced_slippage_model import (
    AdvancedSlippageModel, SlippageConfig, MarketCondition, OrderType
)

# システム情報
CPU_COUNT = mp.cpu_count()
MAX_WORKERS = max(1, CPU_COUNT - 1)

class EnhancedWFAStrategy(TradingStrategy):
    """スリッパージ考慮戦略基底クラス"""
    
    def __init__(self, slippage_model: AdvancedSlippageModel = None):
        self.slippage_model = slippage_model or AdvancedSlippageModel()
    
    def calculate_realistic_performance(self, 
                                      data: pd.DataFrame,
                                      signals: pd.Series,
                                      order_type: OrderType = OrderType.MARKET) -> Dict:
        """現実的パフォーマンス計算（スリッパージ考慮）"""
        
        # 約定シミュレーション
        executions = self.slippage_model.simulate_realistic_execution(
            data=data,
            entry_signals=signals,
            order_type=order_type
        )
        
        if not executions:
            return {
                'total_return': 0.0,
                'sharpe_ratio': np.nan,
                'max_drawdown': 0.0,
                'execution_count': 0,
                'avg_slippage_pct': 0.0
            }
        
        # リターン計算
        returns = []
        equity_curve = [1.0]  # 初期資本1.0
        
        for i, execution in enumerate(executions):
            if i + 1 < len(executions):
                # 次の約定までのリターン
                entry_price = execution['execution_price']
                exit_price = executions[i + 1]['execution_price']
                trade_return = (exit_price - entry_price) / entry_price
                returns.append(trade_return)
                equity_curve.append(equity_curve[-1] * (1 + trade_return))
        
        if not returns:
            return {
                'total_return': 0.0,
                'sharpe_ratio': np.nan,
                'max_drawdown': 0.0,
                'execution_count': len(executions),
                'avg_slippage_pct': np.mean([e['slippage_pct'] for e in executions])
            }
        
        # パフォーマンス指標計算
        total_return = equity_curve[-1] - 1.0
        returns_array = np.array(returns)
        
        # シャープレシオ
        if len(returns) > 1 and returns_array.std() > 0:
            sharpe_ratio = returns_array.mean() / returns_array.std() * np.sqrt(252)
        else:
            sharpe_ratio = np.nan
        
        # 最大ドローダウン
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array / running_max) - 1
        max_drawdown = np.min(drawdowns)
        
        # スリッパージ統計
        avg_slippage_pct = np.mean([e['slippage_pct'] for e in executions])
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'execution_count': len(executions),
            'avg_slippage_pct': avg_slippage_pct,
            'total_slippage_cost': sum([e['slippage_cost'] for e in executions]),
            'detailed_executions': executions
        }

class RealisticBreakoutStrategy(EnhancedWFAStrategy):
    """現実的ブレイクアウト戦略（スリッパージ考慮）"""
    
    def generate_signals(self, data: pd.DataFrame, params: Dict) -> pd.Series:
        """ブレイクアウトシグナル生成"""
        lookback = params.get('lookback', 20)
        
        if len(data) < lookback + 1:
            return pd.Series(False, index=data.index)
        
        # ローリング最高値
        rolling_high = data['High'].rolling(window=lookback).max()
        
        # ブレイクアウト条件（Look-ahead bias修正）
        # 現在足のCloseではなく、当足高値でのブレイクアウト判定
        breakout_condition = data['High'] > rolling_high.shift(1)
        
        return breakout_condition.fillna(False)
    
    def get_parameter_ranges(self) -> Dict:
        return {
            'lookback': {'min': 5, 'max': 50, 'step': 5}
        }
    
    def get_strategy_name(self) -> str:
        return "RealisticBreakoutStrategy"

def calculate_enhanced_fold_wfa(fold_params: Tuple) -> Dict:
    """
    スリッパージ考慮Fold WFA計算
    
    Args:
        fold_params: (fold_id, fold_config, strategy_config, slippage_config, cost_scenario)
    """
    fold_id, fold_config, strategy_config, slippage_config, cost_scenario = fold_params
    
    try:
        # データ分割
        in_sample_data = fold_config['in_sample_data']
        out_sample_data = fold_config['out_sample_data']
        
        # スリッパージモデル初期化
        slippage_model = AdvancedSlippageModel(slippage_config)
        
        # 戦略インスタンス生成
        strategy_name = strategy_config['strategy_name']
        if strategy_name == 'RealisticBreakoutStrategy':
            strategy = RealisticBreakoutStrategy(slippage_model)
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        # In-Sample最適化
        best_params = None
        best_in_sample_sharpe = -np.inf
        
        for params in strategy_config['parameter_combinations']:
            try:
                # シグナル生成
                in_sample_signals = strategy.generate_signals(in_sample_data, params)
                
                if in_sample_signals.sum() > 0:
                    # 現実的パフォーマンス計算
                    performance = strategy.calculate_realistic_performance(
                        data=in_sample_data,
                        signals=in_sample_signals,
                        order_type=OrderType.MARKET
                    )
                    
                    sharpe_ratio = performance['sharpe_ratio']
                    if not np.isnan(sharpe_ratio) and sharpe_ratio > best_in_sample_sharpe:
                        best_in_sample_sharpe = sharpe_ratio
                        best_params = params
                        
            except Exception as e:
                continue
        
        # Out-of-Sample検証
        if best_params is not None:
            out_sample_signals = strategy.generate_signals(out_sample_data, best_params)
            
            if out_sample_signals.sum() > 0:
                out_sample_performance = strategy.calculate_realistic_performance(
                    data=out_sample_data,
                    signals=out_sample_signals,
                    order_type=OrderType.MARKET
                )
                
                return {
                    'fold_id': fold_id,
                    'optimal_params': best_params,
                    'strategy_name': strategy.get_strategy_name(),
                    'in_sample_sharpe': best_in_sample_sharpe,
                    'out_sample_sharpe': out_sample_performance['sharpe_ratio'],
                    'out_sample_return': out_sample_performance['total_return'],
                    'out_sample_drawdown': out_sample_performance['max_drawdown'],
                    'execution_count': out_sample_performance['execution_count'],
                    'avg_slippage_pct': out_sample_performance['avg_slippage_pct'],
                    'total_slippage_cost': out_sample_performance['total_slippage_cost'],
                    'cost_scenario': cost_scenario['name'],
                    'slippage_config': {
                        'base_spread': slippage_config.base_spread,
                        'market_impact_coeff': slippage_config.market_impact_coeff,
                        'execution_delay_ms': slippage_config.execution_delay_ms
                    },
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

class EnhancedParallelWFARunner:
    """スリッパージ統合並列WFAランナー"""
    
    def __init__(self, data: pd.DataFrame, config_path: str = "enhanced_wfa_config.json"):
        self.data = data
        self.config = self.load_config(config_path)
        
    def load_config(self, config_path: str) -> Dict:
        """設定ファイル読み込み"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"✅ 拡張設定ファイル読み込み: {config_path}")
            return config
        except FileNotFoundError:
            print(f"⚠️ 設定ファイル未発見: {config_path}、デフォルト設定使用")
            return self.get_default_enhanced_config()
    
    def get_default_enhanced_config(self) -> Dict:
        """デフォルト拡張設定"""
        return {
            "execution_config": {"num_folds": 3, "max_workers": "auto"},
            "slippage_scenarios": [
                {
                    "name": "Conservative",
                    "base_spread": 0.0001,
                    "market_impact_coeff": 0.3,
                    "execution_delay_ms": 50
                },
                {
                    "name": "Realistic", 
                    "base_spread": 0.0002,
                    "market_impact_coeff": 0.5,
                    "execution_delay_ms": 100
                },
                {
                    "name": "Aggressive",
                    "base_spread": 0.0003,
                    "market_impact_coeff": 0.8,
                    "execution_delay_ms": 200
                }
            ],
            "cost_scenarios": [
                {"name": "Low Cost", "fees": 0.001, "slippage": 0.0005},
                {"name": "Medium Cost", "fees": 0.002, "slippage": 0.001},
                {"name": "High Cost", "fees": 0.003, "slippage": 0.002}
            ]
        }
    
    def run_enhanced_parallel_wfa(self, 
                                 strategy: EnhancedWFAStrategy,
                                 num_folds: int = None) -> Dict:
        """拡張並列WFA実行"""
        
        print(f"🚀 スリッパージ統合並列WFA実行開始")
        print(f"   Fold数: {num_folds or self.config['execution_config']['num_folds']}")
        print(f"   並列ワーカー数: {MAX_WORKERS}")
        
        start_time = time.time()
        
        # 設定取得
        execution_config = self.config.get('execution_config', {})
        if num_folds is None:
            num_folds = execution_config.get('num_folds', 3)
        
        slippage_scenarios = self.config.get('slippage_scenarios', [])
        cost_scenarios = self.config.get('cost_scenarios', [])
        
        # 戦略パラメータ準備
        param_ranges = strategy.get_parameter_ranges()
        parameter_combinations = generate_parameter_combinations(param_ranges)
        
        strategy_config = {
            'strategy_name': strategy.get_strategy_name(),
            'parameter_combinations': parameter_combinations
        }
        
        # Fold設定生成
        total_length = len(self.data)
        fold_configs = []
        
        for fold_id in range(1, num_folds + 1):
            initial_in_sample_size = int(total_length * 0.6)
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
            for slippage_scenario in slippage_scenarios:
                for cost_scenario in cost_scenarios:
                    # スリッパージ設定
                    slippage_config = SlippageConfig(
                        base_spread=slippage_scenario['base_spread'],
                        market_impact_coeff=slippage_scenario['market_impact_coeff'],
                        execution_delay_ms=slippage_scenario['execution_delay_ms']
                    )
                    
                    task = (
                        fold_config['fold_id'],
                        fold_config,
                        strategy_config,
                        slippage_config,
                        {**cost_scenario, 'slippage_scenario': slippage_scenario['name']}
                    )
                    tasks.append(task)
        
        print(f"📊 実行タスク数: {len(tasks)}")
        
        # 並列実行
        results = []
        completed_tasks = 0
        
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_task = {
                executor.submit(calculate_enhanced_fold_wfa, task): task 
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
                completed_tasks += 1
                
                if completed_tasks % 5 == 0 or completed_tasks == len(tasks):
                    progress = (completed_tasks / len(tasks)) * 100
                    print(f"   進捗: {completed_tasks}/{len(tasks)} ({progress:.1f}%)")
        
        execution_time = time.time() - start_time
        
        # 結果分析
        successful_results = [r for r in results if r.get('status') == 'success']
        failed_results = [r for r in results if r.get('status') != 'success']
        
        print(f"\n✅ スリッパージ統合並列WFA実行完了")
        print(f"   実行時間: {execution_time:.2f}秒")
        print(f"   成功: {len(successful_results)}件")
        print(f"   失敗: {len(failed_results)}件")
        
        if successful_results:
            avg_sharpe = np.mean([r['out_sample_sharpe'] for r in successful_results if not np.isnan(r['out_sample_sharpe'])])
            avg_slippage = np.mean([r['avg_slippage_pct'] for r in successful_results])
            print(f"   平均Out-of-Sample Sharpe: {avg_sharpe:.3f}")
            print(f"   平均スリッパージ: {avg_slippage:.4f}%")
        
        return {
            'execution_summary': {
                'execution_timestamp': datetime.now().isoformat(),
                'execution_time_seconds': execution_time,
                'total_tasks': len(tasks),
                'successful_tasks': len(successful_results),
                'failed_tasks': len(failed_results),
                'success_rate': len(successful_results) / len(tasks) if tasks else 0,
                'parallel_workers': MAX_WORKERS,
                'slippage_integration': True
            },
            'successful_results': successful_results,
            'failed_results': failed_results,
            'all_results': results
        }
    
    def save_enhanced_results(self, results: Dict, output_path: str = None):
        """拡張結果保存"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"enhanced_slippage_wfa_results_{timestamp}.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"✅ 拡張結果保存: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 結果保存エラー: {e}")
            return None

def main():
    """メイン実行"""
    print("🚀 スリッパージ統合並列WFAシステム")
    print("=" * 60)
    
    # テストデータ準備
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
    
    print(f"📊 テストデータ: {len(test_data)}日分")
    
    # 拡張ランナー初期化
    runner = EnhancedParallelWFARunner(test_data)
    
    # 現実的ブレイクアウト戦略
    strategy = RealisticBreakoutStrategy()
    
    # 拡張並列WFA実行
    results = runner.run_enhanced_parallel_wfa(
        strategy=strategy,
        num_folds=3
    )
    
    # 結果保存
    results_path = runner.save_enhanced_results(results)
    
    print(f"\n🎉 スリッパージ統合システム実行完了")
    print(f"📁 結果ファイル: {results_path}")

if __name__ == "__main__":
    main()