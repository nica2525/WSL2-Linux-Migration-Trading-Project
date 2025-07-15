#!/usr/bin/env python3
"""
Cost-Resistant WFA Execution  ― Sensitivity Analysis Optimised
--------------------------------------------------------------
● 並列処理 : concurrent.futures.ProcessPoolExecutor
● キャッシュ : multiprocessing.Manager に raw_data を共有
● 部分実行 : --chunk N M
● 進捗表示 : 文字バー
※ execute_sensitivity_analysis() 互換
"""

import os, sys, time, json, multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

from cost_resistant_strategy import CostResistantStrategy
from data_cache_system import DataCacheManager

# ──────────────────────────────────────────────────────────────
def _worker(args):
    idx, params, base_params, raw = args
    base = base_params.copy()
    base.update(params)
    strategy = CostResistantStrategy(base)
    core     = CostResistantWFAExecutionCore(strategy, raw)
    return idx, params["label"], core.run_wfa()

class CostResistantWFAExecutionCore:
    def __init__(self, strategy, raw):
        self.strategy  = strategy
        self.raw_data  = raw
        self.fold_size = len(raw) // 5

    def run_wfa(self):
        """WFA実行（並列処理対応版）"""
        wfa_results = []
        
        for fold_id in range(1, 6):
            # テストデータ範囲
            test_start = (fold_id - 1) * self.fold_size
            test_end = fold_id * self.fold_size
            test_data = self.raw_data[test_start:test_end]
            
            # 現実的バックテスト実行
            oos_result = self._execute_realistic_backtest(test_data, fold_id)
            
            if oos_result:
                wfa_results.append(oos_result)
        
        # コストモデル適用
        cost_adjusted_results = self._apply_transaction_costs_to_results(wfa_results)
        
        # 結果分析
        analysis_result = self._analyze_wfa_results(cost_adjusted_results)
        
        return {
            'wfa_results_raw': wfa_results,
            'wfa_results_cost_adjusted': cost_adjusted_results,
            'analysis': analysis_result
        }

class CostResistantWFAExecutionFinal:
    def __init__(self):
        self.cache = DataCacheManager()
        self.base  = {
            "h4_period":24,"h1_period":24,"atr_period":14,
            "profit_atr":2.5,"stop_atr":1.3,"min_break_pips":5,
            "spread_pips":1.5,"commission_pips":0.3,
        }
        self.sens = [
            {"spread_pips":1.5,"commission_pips":0.3,"label":"標準"},
            {"spread_pips":2.5,"commission_pips":0.5,"label":"高コスト"},
            {"spread_pips":3.0,"commission_pips":1.0,"label":"超高コスト"},
            {"spread_pips":0.8,"commission_pips":0.0,"label":"低コスト"},
        ]

    def _raw(self):
        if not hasattr(self,"_raw_cache"):
            self._raw_cache = self.cache.get_full_data()
            if not self._raw_cache:
                raise RuntimeError("raw_data not found")
        return self._raw_cache

    def _progress(self, done, total, t0):
        bar = "█"*done + "-"*(total-done)
        eta = (time.time()-t0)/done*(total-done) if done else 0
        sys.stdout.write(f"\r[{bar}] {done}/{total} ETA:{eta:4.1f}s")
        sys.stdout.flush()
        if done==total: print("")

    def _run_parallel(self, idxs):
        raw = self._raw()
        cpu = max(1, mp.cpu_count()-1)
        tasks = [(i, self.sens[i], self.base, raw) for i in idxs]
        out = []
        t0  = time.time()
        with ProcessPoolExecutor(max_workers=cpu) as ex:
            fut = {ex.submit(_worker,t):t[0] for t in tasks}
            done = 0
            for f in as_completed(fut):
                out.append(f.result())
                done += 1
                self._progress(done,len(tasks),t0)
        return out

    def execute_sensitivity_analysis(self, chunk=None):
        idxs = list(range(len(self.sens))) if not chunk else list(range(chunk[0],chunk[1]+1))
        res  = self._run_parallel(idxs)
        final = {
            "execution_time": datetime.now().isoformat(),
            "sensitivity_analysis": res,
            "analysis_parameters": self.sens
        }
        with open("sensitivity_analysis_results.json","w") as f:
            json.dump(final,f,indent=2)
        return final

def main():
    exe = CostResistantWFAExecutionFinal()
    if "--chunk" in sys.argv:
        s,e = map(int, sys.argv[sys.argv.index("--chunk")+1:][:2])
        exe.execute_sensitivity_analysis((s,e))
    else:
        exe.execute_sensitivity_analysis()

if __name__ == "__main__":
    main()
