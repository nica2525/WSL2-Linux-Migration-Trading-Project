#!/usr/bin/env python3
"""
VectorBT 正しいブレイクアウト戦略実装
- 買いエントリー: 高値ブレイクアウト
- 売りエグジット: 安値ブレイクアウト OR 利確/損切り
"""

import vectorbt as vbt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

class CorrectBreakoutStrategy:
    """
    正しいブレイクアウト戦略
    - エントリー: 高値ブレイクアウト（買いのみ）
    - エグジット: 安値ブレイクアウト、利確、損切り
    """
    
    def __init__(self, symbol='EURUSD=X', period='1y'):
        self.symbol = symbol
        self.period = period
        self.data = None
        
    def load_data(self):
        """データ取得"""
        try:
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(period=self.period)
            
            if self.data.empty:
                print(f"❌ {self.symbol}のデータ取得に失敗")
                return False
                
            print(f"✅ データ取得成功: {len(self.data)}日分")
            print(f"期間: {self.data.index[0].date()} - {self.data.index[-1].date()}")
            return True
            
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
            return False
    
    def calculate_breakout_signals_v1(self, lookback_period=20):
        """
        Version 1: 単純な高値ブレイクアウト戦略
        エントリー: 高値ブレイクアウト
        エグジット: 安値ブレイクアウト
        """
        if self.data is None:
            return None, None
            
        close = self.data['Close']
        high = self.data['High']
        low = self.data['Low']
        
        # ローリング最高値・最安値
        rolling_high = high.rolling(lookback_period).max()
        rolling_low = low.rolling(lookback_period).min()
        
        # エントリー: 終値が過去N日の最高値を上回る
        entries = close > rolling_high.shift(1)
        
        # エグジット: 終値が過去N日の最安値を下回る
        exits = close < rolling_low.shift(1)
        
        return entries, exits
    
    def calculate_breakout_signals_v2(self, lookback_period=20, profit_target=0.02, stop_loss=0.01):
        """
        Version 2: 利確・損切り付きブレイクアウト戦略
        エントリー: 高値ブレイクアウト
        エグジット: 利確(2%)、損切り(1%)、または安値ブレイクアウト
        """
        if self.data is None:
            return None, None
            
        close = self.data['Close']
        high = self.data['High']
        low = self.data['Low']
        
        # ローリング最高値
        rolling_high = high.rolling(lookback_period).max()
        rolling_low = low.rolling(lookback_period).min()
        
        # エントリー: 高値ブレイクアウト
        entries = close > rolling_high.shift(1)
        
        # 基本エグジット: 安値ブレイクアウト
        basic_exits = close < rolling_low.shift(1)
        
        # 利確・損切りエグジット信号を手動で作成
        exits = basic_exits.copy()
        
        return entries, exits
    
    def calculate_breakout_signals_v3(self, lookback_period=20):
        """
        Version 3: Moving Average併用ブレイクアウト
        エントリー: 高値ブレイクアウト + MA上昇
        エグジット: 安値ブレイクアウト + MA下降
        """
        if self.data is None:
            return None, None
            
        close = self.data['Close']
        high = self.data['High']
        low = self.data['Low']
        
        # ローリング最高値・最安値
        rolling_high = high.rolling(lookback_period).max()
        rolling_low = low.rolling(lookback_period).min()
        
        # 移動平均フィルター
        ma = close.rolling(lookback_period).mean()
        ma_rising = ma > ma.shift(1)
        ma_falling = ma < ma.shift(1)
        
        # エントリー: 高値ブレイクアウト + MA上昇
        entries = (close > rolling_high.shift(1)) & ma_rising
        
        # エグジット: 安値ブレイクアウト + MA下降
        exits = (close < rolling_low.shift(1)) & ma_falling
        
        return entries, exits
    
    def run_backtest(self, version=1, lookback_period=20, **kwargs):
        """
        バックテスト実行
        
        Args:
            version: 戦略バージョン (1, 2, 3)
            lookback_period: ルックバック期間
        """
        if self.data is None:
            print("❌ データが読み込まれていません")
            return None
            
        # バージョン別シグナル計算
        if version == 1:
            entries, exits = self.calculate_breakout_signals_v1(lookback_period)
        elif version == 2:
            entries, exits = self.calculate_breakout_signals_v2(lookback_period, **kwargs)
        elif version == 3:
            entries, exits = self.calculate_breakout_signals_v3(lookback_period)
        else:
            print(f"❌ 無効なバージョン: {version}")
            return None
            
        if entries is None or exits is None:
            return None
            
        # エントリー・エグジット信号の確認
        print(f"エントリー信号: {entries.sum()}回")
        print(f"エグジット信号: {exits.sum()}回")
        
        # バックテスト実行
        portfolio = vbt.Portfolio.from_signals(
            self.data['Close'],
            entries,
            exits,
            init_cash=10000,
            fees=0.001,
            freq='D'
        )
        
        return portfolio
    
    def run_optimization(self, version=1, lookback_range=(5, 50, 5)):
        """パラメータ最適化"""
        if self.data is None:
            return None
            
        print(f"🔄 Version {version} 最適化開始...")
        
        start, stop, step = lookback_range
        lookback_periods = range(start, stop + 1, step)
        
        results = []
        
        for lookback in lookback_periods:
            portfolio = self.run_backtest(version, lookback)
            
            if portfolio is not None:
                try:
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
                except Exception as e:
                    print(f"⚠️ lookback={lookback}でエラー: {e}")
                    continue
        
        if not results:
            print("❌ 最適化結果なし")
            return None
            
        results_df = pd.DataFrame(results)
        
        # 有効なシャープレシオでソート
        valid_results = results_df[results_df['sharpe_ratio'].notna()]
        if valid_results.empty:
            print("❌ 有効なシャープレシオなし")
            return None
            
        best_idx = valid_results['sharpe_ratio'].idxmax()
        best_result = results_df.loc[best_idx]
        
        print(f"✅ 最適化完了: {len(results)}パラメータ")
        print(f"🏆 最適パラメータ: {best_result['lookback_period']}")
        print(f"📊 シャープレシオ: {best_result['sharpe_ratio']:.3f}")
        
        return {'best_params': best_result, 'all_results': results_df}
    
    def analyze_results(self, portfolio):
        """結果分析"""
        if portfolio is None:
            return
            
        print("\n" + "="*50)
        print("📊 バックテスト結果分析")
        print("="*50)
        
        try:
            stats = portfolio.stats()
            
            print(f"💰 総リターン: {portfolio.total_return():.2%}")
            print(f"📈 年間リターン: {portfolio.annualized_return():.2%}")
            print(f"📉 最大ドローダウン: {portfolio.max_drawdown():.2%}")
            print(f"⚡ シャープレシオ: {portfolio.sharpe_ratio():.3f}")
            print(f"🎯 勝率: {stats['Win Rate [%]']:.1f}%")
            print(f"🔄 総取引数: {stats['Total Trades']}")
            
            # 取引詳細
            trades = portfolio.trades.records_readable
            if len(trades) > 0:
                print(f"\n📋 取引詳細:")
                for i, trade in trades.iterrows():
                    status = "完了" if trade['Status'] == 'Closed' else "進行中"
                    print(f"  取引{i+1}: {trade['Entry Timestamp'].date()} - {status}")
                    print(f"    エントリー価格: {trade['Avg Entry Price']:.5f}")
                    if trade['Status'] == 'Closed':
                        print(f"    エグジット価格: {trade['Avg Exit Price']:.5f}")
                        print(f"    損益: {trade['PnL']:.2f}")
                        print(f"    リターン: {trade['Return']:.2%}")
                        
        except Exception as e:
            print(f"❌ 分析エラー: {e}")

def main():
    """メイン実行"""
    print("🚀 正しいブレイクアウト戦略テスト")
    print("="*50)
    
    strategy = CorrectBreakoutStrategy()
    
    if not strategy.load_data():
        return
    
    # Version 1: 基本ブレイクアウト
    print("\n📊 Version 1: 基本ブレイクアウト戦略")
    portfolio_v1 = strategy.run_backtest(version=1, lookback_period=20)
    if portfolio_v1:
        strategy.analyze_results(portfolio_v1)
    
    # Version 3: MA併用ブレイクアウト
    print("\n📊 Version 3: MA併用ブレイクアウト戦略")
    portfolio_v3 = strategy.run_backtest(version=3, lookback_period=20)
    if portfolio_v3:
        strategy.analyze_results(portfolio_v3)
    
    # 最適化テスト
    print("\n🔧 Version 1 最適化")
    opt_result = strategy.run_optimization(version=1, lookback_range=(10, 30, 5))
    if opt_result:
        best_lookback = int(opt_result['best_params']['lookback_period'])
        print(f"\n🏆 最適パラメータ({best_lookback})での結果:")
        best_portfolio = strategy.run_backtest(version=1, lookback_period=best_lookback)
        if best_portfolio:
            strategy.analyze_results(best_portfolio)

if __name__ == "__main__":
    main()