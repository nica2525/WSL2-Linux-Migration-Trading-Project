#!/usr/bin/env python3
"""
JamesORB Demo Trading Analysis
"""
import re

def analyze_expert_log():
    """エキスパートタブの分析"""
    with open('エキスパートタブ.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    orders = []
    for line in lines:
        if 'Order placed successfully' in line:
            # Ticket番号を抽出
            ticket_match = re.search(r'Ticket: (\d+)', line)
            if ticket_match:
                orders.append(ticket_match.group(1))
    
    return orders

def analyze_operation_log():
    """操作ログタブの分析"""
    with open('操作ログタブ.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    trades = {
        'buy_orders': 0,
        'sell_orders': 0,
        'executed_buys': 0,
        'executed_sells': 0,
        'deals': []
    }
    
    for line in lines:
        if 'buy stop' in line and 'order #' in line:
            trades['buy_orders'] += 1
        elif 'sell stop' in line and 'order #' in line:
            trades['sell_orders'] += 1
        elif 'deal #' in line:
            if 'buy' in line:
                trades['executed_buys'] += 1
            elif 'sell' in line:
                trades['executed_sells'] += 1
            
            # Deal情報を抽出
            deal_match = re.search(r'deal #(\d+) (buy|sell) ([\d.]+) (\w+) at ([\d.]+)', line)
            if deal_match:
                trades['deals'].append({
                    'deal_id': deal_match.group(1),
                    'type': deal_match.group(2),
                    'volume': deal_match.group(3),
                    'symbol': deal_match.group(4),
                    'price': deal_match.group(5)
                })
    
    return trades

def analyze_html_reports():
    """HTMLレポートの分析"""
    # UTF-16でエンコードされているHTMLを読み込み
    try:
        with open('ReportHistory-400078005.html', 'rb') as f:
            history_content = f.read().decode('utf-16-le', errors='ignore')
        
        with open('ReportTrade-400078005.html', 'rb') as f:
            trade_content = f.read().decode('utf-16-le', errors='ignore')
    except:
        return None
    
    # 初期入金を探す
    deposit_match = re.search(r'deposit.*?<td.*?>([\d,.-]+)</td>', history_content, re.IGNORECASE | re.DOTALL)
    initial_deposit = float(deposit_match.group(1).replace(',', '')) if deposit_match else 3000000
    
    # 取引履歴から統計を計算
    trade_rows = re.findall(r'<tr.*?>.*?(buy|sell).*?EURUSD.*?<td.*?>([\d.]+)</td>.*?<td.*?>([\d.-]+)</td>.*?<td.*?>([\d,.-]+)</td>.*?</tr>', 
                           history_content, re.DOTALL)
    
    stats = {
        'initial_deposit': initial_deposit,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'gross_profit': 0,
        'gross_loss': 0,
        'largest_profit': 0,
        'largest_loss': 0,
        'trades': []
    }
    
    for row in trade_rows:
        if len(row) >= 3:
            try:
                # 最後の数値が損益
                profit_str = row[-1].replace(',', '')
                profit = float(profit_str)
                
                if profit != 0:  # 手数料行を除外
                    stats['total_trades'] += 1
                    stats['trades'].append(profit)
                    
                    if profit > 0:
                        stats['winning_trades'] += 1
                        stats['gross_profit'] += profit
                        stats['largest_profit'] = max(stats['largest_profit'], profit)
                    else:
                        stats['losing_trades'] += 1
                        stats['gross_loss'] += profit
                        stats['largest_loss'] = min(stats['largest_loss'], profit)
            except:
                pass
    
    return stats

def main():
    print("=== JamesORB Demo運用成績分析 ===")
    print("期間: 2025-07-24 23:47 ～ 2025-07-29 18:29")
    print("")
    
    # エキスパートログ分析
    orders = analyze_expert_log()
    print(f"📊 発注済みオーダー数: {len(orders)}")
    
    # 操作ログ分析
    trades = analyze_operation_log()
    print(f"\n📈 取引実行状況:")
    print(f"  Buy Stop Orders: {trades['buy_orders']}")
    print(f"  Sell Stop Orders: {trades['sell_orders']}")
    print(f"  Executed Buys: {trades['executed_buys']}")
    print(f"  Executed Sells: {trades['executed_sells']}")
    print(f"  Total Deals: {len(trades['deals'])}")
    
    # HTMLレポート分析
    stats = analyze_html_reports()
    if stats:
        print(f"\n💰 取引成績:")
        print(f"  初期証拠金: ${stats['initial_deposit']:,.2f}")
        print(f"  総取引数: {stats['total_trades']}")
        
        if stats['total_trades'] > 0:
            win_rate = (stats['winning_trades'] / stats['total_trades']) * 100
            print(f"  勝ちトレード: {stats['winning_trades']} ({win_rate:.1f}%)")
            print(f"  負けトレード: {stats['losing_trades']} ({100-win_rate:.1f}%)")
            
            print(f"\n  総利益: ${stats['gross_profit']:,.2f}")
            print(f"  総損失: ${stats['gross_loss']:,.2f}")
            print(f"  純損益: ${stats['gross_profit'] + stats['gross_loss']:,.2f}")
            
            if stats['gross_loss'] != 0:
                pf = abs(stats['gross_profit'] / stats['gross_loss'])
                print(f"  プロフィットファクター: {pf:.2f}")
            
            if stats['winning_trades'] > 0 and stats['losing_trades'] > 0:
                avg_win = stats['gross_profit'] / stats['winning_trades']
                avg_loss = stats['gross_loss'] / stats['losing_trades']
                rr_ratio = abs(avg_win / avg_loss)
                print(f"\n  平均勝ちトレード: ${avg_win:.2f}")
                print(f"  平均負けトレード: ${avg_loss:.2f}")
                print(f"  リスクリワード比: 1:{rr_ratio:.2f}")
            
            print(f"\n  最大利益: ${stats['largest_profit']:.2f}")
            print(f"  最大損失: ${stats['largest_loss']:.2f}")
            
            # 現在の状況
            current_balance = stats['initial_deposit'] + stats['gross_profit'] + stats['gross_loss']
            pnl_pct = ((current_balance - stats['initial_deposit']) / stats['initial_deposit']) * 100
            print(f"\n📊 現在の口座状況:")
            print(f"  推定残高: ${current_balance:,.2f}")
            print(f"  総損益率: {pnl_pct:+.2f}%")

if __name__ == "__main__":
    main()