#!/usr/bin/env python3
"""
JamesORB Demo Trading - 正確な成績分析
"""
import re
from datetime import datetime

def analyze_trading_performance():
    """正確な取引成績分析"""
    
    # UTF-16でHTMLファイルを読み込み
    with open('ReportHistory-400078005.html', 'rb') as f:
        content = f.read().decode('utf-16-le', errors='ignore')
    
    print("=== JamesORB Demo Trading Analysis ===")
    print("期間: 2025-07-24 23:47 ～ 2025-07-29 18:29")
    print("口座: 400078005 (Demo)")
    print("EA: JamesORB_v1.0")
    print()
    
    # 全行を抽出
    all_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL)
    
    trades = []
    for row in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
        
        # 取引データの条件：EURUSD、buy/sell、適切な列数
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
                trades.append(trade)
            except (ValueError, IndexError):
                continue
    
    # 統計計算
    if not trades:
        print("❌ 取引データが見つかりません")
        return
    
    print(f"📊 基本統計:")
    print(f"  総取引数: {len(trades)}")
    
    # 勝敗分析
    winning_trades = [t for t in trades if t['profit'] > 0]
    losing_trades = [t for t in trades if t['profit'] < 0]
    breakeven_trades = [t for t in trades if t['profit'] == 0]
    
    win_rate = (len(winning_trades) / len(trades)) * 100
    
    print(f"  勝ちトレード: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"  負けトレード: {len(losing_trades)} ({100-win_rate:.1f}%)")
    print(f"  引き分け: {len(breakeven_trades)}")
    
    # 損益分析
    gross_profit = sum(t['profit'] for t in winning_trades)
    gross_loss = sum(t['profit'] for t in losing_trades)
    net_profit = gross_profit + gross_loss
    
    print(f"\n💰 損益分析:")
    print(f"  総利益: ${gross_profit:.2f}")
    print(f"  総損失: ${gross_loss:.2f}")
    print(f"  純損益: ${net_profit:.2f}")
    
    # プロフィットファクター
    if gross_loss != 0:
        pf = abs(gross_profit / gross_loss)
        print(f"  プロフィットファクター: {pf:.2f}")
    
    # 平均値分析
    if winning_trades:
        avg_win = gross_profit / len(winning_trades)
        print(f"  平均勝ちトレード: ${avg_win:.2f}")
    
    if losing_trades:
        avg_loss = gross_loss / len(losing_trades)
        print(f"  平均負けトレード: ${avg_loss:.2f}")
        
        if winning_trades:
            rr_ratio = abs(avg_win / avg_loss)
            print(f"  リスクリワード比: 1:{rr_ratio:.2f}")
    
    # 最大・最小
    all_profits = [t['profit'] for t in trades]
    print(f"\n📈 極値:")
    print(f"  最大利益: ${max(all_profits):.2f}")
    print(f"  最大損失: ${min(all_profits):.2f}")
    
    # 取引タイプ別分析
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    print(f"\n🔄 取引タイプ別:")
    print(f"  買いポジション: {len(buy_trades)}回")
    if buy_trades:
        buy_profit = sum(t['profit'] for t in buy_trades)
        buy_win_rate = (len([t for t in buy_trades if t['profit'] > 0]) / len(buy_trades)) * 100
        print(f"    損益: ${buy_profit:.2f}, 勝率: {buy_win_rate:.1f}%")
    
    print(f"  売りポジション: {len(sell_trades)}回")
    if sell_trades:
        sell_profit = sum(t['profit'] for t in sell_trades)
        sell_win_rate = (len([t for t in sell_trades if t['profit'] > 0]) / len(sell_trades)) * 100
        print(f"    損益: ${sell_profit:.2f}, 勝率: {sell_win_rate:.1f}%")
    
    # 口座情報推定
    initial_balance = 3000000  # デモ口座の初期残高
    current_balance = initial_balance + net_profit
    roi = (net_profit / initial_balance) * 100
    
    print(f"\n💹 口座パフォーマンス:")
    print(f"  初期残高: ${initial_balance:,.2f}")
    print(f"  推定現在残高: ${current_balance:,.2f}")
    print(f"  投資収益率(ROI): {roi:+.2f}%")
    
    # 日別分析
    daily_stats = {}
    for trade in trades:
        date = trade['close_time'][:10]  # YYYY.MM.DD部分
        if date not in daily_stats:
            daily_stats[date] = {'trades': 0, 'profit': 0}
        daily_stats[date]['trades'] += 1
        daily_stats[date]['profit'] += trade['profit']
    
    print(f"\n📅 日別パフォーマンス:")
    for date, stats in sorted(daily_stats.items()):
        print(f"  {date}: {stats['trades']}回, ${stats['profit']:+.2f}")
    
    # 最新の取引詳細
    print(f"\n📋 最新の取引 (最後の5件):")
    for trade in trades[-5:]:
        result = "勝ち" if trade['profit'] > 0 else "負け" if trade['profit'] < 0 else "引分"
        print(f"  {trade['close_time']} {trade['type'].upper()} ${trade['profit']:+.2f} ({result})")
    
    return {
        'total_trades': len(trades),
        'win_rate': win_rate,
        'net_profit': net_profit,
        'roi': roi,
        'profit_factor': pf if gross_loss != 0 else 0,
        'current_balance': current_balance
    }

if __name__ == "__main__":
    analyze_trading_performance()