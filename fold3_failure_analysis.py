#!/usr/bin/env python3
"""
フォールド3敗因分析システム
目的: PF 0.897の負け期間の根本原因特定と対策立案
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from data_cache_system import DataCacheManager

class Fold3FailureAnalyzer:
    def __init__(self):
        self.cache_manager = DataCacheManager()
        self.results_file = 'cost_resistant_wfa_results_ALL_BIAS_FIXED.json'
        
    def analyze_fold3_period(self):
        """フォールド3期間の詳細分析"""
        print("🔍 フォールド3敗因分析開始...")
        
        # 結果データ読み込み
        with open(self.results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # フォールド3データ抽出
        fold3 = None
        for fold in results['wfa_results_raw']:
            if fold['fold_id'] == 3:
                fold3 = fold
                break
        
        if not fold3:
            print("❌ フォールド3データが見つかりません")
            return
        
        print(f"📊 フォールド3基本データ:")
        print(f"   取引数: {fold3['trades']}")
        print(f"   勝率: {fold3['win_rate']:.1%}")
        print(f"   PF: {fold3['profit_factor']:.3f}")
        print(f"   リターン: {fold3['total_return']:.1%}")
        
        # 取引詳細分析
        self.analyze_trade_patterns(fold3['trades_detail'])
        
        # 市場環境分析
        self.analyze_market_environment(fold3)
        
        # 戦略弱点特定
        self.identify_strategy_weaknesses(fold3)
        
    def analyze_trade_patterns(self, trades):
        """取引パターン分析"""
        print("\n📈 取引パターン分析:")
        
        if not trades:
            print("   取引データなし")
            return
        
        # 勝ち負け分析
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        print(f"   勝ち取引: {len(winning_trades)}回")
        print(f"   負け取引: {len(losing_trades)}回")
        
        if winning_trades:
            avg_win = np.mean([t['pnl'] for t in winning_trades])
            print(f"   平均勝ち: {avg_win:.1f}円")
        
        if losing_trades:
            avg_loss = np.mean([t['pnl'] for t in losing_trades])
            print(f"   平均負け: {avg_loss:.1f}円")
        
        # 連敗分析
        consecutive_losses = self.analyze_consecutive_losses(trades)
        print(f"   最大連敗: {consecutive_losses}回")
        
        # 時間帯分析
        self.analyze_time_patterns(trades)
        
    def analyze_consecutive_losses(self, trades):
        """連敗分析"""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade['pnl'] <= 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
    
    def analyze_time_patterns(self, trades):
        """時間帯パターン分析"""
        print("\n⏰ 時間帯分析:")
        
        hour_performance = {}
        for trade in trades:
            entry_time = datetime.fromisoformat(trade['entry_time'])
            hour = entry_time.hour
            
            if hour not in hour_performance:
                hour_performance[hour] = {'trades': 0, 'pnl': 0}
            
            hour_performance[hour]['trades'] += 1
            hour_performance[hour]['pnl'] += trade['pnl']
        
        # 最悪の時間帯特定
        worst_hour = min(hour_performance.keys(), 
                        key=lambda h: hour_performance[h]['pnl'])
        
        print(f"   最悪時間帯: {worst_hour}時")
        print(f"   損失: {hour_performance[worst_hour]['pnl']:.1f}円")
        print(f"   取引数: {hour_performance[worst_hour]['trades']}回")
        
    def analyze_market_environment(self, fold3):
        """市場環境分析"""
        print("\n🌍 市場環境分析:")
        
        # 戦略統計から環境推定
        stats = fold3.get('strategy_stats', {})
        
        if stats:
            approval_rate = stats.get('approval_rate', 0)
            filter_effectiveness = stats.get('filter_effectiveness', 0)
            
            print(f"   シグナル承認率: {approval_rate:.1%}")
            print(f"   フィルタ効果: {filter_effectiveness:.1%}")
            
            # 環境判定
            if approval_rate < 0.2:
                print("   🚨 環境判定: 低ボラティリティ期間")
                print("   → ブレイクアウト戦略に不利な環境")
            elif filter_effectiveness < 0.5:
                print("   🚨 環境判定: フィルタ機能不全")
                print("   → 偽ブレイクアウト多発期間")
            
    def identify_strategy_weaknesses(self, fold3):
        """戦略弱点特定"""
        print("\n🎯 戦略弱点特定:")
        
        # PF分析
        pf = fold3['profit_factor']
        if pf < 1.0:
            if pf < 0.9:
                print("   🚨 重大な弱点: 損益比率の悪化")
            print("   🔧 推奨対策:")
            print("   1. ストップロス条件の見直し")
            print("   2. テイクプロフィット条件の最適化")
            print("   3. エントリー条件の厳格化")
        
        # 取引頻度分析
        trades_count = fold3['trades']
        if trades_count < 400:
            print("   ⚠️  取引頻度低下")
            print("   → 機会損失の可能性")
        elif trades_count > 600:
            print("   ⚠️  取引頻度過多")
            print("   → オーバートレードの可能性")
            
    def generate_improvement_suggestions(self):
        """改善提案生成"""
        print("\n💡 改善提案:")
        
        suggestions = [
            "1. 市場レジーム検出フィルタの追加",
            "2. ボラティリティ適応型パラメータ調整",
            "3. 時間帯別取引制限の実装",
            "4. 連敗時の取引停止機能",
            "5. 動的ストップロス調整機能"
        ]
        
        for suggestion in suggestions:
            print(f"   {suggestion}")
            
        return suggestions
    
    def run_analysis(self):
        """完全分析実行"""
        self.analyze_fold3_period()
        suggestions = self.generate_improvement_suggestions()
        
        print("\n🎯 分析完了")
        print("次のステップ: Copilotによる創造的改善案生成")
        
        return suggestions

if __name__ == "__main__":
    analyzer = Fold3FailureAnalyzer()
    analyzer.run_analysis()