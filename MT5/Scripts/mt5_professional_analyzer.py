#!/usr/bin/env python3
"""
MT5専門バックテスト分析システム
技術資産源: GitHub Quantreo, jimtin, 他MT5コミュニティ
解決対象: position_id基準の正確な取引ペア化・統計分析

問題履歴:
- 従来システム: 単純な連続取引ペア化（失敗）
- 根本原因: MT5内部構造理解不足・position_id無視
- 解決策: Excel Report + position_id基準の正確分析

作成者: Claude (技術資産統合・問題解決担当)
参考: https://github.com/Quantreo/MetaTrader-5-AUTOMATED-TRADING-using-Python
"""

import json
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd


class MT5ProfessionalAnalyzer:
    """MT5専門バックテスト分析システム（position_id基準）"""

    def __init__(self, mt5_results_path: str):
        self.mt5_results_path = mt5_results_path
        self.trades_df = None
        self.deals_df = None
        self.positions_df = None

    def load_mt5_excel_reports(self) -> bool:
        """MT5 Excelレポート読み込み（GitHub標準手法）"""
        print("📊 === MT5 Excelレポート読み込み開始 ===")

        try:
            # バックテストレポート検索
            backtest_file = None
            for file in os.listdir(self.mt5_results_path):
                if file.startswith("Reportバック") and file.endswith(".xlsx"):
                    backtest_file = os.path.join(self.mt5_results_path, file)
                    break

            if not backtest_file:
                print("❌ バックテストExcelファイルが見つかりません")
                return False

            print(f"📄 対象ファイル: {os.path.basename(backtest_file)}")

            # Excel シート情報取得
            with pd.ExcelFile(backtest_file) as xls:
                sheet_names = xls.sheet_names
                print(f"✅ 利用可能シート: {sheet_names}")

                # MT5レポートシート読み込み（実際の構造に適応）
                # メインデータをSheet1から読み込み
                main_df = pd.read_excel(xls, sheet_name="Sheet1")
                print(f"✅ メインデータ読み込み: {len(main_df)}行")

                # データ内容に応じて分類
                if not main_df.empty:
                    # 全データをdealsとして扱い、後で分析
                    self.deals_df = main_df
                    print(f"✅ Deals設定完了: {len(self.deals_df)}件")

                # 他のシートも確認
                for sheet in sheet_names:
                    if sheet != "Sheet1":
                        try:
                            temp_df = pd.read_excel(xls, sheet_name=sheet)
                            print(f"✅ {sheet}読み込み: {len(temp_df)}行")
                        except:
                            print(f"⚠️ {sheet}読み込み失敗")

                # データ構造確認
                self.analyze_data_structure()

            return True

        except Exception as e:
            print(f"❌ Excel読み込みエラー: {e}")
            return False

    def analyze_data_structure(self):
        """データ構造分析・カラム確認・MT5レポート構造解析"""
        print("\n🔍 === データ構造分析 ===")

        if self.deals_df is not None:
            print(f"📋 データ形状: {self.deals_df.shape}")
            print(f"📋 カラム: {list(self.deals_df.columns)}")

            # MT5レポートは複数セクションに分かれている可能性
            # キーワード検索でセクション特定
            keywords = [
                "取引履歴",
                "Trade History",
                "Deals",
                "Orders",
                "Positions",
                "Time",
                "Type",
                "Order",
                "Size",
                "Price",
                "S/L",
                "T/P",
                "Profit",
            ]

            print("\n🔍 データ内容スキャン:")
            for i, row in self.deals_df.iterrows():
                if i > 50:  # 最初の50行のみチェック
                    break

                row_str = " ".join([str(val) for val in row.values if pd.notna(val)])

                # キーワード検出
                for keyword in keywords:
                    if keyword in row_str:
                        print(f"✅ {keyword} 検出 - 行{i}: {row_str[:100]}...")
                        break

                # ヘッダー行らしき構造検出
                if any(
                    word in row_str.lower()
                    for word in ["time", "order", "price", "profit", "type"]
                ):
                    print(f"🎯 ヘッダー候補 - 行{i}: {row.values}")

                    # この行以降をデータとして抽出
                    if i + 1 < len(self.deals_df):
                        self.extract_trade_data_from_row(i)
                    break

    def extract_trade_data_from_row(self, header_row: int):
        """指定行をヘッダーとしてデータ抽出"""
        print(f"\n📊 === 行{header_row}からデータ抽出開始 ===")

        try:
            # ヘッダー行を列名として設定
            header = self.deals_df.iloc[header_row].values
            data_rows = self.deals_df.iloc[header_row + 1 :].values

            # 新しいDataFrame作成
            trade_df = pd.DataFrame(data_rows, columns=header)

            # 空行・NaN行除去
            trade_df = trade_df.dropna(how="all")

            print(f"✅ 抽出データ形状: {trade_df.shape}")
            print(f"✅ 新カラム: {list(trade_df.columns)}")

            # データ品質確認・デバッグ出力追加
            print("✅ 非空データ確認:")
            for i, col in enumerate(trade_df.columns):
                non_null_count = trade_df[col].notna().sum()
                print(f"  カラム{i} '{col}': {non_null_count}個の非空値")

            print(f"✅ データサンプル:\n{trade_df.head(10)}")

            # 抽出成功なら置き換え
            self.deals_df = trade_df

            # より詳細なキーワード検索で取引データセクション特定
            self.identify_trade_data_section()

        except Exception as e:
            print(f"❌ 抽出エラー: {e}")
            import traceback

            traceback.print_exc()

    def identify_trade_data_section(self):
        """取引データセクション詳細特定"""
        print("\n🎯 === 取引データセクション詳細特定 ===")

        if self.deals_df is None or self.deals_df.empty:
            return

        # 取引関連キーワードでセクション検索
        trade_keywords = [
            "Time",
            "Order",
            "Deal",
            "Type",
            "Buy",
            "Sell",
            "Volume",
            "Price",
            "S/L",
            "T/P",
            "Profit",
            "Balance",
            "時間",
            "注文",
            "取引",
            "種類",
            "数量",
            "価格",
            "損益",
            "残高",
        ]

        potential_headers = []

        # 各行をチェックして取引データらしいヘッダーを特定
        for idx, row in self.deals_df.iterrows():
            if idx > 200:  # 最初の200行のみチェック
                break

            row_text = " ".join([str(val) for val in row.values if pd.notna(val)])

            # キーワードマッチ数をカウント
            keyword_matches = sum(
                1 for keyword in trade_keywords if keyword in row_text
            )

            if keyword_matches >= 3:  # 3個以上キーワードマッチ
                potential_headers.append(
                    {
                        "row_index": idx,
                        "keyword_matches": keyword_matches,
                        "row_content": row.values,
                        "row_text": row_text[:200] + "..."
                        if len(row_text) > 200
                        else row_text,
                    }
                )

        print(f"✅ 取引データヘッダー候補: {len(potential_headers)}個発見")

        for i, header in enumerate(potential_headers[:5]):  # 上位5個表示
            print(
                f"  候補{i+1} (行{header['row_index']}): {header['keyword_matches']}個マッチ"
            )
            print(f"    内容: {header['row_text']}")

        # 最有力候補を選択して再抽出
        if potential_headers:
            best_header = max(potential_headers, key=lambda x: x["keyword_matches"])
            print(
                f"\n🎯 最有力ヘッダー: 行{best_header['row_index']} ({best_header['keyword_matches']}個マッチ)"
            )

            # 最有力候補で再抽出実行
            self.extract_trade_data_from_row(best_header["row_index"])
        else:
            print("❌ 取引データヘッダーが特定できませんでした")

    def create_position_based_trades(self) -> List[Dict]:
        """position_id基準の正確な取引ペア作成（GitHub標準手法）"""
        print("\n🎯 === position_id基準取引ペア作成 ===")

        if self.deals_df is None:
            print("❌ Dealsデータが利用できません")
            return []

        trades = []

        # position_id または Position カラム検索
        position_col = None
        for col in ["Position", "position_id", "Ticket", "Order"]:
            if col in self.deals_df.columns:
                position_col = col
                break

        if not position_col:
            print("❌ position識別カラムが見つかりません")
            return []

        print(f"✅ Position識別カラム: {position_col}")

        # position_idでグループ化
        position_groups = self.deals_df.groupby(position_col)

        for position_id, group in position_groups:
            if len(group) >= 2:  # エントリー・エグジット最低2件
                # 時間順ソート
                group_sorted = group.sort_values(
                    "Time" if "Time" in group.columns else group.columns[0]
                )

                entry = group_sorted.iloc[0]
                exit_deal = group_sorted.iloc[-1]

                # 取引方向・損益計算
                if "Type" in group.columns:
                    entry_type = entry["Type"]
                    is_buy = "Buy" in str(entry_type) or "buy" in str(entry_type)
                else:
                    is_buy = True  # デフォルト

                # 価格・ボリューム取得
                entry_price = entry.get("Price", 0.0)
                exit_price = exit_deal.get("Price", 0.0)
                volume = entry.get("Volume", 0.01)

                # 損益計算（pip基準）
                if is_buy:
                    gross_profit = (exit_price - entry_price) * volume * 100000
                else:
                    gross_profit = (entry_price - exit_price) * volume * 100000

                # 取引コスト（OANDA MT5基準）
                spread_cost = 0.6 * volume * 10
                commission_cost = 2.5 * volume * 2
                swap_cost = 0.8 * volume * 1
                total_cost = spread_cost + commission_cost + swap_cost
                net_profit = gross_profit - total_cost

                trades.append(
                    {
                        "position_id": position_id,
                        "entry_time": entry.get("Time", ""),
                        "exit_time": exit_deal.get("Time", ""),
                        "direction": "buy" if is_buy else "sell",
                        "volume": volume,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "gross_profit": gross_profit,
                        "spread_cost": spread_cost,
                        "commission_cost": commission_cost,
                        "swap_cost": swap_cost,
                        "total_cost": total_cost,
                        "profit": net_profit,
                        "is_winner": net_profit > 0,
                        "deal_count": len(group),
                    }
                )

        print(f"✅ 作成取引ペア: {len(trades)}組")
        print(f"✅ 処理position数: {len(position_groups)}")

        return trades

    def calculate_professional_statistics(self, trades: List[Dict]) -> Dict:
        """professional統計分析（GitHub標準指標）"""
        print("\n📊 === Professional統計分析実行 ===")

        if not trades:
            return {"error": "No trades available"}

        # 基本統計
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["is_winner"])
        losing_trades = total_trades - winning_trades

        # 損益分析
        total_profit = sum(t["profit"] for t in trades if t["profit"] > 0)
        total_loss = abs(sum(t["profit"] for t in trades if t["profit"] < 0))
        net_profit = sum(t["profit"] for t in trades)

        # 主要指標
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
        win_rate = (winning_trades / total_trades) * 100

        # リスクリワード比
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # ドローダウン計算
        balance_curve = [10000]  # 初期残高
        for trade in trades:
            balance_curve.append(balance_curve[-1] + trade["profit"])

        peak = balance_curve[0]
        max_dd = 0
        for balance in balance_curve:
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # 取引コスト分析
        total_cost = sum(t["total_cost"] for t in trades)
        gross_volume = sum(abs(t["gross_profit"]) for t in trades)
        cost_percentage = (total_cost / gross_volume) * 100 if gross_volume > 0 else 0

        results = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "net_profit": net_profit,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "risk_reward_ratio": risk_reward_ratio,
            "max_drawdown_percent": max_dd,
            "total_cost": total_cost,
            "cost_percentage": cost_percentage,
            "final_balance": balance_curve[-1],
        }

        # 結果表示
        print(f"📊 総取引数: {total_trades}")
        print(f"📊 勝率: {win_rate:.1f}%")
        print(f"📊 プロフィットファクター: {profit_factor:.3f}")
        print(f"📊 リスクリワード比: {risk_reward_ratio:.3f}")
        print(f"📊 最大ドローダウン: {max_dd:.2f}%")
        print(f"📊 取引コスト影響: {cost_percentage:.1f}%")
        print(f"📊 最終残高: ${balance_curve[-1]:.2f}")

        return results

    def run_professional_analysis(self) -> Dict:
        """Professional分析実行"""
        print("🚀 === MT5 Professional分析システム開始 ===")
        print("技術基盤: GitHub MT5コミュニティベストプラクティス")
        print()

        # Excel読み込み
        if not self.load_mt5_excel_reports():
            return {"error": "Failed to load Excel reports"}

        # position基準取引作成
        trades = self.create_position_based_trades()
        if not trades:
            return {"error": "Failed to create position-based trades"}

        # 統計分析
        statistics = self.calculate_professional_statistics(trades)

        # 結果保存
        results = {
            "timestamp": datetime.now().isoformat(),
            "method": "position_id_based_analysis",
            "data_source": "MT5_Excel_Reports",
            "trades_data": trades,
            "statistics": statistics,
        }

        output_file = os.path.join(
            self.mt5_results_path, "professional_analysis_results.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print("\n✅ Professional分析完了")
        print(f"📄 結果保存: {output_file}")

        return results


def main():
    """MT5 Professional分析実行"""
    mt5_path = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results"

    analyzer = MT5ProfessionalAnalyzer(mt5_path)
    results = analyzer.run_professional_analysis()

    return results


if __name__ == "__main__":
    main()
