#!/usr/bin/env python3
"""
JamesORB Demo Trading - 日別詳細分析
"""
import re
from collections import defaultdict
from datetime import datetime

def analyze_daily_performance():
    """日別パフォーマンス詳細分析"""
    
    # UTF-16でHTMLファイルを読み込み
    with open('ReportHistory-400078005.html', 'rb') as f:
        content = f.read().decode('utf-16-le', errors='ignore')
    
    print("=== JamesORB Demo Trading - 日別分析 ===")
    print("期間: 2025-07-24 23:47 ～ 2025-07-29 18:29")
    print()
    
    # 全取引を抽出
    all_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL)
    
    trades = []
    for row in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
        
        if (len(clean_cells) >= 14 and 
            'EURUSD' in clean_cells and 
            clean_cells[3] in ['buy', 'sell'] and
            clean_cells[4] == 'JamesORB'):
            
            try:
                trade = {
                    'open_time': clean_cells[0],
                    'ticket': clean_cells[1],
                    'symbol': clean_cells[2],
                    'type': clean_cells[3],
                    'ea': clean_cells[4],
                    'volume': float(clean_cells[5]),
                    'open_price': float(clean_cells[6]),
                    'sl': float(clean_cells[7]),
                    'tp': float(clean_cells[8]),
                    'close_time': clean_cells[9],
                    'close_price': float(clean_cells[10]),
                    'commission': float(clean_cells[11]),
                    'swap': float(clean_cells[12]),
                    'profit': float(clean_cells[13])
                }
                
                # 日付を抽出（close_timeから）
                date_str = trade['close_time'][:10]  # YYYY.MM.DD
                trade['close_date'] = date_str
                trades.append(trade)
            except (ValueError, IndexError):
                continue
    
    if not trades:
        print("❌ 取引データが見つかりません")
        return
    
    # 日別集計
    daily_stats = defaultdict(lambda: {
        'trades': [],
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'gross_profit': 0,
        'gross_loss': 0,
        'net_profit': 0
    })
    
    for trade in trades:
        date = trade['close_date']
        daily_stats[date]['trades'].append(trade)
        daily_stats[date]['total_trades'] += 1
        
        if trade['profit'] > 0:
            daily_stats[date]['winning_trades'] += 1
            daily_stats[date]['gross_profit'] += trade['profit']
        elif trade['profit'] < 0:
            daily_stats[date]['losing_trades'] += 1
            daily_stats[date]['gross_loss'] += trade['profit']
        
        daily_stats[date]['net_profit'] += trade['profit']
    
    # 日別詳細表示
    print("📅 日別パフォーマンス詳細:")
    total_net = 0
    
    for date in sorted(daily_stats.keys()):
        stats = daily_stats[date]
        win_rate = (stats['winning_trades'] / stats['total_trades']) * 100 if stats['total_trades'] > 0 else 0
        
        print(f"\n📊 {date}:")
        print(f"  取引数: {stats['total_trades']}回")
        print(f"  勝敗: {stats['winning_trades']}勝{stats['losing_trades']}敗 (勝率{win_rate:.1f}%)")
        print(f"  損益: ${stats['net_profit']:+.2f}")
        print(f"    利益: ${stats['gross_profit']:.2f}")
        print(f"    損失: ${stats['gross_loss']:.2f}")
        
        # その日の取引詳細
        print(f"  📋 取引詳細:")
        for i, trade in enumerate(stats['trades'], 1):
            result = "勝" if trade['profit'] > 0 else "負" if trade['profit'] < 0 else "分"
            print(f"    {i}. {trade['close_time'][11:19]} {trade['type'].upper()} ${trade['profit']:+.2f} ({result})")
        
        total_net += stats['net_profit']
    
    # 週間サマリー
    print(f"\n📈 運用期間サマリー:")
    print(f"  総取引数: {len(trades)}")
    print(f"  純損益: ${total_net:.2f}")
    print(f"  取引日数: {len(daily_stats)}日")
    print(f"  平均日次損益: ${total_net/len(daily_stats):.2f}")
    
    # 最も良い日・悪い日
    if daily_stats:
        best_day = max(daily_stats.items(), key=lambda x: x[1]['net_profit'])
        worst_day = min(daily_stats.items(), key=lambda x: x[1]['net_profit'])
        
        print(f"\n🎯 極値:")
        print(f"  最高の日: {best_day[0]} (${best_day[1]['net_profit']:+.2f})")
        print(f"  最悪の日: {worst_day[0]} (${worst_day[1]['net_profit']:+.2f})")
    
    # 週の傾向分析
    dates = sorted(daily_stats.keys())
    if len(dates) >= 2:
        first_day_profit = daily_stats[dates[0]]['net_profit']
        last_day_profit = daily_stats[dates[-1]]['net_profit']
        
        print(f"\n📊 トレンド分析:")
        print(f"  初日損益: ${first_day_profit:+.2f}")
        print(f"  最終日損益: ${last_day_profit:+.2f}")
        
        if len(dates) > 2:
            middle_days_profit = sum(daily_stats[date]['net_profit'] for date in dates[1:-1])
            print(f"  中間日損益: ${middle_days_profit:+.2f}")
    
    return daily_stats

if __name__ == "__main__":
    analyze_daily_performance()