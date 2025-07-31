#!/usr/bin/env python3
# JamesORB EA 詳細分析スクリプト
import re


def detailed_analysis():
    """JamesORB EA 2025-07-31 取引データの詳細分析"""

    try:
        with open(
            "MT5/Results/Live/Demo/ReportTrade-400078005.html", encoding="utf-16le"
        ) as f:
            content = f.read()
    except:
        print("ファイル読み込みエラー")
        return

    print("=== JamesORB EA 2025-07-31 徹底分析 ===\n")

    # 1. 完了取引の詳細分析
    print("1. 完了取引詳細分析")
    print("=" * 50)

    # 取引チケット7636803の詳細
    trade_data = {
        "チケット": "7636803",
        "実行時刻": "2025.07.31 13:27:22",
        "取引タイプ": "sell（売り取引）",
        "ロットサイズ": "0.01（最小ロット）",
        "エントリー価格": "1.14310",
        "ストップロス": "1.14393",  # エントリーより+83pips上
        "テイクプロフィット": "1.14206",  # エントリーより-104pips下
        "決済価格": "1.14332",
        "スワップ": "0円",
        "実現損益": "-33円",
        "EA名": "JamesORB",
    }

    for key, value in trade_data.items():
        print(f"{key}: {value}")

    # 2. ORB戦略分析
    print("\n2. ORB戦略パフォーマンス分析")
    print("=" * 50)

    entry_price = 1.14310
    exit_price = 1.14332
    sl_price = 1.14393
    tp_price = 1.14206

    # ピップ計算（EURUSD: 1pip = 0.0001）
    loss_pips = (exit_price - entry_price) * 10000
    sl_distance = (sl_price - entry_price) * 10000
    tp_distance = (entry_price - tp_price) * 10000

    print(f"エントリー価格: {entry_price}")
    print(f"決済価格: {exit_price}")
    print(f"実際の損失: {loss_pips:.1f} pips")
    print(f"SL設定距離: +{sl_distance:.1f} pips")
    print(f"TP設定距離: -{tp_distance:.1f} pips")
    print(f"リスクリワード比: 1:{tp_distance/sl_distance:.2f}")

    # 3. 保留注文分析（buy stop系）
    print("\n3. 保留注文戦略分析")
    print("=" * 50)

    # buy stop注文パターンを抽出
    buy_stop_pattern = r"buy stop.*?1\.1[4-5][0-9]{3}"
    re.findall(buy_stop_pattern, content)

    print("Buy Stop注文数: 検出中...")

    # 時刻別の注文配置パターンを分析
    time_pattern = r"2025\.07\.31 ([0-9]{2}:[0-9]{2}:[0-9]{2})"
    times = re.findall(time_pattern, content)

    if times:
        print("取引活動時間帯:")
        for time in sorted(set(times)):
            print(f"  - {time}")

    # 4. リスク管理評価
    print("\n4. リスク管理評価")
    print("=" * 50)

    account_balance = 3_002_712  # 終了時残高
    initial_balance = 3_000_000  # 初期残高
    daily_pnl = -33

    print(f"開始残高: {initial_balance:,}円")
    print(f"終了残高: {account_balance:,}円")
    print(f"本日損益: {daily_pnl}円")
    print(
        f"口座変動率: {((account_balance - initial_balance) / initial_balance) * 100:.4f}%"
    )
    print(f"1取引あたりリスク: {abs(daily_pnl) / initial_balance * 100:.4f}%")

    # 5. ORB戦略の問題点分析
    print("\n5. ORB戦略問題点分析")
    print("=" * 50)

    print("検出された問題:")
    print("- 売り取引が逆方向に動いて損失発生")
    print("- ストップロスに到達前に何らかの理由で決済")
    print(f"- 実際の損失({loss_pips:.1f}pips)はSL距離({sl_distance:.1f}pips)より小さい")
    print("- Opening Range Breakout の判定ロジック要検証")

    # 6. 推奨改善策
    print("\n6. 推奨改善策")
    print("=" * 50)

    print("immediate推奨:")
    print("1. ORB判定時間の確認（7-8時GMT?）")
    print("2. ブレイクアウト方向判定ロジックの検証")
    print("3. エントリー後の価格推移モニタリング強化")
    print("4. 複数ポジション管理ロジック（buy stop系）の動作確認")
    print("5. 決済条件の詳細確認（SL/TP以外の要因）")

    return True


if __name__ == "__main__":
    detailed_analysis()
