#!/usr/bin/env python3
"""
Phase 2統計機能追加 - 基本統計指標実装
勝率・連勝連敗・日次週次月次損益集計・最大ドローダウン計算
"""

import sqlite3
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
import logging

class StatisticsCalculator:
    """基本統計指標計算・分析エンジン"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
    def calculate_win_rate_stats(self, days: int = 7) -> Dict[str, Any]:
        """勝率統計計算"""
        try:
            position_history = self.db.get_position_history(hours=days*24)
            
            if not position_history:
                return self._empty_win_rate_stats()
            
            # 利益別分類
            profits = [pos['profit'] for pos in position_history]
            winning_trades = [p for p in profits if p > 0]
            losing_trades = [p for p in profits if p < 0]
            breakeven_trades = [p for p in profits if p == 0]
            
            total_trades = len(profits)
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            be_count = len(breakeven_trades)
            
            # 基本勝率統計
            win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
            loss_rate = (loss_count / total_trades) * 100 if total_trades > 0 else 0
            
            # 時間帯別勝率
            hourly_stats = self._calculate_hourly_win_rate(position_history)
            
            # 通貨ペア別勝率
            symbol_stats = self._calculate_symbol_win_rate(position_history)
            
            # 取引タイプ別勝率
            type_stats = self._calculate_type_win_rate(position_history)
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'winning_trades': win_count,
                'losing_trades': loss_count,
                'breakeven_trades': be_count,
                'win_rate': win_rate,
                'loss_rate': loss_rate,
                'breakeven_rate': (be_count / total_trades) * 100 if total_trades > 0 else 0,
                'hourly_win_rates': hourly_stats,
                'symbol_win_rates': symbol_stats,
                'type_win_rates': type_stats,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"勝率統計計算エラー: {e}")
            return self._empty_win_rate_stats()
    
    def _calculate_hourly_win_rate(self, positions: List[Dict]) -> Dict[int, Dict[str, Any]]:
        """時間帯別勝率計算"""
        hourly_data = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total': 0})
        
        for pos in positions:
            try:
                # タイムスタンプから時間抽出
                timestamp = pos['timestamp']
                if 'T' in timestamp:
                    hour = int(timestamp.split('T')[1].split(':')[0])
                else:
                    continue
                
                hourly_data[hour]['total'] += 1
                if pos['profit'] > 0:
                    hourly_data[hour]['wins'] += 1
                elif pos['profit'] < 0:
                    hourly_data[hour]['losses'] += 1
                    
            except (ValueError, IndexError):
                continue
        
        # 勝率計算
        result = {}
        for hour in range(24):
            data = hourly_data[hour]
            if data['total'] > 0:
                win_rate = (data['wins'] / data['total']) * 100
                result[hour] = {
                    'total_trades': data['total'],
                    'wins': data['wins'],
                    'losses': data['losses'],
                    'win_rate': win_rate
                }
            else:
                result[hour] = {'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0}
        
        return result
    
    def _calculate_symbol_win_rate(self, positions: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """通貨ペア別勝率計算"""
        symbol_data = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total': 0, 'profit': 0})
        
        for pos in positions:
            symbol = pos.get('symbol', 'UNKNOWN')
            profit = pos.get('profit', 0)
            
            symbol_data[symbol]['total'] += 1
            symbol_data[symbol]['profit'] += profit
            
            if profit > 0:
                symbol_data[symbol]['wins'] += 1
            elif profit < 0:
                symbol_data[symbol]['losses'] += 1
        
        result = {}
        for symbol, data in symbol_data.items():
            if data['total'] > 0:
                result[symbol] = {
                    'total_trades': data['total'],
                    'wins': data['wins'],
                    'losses': data['losses'],
                    'win_rate': (data['wins'] / data['total']) * 100,
                    'total_profit': data['profit'],
                    'avg_profit': data['profit'] / data['total']
                }
        
        return result
    
    def _calculate_type_win_rate(self, positions: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """取引タイプ別勝率計算"""
        type_data = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total': 0, 'profit': 0})
        
        for pos in positions:
            pos_type = pos.get('type', 'unknown')
            profit = pos.get('profit', 0)
            
            type_data[pos_type]['total'] += 1
            type_data[pos_type]['profit'] += profit
            
            if profit > 0:
                type_data[pos_type]['wins'] += 1
            elif profit < 0:
                type_data[pos_type]['losses'] += 1
        
        result = {}
        for pos_type, data in type_data.items():
            if data['total'] > 0:
                result[pos_type] = {
                    'total_trades': data['total'],
                    'wins': data['wins'],
                    'losses': data['losses'],
                    'win_rate': (data['wins'] / data['total']) * 100,
                    'total_profit': data['profit'],
                    'avg_profit': data['profit'] / data['total']
                }
        
        return result
    
    def calculate_streak_stats(self, days: int = 7) -> Dict[str, Any]:
        """連勝・連敗統計計算"""
        try:
            position_history = self.db.get_position_history(hours=days*24)
            
            if not position_history:
                return self._empty_streak_stats()
            
            # 時系列順にソート
            positions = sorted(position_history, key=lambda x: x['timestamp'])
            
            # 連勝連敗カウント
            current_win_streak = 0
            current_loss_streak = 0
            max_win_streak = 0
            max_loss_streak = 0
            win_streaks = []
            loss_streaks = []
            
            for pos in positions:
                profit = pos['profit']
                
                if profit > 0:  # 勝ち
                    current_win_streak += 1
                    if current_loss_streak > 0:
                        loss_streaks.append(current_loss_streak)
                        max_loss_streak = max(max_loss_streak, current_loss_streak)
                        current_loss_streak = 0
                        
                elif profit < 0:  # 負け
                    current_loss_streak += 1
                    if current_win_streak > 0:
                        win_streaks.append(current_win_streak)
                        max_win_streak = max(max_win_streak, current_win_streak)
                        current_win_streak = 0
                        
                # 引き分けの場合は連勝・連敗を途切れさせる
                else:
                    if current_win_streak > 0:
                        win_streaks.append(current_win_streak)
                        max_win_streak = max(max_win_streak, current_win_streak)
                        current_win_streak = 0
                    if current_loss_streak > 0:
                        loss_streaks.append(current_loss_streak)
                        max_loss_streak = max(max_loss_streak, current_loss_streak)
                        current_loss_streak = 0
            
            # 最終的な連続を記録
            if current_win_streak > 0:
                win_streaks.append(current_win_streak)
                max_win_streak = max(max_win_streak, current_win_streak)
            if current_loss_streak > 0:
                loss_streaks.append(current_loss_streak)
                max_loss_streak = max(max_loss_streak, current_loss_streak)
            
            # 統計計算
            avg_win_streak = sum(win_streaks) / len(win_streaks) if win_streaks else 0
            avg_loss_streak = sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0
            
            return {
                'period_days': days,
                'total_positions': len(positions),
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak,
                'current_win_streak': current_win_streak,
                'current_loss_streak': current_loss_streak,
                'avg_win_streak': avg_win_streak,
                'avg_loss_streak': avg_loss_streak,
                'total_win_streaks': len(win_streaks),
                'total_loss_streaks': len(loss_streaks),
                'win_streak_distribution': self._calculate_streak_distribution(win_streaks),
                'loss_streak_distribution': self._calculate_streak_distribution(loss_streaks),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"連勝連敗統計計算エラー: {e}")
            return self._empty_streak_stats()
    
    def _calculate_streak_distribution(self, streaks: List[int]) -> Dict[int, int]:
        """連勝連敗分布計算"""
        distribution = defaultdict(int)
        for streak in streaks:
            distribution[streak] += 1
        return dict(distribution)
    
    def calculate_period_performance(self, period: str = 'daily') -> Dict[str, Any]:
        """期間別パフォーマンス計算（日次・週次・月次）"""
        try:
            if period == 'daily':
                return self._calculate_daily_performance()
            elif period == 'weekly':
                return self._calculate_weekly_performance()
            elif period == 'monthly':
                return self._calculate_monthly_performance()
            else:
                raise ValueError(f"不正な期間指定: {period}")
                
        except Exception as e:
            self.logger.error(f"期間別パフォーマンス計算エラー: {e}")
            return self._empty_period_performance()
    
    def _calculate_daily_performance(self, days: int = 30) -> Dict[str, Any]:
        """日次パフォーマンス計算"""
        daily_stats = []
        end_date = datetime.now()
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            day_stats = self.db.calculate_daily_stats(date)
            if day_stats['total_trades'] > 0:
                daily_stats.append(day_stats)
        
        if not daily_stats:
            return self._empty_period_performance()
        
        # 集計計算
        total_profit = sum(s['net_profit'] for s in daily_stats)
        positive_days = len([s for s in daily_stats if s['net_profit'] > 0])
        negative_days = len([s for s in daily_stats if s['net_profit'] < 0])
        
        return {
            'period_type': 'daily',
            'period_count': len(daily_stats),
            'total_profit': total_profit,
            'avg_daily_profit': total_profit / len(daily_stats),
            'positive_days': positive_days,
            'negative_days': negative_days,
            'positive_day_rate': (positive_days / len(daily_stats)) * 100,
            'best_day': max(daily_stats, key=lambda x: x['net_profit']),
            'worst_day': min(daily_stats, key=lambda x: x['net_profit']),
            'daily_data': daily_stats,
            'calculated_at': datetime.now().isoformat()
        }
    
    def _calculate_weekly_performance(self, weeks: int = 12) -> Dict[str, Any]:
        """週次パフォーマンス計算"""
        weekly_stats = []
        end_date = datetime.now()
        
        for i in range(weeks):
            week_end = end_date - timedelta(weeks=i)
            week_start = week_end - timedelta(days=6)
            
            # その週の全ポジション取得
            positions = self.db.get_position_history(hours=7*24)
            week_positions = [
                pos for pos in positions
                if week_start.isoformat() <= pos['timestamp'] <= week_end.isoformat()
            ]
            
            if week_positions:
                profits = [pos['profit'] for pos in week_positions]
                net_profit = sum(profits)
                
                weekly_stats.append({
                    'week_start': week_start.strftime('%Y-%m-%d'),
                    'week_end': week_end.strftime('%Y-%m-%d'),
                    'total_trades': len(week_positions),
                    'net_profit': net_profit,
                    'avg_trade_profit': net_profit / len(week_positions)
                })
        
        if not weekly_stats:
            return self._empty_period_performance()
        
        total_profit = sum(s['net_profit'] for s in weekly_stats)
        positive_weeks = len([s for s in weekly_stats if s['net_profit'] > 0])
        
        return {
            'period_type': 'weekly',
            'period_count': len(weekly_stats),
            'total_profit': total_profit,
            'avg_weekly_profit': total_profit / len(weekly_stats),
            'positive_weeks': positive_weeks,
            'positive_week_rate': (positive_weeks / len(weekly_stats)) * 100,
            'best_week': max(weekly_stats, key=lambda x: x['net_profit']),
            'worst_week': min(weekly_stats, key=lambda x: x['net_profit']),
            'weekly_data': weekly_stats,
            'calculated_at': datetime.now().isoformat()
        }
    
    def _calculate_monthly_performance(self, months: int = 6) -> Dict[str, Any]:
        """月次パフォーマンス計算"""
        monthly_stats = []
        current_date = datetime.now()
        
        for i in range(months):
            # 月の開始日・終了日計算
            if i == 0:
                month_end = current_date
                month_start = current_date.replace(day=1)
            else:
                month_end = (current_date.replace(day=1) - timedelta(days=1))
                month_start = month_end.replace(day=1)
                current_date = month_end
            
            # その月の統計計算
            positions = self.db.get_position_history(hours=31*24)
            month_positions = [
                pos for pos in positions
                if month_start.isoformat() <= pos['timestamp'] <= month_end.isoformat()
            ]
            
            if month_positions:
                profits = [pos['profit'] for pos in month_positions]
                net_profit = sum(profits)
                winning_trades = len([p for p in profits if p > 0])
                
                monthly_stats.append({
                    'month': month_start.strftime('%Y-%m'),
                    'month_start': month_start.strftime('%Y-%m-%d'),
                    'month_end': month_end.strftime('%Y-%m-%d'),
                    'total_trades': len(month_positions),
                    'winning_trades': winning_trades,
                    'win_rate': (winning_trades / len(month_positions)) * 100,
                    'net_profit': net_profit,
                    'avg_trade_profit': net_profit / len(month_positions)
                })
        
        if not monthly_stats:
            return self._empty_period_performance()
        
        total_profit = sum(s['net_profit'] for s in monthly_stats)
        positive_months = len([s for s in monthly_stats if s['net_profit'] > 0])
        
        return {
            'period_type': 'monthly',
            'period_count': len(monthly_stats),
            'total_profit': total_profit,
            'avg_monthly_profit': total_profit / len(monthly_stats),
            'positive_months': positive_months,
            'positive_month_rate': (positive_months / len(monthly_stats)) * 100,
            'best_month': max(monthly_stats, key=lambda x: x['net_profit']),
            'worst_month': min(monthly_stats, key=lambda x: x['net_profit']),
            'monthly_data': monthly_stats,
            'calculated_at': datetime.now().isoformat()
        }
    
    def calculate_drawdown_analysis(self, days: int = 30) -> Dict[str, Any]:
        """最大ドローダウン分析"""
        try:
            account_history = self.db.get_account_history(hours=days*24)
            
            if not account_history:
                return self._empty_drawdown_stats()
            
            # 時系列順にソート
            history = sorted(account_history, key=lambda x: x['timestamp'])
            
            # エクイティカーブからドローダウン計算
            equity_values = [h['equity'] for h in history]
            
            max_equity = equity_values[0]
            max_drawdown = 0
            current_drawdown = 0
            drawdown_periods = []
            peak_to_trough = []
            
            dd_start_idx = None
            
            for i, equity in enumerate(equity_values):
                if equity >= max_equity:
                    # 新しいピーク
                    if dd_start_idx is not None:
                        # ドローダウン期間終了
                        drawdown_periods.append({
                            'start_idx': dd_start_idx,
                            'end_idx': i,
                            'duration_hours': i - dd_start_idx,
                            'max_dd': current_drawdown,
                            'recovery_equity': equity
                        })
                        dd_start_idx = None
                    
                    max_equity = equity
                    current_drawdown = 0
                else:
                    # ドローダウン中
                    if dd_start_idx is None:
                        dd_start_idx = i - 1  # ピークの位置
                    
                    current_drawdown = max_equity - equity
                    max_drawdown = max(max_drawdown, current_drawdown)
                    
                    peak_to_trough.append({
                        'timestamp': history[i]['timestamp'],
                        'equity': equity,
                        'drawdown': current_drawdown,
                        'drawdown_pct': (current_drawdown / max_equity) * 100
                    })
            
            # 現在進行中のドローダウン
            if dd_start_idx is not None:
                drawdown_periods.append({
                    'start_idx': dd_start_idx,
                    'end_idx': len(equity_values) - 1,
                    'duration_hours': len(equity_values) - 1 - dd_start_idx,
                    'max_dd': current_drawdown,
                    'recovery_equity': None  # 未回復
                })
            
            # ドローダウン統計
            max_dd_pct = (max_drawdown / max(equity_values)) * 100 if equity_values else 0
            avg_dd_duration = sum(p['duration_hours'] for p in drawdown_periods) / len(drawdown_periods) if drawdown_periods else 0
            
            return {
                'period_days': days,
                'max_drawdown_absolute': max_drawdown,
                'max_drawdown_percent': max_dd_pct,
                'current_drawdown': current_drawdown,
                'current_drawdown_pct': (current_drawdown / max_equity) * 100 if max_equity > 0 else 0,
                'total_drawdown_periods': len(drawdown_periods),
                'avg_drawdown_duration_hours': avg_dd_duration,
                'longest_drawdown_hours': max(p['duration_hours'] for p in drawdown_periods) if drawdown_periods else 0,
                'recovery_factor': max_equity / (max_equity - max_drawdown) if max_drawdown > 0 else 1,
                'drawdown_periods': drawdown_periods[-10:],  # 最新10件
                'equity_curve': equity_values,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"ドローダウン分析エラー: {e}")
            return self._empty_drawdown_stats()
    
    # 空の統計データ生成メソッド
    def _empty_win_rate_stats(self) -> Dict[str, Any]:
        return {
            'period_days': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'breakeven_trades': 0,
            'win_rate': 0.0,
            'loss_rate': 0.0,
            'breakeven_rate': 0.0,
            'hourly_win_rates': {},
            'symbol_win_rates': {},
            'type_win_rates': {},
            'calculated_at': datetime.now().isoformat()
        }
    
    def _empty_streak_stats(self) -> Dict[str, Any]:
        return {
            'period_days': 0,
            'total_positions': 0,
            'max_win_streak': 0,
            'max_loss_streak': 0,
            'current_win_streak': 0,
            'current_loss_streak': 0,
            'avg_win_streak': 0.0,
            'avg_loss_streak': 0.0,
            'total_win_streaks': 0,
            'total_loss_streaks': 0,
            'win_streak_distribution': {},
            'loss_streak_distribution': {},
            'calculated_at': datetime.now().isoformat()
        }
    
    def _empty_period_performance(self) -> Dict[str, Any]:
        return {
            'period_type': 'unknown',
            'period_count': 0,
            'total_profit': 0.0,
            'calculated_at': datetime.now().isoformat()
        }
    
    def _empty_drawdown_stats(self) -> Dict[str, Any]:
        return {
            'period_days': 0,
            'max_drawdown_absolute': 0.0,
            'max_drawdown_percent': 0.0,
            'current_drawdown': 0.0,
            'current_drawdown_pct': 0.0,
            'total_drawdown_periods': 0,
            'avg_drawdown_duration_hours': 0.0,
            'longest_drawdown_hours': 0,
            'recovery_factor': 1.0,
            'drawdown_periods': [],
            'equity_curve': [],
            'calculated_at': datetime.now().isoformat()
        }

# 使用例・テスト関数
def test_statistics():
    """統計計算テスト"""
    from database_manager import DatabaseManager
    
    db = DatabaseManager()
    calc = StatisticsCalculator(db)
    
    # テストデータ作成
    test_positions = []
    for i in range(20):
        profit = (-1) ** i * (50 + i * 10)  # 交互に勝ち負け
        test_data = {
            "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
            "account": {"balance": 3000000, "equity": 3000000 + profit, "profit": profit},
            "positions": [{
                "ticket": 100000 + i,
                "symbol": "EURUSD",
                "type": "buy" if i % 2 == 0 else "sell",
                "volume": 0.01,
                "profit": profit,
                "open_price": 1.0850,
                "current_price": 1.0850 + profit * 0.0001,
                "open_time": (datetime.now() - timedelta(hours=i)).isoformat()
            }]
        }
        db.store_mt5_data(test_data)
    
    # 統計計算テスト
    win_rate_stats = calc.calculate_win_rate_stats(days=7)
    print(f"勝率統計: 勝率{win_rate_stats['win_rate']:.1f}% ({win_rate_stats['winning_trades']}/{win_rate_stats['total_trades']})")
    
    streak_stats = calc.calculate_streak_stats(days=7)
    print(f"連勝連敗: 最大連勝{streak_stats['max_win_streak']}, 最大連敗{streak_stats['max_loss_streak']}")
    
    daily_perf = calc.calculate_period_performance('daily')
    print(f"日次パフォーマンス: {daily_perf['period_count']}日間, 総利益${daily_perf['total_profit']:.2f}")
    
    dd_analysis = calc.calculate_drawdown_analysis(days=7)
    print(f"ドローダウン分析: 最大DD${dd_analysis['max_drawdown_absolute']:.2f} ({dd_analysis['max_drawdown_percent']:.2f}%)")

if __name__ == "__main__":
    test_statistics()