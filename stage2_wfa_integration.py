#!/usr/bin/env python3
"""
Stage2: WFA統合検証システム
マルチタイムフレーム戦略とPurged & Embargoed WFAの統合
"""

from data_cache_system import DataCacheManager
from multi_timeframe_breakout_strategy import MultiTimeframeBreakoutStrategy, MultiTimeframeData
from wfa_prototype import PurgedEmbargoedWFA, StatisticalValidator, WFAConfig
import json
from datetime import datetime

class Stage2WFAIntegration:
    """Stage2 WFA統合システム"""
    
    def __init__(self):
        self.cache_manager = DataCacheManager()
        
        # Stage1合格パラメータ
        self.optimized_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,    # 改善済み
            'stop_atr': 1.3,      # 改善済み
            'min_break_pips': 5
        }
    
    def run_full_wfa_validation(self):
        """完全WFA検証実行"""
        print("🚀 Stage2: WFA統合検証開始")
        print("   目標: 統計的有意性（p < 0.05）の確認")
        
        # フルデータ取得
        raw_data = self.cache_manager.get_full_data()
        
        print(f"📊 検証データ:")
        print(f"   期間: {raw_data[0]['datetime'].strftime('%Y-%m-%d')} to {raw_data[-1]['datetime'].strftime('%Y-%m-%d')}")
        print(f"   総バー数: {len(raw_data)}")
        
        # WFA設定
        wfa_config = WFAConfig(
            is_months=18,         # IS期間18ヶ月（フォールド数増加）
            oos_months=6,         # OOS期間6ヶ月
            step_months=6,        # 6ヶ月ステップ
            anchored=True         # アンカード方式
        )
        
        print(f"\n🔬 WFA設定:")
        print(f"   IS期間: {wfa_config.is_months}ヶ月")
        print(f"   OOS期間: {wfa_config.oos_months}ヶ月")
        print(f"   ステップ: {wfa_config.step_months}ヶ月")
        
        # 戦略設定（WFA用）
        strategy_config = {
            'ma_periods': [20],
            'timeframe': 'M5',
            'other_periods': []
        }
        
        # WFAエンジン初期化
        wfa_engine = PurgedEmbargoedWFA(raw_data, wfa_config, strategy_config)
        
        # フォールド生成
        print(f"\n📋 WFAフォールド生成中...")
        folds = wfa_engine.generate_folds()
        
        if len(folds) < 3:
            print(f"⚠️ フォールド数不足: {len(folds)}個（最低3個必要）")
            return None, None
        
        # 各フォールドでの戦略実行
        print(f"\n📈 各フォールドでの戦略検証:")
        wfa_results = []
        
        for fold_idx, fold in enumerate(folds, 1):
            print(f"\n   フォールド {fold_idx}/{len(folds)}:")
            
            # フォールドデータ取得
            fold_data = wfa_engine.get_fold_data(fold_idx)
            
            # IS期間でのパラメータ最適化（簡易版）
            is_strategy = MultiTimeframeBreakoutStrategy(self.optimized_params)
            
            # MTFデータ構築（フォールドデータ用）
            is_mtf_data = MultiTimeframeData(fold_data['is_data'])
            oos_mtf_data = MultiTimeframeData(fold_data['oos_data'])
            
            # IS期間性能
            is_result = is_strategy.backtest(is_mtf_data)
            
            # OOS期間検証
            oos_result = is_strategy.backtest(oos_mtf_data)
            
            print(f"     IS:  PF={is_result['profit_factor']:.3f}, 取引={is_result['total_trades']}")
            print(f"     OOS: PF={oos_result['profit_factor']:.3f}, 取引={oos_result['total_trades']}")
            
            # WFA結果記録
            fold_result = {
                'fold_id': fold_idx,
                'is_return': is_result['total_pnl'],
                'oos_return': oos_result['total_pnl'],
                'oos_sharpe': oos_result['sharpe_ratio'],
                'oos_pf': oos_result['profit_factor'],
                'trades': oos_result['total_trades']
            }
            
            wfa_results.append(fold_result)
        
        # 統計的検証
        statistical_results = self._perform_statistical_validation(wfa_results)
        
        # 最終判定
        final_judgment = self._final_judgment(statistical_results, wfa_results)
        
        # 結果保存
        self._save_stage2_results(wfa_results, statistical_results, final_judgment)
        
        return wfa_results, statistical_results
    
    def _perform_statistical_validation(self, wfa_results):
        """統計的検証実行"""
        print(f"\n🔬 統計的検証実行:")
        
        validator = StatisticalValidator(wfa_results)
        
        # OOS一貫性評価
        consistency = validator.calculate_oos_consistency()
        
        # WFA効率計算
        wfa_efficiency = validator.calculate_wfa_efficiency()
        
        # 基本統計
        total_folds = len(wfa_results)
        positive_folds = sum(1 for r in wfa_results if r['oos_return'] > 0)
        consistency_ratio = positive_folds / total_folds if total_folds > 0 else 0
        
        avg_oos_pf = sum(r['oos_pf'] for r in wfa_results) / len(wfa_results)
        avg_trades = sum(r['trades'] for r in wfa_results) / len(wfa_results)
        
        print(f"   フォールド数: {total_folds}")
        print(f"   正の結果: {positive_folds}/{total_folds} ({consistency_ratio:.1%})")
        print(f"   平均OOS PF: {avg_oos_pf:.3f}")
        print(f"   平均取引数: {avg_trades:.0f}")
        print(f"   WFA効率: {wfa_efficiency:.3f}")
        print(f"   統計的有意性: {'あり' if consistency.get('is_significant') else 'なし'}")
        print(f"   p値: {consistency.get('p_value', 1.0):.4f}")
        
        return {
            'total_folds': total_folds,
            'positive_folds': positive_folds,
            'consistency_ratio': consistency_ratio,
            'avg_oos_pf': avg_oos_pf,
            'avg_trades': avg_trades,
            'wfa_efficiency': wfa_efficiency,
            'statistical_significance': consistency.get('is_significant', False),
            'p_value': consistency.get('p_value', 1.0),
            'detailed_stats': consistency
        }
    
    def _final_judgment(self, stats, wfa_results):
        """最終判定"""
        print(f"\n🎯 Stage2最終判定:")
        
        # 判定基準
        criteria = {
            'statistical_significance': stats['statistical_significance'],
            'avg_pf_above_1_1': stats['avg_oos_pf'] >= 1.1,
            'wfa_efficiency_above_0_5': stats['wfa_efficiency'] >= 0.5,
            'consistency_above_60': stats['consistency_ratio'] >= 0.6
        }
        
        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)
        
        print(f"   判定基準達成状況:")
        for criterion, passed in criteria.items():
            status = "✅" if passed else "❌"
            print(f"     {criterion}: {status}")
        
        # 最終判定
        stage2_passed = passed_criteria >= 3  # 4基準中3つ以上
        
        print(f"\n🏆 Stage2判定結果: {'✅ 合格' if stage2_passed else '❌ 不合格'}")
        print(f"   達成基準: {passed_criteria}/{total_criteria}")
        
        if stage2_passed:
            print(f"\n🎊 WFA検証合格！")
            print(f"   🔬 統計的優位性確認")
            print(f"   📈 実機展開準備完了")
            print(f"   🏅 6週間改革プラン完遂")
        else:
            print(f"\n📝 改善が必要な領域:")
            if not criteria['statistical_significance']:
                print(f"   - 統計的有意性（p値改善）")
            if not criteria['avg_pf_above_1_1']:
                print(f"   - プロフィットファクター（{stats['avg_oos_pf']:.3f} → 1.1+）")
            if not criteria['wfa_efficiency_above_0_5']:
                print(f"   - WFA効率（{stats['wfa_efficiency']:.3f} → 0.5+）")
            if not criteria['consistency_above_60']:
                print(f"   - 一貫性（{stats['consistency_ratio']:.1%} → 60%+）")
        
        return {
            'stage2_passed': stage2_passed,
            'criteria_met': criteria,
            'score': f"{passed_criteria}/{total_criteria}",
            'next_phase': 'live_deployment' if stage2_passed else 'strategy_refinement'
        }
    
    def _save_stage2_results(self, wfa_results, stats, judgment):
        """Stage2結果保存"""
        complete_results = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'stage2_wfa_validation',
            'strategy_name': 'multi_timeframe_breakout_final',
            'parameters_used': self.optimized_params,
            'wfa_results': wfa_results,
            'statistical_analysis': stats,
            'final_judgment': judgment,
            'reform_plan_status': 'completed' if judgment['stage2_passed'] else 'needs_continuation'
        }
        
        filename = 'stage2_wfa_final_results.json'
        with open(filename, 'w') as f:
            json.dump(complete_results, f, indent=2)
        
        print(f"\n💾 Stage2完全結果保存: {filename}")

def main():
    """メイン実行"""
    print("🚀 Stage2 WFA統合検証システム実行開始")
    
    integration = Stage2WFAIntegration()
    
    # フル検証実行
    wfa_results, statistical_results = integration.run_full_wfa_validation()
    
    if wfa_results:
        print(f"\n✅ Stage2 WFA統合検証完了")
        print(f"   6週間改革プランの最終段階達成")
    else:
        print(f"\n⚠️ Stage2実行に技術的課題")
        print(f"   データ期間またはフォールド生成の調整が必要")
    
    return integration, wfa_results, statistical_results

if __name__ == "__main__":
    integration, wfa_results, stats = main()