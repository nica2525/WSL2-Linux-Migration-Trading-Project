#!/usr/bin/env python3
"""
リスク管理vs検証品質分析
過度なリスク管理による検証サンプル減少リスクの評価
"""

import json
from datetime import datetime, timedelta
from enhanced_breakout_strategy import EnhancedBreakoutStrategy
from multi_timeframe_breakout_strategy import MultiTimeframeData, create_enhanced_sample_data

def analyze_risk_vs_validation_quality():
    """リスク管理レベル別の検証品質分析"""
    
    print("⚖️ リスク管理vs検証品質分析開始")
    print("=" * 60)
    
    # テストデータ生成
    print("📊 テストデータ生成中...")
    sample_data = create_enhanced_sample_data()
    mtf_data = MultiTimeframeData(sample_data)
    
    test_period_start = datetime(2019, 1, 1)
    test_period_end = datetime(2019, 12, 31)
    
    print(f"✅ データ準備完了")
    print(f"   期間: {test_period_start.strftime('%Y-%m-%d')} - {test_period_end.strftime('%Y-%m-%d')}")
    
    # 基本パラメータ
    base_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,
        'stop_atr': 1.3,
        'min_break_pips': 5
    }
    
    # リスク管理レベル別テスト
    risk_levels = {
        'なし': {
            'enable_adaptive_risk': False,
            'enable_market_filter': False,
            'enable_volatility_filter': False
        },
        '軽度': {
            'enable_adaptive_risk': True,
            'enable_market_filter': False,
            'enable_volatility_filter': False
        },
        '中程度': {
            'enable_adaptive_risk': True,
            'enable_market_filter': True,
            'enable_volatility_filter': False
        },
        '強度': {
            'enable_adaptive_risk': True,
            'enable_market_filter': True,
            'enable_volatility_filter': True
        }
    }
    
    results = {}
    
    for level_name, config in risk_levels.items():
        print(f"\n🔄 リスク管理レベル: {level_name}")
        print("-" * 40)
        
        # 戦略初期化
        strategy = EnhancedBreakoutStrategy(base_params)
        strategy.enable_adaptive_risk = config['enable_adaptive_risk']
        strategy.enable_market_filter = config['enable_market_filter']
        strategy.enable_volatility_filter = config['enable_volatility_filter']
        
        # バックテスト実行（短時間版）
        try:
            # シグナル生成テスト（サンプリング）
            signals_count = 0
            filtered_count = 0
            
            h1_data = mtf_data.get_h1_data()
            
            # 100本おきにサンプリング（高速化）
            for i in range(100, min(1000, len(h1_data)), 100):
                current_time = h1_data[i]['datetime']
                
                signal = strategy.generate_enhanced_signal(
                    mtf_data, current_time, 0.0, 0.0, 0
                )
                
                signals_count += 1
                if signal:
                    filtered_count += 1
            
            # 検証品質指標計算
            if signals_count > 0:
                signal_survival_rate = filtered_count / signals_count
                estimated_annual_trades = filtered_count * (365 * 24 / 100)  # 年間推定取引数
                validation_feasibility = "可能" if estimated_annual_trades >= 30 else "困難"
                statistical_power = "高" if estimated_annual_trades >= 100 else ("中" if estimated_annual_trades >= 50 else "低")
            else:
                signal_survival_rate = 0
                estimated_annual_trades = 0
                validation_feasibility = "不可能"
                statistical_power = "なし"
            
            results[level_name] = {
                'signal_survival_rate': signal_survival_rate,
                'estimated_annual_trades': estimated_annual_trades,
                'validation_feasibility': validation_feasibility,
                'statistical_power': statistical_power,
                'config': config
            }
            
            print(f"   シグナル生存率: {signal_survival_rate:.1%}")
            print(f"   年間推定取引数: {estimated_annual_trades:.0f}回")
            print(f"   検証実行可能性: {validation_feasibility}")
            print(f"   統計的検出力: {statistical_power}")
            
        except Exception as e:
            print(f"   ❌ エラー: {str(e)}")
            results[level_name] = {
                'error': str(e),
                'validation_feasibility': '不可能'
            }
    
    # 推奨レベル分析
    print(f"\n📊 総合分析")
    print("-" * 40)
    
    recommended_level = analyze_recommendations(results)
    
    print(f"💡 推奨リスク管理レベル: {recommended_level['level']}")
    print(f"   理由: {recommended_level['reason']}")
    print(f"   期待取引数: {recommended_level['trades']:.0f}回/年")
    print(f"   検証実行可能性: {recommended_level['feasibility']}")
    
    # 最適化提案
    print(f"\n🔧 最適化提案")
    print("-" * 40)
    
    optimization_suggestions = generate_optimization_suggestions(results)
    
    for i, suggestion in enumerate(optimization_suggestions, 1):
        print(f"   {i}. {suggestion}")
    
    # 結果保存
    analysis_results = {
        'analysis_type': 'risk_vs_validation_quality',
        'timestamp': datetime.now().isoformat(),
        'test_period': f"{test_period_start.strftime('%Y-%m-%d')} to {test_period_end.strftime('%Y-%m-%d')}",
        'risk_level_results': results,
        'recommendation': recommended_level,
        'optimization_suggestions': optimization_suggestions
    }
    
    filename = f"risk_vs_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📝 分析結果保存: {filename}")
    print("✅ リスク管理vs検証品質分析完了")
    
    return analysis_results

def analyze_recommendations(results):
    """推奨レベル分析"""
    
    # 検証実行可能性を重視した推奨
    feasible_levels = {
        level: data for level, data in results.items() 
        if data.get('validation_feasibility') == '可能' and 'error' not in data
    }
    
    if not feasible_levels:
        return {
            'level': 'なし',
            'reason': '全レベルで検証困難のため、リスク管理なしを推奨',
            'trades': results.get('なし', {}).get('estimated_annual_trades', 0),
            'feasibility': results.get('なし', {}).get('validation_feasibility', '不明')
        }
    
    # 最適バランス選択（取引数と実行可能性）
    best_level = None
    best_score = 0
    
    for level, data in feasible_levels.items():
        # スコア計算（取引数 + 統計力）
        trades = data['estimated_annual_trades']
        power_score = {'高': 3, '中': 2, '低': 1, 'なし': 0}.get(data['statistical_power'], 0)
        
        # 最低30取引は必須
        if trades >= 30:
            score = min(trades / 100, 2) + power_score  # 正規化
            if score > best_score:
                best_score = score
                best_level = level
    
    if best_level:
        return {
            'level': best_level,
            'reason': f'検証品質とリスク管理のバランスが最適',
            'trades': feasible_levels[best_level]['estimated_annual_trades'],
            'feasibility': feasible_levels[best_level]['validation_feasibility']
        }
    else:
        # フォールバック
        return {
            'level': 'なし',
            'reason': '検証品質確保のため、リスク管理なしを推奨',
            'trades': results.get('なし', {}).get('estimated_annual_trades', 0),
            'feasibility': results.get('なし', {}).get('validation_feasibility', '不明')
        }

def generate_optimization_suggestions(results):
    """最適化提案生成"""
    
    suggestions = []
    
    # 取引数が少ない場合の提案
    max_trades = max(
        data.get('estimated_annual_trades', 0) 
        for data in results.values() 
        if 'error' not in data
    )
    
    if max_trades < 50:
        suggestions.append("フィルター条件を緩和して取引機会を増加")
        suggestions.append("複数通貨ペアでの分散実装を検討")
    
    # リスク管理レベル別提案
    strong_risk_data = results.get('強度', {})
    if strong_risk_data.get('estimated_annual_trades', 0) == 0:
        suggestions.append("ボラティリティフィルターの閾値を調整")
        suggestions.append("市場環境フィルターの条件緩和")
    
    # 統計的検出力向上提案
    low_power_levels = [
        level for level, data in results.items()
        if data.get('statistical_power') in ['低', 'なし'] and 'error' not in data
    ]
    
    if low_power_levels:
        suggestions.append("検証期間延長による統計的検出力向上")
        suggestions.append("段階的リスク管理導入（Phase 1→2→3）")
    
    # デフォルト提案
    if not suggestions:
        suggestions.append("現在のバランスは適切、段階的強化を推奨")
        suggestions.append("定期的な検証サンプル数モニタリング")
    
    return suggestions

if __name__ == "__main__":
    analyze_risk_vs_validation_quality()