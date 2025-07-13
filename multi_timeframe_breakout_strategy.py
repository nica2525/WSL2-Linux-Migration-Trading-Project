#!/usr/bin/env python3
"""
マルチタイムフレーム・ブレイクアウト戦略
フェーズ3: 高頻度・統計的信頼性重視の次世代戦略

フェーズ2の学習成果:
- 時間制限撤廃による取引頻度向上
- 複数時間軸による確度向上
- ATR動的リスク管理
"""

import math
import random
from datetime import datetime, timedelta
from collections import defaultdict

class MultiTimeframeData:
    """複数時間軸データ管理クラス"""
    
    def __init__(self, raw_data, base_timeframe='M5'):
        """
        初期化
        
        Args:
            raw_data: M5ベースの生データ
            base_timeframe: ベース時間軸（M5）
        """
        self.raw_data = sorted(raw_data, key=lambda x: x['datetime'])
        self.base_timeframe = base_timeframe
        self.h1_data = self._aggregate_to_h1()
        self.h4_data = self._aggregate_to_h4()
        
    def _aggregate_to_h1(self):
        """M5データをH1に集約"""
        h1_data = []
        current_hour = None
        hour_bars = []
        
        for bar in self.raw_data:
            hour_key = bar['datetime'].replace(minute=0, second=0, microsecond=0)
            
            if current_hour != hour_key:
                if hour_bars:
                    # 前の時間のH1バーを作成
                    h1_bar = self._create_aggregated_bar(hour_bars, current_hour)
                    h1_data.append(h1_bar)
                
                current_hour = hour_key
                hour_bars = [bar]
            else:
                hour_bars.append(bar)
        
        # 最後の時間のバーを処理
        if hour_bars:
            h1_bar = self._create_aggregated_bar(hour_bars, current_hour)
            h1_data.append(h1_bar)
            
        return h1_data
    
    def _aggregate_to_h4(self):
        """H1データをH4に集約"""
        h4_data = []
        current_h4 = None
        h4_bars = []
        
        for bar in self.h1_data:
            # H4の開始時間（0, 4, 8, 12, 16, 20時）
            h4_hour = (bar['datetime'].hour // 4) * 4
            h4_key = bar['datetime'].replace(hour=h4_hour, minute=0, second=0, microsecond=0)
            
            if current_h4 != h4_key:
                if h4_bars:
                    # 前のH4バーを作成
                    h4_bar = self._create_aggregated_bar(h4_bars, current_h4)
                    h4_data.append(h4_bar)
                
                current_h4 = h4_key
                h4_bars = [bar]
            else:
                h4_bars.append(bar)
        
        # 最後のH4バーを処理
        if h4_bars:
            h4_bar = self._create_aggregated_bar(h4_bars, current_h4)
            h4_data.append(h4_bar)
            
        return h4_data
    
    def _create_aggregated_bar(self, bars, datetime_key):
        """複数バーから集約バーを作成"""
        if not bars:
            return None
            
        return {
            'datetime': datetime_key,
            'open': bars[0]['open'],
            'high': max(bar['high'] for bar in bars),
            'low': min(bar['low'] for bar in bars),
            'close': bars[-1]['close'],
            'volume': sum(bar['volume'] for bar in bars)
        }
    
    def get_aligned_data(self, target_datetime):
        """指定時刻での各時間軸データを取得"""
        # M5データ
        m5_bar = None
        for bar in reversed(self.raw_data):
            if bar['datetime'] <= target_datetime:
                m5_bar = bar
                break
        
        # H1データ
        h1_bar = None
        for bar in reversed(self.h1_data):
            if bar['datetime'] <= target_datetime:
                h1_bar = bar
                break
        
        # H4データ
        h4_bar = None
        for bar in reversed(self.h4_data):
            if bar['datetime'] <= target_datetime:
                h4_bar = bar
                break
                
        return {
            'M5': m5_bar,
            'H1': h1_bar,
            'H4': h4_bar
        }
    
    def get_h1_data(self):
        """H1データを取得（互換性用）"""
        return self.h1_data
    
    def get_h4_data(self):
        """H4データを取得（互換性用）"""
        return self.h4_data

class ATRCalculator:
    """ATR（Average True Range）計算クラス"""
    
    def __init__(self, period=14):
        self.period = period
        
    def calculate_tr(self, current_bar, previous_bar):
        """True Range計算"""
        if not previous_bar:
            return current_bar['high'] - current_bar['low']
            
        tr1 = current_bar['high'] - current_bar['low']
        tr2 = abs(current_bar['high'] - previous_bar['close'])
        tr3 = abs(current_bar['low'] - previous_bar['close'])
        
        return max(tr1, tr2, tr3)
    
    def calculate_atr(self, data, index):
        """ATR計算"""
        if index < self.period:
            return 0.001  # デフォルト値
            
        tr_values = []
        for i in range(index - self.period + 1, index + 1):
            if i > 0:
                tr = self.calculate_tr(data[i], data[i-1])
                tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values) if tr_values else 0.001

class MultiTimeframeBreakoutStrategy:
    """マルチタイムフレーム・ブレイクアウト戦略"""
    
    def __init__(self, params=None):
        """
        初期化
        
        Args:
            params: 戦略パラメータ
        """
        self.params = params or {
            'h4_period': 24,      # H4レンジ期間（4日間）
            'h1_period': 24,      # H1レンジ期間（1日間）
            'atr_period': 14,     # ATR期間
            'profit_atr': 2.0,    # 利確ATR倍数
            'stop_atr': 1.5,      # 損切ATR倍数
            'min_break_pips': 5   # 最小ブレイク幅（pips）
        }
        
        self.atr_calc = ATRCalculator(self.params['atr_period'])
        
    def get_h4_range(self, h4_data, current_index):
        """H4レンジの高値・安値を取得"""
        if current_index < self.params['h4_period']:
            return None, None
            
        start_idx = current_index - self.params['h4_period']
        end_idx = current_index
        
        range_bars = h4_data[start_idx:end_idx]
        if not range_bars:
            return None, None
            
        h4_high = max(bar['high'] for bar in range_bars)
        h4_low = min(bar['low'] for bar in range_bars)
        
        return h4_high, h4_low
    
    def get_h1_range(self, h1_data, current_index):
        """H1レンジの高値・安値を取得"""
        if current_index < self.params['h1_period']:
            return None, None
            
        start_idx = current_index - self.params['h1_period']
        end_idx = current_index
        
        range_bars = h1_data[start_idx:end_idx]
        if not range_bars:
            return None, None
            
        h1_high = max(bar['high'] for bar in range_bars)
        h1_low = min(bar['low'] for bar in range_bars)
        
        return h1_high, h1_low
    
    def check_session_filter(self, dt):
        """主要セッション時間フィルター"""
        hour = dt.hour
        
        # 主要セッション時間（GMT基準）
        # ロンドン: 07:00-16:00, NY: 12:00-21:00, 東京: 23:00-08:00
        london_session = 7 <= hour < 16
        ny_session = 12 <= hour < 21
        tokyo_session = hour >= 23 or hour < 8
        
        # いずれかの主要セッション時間であればOK
        return london_session or ny_session or tokyo_session
    
    def generate_signal(self, mtf_data, current_datetime):
        """
        シグナル生成
        
        Args:
            mtf_data: マルチタイムフレームデータ
            current_datetime: 現在時刻
            
        Returns:
            dict: シグナル情報またはNone
        """
        aligned_data = mtf_data.get_aligned_data(current_datetime)
        
        # データ不足チェック
        if not all(aligned_data.values()):
            return None
        
        # セッション時間フィルター
        if not self.check_session_filter(current_datetime):
            return None
        
        current_price = aligned_data['M5']['close']
        
        # H4レンジ取得
        h4_index = len([bar for bar in mtf_data.h4_data if bar['datetime'] <= current_datetime]) - 1
        h4_high, h4_low = self.get_h4_range(mtf_data.h4_data, h4_index)
        
        # H1レンジ取得
        h1_index = len([bar for bar in mtf_data.h1_data if bar['datetime'] <= current_datetime]) - 1
        h1_high, h1_low = self.get_h1_range(mtf_data.h1_data, h1_index)
        
        if h4_high is None or h1_high is None:
            return None
        
        # ATR計算
        h1_atr = self.atr_calc.calculate_atr(mtf_data.h1_data, h1_index)
        
        # 最小ブレイク幅
        min_break = self.params['min_break_pips'] * 0.0001
        
        # マルチタイムフレーム・ブレイクアウト判定
        signal = None
        
        # ロングシグナル: H4とH1両方の高値ブレイク
        if (current_price > h4_high + min_break and 
            current_price > h1_high + min_break):
            
            signal = {
                'type': 'long',
                'datetime': current_datetime,
                'entry_price': current_price,
                'profit_target': current_price + (h1_atr * self.params['profit_atr']),
                'stop_loss': current_price - (h1_atr * self.params['stop_atr']),
                'h4_high': h4_high,
                'h4_low': h4_low,
                'h1_high': h1_high,
                'h1_low': h1_low,
                'atr': h1_atr
            }
        
        # ショートシグナル: H4とH1両方の安値ブレイク
        elif (current_price < h4_low - min_break and 
              current_price < h1_low - min_break):
            
            signal = {
                'type': 'short',
                'datetime': current_datetime,
                'entry_price': current_price,
                'profit_target': current_price - (h1_atr * self.params['profit_atr']),
                'stop_loss': current_price + (h1_atr * self.params['stop_atr']),
                'h4_high': h4_high,
                'h4_low': h4_low,
                'h1_high': h1_high,
                'h1_low': h1_low,
                'atr': h1_atr
            }
        
        return signal
    
    def backtest(self, mtf_data, start_date=None, end_date=None):
        """
        バックテスト実行
        
        Args:
            mtf_data: マルチタイムフレームデータ
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            dict: バックテスト結果
        """
        signals = []
        trades = []
        
        # データ期間の設定
        if start_date is None:
            start_date = mtf_data.raw_data[0]['datetime']
        if end_date is None:
            end_date = mtf_data.raw_data[-1]['datetime']
        
        # シグナル生成（1時間ごとにチェック）
        current_dt = start_date
        while current_dt <= end_date:
            signal = self.generate_signal(mtf_data, current_dt)
            if signal:
                signals.append(signal)
            
            current_dt += timedelta(hours=1)  # 1時間ステップ
        
        # トレード結果計算（実際の価格追跡による）
        for signal in signals:
            # 実際の価格データを使用した取引結果計算
            exit_price, result = self._track_trade_outcome(signal, mtf_data)
            
            # PnL計算
            if signal['type'] == 'long':
                pnl = exit_price - signal['entry_price']
            else:  # short
                pnl = signal['entry_price'] - exit_price
            
            trade = {
                'datetime': signal['datetime'],
                'type': signal['type'],
                'entry_price': signal['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'result': result,
                'atr': signal['atr']
            }
            trades.append(trade)
        
        # パフォーマンス計算
        return self._calculate_performance(trades)
    
    def _calculate_performance(self, trades):
        """パフォーマンス指標計算"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade['result'] == 'win')
        win_rate = winning_trades / total_trades
        
        wins = [trade['pnl'] for trade in trades if trade['pnl'] > 0]
        losses = [trade['pnl'] for trade in trades if trade['pnl'] < 0]
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0.001
        
        profit_factor = gross_profit / gross_loss
        total_pnl = sum(trade['pnl'] for trade in trades)
        
        # ドローダウン計算
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
            std_return = math.sqrt(variance) if variance > 0 else 0.001
            sharpe_ratio = mean_return / std_return
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': sum(wins) / len(wins) if wins else 0,
            'avg_loss': sum(losses) / len(losses) if losses else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'trades': trades
        }
    
    def _track_trade_outcome(self, signal, mtf_data):
        """
        実際の価格追跡による取引結果計算
        
        Args:
            signal: 取引シグナル
            mtf_data: マルチタイムフレームデータ
            
        Returns:
            tuple: (exit_price, result)
        """
        signal_time = signal['datetime']
        signal_type = signal['type']
        entry_price = signal['entry_price']
        profit_target = signal['profit_target']
        stop_loss = signal['stop_loss']
        
        # シグナル発生後の価格を追跡（最大48時間または100バー）
        max_tracking_hours = 48
        end_time = signal_time + timedelta(hours=max_tracking_hours)
        
        current_time = signal_time + timedelta(hours=1)  # 1時間後から開始
        
        while current_time <= end_time:
            # 現在時刻での価格データ取得
            aligned_data = mtf_data.get_aligned_data(current_time)
            
            if aligned_data['M5'] is None:
                current_time += timedelta(hours=1)
                continue
                
            current_high = aligned_data['M5']['high']
            current_low = aligned_data['M5']['low']
            
            if signal_type == 'long':
                # ロングポジション
                if current_high >= profit_target:
                    # 利確達成
                    return profit_target, 'win'
                elif current_low <= stop_loss:
                    # ストップロス到達
                    return stop_loss, 'loss'
            else:
                # ショートポジション
                if current_low <= profit_target:
                    # 利確達成
                    return profit_target, 'win'
                elif current_high >= stop_loss:
                    # ストップロス到達
                    return stop_loss, 'loss'
            
            current_time += timedelta(hours=1)
        
        # 追跡期間内に決着がつかない場合は最終価格で決済
        final_aligned_data = mtf_data.get_aligned_data(end_time)
        if final_aligned_data['M5']:
            final_price = final_aligned_data['M5']['close']
            return final_price, 'timeout'
        else:
            # データなしの場合はエントリー価格で決済
            return entry_price, 'timeout'

def create_enhanced_sample_data():
    """強化されたサンプルデータ生成（5年間・40万バー）"""
    import random
    
    base_date = datetime(2019, 1, 1)  # 5年間データ
    data = []
    
    current_date = base_date
    price = 1.1000
    
    # より現実的な価格変動パターン
    trend_direction = 1
    trend_strength = 0.0001
    volatility = 0.0001
    
    for i in range(400000):  # 約5年分のM5バー（品質優先）
        # トレンドとボラティリティの変化
        if i % 5000 == 0:  # 約2週間ごとにトレンド変更
            trend_direction = random.choice([-1, 0, 1])
            trend_strength = random.uniform(0.00005, 0.0002)
            volatility = random.uniform(0.00005, 0.0003)
        
        # 価格変動
        trend_component = trend_direction * trend_strength
        random_component = random.gauss(0, volatility)
        price_change = trend_component + random_component
        
        price += price_change
        price = max(0.9000, min(1.3000, price))  # 価格範囲制限
        
        # OHLC生成
        base_price = price
        high = base_price + random.uniform(0, volatility * 2)
        low = base_price - random.uniform(0, volatility * 2)
        close = base_price + random.gauss(0, volatility * 0.5)
        
        data.append({
            'datetime': current_date,
            'open': base_price,
            'high': max(base_price, high, close),
            'low': min(base_price, low, close),
            'close': close,
            'volume': random.randint(50, 200)
        })
        
        current_date += timedelta(minutes=5)
        
        # 週末はスキップ
        if current_date.weekday() >= 5:
            current_date += timedelta(days=2)
            current_date = current_date.replace(hour=0, minute=0)
    
    return data

def main():
    """メイン実行関数"""
    print("🚀 フェーズ3: マルチタイムフレーム・ブレイクアウト戦略実行開始")
    
    # 強化されたサンプルデータ生成
    print("📊 5年間サンプルデータ生成中...")
    raw_data = create_enhanced_sample_data()
    print(f"   生成データ数: {len(raw_data)}バー")
    
    # マルチタイムフレームデータ構築
    print("🔄 マルチタイムフレームデータ構築中...")
    mtf_data = MultiTimeframeData(raw_data)
    print(f"   H1データ: {len(mtf_data.h1_data)}バー")
    print(f"   H4データ: {len(mtf_data.h4_data)}バー")
    
    # 戦略パラメータ
    strategy_params = {
        'h4_period': 24,      # H4レンジ期間（4日間）
        'h1_period': 24,      # H1レンジ期間（1日間）
        'atr_period': 14,     # ATR期間
        'profit_atr': 2.0,    # 利確ATR倍数
        'stop_atr': 1.5,      # 損切ATR倍数
        'min_break_pips': 5   # 最小ブレイク幅
    }
    
    # 戦略インスタンス
    strategy = MultiTimeframeBreakoutStrategy(strategy_params)
    
    # Stage1: 高速検証（70/30分割）
    print(f"\n📈 Stage1: 高速検証実行中...")
    
    total_days = (raw_data[-1]['datetime'] - raw_data[0]['datetime']).days
    is_end_date = raw_data[0]['datetime'] + timedelta(days=int(total_days * 0.7))
    
    # IS期間バックテスト
    is_result = strategy.backtest(mtf_data, raw_data[0]['datetime'], is_end_date)
    print(f"   IS結果: PF={is_result['profit_factor']:.3f}, 取引数={is_result['total_trades']}")
    
    # OOS期間バックテスト
    oos_result = strategy.backtest(mtf_data, is_end_date, raw_data[-1]['datetime'])
    print(f"   OOS結果: PF={oos_result['profit_factor']:.3f}, 取引数={oos_result['total_trades']}")
    
    # Stage1判定
    stage1_pass = (oos_result['profit_factor'] >= 1.1 and 
                   oos_result['total_trades'] >= 100)
    
    print(f"\n🎯 Stage1判定: {'合格' if stage1_pass else '不合格'}")
    print(f"   OOS PF: {oos_result['profit_factor']:.3f} ({'≥1.1' if oos_result['profit_factor'] >= 1.1 else '<1.1'})")
    print(f"   取引数: {oos_result['total_trades']} ({'≥100' if oos_result['total_trades'] >= 100 else '<100'})")
    print(f"   勝率: {oos_result['win_rate']:.1%}")
    print(f"   最大DD: {oos_result['max_drawdown']:.4f}")
    
    if stage1_pass:
        print(f"\n✅ Stage1合格！Stage2（WFA検証）への移行準備完了")
    else:
        print(f"\n❌ Stage1不合格。パラメータ調整または戦略見直しが必要")
        print(f"   改善点:")
        if oos_result['profit_factor'] < 1.1:
            print(f"   - プロフィットファクター向上（現在{oos_result['profit_factor']:.3f}）")
        if oos_result['total_trades'] < 100:
            print(f"   - 取引頻度向上（現在{oos_result['total_trades']}回）")
    
    return mtf_data, strategy, is_result, oos_result, stage1_pass

if __name__ == "__main__":
    mtf_data, strategy, is_result, oos_result, stage1_pass = main()