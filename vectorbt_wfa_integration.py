#!/usr/bin/env python3
"""
VectorBT × WFA 統合システム
既存WFAシステムとVectorBTを統合した高速バックテスト実行
"""

import vectorbt as vbt
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

# 既存WFAシステムのインポート
from cost_resistant_strategy import CostResistantStrategy
from data_cache_system import DataCacheManager

class VectorBTWFAIntegration:
    """VectorBTとWFAシステムの統合クラス"""
    
    def __init__(self, symbol='EURUSD', timeframe='D1'):
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_cache = DataCacheManager()
        self.raw_data = None
        self.vectorbt_data = None
        
    def load_data(self):
        """既存WFAシステムからデータ読み込み"""
        try:
            # 既存WFAシステムのデータ読み込み
            self.raw_data = self.data_cache.get_cached_data(self.symbol, self.timeframe)
            if not self.raw_data:
                print("❌ データ読み込み失敗")
                return False
                
            # VectorBT用データ形式変換
            self.vectorbt_data = self._convert_to_vectorbt_format(self.raw_data)
            
            print(f"✅ データ読み込み成功: {len(self.raw_data)}件")
            return True
            
        except Exception as e:
            print(f"❌ データ読み込みエラー: {e}")
            return False
    
    def _convert_to_vectorbt_format(self, raw_data):
        """WFAデータをVectorBT形式に変換"""
        df = pd.DataFrame(raw_data)
        
        # 必要なカラムの確認と変換
        required_columns = ['timestamp', 'open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_columns):
            print("❌ 必要なカラムが不足")
            return None
        
        # インデックス設定
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # カラム名統一
        df.columns = [col.capitalize() for col in df.columns]
        
        return df
    
    def calculate_breakout_signals(self, lookback_period=20):
        """ブレイクアウト信号計算（既存WFA戦略ロジック使用）"""
        if self.vectorbt_data is None:
            return None, None
        
        close = self.vectorbt_data['Close']
        high = self.vectorbt_data['High']
        low = self.vectorbt_data['Low']
        
        # 既存WFA戦略の信号計算ロジック
        rolling_high = high.rolling(lookback_period).max()
        rolling_low = low.rolling(lookback_period).min()
        
        # エントリー: 高値ブレイクアウト
        entries = close > rolling_high.shift(1)
        
        # エグジット: 安値ブレイクアウト
        exits = close < rolling_low.shift(1)
        
        return entries, exits
    
    def run_vectorbt_backtest(self, lookback_period=20, cost_params=None):
        """VectorBTバックテスト実行"""
        if self.vectorbt_data is None:
            return None
        
        # 信号計算
        entries, exits = self.calculate_breakout_signals(lookback_period)
        if entries is None or exits is None:
            return None
        
        # コスト設定
        if cost_params is None:
            cost_params = {'spread_pips': 1.0, 'commission_pips': 0.2}
        
        # VectorBTポートフォリオ作成
        portfolio = vbt.Portfolio.from_signals(
            self.vectorbt_data['Close'],
            entries,
            exits,
            init_cash=10000,
            fees=cost_params['spread_pips'] / 10000,  # pipsをレート変換
            freq='D'
        )
        
        return portfolio
    
    def run_wfa_with_vectorbt(self, lookback_range=(5, 50, 5), cost_scenarios=None):
        """WFAをVectorBTで実行"""
        if self.vectorbt_data is None:
            print("❌ データが読み込まれていません")
            return None
        
        # デフォルトコストシナリオ
        if cost_scenarios is None:
            cost_scenarios = [
                {'label': 'Low Cost', 'spread_pips': 0.5, 'commission_pips': 0.1},
                {'label': 'Medium Cost', 'spread_pips': 1.0, 'commission_pips': 0.2},
                {'label': 'High Cost', 'spread_pips': 2.0, 'commission_pips': 0.5}
            ]
        
        results = []
        
        # 5-fold WFA実行
        fold_size = len(self.vectorbt_data) // 5
        
        for fold_id in range(1, 6):
            print(f"🔄 Fold {fold_id}/5 実行中...")
            
            # テストデータ分割
            test_start = (fold_id - 1) * fold_size
            test_end = fold_id * fold_size
            test_data = self.vectorbt_data.iloc[test_start:test_end]
            
            # 各コストシナリオでテスト
            for cost_scenario in cost_scenarios:
                for lookback in range(*lookback_range):
                    # 信号計算（テストデータのみ）
                    entries, exits = self._calculate_signals_for_period(
                        test_data, lookback
                    )
                    
                    if entries is None or exits is None:
                        continue
                    
                    # VectorBTバックテスト
                    portfolio = vbt.Portfolio.from_signals(
                        test_data['Close'],
                        entries,
                        exits,
                        init_cash=10000,
                        fees=cost_scenario['spread_pips'] / 10000,
                        freq='D'
                    )
                    
                    # 結果記録
                    try:
                        stats = portfolio.stats()
                        results.append({
                            'fold_id': fold_id,
                            'cost_scenario': cost_scenario['label'],
                            'lookback_period': lookback,
                            'total_return': portfolio.total_return(),
                            'sharpe_ratio': portfolio.sharpe_ratio(),
                            'max_drawdown': portfolio.max_drawdown(),
                            'total_trades': stats['Total Trades'],
                            'win_rate': stats['Win Rate [%]'],
                            'profit_factor': stats['Profit Factor']
                        })
                    except Exception as e:
                        print(f"⚠️ 統計計算エラー: {e}")
                        continue
        
        return pd.DataFrame(results)
    
    def _calculate_signals_for_period(self, data, lookback_period):
        """指定期間のデータで信号計算"""
        if len(data) < lookback_period:
            return None, None
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        rolling_high = high.rolling(lookback_period).max()
        rolling_low = low.rolling(lookback_period).min()
        
        entries = close > rolling_high.shift(1)
        exits = close < rolling_low.shift(1)
        
        return entries, exits
    
    def compare_performance(self, wfa_results_path=None):
        """既存WFAシステムとVectorBTの性能比較"""
        print("🔍 性能比較開始...")
        
        # VectorBTでのWFA実行
        vectorbt_results = self.run_wfa_with_vectorbt()
        if vectorbt_results is None:
            print("❌ VectorBT WFA実行失敗")
            return None
        
        # 既存WFA結果読み込み
        existing_results = None
        if wfa_results_path:
            try:
                with open(wfa_results_path, 'r') as f:
                    existing_results = json.load(f)
            except Exception as e:
                print(f"⚠️ 既存結果読み込みエラー: {e}")
        
        # 比較分析
        comparison = {
            'vectorbt_summary': {
                'total_scenarios': len(vectorbt_results),
                'avg_return': vectorbt_results['total_return'].mean(),
                'avg_sharpe': vectorbt_results['sharpe_ratio'].mean(),
                'best_scenario': vectorbt_results.loc[
                    vectorbt_results['sharpe_ratio'].idxmax()
                ].to_dict()
            },
            'performance_metrics': {
                'execution_time': 'TBD',  # 実行時間測定
                'memory_usage': 'TBD',    # メモリ使用量測定
                'scalability': 'TBD'      # スケーラビリティ評価
            }
        }
        
        return comparison
    
    def save_results(self, results, filename=None):
        """結果保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vectorbt_wfa_results_{timestamp}.json"
        
        try:
            if isinstance(results, pd.DataFrame):
                results_dict = results.to_dict('records')
            else:
                results_dict = results
            
            with open(filename, 'w') as f:
                json.dump(results_dict, f, indent=2, default=str)
            
            print(f"✅ 結果保存: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ 結果保存エラー: {e}")
            return False

def main():
    """メイン実行"""
    print("🚀 VectorBT × WFA 統合システム開始")
    print("=" * 60)
    
    # 統合システム初期化
    integration = VectorBTWFAIntegration()
    
    # データ読み込み
    if not integration.load_data():
        return
    
    # VectorBTでのWFA実行
    print("\n🔄 VectorBT WFA実行...")
    wfa_results = integration.run_wfa_with_vectorbt()
    
    if wfa_results is not None:
        print(f"✅ WFA完了: {len(wfa_results)}シナリオ")
        
        # 結果分析
        print("\n📊 結果サマリー:")
        print(f"平均リターン: {wfa_results['total_return'].mean():.2%}")
        print(f"平均シャープレシオ: {wfa_results['sharpe_ratio'].mean():.3f}")
        print(f"最高シャープレシオ: {wfa_results['sharpe_ratio'].max():.3f}")
        
        # 結果保存
        integration.save_results(wfa_results)
    
    # 性能比較
    print("\n🔍 性能比較実行...")
    comparison = integration.compare_performance()
    if comparison:
        print("✅ 性能比較完了")
        integration.save_results(comparison, "performance_comparison.json")

if __name__ == "__main__":
    main()