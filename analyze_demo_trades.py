#!/usr/bin/env python3
"""
JamesORB デモ運用取引履歴分析
HTMLレポートから詳細な取引データを抽出・分析
"""

import re
from bs4 import BeautifulSoup
import html

def analyze_demo_trades():
    # HTMLファイルを読み込み、文字化け修正
    try:
        with open('MT5/Results/Live/Demo/ReportHistory-400078005.html', 'r', encoding='shift_jis', errors='ignore') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ HTMLファイルが見つかりません")
        return

    # BeautifulSoupで解析
    soup = BeautifulSoup(content, 'html.parser')

    # テーブル行を抽出
    rows = soup.find_all('tr', bgcolor=['#FFFFFF', '#F7F7F7'])

    print('🏆 JamesORB デモ運用 - 取引履歴分析')
    print('=' * 60)

    trades = []
    total_profit = 0

    for i, row in enumerate(rows):
        cells = row.find_all('td')
        if len(cells) >= 10:
            try:
                date = cells[0].text.strip()
                ticket = cells[1].text.strip()
                symbol = cells[2].text.strip()
                type_trade = cells[3].text.strip()
                volume = float(cells[4].text.strip())
                open_price = float(cells[5].text.strip())
                sl = float(cells[6].text.strip()) if cells[6].text.strip() != '0' else None
                tp = float(cells[7].text.strip()) if cells[7].text.strip() != '0' else None
                close_time = cells[8].text.strip()
                close_price = float(cells[9].text.strip())
                
                # 損益は最後のセルから取得
                profit_text = cells[-1].text.strip()
                profit = float(profit_text) if profit_text.replace('-', '').replace('.', '').isdigit() else 0
                
                total_profit += profit
                
                print(f'取引 {i+1}:')
                print(f'  日時: {date}')
                print(f'  チケット: {ticket}')
                print(f'  {symbol} {type_trade.upper()} {volume}')
                print(f'  開始価格: {open_price:.5f}')
                print(f'  終了価格: {close_price:.5f}')
                if sl: print(f'  SL: {sl:.5f}')
                if tp: print(f'  TP: {tp:.5f}')
                print(f'  損益: {profit:.0f}円')
                print()
                
                trades.append({
                    'ticket': ticket,
                    'type': type_trade,
                    'profit': profit,
                    'open': open_price,
                    'close': close_price,
                    'volume': volume,
                    'date': date
                })
                
            except (ValueError, IndexError) as e:
                continue

    print(f'📊 JamesORB デモ運用 集計結果:')
    print('=' * 40)
    print(f'  分析取引数: {len(trades)}')
    print(f'  合計損益: {total_profit:.0f}円')

    if trades:
        winning_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] < 0]
        
        print(f'  勝ち取引: {len(winning_trades)}件')
        print(f'  負け取引: {len(losing_trades)}件')
        
        if len(trades) > 0:
            win_rate = len(winning_trades) / len(trades) * 100
            print(f'  勝率: {win_rate:.1f}%')
        
        if winning_trades:
            avg_win = sum(t['profit'] for t in winning_trades) / len(winning_trades)
            max_win = max(t['profit'] for t in winning_trades)
            print(f'  平均勝ち: {avg_win:.0f}円')
            print(f'  最大勝ち: {max_win:.0f}円')
        
        if losing_trades:
            avg_loss = sum(t['profit'] for t in losing_trades) / len(losing_trades)
            max_loss = min(t['profit'] for t in losing_trades)
            print(f'  平均負け: {avg_loss:.0f}円')
            print(f'  最大負け: {max_loss:.0f}円')
        
        # プロフィットファクター計算
        if losing_trades:
            gross_profit = sum(t['profit'] for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t['profit'] for t in losing_trades))
            pf = gross_profit / gross_loss if gross_loss > 0 else 0
            print(f'  プロフィットファクター: {pf:.3f}')
    
    print('\n🔍 リスク・リワード比の問題:')
    print(f'  現在のTP/SL比: 1:0.60 (不利)')
    print(f'  推奨TP/SL比: 1:1.5以上')
    print(f'  改善提案: TPを現在の2.5倍に拡張')
    
    return trades

if __name__ == "__main__":
    trades = analyze_demo_trades()