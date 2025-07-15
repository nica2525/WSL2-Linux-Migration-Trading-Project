#!/usr/bin/env python3
"""
Cost-Resistant WFA Execution ― 根本修正版
------------------------------------------------
● 逐次・並列で同一ロジック実行を保証
● CostResistantStrategy を全処理で使用
● DRY 原則適用: _execute_realistic_backtest を唯一のバックテスト実装
● ステートレス並列化: ProcessPoolExecutor
"""

import json
import numpy as np
import multiprocessing as mp
import time
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict

from cost_resistant_strategy import CostResistantStrategy
from data_cache_system import DataCacheManager

class Position:
    # （既存 Position クラスをそのまま利用）
    ...

class CostResistantWFAExecutionFixed:
    def __init__(self):
        self.cache_manager = DataCacheManager()
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

    def _backtest_fold(self, test_data: List, fold_id: int) -> Dict:
        """逐次版と完全同一のバックテストロジックを実行"""
        # CostResistantStrategy インスタンスを毎回生成（ステートレス設計）
        strategy = CostResistantStrategy(self.base_params.copy())
        # ここで既存の _execute_realistic_backtest と同一処理を呼び出し
        return self._execute_realistic_backtest(test_data, fold_id, strategy)

    def execute_sensitivity_analysis_parallel(self) -> Dict:
        """並列感度分析: 全シナリオを _backtest_fold で処理"""
        raw_data = self.cache_manager.get_full_data()
        assert raw_data and len(raw_data) >= 1000, "データ不足"
        # 5フォールド分割
        fold_size = len(raw_data) // 5
        tasks = []
        for fold_id in range(1, 6):
            start = (fold_id - 1) * fold_size
            end = fold_id * fold_size
            tasks.append((raw_data[start:end], fold_id))

        cpu = max(1, mp.cpu_count() - 1)
        results = []
        start_time = time.time()
        with ProcessPoolExecutor(max_workers=cpu) as executor:
            future_to_fold = {
                executor.submit(self._backtest_fold, data, fid): fid
                for data, fid in tasks
            }
            completed = 0
            for future in as_completed(future_to_fold):
                res = future.result()
                if res:
                    results.append(res)
                completed += 1
                elapsed = time.time() - start_time
                eta = (elapsed / completed) * (len(tasks) - completed) if completed else 0
                bar = '█' * completed + '-' * (len(tasks) - completed)
                sys.stdout.write(f"\r[{bar}] {completed}/{len(tasks)} ETA:{eta:.1f}s")
                sys.stdout.flush()
        total_time = time.time() - start_time
        print(f"\nParallel execution time: {total_time:.1f}s")

        # レポート生成
        sensitivity_report = self._generate_sensitivity_report(results)
        return {
            'sensitivity_analysis': results,
            'sensitivity_report': sensitivity_report,
            'execution_time': datetime.now().isoformat(),
            'performance_info': {
                'cpu_cores': cpu,
                'total_time': total_time
            }
        }

    # 以下、_execute_realistic_backtest, _generate_sensitivity_report を
    # cost_resistant_wfa_execution_FINAL.py から DRY にコピーしてください。

def main():
    executor = CostResistantWFAExecutionFixed()
    if len(sys.argv) > 1 and sys.argv[1] == '--sensitivity-parallel':
        res = executor.execute_sensitivity_analysis_parallel()
        with open('sensitivity_analysis_results.json', 'w') as f:
            json.dump(res, f, indent=2)
    else:
        print("Usage: --sensitivity-parallel")

if __name__ == '__main__':
    main()
