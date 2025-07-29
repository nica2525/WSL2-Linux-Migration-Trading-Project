#!/usr/bin/env python3
"""
HTML構造のデバッグと調査
"""
import re

def debug_html_structure():
    # UTF-16でHTMLファイルを読み込み
    with open('ReportHistory-400078005.html', 'rb') as f:
        content = f.read().decode('utf-16-le', errors='ignore')

    print('=== HTML Structure Analysis ===')
    print(f'Content length: {len(content)} characters')

    # テーブル構造を探す
    tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.DOTALL)
    print(f'\nFound {len(tables)} tables')

    for i, table in enumerate(tables):
        print(f'\n--- Table {i+1} ---')
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        print(f'Rows: {len(rows)}')
        
        # 最初の数行の内容を確認
        for j, row in enumerate(rows[:5]):
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
            if clean_cells:  # 空でない行のみ表示
                print(f'  Row {j+1} ({len(clean_cells)} cells): {clean_cells[:8]}')

    # 特定のキーワードを含む行を探す
    print('\n=== Searching for Trading Data ===')
    
    # EURUSD取引を探す
    eurusd_matches = re.findall(r'<tr[^>]*>.*?EURUSD.*?</tr>', content, re.DOTALL)
    print(f'Found {len(eurusd_matches)} EURUSD rows')
    
    for i, match in enumerate(eurusd_matches[:3]):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', match, re.DOTALL)
        clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
        print(f'  EURUSD Row {i+1}: {clean_cells}')

    # buy/sell取引を探す
    trade_pattern = r'<tr[^>]*>.*?(buy|sell).*?EURUSD.*?</tr>'
    trade_matches = re.findall(trade_pattern, content, re.DOTALL | re.IGNORECASE)
    print(f'\nFound {len(trade_matches)} buy/sell trades')

    # より詳細な取引行の解析
    detailed_pattern = r'<tr[^>]*>(.*?)</tr>'
    all_rows = re.findall(detailed_pattern, content, re.DOTALL)
    
    trade_rows = []
    for row in all_rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
        
        # 取引データらしい行を判定（EURUSDと数値を含む）
        if (any('EURUSD' in cell for cell in clean_cells) and 
            any(cell.replace('.', '').replace('-', '').isdigit() for cell in clean_cells) and
            len(clean_cells) >= 7):
            trade_rows.append(clean_cells)

    print(f'\nFound {len(trade_rows)} potential trade rows:')
    for i, row in enumerate(trade_rows[:5]):
        print(f'  Trade {i+1}: {row}')

    # 入金データを探す
    deposit_pattern = r'<tr[^>]*>.*?deposit.*?</tr>'
    deposit_matches = re.findall(deposit_pattern, content, re.DOTALL | re.IGNORECASE)
    print(f'\nFound {len(deposit_matches)} deposit entries')
    
    for i, match in enumerate(deposit_matches):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', match, re.DOTALL)
        clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
        print(f'  Deposit {i+1}: {clean_cells}')

if __name__ == "__main__":
    debug_html_structure()