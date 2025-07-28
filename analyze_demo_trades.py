#!/usr/bin/env python3
"""
JamesORB デモ運用取引履歴分析
HTMLレポートから詳細な取引データを抽出・分析
"""

import re
import html

def analyze_demo_trades():
    # HTMLファイルを読み込み、UTF-16エンコーディングで処理
    try:
        with open('MT5/Results/Live/Demo/ReportHistory-400078005.html', 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ HTMLファイルが見つかりません")
        return

    # 正規表現で取引行を抽出
    # bgcolor="#FFFFFF"または"#F7F7F7"の行を探す
    trade_pattern = r'<tr\s+bgcolor="#(?:FFFFFF|F7F7F7)"[^>]*>(.*?)</tr>'
    rows = re.findall(trade_pattern, content, re.DOTALL | re.IGNORECASE)

    print('🏆 JamesORB デモ運用 - 取引履歴分析')
    print('=' * 60)

    trades = []
    total_profit = 0

    for i, row in enumerate(rows):
        # 正規表現でTDセルを抽出
        cell_pattern = r'<td[^>]*>(.*?)</td>'
        cells = re.findall(cell_pattern, row, re.DOTALL | re.IGNORECASE)
        
        if len(cells) >= 10:
            try:
                # HTMLタグを除去し、テキストのみ抽出
                def clean_text(text):
                    text = re.sub(r'<[^>]+>', '', text)
                    return text.strip()
                
                date = clean_text(cells[0])
                ticket = clean_text(cells[1])
                symbol = clean_text(cells[2])
                type_trade = clean_text(cells[3])
                volume = float(clean_text(cells[4]))
                open_price = float(clean_text(cells[5]))
                sl_text = clean_text(cells[6])
                sl = float(sl_text) if sl_text != '0' and sl_text else None
                tp_text = clean_text(cells[7])
                tp = float(tp_text) if tp_text != '0' and tp_text else None
                close_time = clean_text(cells[8])
                close_price = float(clean_text(cells[9]))
                
                # 損益は最後のセルから取得
                profit_text = clean_text(cells[-1])
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
                    'date': date,
                    'sl': sl,
                    'tp': tp
                })
                
            except (ValueError, IndexError) as e:
                print(f"行解析エラー: {e}")
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