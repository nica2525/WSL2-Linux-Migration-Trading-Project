#!/usr/bin/env python3
"""
MT5 HTML Report Parser
正確なMT5取引レポート解析ツール
"""
import re
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class MT5HTMLParser:
    """MT5のHTMLレポートを正確に解析するクラス"""
    
    def __init__(self):
        self.encoding = 'utf-16-le'  # MT5標準エンコーディング
        
    def parse_report_trade(self, filepath: str) -> Dict:
        """ReportTrade HTMLファイルを解析"""
        content = self._read_html(filepath)
        if not content:
            return {}
        
        result = {
            'account_info': {},
            'summary': {},
            'open_positions': [],
            'pending_orders': [],
            'closed_positions': []
        }
        
        # アカウント情報の抽出
        result['account_info'] = self._extract_account_info(content)
        
        # サマリー情報の抽出
        result['summary'] = self._extract_summary(content)
        
        # ポジション情報の抽出
        result['open_positions'] = self._extract_positions(content, 'open')
        result['pending_orders'] = self._extract_positions(content, 'pending')
        result['closed_positions'] = self._extract_positions(content, 'closed')
        
        return result
    
    def parse_report_history(self, filepath: str) -> Dict:
        """ReportHistory HTMLファイルを解析"""
        content = self._read_html(filepath)
        if not content:
            return {}
        
        result = {
            'deals': [],
            'deposits': [],
            'statistics': {}
        }
        
        # 取引履歴の抽出
        result['deals'] = self._extract_deals(content)
        
        # 入金情報の抽出
        result['deposits'] = self._extract_deposits(content)
        
        # 統計情報の計算
        result['statistics'] = self._calculate_statistics(result['deals'])
        
        return result
    
    def _read_html(self, filepath: str) -> Optional[str]:
        """HTMLファイルを適切なエンコーディングで読み込む"""
        if not os.path.exists(filepath):
            print(f"Error: File not found - {filepath}")
            return None
            
        try:
            with open(filepath, 'rb') as f:
                raw_content = f.read()
                
            # エンコーディング検出
            if raw_content.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                return raw_content.decode('utf-16-le', errors='ignore')
            elif raw_content.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                return raw_content.decode('utf-16-be', errors='ignore')
            else:
                # UTF-8を試す
                try:
                    return raw_content.decode('utf-8')
                except:
                    return raw_content.decode('latin-1', errors='ignore')
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def _extract_account_info(self, content: str) -> Dict:
        """アカウント情報を抽出"""
        info = {}
        
        # アカウント番号
        account_match = re.search(r'<b>(\d+):\s*(\w+)', content)
        if account_match:
            info['account_number'] = account_match.group(1)
            info['account_name'] = account_match.group(2)
        
        # サーバー情報
        server_match = re.search(r'<b>Server:</b></td><td[^>]*>(.*?)</td>', content)
        if server_match:
            info['server'] = server_match.group(1).strip()
            
        return info
    
    def _extract_summary(self, content: str) -> Dict:
        """サマリー情報を正確に抽出"""
        summary = {}
        
        # テーブルから各項目を抽出するパターン
        patterns = {
            'balance': r'<b>Balance:</b></td><td[^>]*>([\d\s,.-]+)</td>',
            'equity': r'<b>Equity:</b></td><td[^>]*>([\d\s,.-]+)</td>',
            'margin': r'<b>Margin:</b></td><td[^>]*>([\d\s,.-]+)</td>',
            'free_margin': r'<b>Free Margin:</b></td><td[^>]*>([\d\s,.-]+)</td>',
            'margin_level': r'<b>Margin Level:</b></td><td[^>]*>([\d\s,.%]+)</td>',
            'deposit_load': r'<b>Deposit/Withdrawal:</b></td><td[^>]*>([\d\s,.-]+)</td>',
            'credit': r'<b>Credit:</b></td><td[^>]*>([\d\s,.-]+)</td>',
            'floating_pl': r'<b>Floating P/L:</b></td><td[^>]*>([\d\s,.-]+)</td>'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1).strip().replace(' ', '').replace(',', '')
                try:
                    summary[key] = float(value)
                except:
                    summary[key] = value
        
        # 統計情報のテーブルを探す
        stats_section = re.search(r'<table[^>]*>.*?Total Net Profit.*?</table>', content, re.DOTALL)
        if stats_section:
            stats_content = stats_section.group(0)
            
            # 統計パターン
            stat_patterns = {
                'total_net_profit': r'Total Net Profit[^<]*<[^>]*>([\d\s,.-]+)',
                'gross_profit': r'Gross Profit[^<]*<[^>]*>([\d\s,.-]+)',
                'gross_loss': r'Gross Loss[^<]*<[^>]*>([\d\s,.-]+)',
                'profit_factor': r'Profit Factor[^<]*<[^>]*>([\d\s,.-]+)',
                'expected_payoff': r'Expected Payoff[^<]*<[^>]*>([\d\s,.-]+)',
                'margin_level': r'Margin Level[^<]*<[^>]*>([\d\s,.%]+)',
                'absolute_drawdown': r'Absolute Drawdown[^<]*<[^>]*>([\d\s,.-]+)',
                'maximal_drawdown': r'Maximal Drawdown[^<]*<[^>]*>([\d\s,.-]+)',
                'relative_drawdown': r'Relative Drawdown[^<]*<[^>]*>([\d\s,.%]+)',
                'total_trades': r'Total Trades[^<]*<[^>]*>(\d+)',
                'profit_trades': r'Profit Trades.*?<[^>]*>(\d+)',
                'loss_trades': r'Loss Trades.*?<[^>]*>(\d+)',
                'short_positions': r'Short Positions.*?<[^>]*>(\d+)',
                'long_positions': r'Long Positions.*?<[^>]*>(\d+)'
            }
            
            for key, pattern in stat_patterns.items():
                match = re.search(pattern, stats_content, re.DOTALL)
                if match:
                    value = match.group(1).strip().replace(' ', '').replace(',', '')
                    try:
                        if '%' in value:
                            summary[key] = value
                        else:
                            summary[key] = float(value) if '.' in value else int(value)
                    except:
                        summary[key] = value
        
        return summary
    
    def _extract_positions(self, content: str, position_type: str) -> List[Dict]:
        """ポジション情報を抽出"""
        positions = []
        
        # ポジションタイプに応じたセクションを探す
        if position_type == 'open':
            section_pattern = r'<b>Open Positions.*?</table>'
        elif position_type == 'pending':
            section_pattern = r'<b>Working Orders.*?</table>'
        else:
            section_pattern = r'<b>Closed Transactions.*?</table>'
            
        section_match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)
        if not section_match:
            return positions
            
        section_content = section_match.group(0)
        
        # 各行を抽出
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, section_content, re.DOTALL)
        
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 8:
                try:
                    position = {
                        'ticket': cells[0].strip(),
                        'open_time': cells[1].strip(),
                        'type': cells[2].strip(),
                        'volume': float(cells[3].strip()),
                        'symbol': cells[4].strip(),
                        'price': float(cells[5].strip()),
                        'sl': float(cells[6].strip()) if cells[6].strip() else 0,
                        'tp': float(cells[7].strip()) if cells[7].strip() else 0
                    }
                    
                    if len(cells) >= 11 and position_type != 'pending':
                        position['close_time'] = cells[8].strip()
                        position['commission'] = float(cells[9].strip()) if cells[9].strip() else 0
                        position['swap'] = float(cells[10].strip()) if cells[10].strip() else 0
                        position['profit'] = float(cells[11].strip()) if cells[11].strip() else 0
                        
                    positions.append(position)
                except:
                    continue
                    
        return positions
    
    def _extract_deals(self, content: str) -> List[Dict]:
        """取引履歴を抽出"""
        deals = []
        
        # テーブルを探す
        table_match = re.search(r'<table[^>]*>.*?</table>', content, re.DOTALL)
        if not table_match:
            return deals
            
        table_content = table_match.group(0)
        
        # 各行を抽出
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL)
        
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            
            # 取引データの行を識別（通常は7列以上）
            if len(cells) >= 7:
                # HTMLタグを除去
                clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
                
                # 取引タイプを確認（buy/sell/deposit）
                if any(word in clean_cells[2].lower() for word in ['buy', 'sell']):
                    try:
                        deal = {
                            'time': clean_cells[0],
                            'deal': clean_cells[1],
                            'type': clean_cells[2],
                            'volume': float(clean_cells[3]) if clean_cells[3] else 0,
                            'symbol': clean_cells[4],
                            'price': float(clean_cells[5]) if clean_cells[5] else 0,
                            'profit': float(clean_cells[6]) if clean_cells[6] else 0
                        }
                        
                        if len(clean_cells) >= 9:
                            deal['balance'] = float(clean_cells[8]) if clean_cells[8] else 0
                            
                        deals.append(deal)
                    except:
                        continue
                        
        return deals
    
    def _extract_deposits(self, content: str) -> List[Dict]:
        """入金情報を抽出"""
        deposits = []
        
        # deposit行を探す
        deposit_pattern = r'<tr[^>]*>.*?deposit.*?</tr>'
        deposit_rows = re.findall(deposit_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for row in deposit_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 7:
                clean_cells = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]
                try:
                    deposit = {
                        'time': clean_cells[0],
                        'type': 'deposit',
                        'amount': float(clean_cells[6]) if clean_cells[6] else 0
                    }
                    deposits.append(deposit)
                except:
                    continue
                    
        return deposits
    
    def _calculate_statistics(self, deals: List[Dict]) -> Dict:
        """取引統計を計算"""
        stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'win_rate': 0,
            'average_win': 0,
            'average_loss': 0,
            'risk_reward_ratio': 0,
            'largest_profit': 0,
            'largest_loss': 0
        }
        
        profits = []
        wins = []
        losses = []
        
        for deal in deals:
            if 'profit' in deal and deal['profit'] != 0:
                stats['total_trades'] += 1
                profits.append(deal['profit'])
                
                if deal['profit'] > 0:
                    stats['winning_trades'] += 1
                    stats['gross_profit'] += deal['profit']
                    wins.append(deal['profit'])
                    stats['largest_profit'] = max(stats['largest_profit'], deal['profit'])
                else:
                    stats['losing_trades'] += 1
                    stats['gross_loss'] += deal['profit']
                    losses.append(deal['profit'])
                    stats['largest_loss'] = min(stats['largest_loss'], deal['profit'])
        
        # 統計計算
        if stats['total_trades'] > 0:
            stats['net_profit'] = stats['gross_profit'] + stats['gross_loss']
            stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
            
        if stats['gross_loss'] != 0:
            stats['profit_factor'] = abs(stats['gross_profit'] / stats['gross_loss'])
            
        if wins:
            stats['average_win'] = sum(wins) / len(wins)
            
        if losses:
            stats['average_loss'] = sum(losses) / len(losses)
            
        if stats['average_loss'] != 0:
            stats['risk_reward_ratio'] = abs(stats['average_win'] / stats['average_loss'])
            
        return stats


def analyze_demo_reports(report_dir: str):
    """デモ取引レポートを分析"""
    parser = MT5HTMLParser()
    
    # ファイルパス
    trade_report = os.path.join(report_dir, 'ReportTrade-400078005.html')
    history_report = os.path.join(report_dir, 'ReportHistory-400078005.html')
    
    print("=== MT5 Demo Trading Analysis ===")
    print(f"Report Directory: {report_dir}\n")
    
    # Trade Report解析
    if os.path.exists(trade_report):
        trade_data = parser.parse_report_trade(trade_report)
        
        if trade_data.get('account_info'):
            print("📊 Account Information:")
            for key, value in trade_data['account_info'].items():
                print(f"  {key}: {value}")
            print()
        
        if trade_data.get('summary'):
            print("💰 Account Summary:")
            summary = trade_data['summary']
            print(f"  Balance: ${summary.get('balance', 0):,.2f}")
            print(f"  Equity: ${summary.get('equity', 0):,.2f}")
            print(f"  Margin: ${summary.get('margin', 0):,.2f}")
            print(f"  Free Margin: ${summary.get('free_margin', 0):,.2f}")
            
            if 'total_net_profit' in summary:
                print(f"\n📈 Trading Statistics:")
                print(f"  Total Net Profit: ${summary.get('total_net_profit', 0):,.2f}")
                print(f"  Gross Profit: ${summary.get('gross_profit', 0):,.2f}")
                print(f"  Gross Loss: ${summary.get('gross_loss', 0):,.2f}")
                print(f"  Profit Factor: {summary.get('profit_factor', 0):.2f}")
                print(f"  Total Trades: {summary.get('total_trades', 0)}")
                print(f"  Profit Trades: {summary.get('profit_trades', 0)} ({summary.get('profit_trades', 0)/max(summary.get('total_trades', 1), 1)*100:.1f}%)")
                print(f"  Loss Trades: {summary.get('loss_trades', 0)} ({summary.get('loss_trades', 0)/max(summary.get('total_trades', 1), 1)*100:.1f}%)")
            print()
    
    # History Report解析
    if os.path.exists(history_report):
        history_data = parser.parse_report_history(history_report)
        
        if history_data.get('deposits'):
            print("💵 Deposits:")
            total_deposits = 0
            for deposit in history_data['deposits']:
                print(f"  {deposit['time']}: ${deposit['amount']:,.2f}")
                total_deposits += deposit['amount']
            print(f"  Total Deposits: ${total_deposits:,.2f}\n")
        
        if history_data.get('statistics'):
            stats = history_data['statistics']
            print("📊 Calculated Statistics:")
            print(f"  Total Trades: {stats['total_trades']}")
            print(f"  Win Rate: {stats['win_rate']:.1f}%")
            print(f"  Net Profit: ${stats['net_profit']:,.2f}")
            print(f"  Profit Factor: {stats['profit_factor']:.2f}")
            print(f"  Average Win: ${stats['average_win']:,.2f}")
            print(f"  Average Loss: ${stats['average_loss']:,.2f}")
            print(f"  Risk/Reward Ratio: 1:{stats['risk_reward_ratio']:.2f}")
            print(f"  Largest Profit: ${stats['largest_profit']:,.2f}")
            print(f"  Largest Loss: ${stats['largest_loss']:,.2f}")
            
            # 初期資金との比較
            if history_data.get('deposits'):
                initial_balance = sum(d['amount'] for d in history_data['deposits'])
                roi = (stats['net_profit'] / initial_balance) * 100 if initial_balance > 0 else 0
                print(f"\n💹 Return on Investment: {roi:+.2f}%")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        report_dir = sys.argv[1]
    else:
        report_dir = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5/Results/Live/Demo"
    
    analyze_demo_reports(report_dir)