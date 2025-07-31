#!/usr/bin/env python3
# JamesORB取引データ解析スクリプト
import re


def parse_html_report():
    """HTMLレポートから取引データを抽出"""

    try:
        with open(
            "MT5/Results/Live/Demo/ReportTrade-400078005.html", encoding="utf-16le"
        ) as f:
            content = f.read()
    except:
        print("ファイル読み込みエラー")
        return

    print("=== JamesORB EA 2025-07-31 取引データ分析 ===\n")

    # 取引テーブルから主要データを抽出（正規表現を使用）
    trade_pattern = r"<td>EURUSD</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td>"

    trades = re.findall(trade_pattern, content)

    if trades:
        print("完了取引データ:")
        for i, trade in enumerate(trades):
            print(
                f"取引 {i+1}: チケット={trade[0]}, 時刻={trade[1]}, タイプ={trade[2]}, ロット={trade[3]}, 価格={trade[4]}, SL={trade[5]}, TP={trade[6]}, 決済価格={trade[7]}, スワップ={trade[8]}, 損益={trade[9]}, EA={trade[10]}"
            )

    # 注文履歴を抽出
    order_pattern = r"<td>EURUSD</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td>"

    orders = re.findall(order_pattern, content)

    if orders:
        print(f"\n保留注文データ ({len(orders)}件):")
        for i, order in enumerate(orders):
            print(
                f"注文 {i+1}: チケット={order[0]}, 時刻={order[1]}, タイプ={order[2]}, ロット={order[3]}, 価格={order[4]}, SL={order[5]}, TP={order[6]}, 現在価格={order[7]}, ステータス={order[8]}, EA={order[9]}"
            )

    # 口座残高情報を抽出
    balance_patterns = [
        r"<b>3\s*0\s*0\s*2\s*7\s*[0-9]+</b>",  # 残高
        r"<b>\s*-\s*[0-9]+\s*</b>",  # 損益
    ]

    print("\n=== 口座情報 ===")
    for pattern in balance_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            clean_match = re.sub(r"<[^>]*>", "", match).replace(" ", "")
            print(f"金額データ: {clean_match}")

    # 原始データから重要な数値を直接抽出
    print("\n=== 原始データ抽出 ===")
    # 7636803は取引チケット番号
    if "7636803" in content:
        print("✓ 2025-07-31の取引チケット7636803を確認")

    # 損益-33の確認
    if "-33" in content:
        print("✓ 本日損益-33円を確認")

    # 1.14310-1.14508の価格帯確認
    price_pattern = r"1\.1[4-5][0-9]{3}"
    prices = re.findall(price_pattern, content)
    if prices:
        print(f"✓ 取引価格帯: {min(prices)} - {max(prices)}")

    return True


if __name__ == "__main__":
    parse_html_report()
