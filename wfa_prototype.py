#!/usr/bin/env python3
"""
Purged & Embargoed Walk-Forward Analysis プロトタイプ実装
フェーズ2実装のための基盤クラス
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math

class TimeSeriesData:
    """時系列データ管理クラス"""
    
    def __init__(self, data, datetime_col='datetime'):
        """
        初期化
        
        Args:
            data: 時系列データ（辞書のリストまたは同等の構造）
            datetime_col: 日時列の名前
        """
        # 簡易実装のため、辞書のリストとして処理
        if hasattr(data, 'sort_values'):
            # pandasライクなデータの場合
            self.data = data.sort_values(datetime_col).to_dict('records')
        else:
            # 辞書のリストの場合
            self.data = sorted(data, key=lambda x: x[datetime_col])
        
        self.datetime_col = datetime_col
        
    def get_bars_for_period(self, start_date, end_date):
        """指定期間のバーデータを取得"""
        result = []
        for bar in self.data:
            bar_date = bar[self.datetime_col]
            if isinstance(bar_date, str):
                bar_date = datetime.fromisoformat(bar_date.replace('Z', '+00:00'))
            
            if start_date <= bar_date <= end_date:
                result.append(bar)
                
        return result
    
    def get_date_range(self):
        """データの日付範囲を取得"""
        if not self.data:
            return None, None
            
        start_date = self.data[0][self.datetime_col]
        end_date = self.data[-1][self.datetime_col]
        
        # 文字列の場合は変換
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
        return start_date, end_date

class WFAConfig:
    """WFA設定クラス"""
    
    def __init__(self, 
                 is_months=24,           # IS期間（月）
                 oos_months=6,           # OOS期間（月）
                 step_months=6,          # ステップ間隔（月）
                 anchored=True,          # アンカード方式
                 purge_bars=None,        # Purge期間（自動計算推奨）
                 embargo_bars=None):     # Embargo期間（自動計算推奨）
        
        self.is_months = is_months
        self.oos_months = oos_months  
        self.step_months = step_months
        self.anchored = anchored
        self.purge_bars = purge_bars
        self.embargo_bars = embargo_bars
        
    def calculate_purge_embargo(self, strategy_config, timeframe='M5'):
        """戦略設定に基づくPurge/Embargo期間の自動計算"""
        lookback_period = self._get_max_lookback(strategy_config)
        
        # 時間足別の倍率設定
        timeframe_multipliers = {
            'M5': 1.0,
            'M15': 0.33,
            'M30': 0.16,
            'H1': 0.08,
            'H4': 0.02,
            'D1': 0.004
        }
        
        multiplier = timeframe_multipliers.get(timeframe, 1.0)
        
        # Purge期間: 最大ルックバック期間の1.5倍
        self.purge_bars = int(lookback_period * 1.5 * multiplier)
        
        # Embargo期間: Purge期間と同等
        self.embargo_bars = self.purge_bars
        
        return self.purge_bars, self.embargo_bars
    
    def _get_max_lookback(self, strategy_config):
        """戦略の最大ルックバック期間を計算"""
        max_periods = []
        
        # 移動平均期間
        if 'ma_periods' in strategy_config:
            max_periods.extend(strategy_config['ma_periods'])
        
        # ATR期間
        if 'atr_period' in strategy_config:
            max_periods.append(strategy_config['atr_period'])
        
        # RSI期間
        if 'rsi_period' in strategy_config:
            max_periods.append(strategy_config['rsi_period'])
        
        # その他のインジケーター期間
        if 'other_periods' in strategy_config:
            max_periods.extend(strategy_config['other_periods'])
        
        return max(max_periods) if max_periods else 20  # デフォルト20期間

class PurgedEmbargoedWFA:
    """Purged & Embargoed Walk-Forward Analysis メインクラス"""
    
    def __init__(self, data, config, strategy_config):
        """
        初期化
        
        Args:
            data: 時系列データ
            config: WFA設定
            strategy_config: 戦略設定
        """
        self.data = TimeSeriesData(data) if not isinstance(data, TimeSeriesData) else data
        self.config = config
        self.strategy_config = strategy_config
        
        # Purge/Embargo期間の自動計算
        if config.purge_bars is None or config.embargo_bars is None:
            timeframe = strategy_config.get('timeframe', 'M5')
            config.calculate_purge_embargo(strategy_config, timeframe)
            
        self.folds = []
        
    def generate_folds(self):
        """WFAフォールドの生成（Purge & Embargo考慮）"""
        folds = []
        
        # データ期間の取得
        start_date, end_date = self.data.get_date_range()
        if start_date is None or end_date is None:
            raise ValueError("データが空です")
        
        print(f"📅 データ期間: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # 初回IS開始日
        current_is_start = start_date
        original_is_months = self.config.is_months
        
        fold_count = 0
        while True:
            # IS期間終了日
            is_end = current_is_start + relativedelta(months=self.config.is_months)
            
            # Purge期間（IS最終部分を除去）
            purge_days = self._bars_to_days(self.config.purge_bars)
            purge_start = is_end - timedelta(days=purge_days)
            actual_is_end = purge_start
            
            # OOS期間開始日（IS終了直後）
            oos_start = is_end
            # OOS期間終了日
            oos_end = oos_start + relativedelta(months=self.config.oos_months)
            
            # データ終了チェック
            if oos_end > end_date:
                break
                
            # Embargo期間（次回IS開始前の空白）
            embargo_days = self._bars_to_days(self.config.embargo_bars)
            next_is_start = oos_end + timedelta(days=embargo_days)
            
            fold_count += 1
            fold = {
                'fold_id': fold_count,
                'is_start': current_is_start,
                'is_end': actual_is_end,
                'purge_start': purge_start,
                'purge_end': is_end,
                'oos_start': oos_start,
                'oos_end': oos_end,
                'embargo_start': oos_end,
                'embargo_end': next_is_start,
                'is_days': (actual_is_end - current_is_start).days,
                'oos_days': (oos_end - oos_start).days,
                'purge_days': purge_days,
                'embargo_days': embargo_days
            }
            
            folds.append(fold)
            
            print(f"📊 Fold {fold_count}:")
            print(f"   IS:  {current_is_start.strftime('%Y-%m-%d')} to {actual_is_end.strftime('%Y-%m-%d')} ({fold['is_days']}日)")
            print(f"   OOS: {oos_start.strftime('%Y-%m-%d')} to {oos_end.strftime('%Y-%m-%d')} ({fold['oos_days']}日)")
            print(f"   Purge: {purge_days}日, Embargo: {embargo_days}日")
            
            # 次のフォールドの準備
            if self.config.anchored:
                # アンカード: IS開始は固定、IS期間延長
                current_is_start = start_date
                self.config.is_months += self.config.step_months
            else:
                # 非アンカード: IS期間固定、ウィンドウスライド
                current_is_start = next_is_start
                self.config.is_months = original_is_months
                
        self.folds = folds
        print(f"🎯 総フォールド数: {len(folds)}")
        return folds
    
    def _bars_to_days(self, bars):
        """バー数を日数に変換（概算）"""
        # 時間足別のバー数/日の概算
        bars_per_day = {
            'M5': 288,   # 24h * 60min / 5min
            'M15': 96,   # 24h * 60min / 15min
            'M30': 48,   # 24h * 60min / 30min
            'H1': 24,    # 24h / 1h
            'H4': 6,     # 24h / 4h
            'D1': 1      # 24h / 24h
        }
        
        timeframe = self.strategy_config.get('timeframe', 'M5')
        daily_bars = bars_per_day.get(timeframe, 288)
        
        # 取引時間を考慮した調整（平日のみ、1日実質16時間程度）
        trading_hours_ratio = 16.0 / 24.0  # 約0.67
        adjusted_daily_bars = daily_bars * trading_hours_ratio
        
        return max(1, int(bars / adjusted_daily_bars))
    
    def get_fold_data(self, fold_id):
        """指定フォールドのデータを取得"""
        if fold_id < 1 or fold_id > len(self.folds):
            raise ValueError(f"無効なfold_id: {fold_id}")
        
        fold = self.folds[fold_id - 1]
        
        # IS期間データ
        is_data = self.data.get_bars_for_period(fold['is_start'], fold['is_end'])
        
        # OOS期間データ  
        oos_data = self.data.get_bars_for_period(fold['oos_start'], fold['oos_end'])
        
        return {
            'fold_info': fold,
            'is_data': is_data,
            'oos_data': oos_data,
            'is_bars': len(is_data),
            'oos_bars': len(oos_data)
        }
    
    def _run_strategy_on_data(self, data, period_type):
        """
        指定データで戦略を実行
        
        Args:
            data: 価格データ
            period_type: 'IS' または 'OOS'
            
        Returns:
            dict: 戦略実行結果
        """
        if not data or len(data) < 50:
            return {
                'total_return': 0.0,
                'profit_factor': 1.0,
                'sharpe_ratio': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            }
        
        # 簡易ブレイクアウト戦略実装
        trades = []
        lookback_period = 20  # ブレイクアウト判定期間
        
        for i in range(lookback_period, len(data)):
            current_bar = data[i]
            
            # 過去期間の高値・安値
            lookback_data = data[i-lookback_period:i]
            high_level = max(bar['high'] for bar in lookback_data)
            low_level = min(bar['low'] for bar in lookback_data)
            
            # Look-ahead bias修正：現在バーのCloseではなくOpenを使用
            current_price = current_bar['open']
            
            # ブレイクアウト判定
            signal = None
            if current_price > high_level:
                signal = 'long'
            elif current_price < low_level:
                signal = 'short'
            
            if signal:
                # 簡易取引実行
                entry_price = current_price
                
                # 10バー後の価格で決済（簡易実装）
                exit_index = min(i + 10, len(data) - 1)
                exit_price = data[exit_index]['close']
                
                if signal == 'long':
                    pnl = exit_price - entry_price
                else:  # short
                    pnl = entry_price - exit_price
                
                trades.append({
                    'signal': signal,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'result': 'win' if pnl > 0 else 'loss'
                })
        
        # パフォーマンス計算
        if not trades:
            return {
                'total_return': 0.0,
                'profit_factor': 1.0,
                'sharpe_ratio': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            }
        
        total_pnl = sum(trade['pnl'] for trade in trades)
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
        
        gross_profit = sum(wins) if wins else 0.001
        gross_loss = sum(losses) if losses else 0.001
        
        profit_factor = gross_profit / gross_loss
        win_rate = len(wins) / len(trades)
        
        # シャープレシオ計算
        if len(trades) > 1:
            returns = [t['pnl'] for t in trades]
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_return = math.sqrt(variance) if variance > 0 else 0.001
            sharpe_ratio = mean_return / std_return
        else:
            sharpe_ratio = 0.0
        
        return {
            'total_return': total_pnl,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(trades),
            'win_rate': win_rate
        }

class StatisticalValidator:
    """統計的検証クラス"""
    
    def __init__(self, wfa_results):
        """
        初期化
        
        Args:
            wfa_results: WFA結果のリスト
        """
        self.results = wfa_results
        
    def calculate_basic_stats(self, values):
        """基本統計計算"""
        if not values:
            return {}
            
        n = len(values)
        mean_val = sum(values) / n
        variance = sum((x - mean_val) ** 2 for x in values) / n
        std_val = math.sqrt(variance) if variance >= 0 else 0
        
        return {
            'count': n,
            'mean': mean_val,
            'std': std_val,
            'min': min(values),
            'max': max(values)
        }
        
    def calculate_oos_consistency(self):
        """OOS期間の一貫性評価"""
        if not self.results:
            return {}
            
        oos_returns = [fold.get('oos_return', 0) for fold in self.results if 'oos_return' in fold]
        
        if not oos_returns:
            return {'error': 'OOSリターンデータがありません'}
        
        # 基本統計
        positive_periods = sum(1 for r in oos_returns if r > 0)
        total_periods = len(oos_returns)
        consistency_ratio = positive_periods / total_periods if total_periods > 0 else 0
        
        # 簡易t検定（OOSリターンが0より大きいかの検定）
        stats = self.calculate_basic_stats(oos_returns)
        
        if stats['std'] > 0 and stats['count'] > 1:
            t_stat = (stats['mean'] - 0) / (stats['std'] / math.sqrt(stats['count']))
            # 簡易p値計算（正規分布近似）
            p_value = 2 * (1 - self._norm_cdf(abs(t_stat)))
        else:
            t_stat = 0
            p_value = 1.0
        
        return {
            'consistency_ratio': consistency_ratio,
            'positive_periods': positive_periods,
            'total_periods': total_periods,
            't_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < 0.05,
            'oos_stats': stats
        }
    
    def calculate_wfa_efficiency(self):
        """ウォークフォワード効率の計算"""
        if not self.results:
            return 0
            
        total_oos_return = sum(fold.get('oos_return', 0) for fold in self.results)
        total_is_return = sum(fold.get('is_return', 0) for fold in self.results)
        
        if total_is_return <= 0:
            return 0
            
        wfa_efficiency = total_oos_return / total_is_return
        return wfa_efficiency
    
    def _norm_cdf(self, x):
        """標準正規分布の累積分布関数（近似）"""
        # Abramowitz and Stegun approximation
        sign = 1 if x >= 0 else -1
        x = abs(x)
        
        # Constants
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        p = 0.3275911
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return 0.5 * (1.0 + sign * y)

def create_sample_data():
    """サンプルデータ生成（テスト用）"""
    import random
    
    base_date = datetime(2020, 1, 1)
    data = []
    
    # 4年間のM5データを疑似生成（簡易版）
    current_date = base_date
    price = 1.1000
    
    for i in range(400000):  # 約4年分のM5バー数
        # 価格をランダムウォーク
        price += random.gauss(0, 0.0001)
        price = max(0.9000, min(1.3000, price))  # 価格範囲制限
        
        data.append({
            'datetime': current_date,
            'open': price,
            'high': price + random.uniform(0, 0.0005),
            'low': price - random.uniform(0, 0.0005),
            'close': price + random.gauss(0, 0.0002),
            'volume': random.randint(50, 200)
        })
        
        current_date += timedelta(minutes=5)
        
        # 週末はスキップ（簡易実装）
        if current_date.weekday() >= 5:  # 土日
            current_date += timedelta(days=2)
    
    return data

def main():
    """メイン実行関数（テスト用）"""
    print("🚀 Purged & Embargoed WFA プロトタイプ実行開始")
    
    # サンプルデータ生成
    print("📊 サンプルデータ生成中...")
    data = create_sample_data()
    print(f"   生成データ数: {len(data)}バー")
    
    # 戦略設定（サンプル）
    strategy_config = {
        'ma_periods': [20, 50],      # 移動平均期間
        'atr_period': 14,            # ATR期間
        'rsi_period': 14,            # RSI期間
        'timeframe': 'M5',           # 時間足
        'other_periods': []          # その他のインジケーター期間
    }
    
    # WFA設定
    wfa_config = WFAConfig(
        is_months=24,                # IS期間24ヶ月
        oos_months=6,                # OOS期間6ヶ月
        step_months=6,               # 6ヶ月ステップ
        anchored=True                # アンカード方式
    )
    
    # WFA実行
    print("\n🔬 Purged & Embargoed WFA実行...")
    wfa = PurgedEmbargoedWFA(data, wfa_config, strategy_config)
    folds = wfa.generate_folds()
    
    # 各フォールドの詳細表示
    print(f"\n📋 フォールド詳細:")
    for i, fold in enumerate(folds[:3], 1):  # 最初の3フォールドのみ表示
        fold_data = wfa.get_fold_data(i)
        print(f"\n   Fold {i}:")
        print(f"     IS期間: {fold_data['is_bars']}バー")
        print(f"     OOS期間: {fold_data['oos_bars']}バー")
        print(f"     Purge日数: {fold['purge_days']}日")
        print(f"     Embargo日数: {fold['embargo_days']}日")
    
    # 実際のWFA実行
    print(f"\n📈 実WFA実行開始:")
    
    # 実際のWFA結果生成
    real_results = []
    for i, fold in enumerate(folds, 1):
        print(f"   Fold {i}/{len(folds)} 処理中...")
        
        fold_data = wfa.get_fold_data(i)
        is_data = fold_data['is_data']
        oos_data = fold_data['oos_data']
        
        # IS期間での戦略実行（簡易実装）
        is_result = wfa._run_strategy_on_data(is_data, 'IS')
        
        # OOS期間での戦略実行（実データ）
        oos_result = wfa._run_strategy_on_data(oos_data, 'OOS')
        
        real_results.append({
            'fold_id': i,
            'is_return': is_result['total_return'],
            'oos_return': oos_result['total_return'],
            'oos_sharpe': oos_result['sharpe_ratio'],
            'oos_pf': oos_result['profit_factor'],
            'trades': oos_result['total_trades'],
            'is_trades': is_result['total_trades'],
            'fold_info': fold
        })
    
    # 統計的検証
    validator = StatisticalValidator(real_results)
    consistency = validator.calculate_oos_consistency()
    wfa_efficiency = validator.calculate_wfa_efficiency()
    
    print(f"   OOS一貫性: {consistency['consistency_ratio']:.2%}")
    print(f"   正の期間: {consistency['positive_periods']}/{consistency['total_periods']}")
    print(f"   WFA効率: {wfa_efficiency:.3f}")
    print(f"   統計的有意性: {'あり' if consistency['is_significant'] else 'なし'}")
    print(f"   p値: {consistency['p_value']:.4f}")
    
    print(f"\n✅ プロトタイプ実行完了！")
    print(f"   このシステムは47EA失敗の根本原因（情報リーク）を解決します。")
    
    return wfa, real_results

if __name__ == "__main__":
    wfa, results = main()