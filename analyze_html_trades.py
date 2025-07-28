#!/usr/bin/env python3
"""
JamesORB デモ運用取引履歴分析 (HTML版)
UTF-16エンコーディング対応版
"""

import re
import subprocess

def analyze_html_trades():
    print('🏆 JamesORB デモ運用 - 取引履歴分析 (v2.02対応)')
    print('=' * 60)
    
    try:
        # iconvでUTF-16からUTF-8に変換してデータを取得
        result = subprocess.run([
            'iconv', '-f', 'utf-16le', '-t', 'utf-8', 
            'MT5/Results/Live/Demo/ReportHistory-400078005.html'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ HTMLファイルの変換に失敗しました")
            return
            
        content = result.stdout
        
    except Exception as e:
        print(f"❌ ファイル処理エラー: {e}")
        return

    # 取引行を抽出（bgcolor="#FFFFFF"または"#F7F7F7"の行）
    trade_pattern = r'<tr bgcolor="#(?:FFFFFF|F7F7F7)" align="right">(.*?)</tr>'
    rows = re.findall(trade_pattern, content, re.DOTALL)
    
    trades = []
    total_profit = 0
    v2_02_trades = []  # v2.02調整後の取引
    
    for i, row in enumerate(rows):
        # TDセルを抽出
        cell_pattern = r'<td[^>]*>(.*?)</td>'
        cells = re.findall(cell_pattern, row, re.DOTALL)
        
        if len(cells) >= 9:
            try:
                def clean_text(text):
                    # HTMLタグとクラス属性を除去
                    text = re.sub(r'<[^>]+>', '', text)
                    return text.strip()
                
                date = clean_text(cells[0])
                ticket = clean_text(cells[1])
                symbol = clean_text(cells[2])
                type_trade = clean_text(cells[3])
                
                # volume処理（"0.01"のみ抽出）
                volume_text = clean_text(cells[5])
                volume = float(volume_text.split()[0]) if volume_text else 0.01
                
                open_price = float(clean_text(cells[6]))
                sl = float(clean_text(cells[7])) if clean_text(cells[7]) != '0' else None
                tp = float(clean_text(cells[8])) if clean_text(cells[8]) != '0' else None
                close_time = clean_text(cells[9])
                close_price = float(clean_text(cells[10]))
                
                # 損益（最後の列）
                profit_text = clean_text(cells[-1])
                profit = float(profit_text) if profit_text.replace('-', '').replace('.', '').isdigit() else 0
                
                total_profit += profit
                
                # RR比計算
                rr_ratio = None
                if sl and tp and open_price:
                    if type_trade == 'buy':
                        sl_distance = abs(open_price - sl)
                        tp_distance = abs(tp - open_price)
                    else:  # sell
                        sl_distance = abs(sl - open_price)
                        tp_distance = abs(open_price - tp)
                    
                    if sl_distance > 0:
                        rr_ratio = tp_distance / sl_distance
                
                print(f'取引 {i+1}: #{ticket}')
                print(f'  日時: {date} → {close_time}')
                print(f'  {symbol} {type_trade.upper()} {volume}')
                print(f'  価格: {open_price:.5f} → {close_price:.5f}')
                if sl: print(f'  SL: {sl:.5f}')
                if tp: print(f'  TP: {tp:.5f}')
                if rr_ratio: print(f'  RR比: 1:{rr_ratio:.2f}')
                print(f'  損益: {profit:.0f}円')
                
                # v2.02後の取引判定（18:36以降）
                if '18:36' in date or '19:' in date or '20:' in date:
                    v2_02_trades.append({
                        'ticket': ticket, 'rr_ratio': rr_ratio, 'profit': profit
                    })
                    print('  🆕 v2.02調整後')
                
                print()
                
                trades.append({
                    'ticket': ticket, 'type': type_trade, 'profit': profit,
                    'open': open_price, 'close': close_price, 'volume': volume,
                    'date': date, 'sl': sl, 'tp': tp, 'rr_ratio': rr_ratio
                })
                
            except (ValueError, IndexError) as e:
                print(f"取引 {i+1}: 解析エラー ({e})")
                continue

    # 集計結果
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
    
    # v2.02調整後の効果
    if v2_02_trades:
        print(f'\\n🆕 v2.02調整後の取引:')
        print(f'  取引数: {len(v2_02_trades)}件')
        rr_ratios = [t['rr_ratio'] for t in v2_02_trades if t['rr_ratio']]
        if rr_ratios:
            avg_rr = sum(rr_ratios) / len(rr_ratios)
            print(f'  平均RR比: 1:{avg_rr:.2f}')
            if avg_rr > 1.0:
                print('  ✅ RR比改善成功！')
            else:
                print('  ⚠️ RR比がまだ1.0以下')
    
    return trades

if __name__ == "__main__":
    trades = analyze_html_trades()