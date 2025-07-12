#!/usr/bin/env python3
"""
取引詳細分析: コスト崩壊の原因徹底調査
なぜリアリティコストで戦略が破綻したのかを解明
"""

import json
import numpy as np

class TradeAnalysisDeepDive:
    """取引詳細分析クラス"""
    
    def __init__(self):
        self.cost_per_trade_pips = 2.0  # スプレッド(1.5) + 手数料(0.3) + スリッページ(0.2)
        self.cost_per_trade_price = 0.0002  # 2.0 pips = 0.0002
    
    def analyze_cost_breakdown(self, wfa_file='minimal_wfa_results.json'):
        """コスト破綻の原因分析"""
        print("🔍 取引詳細分析: コスト破綻の原因調査")
        
        # WFA結果読み込み
        with open(wfa_file, 'r') as f:
            data = json.load(f)
        
        wfa_results = data['wfa_results']
        
        print(f"\n📊 各フォールドの詳細分析:")
        
        for result in wfa_results:
            fold_id = result['fold_id']
            oos_pf = result['oos_pf']
            oos_trades = result['oos_trades']
            oos_return = result['oos_return']
            oos_win_rate = result.get('oos_win_rate', 0)
            
            # 基本計算
            avg_return_per_trade = oos_return / oos_trades if oos_trades > 0 else 0
            avg_return_pips = avg_return_per_trade / 0.0001  # price to pips
            
            # コスト影響
            total_cost = self.cost_per_trade_price * oos_trades
            cost_impact_ratio = total_cost / abs(oos_return) if oos_return != 0 else 0
            
            # 勝ち負け分析（簡易推定）
            if oos_pf > 0 and oos_trades > 0:
                # PFから勝ち取引と負け取引のリターンを推定
                win_trades = int(oos_trades * oos_win_rate)
                lose_trades = oos_trades - win_trades
                
                if lose_trades > 0:
                    # PF = 勝ち取引の総利益 / 負け取引の総損失
                    # oos_return = 勝ち取引の総利益 - 負け取引の総損失
                    # 連立方程式を解く
                    total_wins = (oos_return + oos_return * oos_pf) / (1 + oos_pf)
                    total_losses = total_wins / oos_pf if oos_pf > 0 else 0
                    
                    avg_win_pips = (total_wins / win_trades / 0.0001) if win_trades > 0 else 0
                    avg_loss_pips = (total_losses / lose_trades / 0.0001) if lose_trades > 0 else 0
                else:
                    avg_win_pips = avg_return_pips
                    avg_loss_pips = 0
            else:
                avg_win_pips = 0
                avg_loss_pips = 0
                win_trades = 0
                lose_trades = 0
            
            # コスト後の状況
            net_avg_win_pips = avg_win_pips - self.cost_per_trade_pips
            net_avg_loss_pips = avg_loss_pips + self.cost_per_trade_pips
            
            # コスト後PF
            if net_avg_loss_pips > 0 and net_avg_win_pips > 0:
                cost_adjusted_pf = net_avg_win_pips / net_avg_loss_pips
            else:
                cost_adjusted_pf = 0
            
            # ブレイクイーブン分析
            breakeven_win_pips = self.cost_per_trade_pips + avg_loss_pips
            current_edge_pips = avg_win_pips - breakeven_win_pips
            
            print(f"\n   📋 フォールド{fold_id}:")
            print(f"     基本情報:")
            print(f"       取引数: {oos_trades}, 勝率: {oos_win_rate:.1%}")
            print(f"       元PF: {oos_pf:.3f}")
            print(f"     \n     収益分析:")
            print(f"       平均リターン/取引: {avg_return_pips:.1f} pips")
            print(f"       推定平均勝ち: {avg_win_pips:.1f} pips")
            print(f"       推定平均負け: {avg_loss_pips:.1f} pips")
            print(f"     \n     コスト影響:")
            print(f"       コスト/取引: {self.cost_per_trade_pips:.1f} pips")
            print(f"       コスト後平均勝ち: {net_avg_win_pips:.1f} pips")
            print(f"       コスト後平均負け: {net_avg_loss_pips:.1f} pips")
            print(f"       コスト後PF: {cost_adjusted_pf:.3f}")
            print(f"     \n     生存性分析:")
            print(f"       必要エッジ: {breakeven_win_pips:.1f} pips/勝ち取引")
            print(f"       実際エッジ: {current_edge_pips:.1f} pips")
            print(f"       エッジ不足: {-current_edge_pips:.1f} pips" if current_edge_pips < 0 else f"       エッジ余裕: {current_edge_pips:.1f} pips")
        
        # 全体サマリー
        self._generate_summary_analysis(wfa_results)
    
    def _generate_summary_analysis(self, wfa_results):
        """全体サマリー分析"""
        print(f"\n🎯 全体サマリー分析:")
        
        # 統計
        total_trades = sum([r['oos_trades'] for r in wfa_results])
        avg_trades_per_fold = total_trades / len(wfa_results)
        avg_win_rate = np.mean([r.get('oos_win_rate', 0) for r in wfa_results])
        
        # 平均リターン
        avg_returns = [r['oos_return'] / r['oos_trades'] if r['oos_trades'] > 0 else 0 for r in wfa_results]
        overall_avg_return_pips = np.mean(avg_returns) / 0.0001
        
        print(f"   平均取引数/フォールド: {avg_trades_per_fold:.1f}")
        print(f"   平均勝率: {avg_win_rate:.1%}")
        print(f"   平均リターン/取引: {overall_avg_return_pips:.1f} pips")
        print(f"   必要コスト: {self.cost_per_trade_pips:.1f} pips/取引")
        
        # 根本問題の診断
        print(f"\n🔬 根本問題の診断:")
        
        if overall_avg_return_pips < self.cost_per_trade_pips:
            print(f"   ❌ 致命的問題: 平均利益({overall_avg_return_pips:.1f}pips) < コスト({self.cost_per_trade_pips:.1f}pips)")
            print(f"   → 取引毎に平均{self.cost_per_trade_pips - overall_avg_return_pips:.1f}pipsの損失")
        else:
            print(f"   ✅ 平均利益はコストを上回っている")
        
        if avg_trades_per_fold > 100:
            print(f"   ⚠️ 高頻度取引: 平均{avg_trades_per_fold:.0f}取引/フォールド")
            print(f"   → コスト影響が累積的に増大")
        
        if avg_win_rate < 0.5:
            print(f"   ⚠️ 低勝率: {avg_win_rate:.1%}")
            print(f"   → 勝ち取引で大きなエッジが必要")
        
        # 改善方針
        print(f"\n💡 改善方針:")
        
        required_improvement = self.cost_per_trade_pips - overall_avg_return_pips
        if required_improvement > 0:
            print(f"   1. 平均利益を{required_improvement:.1f}pips改善")
            print(f"   2. 取引頻度を{required_improvement/overall_avg_return_pips*100:.0f}%削減")
            print(f"   3. 勝率を{required_improvement/overall_avg_return_pips*avg_win_rate:.1%}改善")
        
        print(f"   4. より大きなブレイクアウトのみに絞る")
        print(f"   5. 利確・損切りレベルの最適化")
        print(f"   6. 時間軸の変更（より大きな動きを狙う）")

if __name__ == "__main__":
    analyzer = TradeAnalysisDeepDive()
    analyzer.analyze_cost_breakdown()