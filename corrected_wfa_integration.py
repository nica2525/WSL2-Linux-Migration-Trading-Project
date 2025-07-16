#!/usr/bin/env python3
"""
修正版 VectorBT × WFA 統合システム
Gemini査読指摘事項を修正：正しいウォークフォワード分析実装
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

class CorrectedVectorBTWFAIntegration:
    """修正版VectorBTとWFAシステムの統合クラス"""
    
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
            self.raw_data = self.data_cache.get_full_data()
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
        required_columns = ['datetime', 'open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_columns):
            print("❌ 必要なカラムが不足")
            print(f"実際のカラム: {list(df.columns)}")
            return None
        
        # インデックス設定
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # カラム名統一
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
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
    
    def run_proper_wfa_with_vectorbt(self, lookback_range=(5, 50, 5), cost_scenarios=None, num_folds=5):
        """
        正しいウォークフォワード分析をVectorBTで実行
        時系列順序を維持し、In-Sampleで最適化、Out-of-Sampleで検証
        """
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
        total_length = len(self.vectorbt_data)
        
        # 最初のIn-Sampleサイズを全データの60%に設定
        initial_in_sample_size = int(total_length * 0.6)
        fold_step = (total_length - initial_in_sample_size) // num_folds
        
        print(f"📋 正しいWFA設定:")
        print(f"  全データ数: {total_length}")
        print(f"  初期In-Sampleサイズ: {initial_in_sample_size}")
        print(f"  Foldステップ: {fold_step}")
        
        for fold_id in range(1, num_folds + 1):
            print(f"🔄 Fold {fold_id}/{num_folds} 実行中...")
            
            # 時系列順序を維持したIn-Sample/Out-of-Sample分割
            in_sample_end = initial_in_sample_size + (fold_id - 1) * fold_step
            out_sample_start = in_sample_end
            out_sample_end = min(in_sample_end + fold_step, total_length)
            
            # In-Sampleデータ（過去データのみ）
            in_sample_data = self.vectorbt_data.iloc[:in_sample_end]
            # Out-of-Sampleデータ（直後の未来データ）
            out_sample_data = self.vectorbt_data.iloc[out_sample_start:out_sample_end]
            
            print(f"  In-Sample: [0:{in_sample_end}] ({len(in_sample_data)}件)")
            print(f"  Out-of-Sample: [{out_sample_start}:{out_sample_end}] ({len(out_sample_data)}件)")
            
            if len(out_sample_data) < 10:  # テストデータが少なすぎる場合
                print(f"  ⚠️ Out-of-Sampleデータが不十分: {len(out_sample_data)}件")
                continue
            
            # Step 1: In-Sampleで最適パラメータを探索
            best_params = self._optimize_parameters_in_sample(
                in_sample_data, lookback_range, cost_scenarios
            )
            
            if not best_params:
                print(f"  ⚠️ In-Sample最適化失敗")
                continue
            
            # Step 2: 最適パラメータでOut-of-Sampleで検証
            for cost_scenario in cost_scenarios:
                if cost_scenario['label'] not in best_params:
                    continue
                    
                optimal_lookback = best_params[cost_scenario['label']]['lookback']
                
                # Out-of-Sampleでバックテスト
                entries, exits = self._calculate_signals_for_period(
                    out_sample_data, optimal_lookback
                )
                
                if entries is None or exits is None:
                    continue
                
                portfolio = vbt.Portfolio.from_signals(
                    out_sample_data['Close'],
                    entries,
                    exits,
                    init_cash=10000,
                    fees=cost_scenario['spread_pips'] / 10000,
                    freq='D'
                )
                
                try:
                    stats = portfolio.stats()
                    results.append({
                        'fold_id': fold_id,
                        'cost_scenario': cost_scenario['label'],
                        'optimal_lookback': optimal_lookback,
                        'in_sample_size': len(in_sample_data),
                        'out_sample_size': len(out_sample_data),
                        'total_return': portfolio.total_return(),
                        'sharpe_ratio': portfolio.sharpe_ratio(),
                        'max_drawdown': portfolio.max_drawdown(),
                        'total_trades': stats['Total Trades'],
                        'win_rate': stats['Win Rate [%]'],
                        'profit_factor': stats['Profit Factor'],
                        'in_sample_performance': best_params[cost_scenario['label']]['performance']
                    })
                    
                    print(f"    {cost_scenario['label']}: 最適Lookback={optimal_lookback}, "
                          f"Out-of-Sample SR={portfolio.sharpe_ratio():.3f}")
                    
                except Exception as e:
                    print(f"  ⚠️ Out-of-Sample結果計算エラー: {e}")
                    continue
        
        return pd.DataFrame(results)
    
    def _optimize_parameters_in_sample(self, in_sample_data, lookback_range, cost_scenarios):
        """
        In-Sampleデータでパラメータ最適化
        各コストシナリオに対して最適なlookback_periodを探索
        """
        best_params = {}
        
        print(f"    In-Sample最適化開始 (lookback範囲: {lookback_range})")
        
        for cost_scenario in cost_scenarios:
            best_sharpe = -np.inf
            best_lookback = None
            best_performance = None
            
            for lookback in range(*lookback_range):
                entries, exits = self._calculate_signals_for_period(
                    in_sample_data, lookback
                )
                
                if entries is None or exits is None:
                    continue
                
                try:
                    portfolio = vbt.Portfolio.from_signals(
                        in_sample_data['Close'],
                        entries,
                        exits,
                        init_cash=10000,
                        fees=cost_scenario['spread_pips'] / 10000,
                        freq='D'
                    )
                    
                    sharpe_ratio = portfolio.sharpe_ratio()
                    
                    if not np.isnan(sharpe_ratio) and sharpe_ratio > best_sharpe:
                        best_sharpe = sharpe_ratio
                        best_lookback = lookback
                        best_performance = {
                            'sharpe_ratio': sharpe_ratio,
                            'total_return': portfolio.total_return(),
                            'max_drawdown': portfolio.max_drawdown()
                        }
                        
                except Exception as e:
                    continue
            
            if best_lookback is not None:
                best_params[cost_scenario['label']] = {
                    'lookback': best_lookback,
                    'performance': best_performance
                }
                print(f"    {cost_scenario['label']}: 最適Lookback={best_lookback}, "
                      f"In-Sample SR={best_performance['sharpe_ratio']:.3f}")
        
        return best_params
    
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
    
    def analyze_wfa_results(self, results_df):
        """WFA結果の統計的分析"""
        if results_df is None or len(results_df) == 0:
            print("❌ 分析対象の結果がありません")
            return None
        
        print("\n📊 WFA結果統計分析:")
        
        # コストシナリオ別分析
        for cost_scenario in results_df['cost_scenario'].unique():
            scenario_data = results_df[results_df['cost_scenario'] == cost_scenario]
            
            print(f"\n💰 {cost_scenario}:")
            print(f"  Fold数: {len(scenario_data)}")
            print(f"  平均シャープレシオ: {scenario_data['sharpe_ratio'].mean():.3f}")
            print(f"  シャープレシオ標準偏差: {scenario_data['sharpe_ratio'].std():.3f}")
            print(f"  平均リターン: {scenario_data['total_return'].mean():.2%}")
            print(f"  最大ドローダウン平均: {scenario_data['max_drawdown'].mean():.2%}")
            print(f"  勝率平均: {scenario_data['win_rate'].mean():.1f}%")
            
            # 統計的有意性の簡易検定
            positive_sharpe_count = (scenario_data['sharpe_ratio'] > 0).sum()
            total_folds = len(scenario_data)
            win_rate_folds = positive_sharpe_count / total_folds
            
            print(f"  正のシャープレシオFold数: {positive_sharpe_count}/{total_folds} ({win_rate_folds:.1%})")
            
            if win_rate_folds >= 0.6:
                print(f"  ✅ 統計的に有望 (60%以上のFoldで正のシャープレシオ)")
            else:
                print(f"  ⚠️ 統計的に不安定 (正のシャープレシオが60%未満)")
        
        # 全体統計
        print(f"\n🔍 全体統計:")
        print(f"  全Fold数: {len(results_df)}")
        print(f"  全体平均シャープレシオ: {results_df['sharpe_ratio'].mean():.3f}")
        print(f"  最高シャープレシオ: {results_df['sharpe_ratio'].max():.3f}")
        print(f"  最低シャープレシオ: {results_df['sharpe_ratio'].min():.3f}")
        
        return {
            'summary_stats': results_df.groupby('cost_scenario').agg({
                'sharpe_ratio': ['mean', 'std', 'min', 'max'],
                'total_return': ['mean', 'std'],
                'max_drawdown': ['mean', 'std'],
                'win_rate': 'mean'
            }),
            'raw_results': results_df
        }
    
    def save_results(self, results, filename=None):
        """結果保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"corrected_wfa_results_{timestamp}.json"
        
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
    print("🚀 修正版 VectorBT × WFA 統合システム開始")
    print("=" * 60)
    
    # 修正版統合システム初期化
    integration = CorrectedVectorBTWFAIntegration()
    
    # データ読み込み
    if not integration.load_data():
        return
    
    # 正しいWFA実行
    print("\n🔄 正しいWFA実行...")
    wfa_results = integration.run_proper_wfa_with_vectorbt()
    
    if wfa_results is not None and len(wfa_results) > 0:
        print(f"\n✅ WFA完了: {len(wfa_results)}シナリオ")
        
        # 結果分析
        analysis = integration.analyze_wfa_results(wfa_results)
        
        # 結果保存
        integration.save_results(wfa_results)
        
        print(f"\n🎯 修正後の結果:")
        print(f"  平均シャープレシオ: {wfa_results['sharpe_ratio'].mean():.3f}")
        print(f"  シャープレシオ標準偏差: {wfa_results['sharpe_ratio'].std():.3f}")
        print(f"  最高シャープレシオ: {wfa_results['sharpe_ratio'].max():.3f}")
        
    else:
        print("❌ WFA実行失敗または結果なし")

if __name__ == "__main__":
    main()