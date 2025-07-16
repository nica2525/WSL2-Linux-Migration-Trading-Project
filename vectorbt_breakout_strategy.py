#!/usr/bin/env python3
"""
VectorBT ブレイクアウト戦略実装
現在のプロジェクトの品質問題を解決するためのサンプル実装
"""

import vectorbt as vbt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

class BreakoutStrategy:
    """
    ブレイクアウト戦略クラス
    - 高値・安値ブレイクアウト
    - 複数パラメータ最適化
    - 詳細な統計分析
    """
    
    def __init__(self, symbol='EURUSD=X', period='1y'):
        """
        初期化
        
        Args:
            symbol: 取引シンボル
            period: データ期間
        """
        self.symbol = symbol
        self.period = period
        self.data = None
        self.results = {}
        
    def load_data(self):
        """データ取得"""
        try:
            # Yahoo Financeからデータ取得
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(period=self.period)
            
            if self.data.empty:
                print(f"⚠️ {self.symbol}のデータ取得に失敗しました")
                return False
                
            print(f"✅ データ取得成功: {len(self.data)}日分")
            print(f"期間: {self.data.index[0].date()} - {self.data.index[-1].date()}")
            return True
            
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
            return False
    
    def calculate_breakout_signals(self, lookback_period=20):
        """
        ブレイクアウトシグナル計算
        
        Args:
            lookback_period: ルックバック期間
            
        Returns:
            tuple: (buy_signals, sell_signals)
        """
        if self.data is None:
            return None, None
            
        close = self.data['Close']
        high = self.data['High']
        low = self.data['Low']
        
        # ローリング最高値・最安値計算
        rolling_high = high.rolling(lookback_period).max()
        rolling_low = low.rolling(lookback_period).min()
        
        # ブレイクアウトシグナル
        # 上方ブレイクアウト: 終値が過去N日の最高値を更新
        buy_signals = close > rolling_high.shift(1)
        
        # 下方ブレイクアウト: 終値が過去N日の最安値を下回る
        sell_signals = close < rolling_low.shift(1)
        
        return buy_signals, sell_signals
    
    def run_single_backtest(self, lookback_period=20):
        """
        単一パラメータでのバックテスト
        
        Args:
            lookback_period: ルックバック期間
            
        Returns:
            vbt.Portfolio: ポートフォリオ結果
        """
        if self.data is None:
            print("❌ データが読み込まれていません")
            return None
            
        # シグナル計算
        buy_signals, sell_signals = self.calculate_breakout_signals(lookback_period)
        
        if buy_signals is None:
            return None
            
        # バックテスト実行
        portfolio = vbt.Portfolio.from_signals(
            self.data['Close'],
            buy_signals,
            sell_signals,
            init_cash=10000,
            fees=0.001  # 0.1%の手数料
        )
        
        return portfolio
    
    def run_parameter_optimization(self, lookback_range=(5, 50, 5)):
        """
        パラメータ最適化
        
        Args:
            lookback_range: (start, stop, step)
            
        Returns:
            dict: 最適化結果
        """
        if self.data is None:
            print("❌ データが読み込まれていません")
            return None
            
        print("🔄 パラメータ最適化開始...")
        
        start, stop, step = lookback_range
        lookback_periods = range(start, stop + 1, step)
        
        results = []
        
        for lookback in lookback_periods:
            portfolio = self.run_single_backtest(lookback)
            
            if portfolio is not None:
                stats = portfolio.stats()
                results.append({
                    'lookback_period': lookback,
                    'total_return': portfolio.total_return(),
                    'sharpe_ratio': portfolio.sharpe_ratio(),
                    'max_drawdown': portfolio.max_drawdown(),
                    'total_trades': stats['Total Trades'],
                    'win_rate': stats['Win Rate [%]'],
                    'profit_factor': stats['Profit Factor']
                })
        
        # 結果をDataFrameに変換
        results_df = pd.DataFrame(results)
        
        # シャープレシオで最適化
        best_idx = results_df['sharpe_ratio'].idxmax()
        best_result = results_df.loc[best_idx]
        
        print(f"✅ 最適化完了: {len(results)}パラメータをテスト")
        print(f"🏆 最適パラメータ: {best_result['lookback_period']}")
        print(f"📊 最適シャープレシオ: {best_result['sharpe_ratio']:.3f}")
        
        return {
            'best_params': best_result,
            'all_results': results_df
        }
    
    def analyze_results(self, portfolio):
        """
        詳細な結果分析
        
        Args:
            portfolio: VectorBTポートフォリオ
        """
        if portfolio is None:
            return
            
        print("\n" + "="*50)
        print("📊 バックテスト結果分析")
        print("="*50)
        
        # 基本統計
        stats = portfolio.stats()
        
        print(f"💰 総リターン: {portfolio.total_return():.2%}")
        print(f"📈 年間リターン: {portfolio.annualized_return():.2%}")
        print(f"📉 最大ドローダウン: {portfolio.max_drawdown():.2%}")
        print(f"⚡ シャープレシオ: {portfolio.sharpe_ratio():.3f}")
        print(f"🎯 勝率: {stats['Win Rate [%]']:.1f}%")
        print(f"🔄 総取引数: {stats['Total Trades']}")
        print(f"💹 プロフィットファクター: {stats['Profit Factor']:.3f}")
        
        # 取引詳細
        trades = portfolio.trades.records_readable
        if len(trades) > 0:
            print(f"\n🏆 平均利益: {trades['PnL'].mean():.2f}")
            print(f"📊 勝利取引数: {(trades['PnL'] > 0).sum()}")
            print(f"📊 損失取引数: {(trades['PnL'] <= 0).sum()}")
            
            # 最大利益・損失
            max_win = trades['PnL'].max()
            max_loss = trades['PnL'].min()
            print(f"🎉 最大利益: {max_win:.2f}")
            print(f"😱 最大損失: {max_loss:.2f}")

def main():
    """メイン実行関数"""
    print("🚀 VectorBT ブレイクアウト戦略テスト開始")
    print("="*50)
    
    # 戦略インスタンス作成
    strategy = BreakoutStrategy()
    
    # データ取得
    if not strategy.load_data():
        return
    
    # 単一パラメータテスト
    print("\n📊 単一パラメータテスト (lookback=20)")
    portfolio = strategy.run_single_backtest(lookback_period=20)
    
    if portfolio is not None:
        strategy.analyze_results(portfolio)
    
    # パラメータ最適化
    print("\n🔧 パラメータ最適化実行")
    optimization_results = strategy.run_parameter_optimization()
    
    if optimization_results:
        # 最適パラメータでのバックテスト
        best_lookback = int(optimization_results['best_params']['lookback_period'])
        print(f"\n🏆 最適パラメータ({best_lookback})での詳細分析")
        
        best_portfolio = strategy.run_single_backtest(best_lookback)
        if best_portfolio:
            strategy.analyze_results(best_portfolio)

if __name__ == "__main__":
    main()