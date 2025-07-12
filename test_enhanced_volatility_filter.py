#!/usr/bin/env python3
"""
強化ボラティリティフィルター効果検証テスト
"""

import json
import sys
from datetime import datetime, timedelta
from enhanced_breakout_strategy import EnhancedBreakoutStrategy
from multi_timeframe_breakout_strategy import MultiTimeframeData, create_enhanced_sample_data

def test_volatility_filter_effect():
    """ボラティリティフィルター効果検証"""
    
    print("🔍 強化ボラティリティフィルター効果検証開始")
    print("=" * 60)
    
    try:
        # 短期テストデータ（2019年1月-6月）
        start_date = datetime(2019, 1, 1)
        end_date = datetime(2019, 6, 30)
        
        print(f"テスト期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        
        # データ生成
        print("📊 テストデータ生成中...")
        sample_data = create_enhanced_sample_data()
        
        if not sample_data:
            print("❌ データ生成に失敗")
            return
        
        # MultiTimeframeDataオブジェクト作成
        mtf_data = MultiTimeframeData(sample_data)
        
        print(f"✅ データ生成完了")
        print(f"   H1データ: {len(mtf_data.get_h1_data())}本")
        print(f"   H4データ: {len(mtf_data.get_h4_data())}本")
        
        # 基本パラメータ
        base_params = {
            'h4_period': 24,
            'h1_period': 24,
            'atr_period': 14,
            'profit_atr': 2.5,
            'stop_atr': 1.3,
            'min_break_pips': 5
        }
        
        # テスト1: フィルター無効版
        print("\n🔄 テスト1: フィルター無効版")
        print("-" * 30)
        
        strategy_without_filter = EnhancedBreakoutStrategy(base_params)
        strategy_without_filter.enable_volatility_filter = False
        
        results_without = strategy_without_filter.backtest_enhanced_strategy(
            mtf_data, start_date, end_date
        )
        
        print(f"結果（フィルター無効）:")
        print(f"   取引数: {results_without['total_trades']}")
        print(f"   勝率: {results_without['win_rate']:.1%}")
        print(f"   PF: {results_without['profit_factor']:.3f}")
        print(f"   総損益: ${results_without['total_pnl']:.2f}")
        print(f"   最大DD: {results_without['max_drawdown']:.1%}")
        
        # テスト2: フィルター有効版
        print("\n🔄 テスト2: フィルター有効版")
        print("-" * 30)
        
        strategy_with_filter = EnhancedBreakoutStrategy(base_params)
        strategy_with_filter.enable_volatility_filter = True
        
        results_with = strategy_with_filter.backtest_enhanced_strategy(
            mtf_data, start_date, end_date
        )
        
        print(f"結果（フィルター有効）:")
        print(f"   取引数: {results_with['total_trades']}")
        print(f"   勝率: {results_with['win_rate']:.1%}")
        print(f"   PF: {results_with['profit_factor']:.3f}")
        print(f"   総損益: ${results_with['total_pnl']:.2f}")
        print(f"   最大DD: {results_with['max_drawdown']:.1%}")
        
        # フィルター統計
        filter_stats = results_with.get('signal_statistics', {})
        print(f"   フィルタリング率: {filter_stats.get('filter_ratio', 0):.1%}")
        print(f"   実行率: {filter_stats.get('execution_ratio', 0):.1%}")
        
        # 効果分析
        print("\n📊 フィルター効果分析")
        print("-" * 30)
        
        improvement_analysis = analyze_filter_improvement(results_without, results_with)
        
        for metric, data in improvement_analysis.items():
            print(f"{metric}: {data['improvement']:+.1%} ({data['before']:.3f} → {data['after']:.3f})")
        
        # 詳細分析
        print("\n🔍 詳細分析")
        print("-" * 30)
        
        # 信頼度別分析
        if 'confidence_analysis' in results_with:
            print("信頼度別取引分析:")
            for confidence, data in results_with['confidence_analysis'].items():
                print(f"   {confidence}: {data['trades']}取引, 勝率{data['win_rate']:.1%}, 平均PnL${data['avg_pnl']:.2f}")
        
        # 総合判定
        print("\n🎯 総合判定")
        print("-" * 30)
        
        overall_score = calculate_overall_improvement_score(improvement_analysis)
        
        if overall_score >= 0.3:
            judgment = "🟢 フィルター効果：優秀"
        elif overall_score >= 0.1:
            judgment = "🟡 フィルター効果：良好"
        elif overall_score >= 0:
            judgment = "🟠 フィルター効果：軽微"
        else:
            judgment = "🔴 フィルター効果：悪化"
        
        print(f"{judgment} (スコア: {overall_score:+.3f})")
        
        # 結果保存
        save_test_results(results_without, results_with, improvement_analysis, overall_score)
        
        print("\n✅ ボラティリティフィルター効果検証完了")
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def analyze_filter_improvement(results_before, results_after):
    """フィルター改善効果分析"""
    
    metrics = {
        'プロフィットファクター': {
            'before': results_before.get('profit_factor', 0),
            'after': results_after.get('profit_factor', 0)
        },
        '勝率': {
            'before': results_before.get('win_rate', 0),
            'after': results_after.get('win_rate', 0)
        },
        '平均取引損益': {
            'before': results_before.get('avg_trade_pnl', 0),
            'after': results_after.get('avg_trade_pnl', 0)
        },
        '最大ドローダウン': {
            'before': results_before.get('max_drawdown', 0),
            'after': results_after.get('max_drawdown', 0)
        },
        'シャープ比': {
            'before': results_before.get('sharpe_ratio', 0),
            'after': results_after.get('sharpe_ratio', 0)
        }
    }
    
    analysis = {}
    
    for metric, data in metrics.items():
        before = data['before']
        after = data['after']
        
        if metric == '最大ドローダウン':
            # ドローダウンは小さいほど良い
            improvement = (before - after) / before if before != 0 else 0
        else:
            # 他の指標は大きいほど良い
            improvement = (after - before) / before if before != 0 else 0
        
        analysis[metric] = {
            'before': before,
            'after': after,
            'improvement': improvement
        }
    
    return analysis

def calculate_overall_improvement_score(improvement_analysis):
    """総合改善スコア計算"""
    
    weights = {
        'プロフィットファクター': 0.3,
        '勝率': 0.2,
        '平均取引損益': 0.2,
        '最大ドローダウン': 0.2,
        'シャープ比': 0.1
    }
    
    total_score = 0
    
    for metric, data in improvement_analysis.items():
        weight = weights.get(metric, 0)
        improvement = data['improvement']
        total_score += improvement * weight
    
    return total_score

def save_test_results(results_before, results_after, improvement_analysis, overall_score):
    """テスト結果保存"""
    
    test_results = {
        'test_type': 'volatility_filter_effectiveness',
        'timestamp': datetime.now().isoformat(),
        'results_before_filter': results_before,
        'results_after_filter': results_after,
        'improvement_analysis': improvement_analysis,
        'overall_improvement_score': overall_score,
        'test_period': '2019-01-01 to 2019-06-30'
    }
    
    filename = f"volatility_filter_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"📝 テスト結果保存: {filename}")

if __name__ == "__main__":
    success = test_volatility_filter_effect()
    sys.exit(0 if success else 1)