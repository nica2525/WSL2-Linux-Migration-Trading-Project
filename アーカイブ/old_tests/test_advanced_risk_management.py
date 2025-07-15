#!/usr/bin/env python3
"""
高度なリスク管理システムのテスト
"""

import json
from datetime import datetime, timedelta
from risk_management_system import AdaptiveRiskManager, RiskParameters

def test_advanced_risk_management():
    """高度なリスク管理システムテスト"""
    
    print("🛡️ 高度なリスク管理システムテスト開始")
    print("=" * 60)
    
    # 基本パラメータ
    base_params = {
        'stop_atr': 1.3,
        'profit_atr': 2.5,
        'atr_period': 14
    }
    
    # リスク管理システム初期化
    risk_manager = AdaptiveRiskManager(base_params)
    
    # テストデータ生成
    print("📊 テストデータ生成中...")
    
    # 価格データ
    price_data = generate_test_price_data()
    
    # 取引履歴（一部負け取引を含む）
    trade_history = generate_test_trade_history()
    
    # 現在のポジション
    current_positions = generate_test_positions()
    
    print(f"✅ データ生成完了")
    print(f"   価格データ: {len(price_data)}本")
    print(f"   取引履歴: {len(trade_history)}取引")
    print(f"   現在ポジション: {len(current_positions)}ポジション")
    
    # テスト1: 適応型リスク管理パラメータ
    print("\n🔄 テスト1: 適応型リスク管理パラメータ")
    print("-" * 40)
    
    current_time = datetime.now()
    risk_params = risk_manager.calculate_adaptive_risk_parameters(
        price_data, current_time, 0.05  # 5%ドローダウン
    )
    
    print(f"適応型リスク管理パラメータ:")
    print(f"   ポジションサイズ: {risk_params.position_size:.3f}ロット")
    print(f"   ストップロス: {risk_params.stop_loss_pips:.1f}pips")
    print(f"   テイクプロフィット: {risk_params.take_profit_pips:.1f}pips")
    print(f"   最大DD限界: {risk_params.max_drawdown_limit:.1%}")
    print(f"   日次損失限界: ${risk_params.daily_loss_limit:.2f}")
    print(f"   連続損失限界: {risk_params.max_consecutive_losses}回")
    print(f"   相関限界: {risk_params.correlation_limit:.1%}")
    print(f"   エクスポージャー限界: {risk_params.exposure_limit:.1%}")
    print(f"   ケリー基準適用率: {risk_params.kelly_fraction:.1%}")
    
    # テスト2: 高度なリスク指標
    print("\n🔄 テスト2: 高度なリスク指標")
    print("-" * 40)
    
    advanced_metrics = risk_manager.calculate_advanced_risk_metrics(
        trade_history, current_positions
    )
    
    metrics = advanced_metrics['advanced_metrics']
    alerts = advanced_metrics['risk_alerts']
    recommendations = advanced_metrics['recommended_actions']
    
    print(f"高度なリスク指標:")
    print(f"   連続損失回数: {metrics['consecutive_losses']}回")
    print(f"   ヒートインデックス: {metrics['heat_index']:.3f}")
    print(f"   相関リスク: {metrics['correlation_risk']:.3f}")
    print(f"   総エクスポージャー: {metrics['total_exposure']:.3f}")
    print(f"   ケリー推奨サイズ: {metrics['kelly_recommended_size']:.3f}")
    
    print(f"\nリスクアラート:")
    for alert_type, is_active in alerts.items():
        status = "🚨 アクティブ" if is_active else "✅ 正常"
        print(f"   {alert_type}: {status}")
    
    print(f"\n推奨事項:")
    for i, recommendation in enumerate(recommendations, 1):
        print(f"   {i}. {recommendation}")
    
    # テスト3: 市場分析
    print("\n🔄 テスト3: 市場分析")
    print("-" * 40)
    
    market_analysis = risk_manager.get_market_analysis(price_data, current_time)
    
    market_env = market_analysis['market_environment']
    risk_params_analysis = market_analysis['risk_parameters']
    trading_conditions = market_analysis['trading_conditions']
    
    print(f"市場環境:")
    print(f"   ボラティリティレベル: {market_env['volatility_level']}")
    print(f"   現在ATR: {market_env['current_atr']:.6f}")
    print(f"   トレンド強度: {market_env['trend_strength']:.3f}")
    print(f"   セッション: {market_env['session_type']}")
    print(f"   高インパクトニュース: {market_env['is_high_impact_news']}")
    
    print(f"\n取引条件:")
    print(f"   推奨アクション: {trading_conditions['recommended_action']}")
    print(f"   信頼度: {trading_conditions['confidence_level']}")
    print(f"   リスク評価: {trading_conditions['risk_assessment']}")
    
    # テスト4: 取引判定
    print("\n🔄 テスト4: 取引判定")
    print("-" * 40)
    
    can_trade, reason = risk_manager.should_enter_trade(
        price_data, current_time, 0.05, 1000, 2  # 5%DD、1000$日次損失、2ポジション
    )
    
    print(f"取引判定:")
    print(f"   取引可能: {'✅ YES' if can_trade else '❌ NO'}")
    print(f"   判定理由: {reason}")
    
    # 結果保存
    print("\n📝 テスト結果保存")
    print("-" * 40)
    
    test_results = {
        'test_type': 'advanced_risk_management',
        'timestamp': datetime.now().isoformat(),
        'risk_parameters': {
            'position_size': risk_params.position_size,
            'stop_loss_pips': risk_params.stop_loss_pips,
            'take_profit_pips': risk_params.take_profit_pips,
            'max_drawdown_limit': risk_params.max_drawdown_limit,
            'daily_loss_limit': risk_params.daily_loss_limit,
            'max_consecutive_losses': risk_params.max_consecutive_losses,
            'correlation_limit': risk_params.correlation_limit,
            'exposure_limit': risk_params.exposure_limit,
            'kelly_fraction': risk_params.kelly_fraction
        },
        'advanced_metrics': advanced_metrics,
        'market_analysis': market_analysis,
        'trading_decision': {
            'can_trade': can_trade,
            'reason': reason
        }
    }
    
    filename = f"advanced_risk_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"結果保存: {filename}")
    print("\n✅ 高度なリスク管理システムテスト完了")
    
    return True

def generate_test_price_data():
    """テスト用価格データ生成"""
    import random
    
    data = []
    base_price = 1.1000
    base_date = datetime.now() - timedelta(hours=300)
    
    for i in range(300):
        # 価格変動
        change = random.uniform(-0.0020, 0.0020)
        base_price += change
        
        # 時間増分
        current_time = base_date + timedelta(hours=i)
        
        # バーデータ
        high_low_range = random.uniform(0.0010, 0.0040)
        
        bar = {
            'datetime': current_time,
            'open': base_price,
            'high': base_price + high_low_range * 0.6,
            'low': base_price - high_low_range * 0.4,
            'close': base_price,
            'volume': random.randint(800, 1200)
        }
        
        data.append(bar)
    
    return data

def generate_test_trade_history():
    """テスト用取引履歴生成"""
    import random
    
    history = []
    base_date = datetime.now() - timedelta(days=30)
    
    # 50取引のシミュレーション
    for i in range(50):
        # 意図的に連続損失を作成
        if 45 <= i <= 47:  # 最後の3取引を損失に
            pnl = random.uniform(-200, -50)
        else:
            # 60%の勝率
            pnl = random.uniform(50, 150) if random.random() < 0.6 else random.uniform(-150, -30)
        
        trade = {
            'timestamp': (base_date + timedelta(hours=i*12)).isoformat(),
            'direction': random.choice(['BUY', 'SELL']),
            'entry_price': 1.1000 + random.uniform(-0.01, 0.01),
            'exit_price': 1.1000 + random.uniform(-0.01, 0.01),
            'position_size': random.uniform(0.01, 0.10),
            'pnl': pnl,
            'holding_time': random.randint(1, 48)
        }
        
        history.append(trade)
    
    return history

def generate_test_positions():
    """テスト用現在ポジション生成"""
    import random
    
    positions = []
    
    # 3つのポジション（うち2つは同方向）
    for i in range(3):
        direction = 'BUY' if i < 2 else 'SELL'  # 意図的に相関を作成
        
        position = {
            'direction': direction,
            'entry_price': 1.1000 + random.uniform(-0.005, 0.005),
            'position_size': random.uniform(0.01, 0.05),
            'unrealized_pnl': random.uniform(-100, 100),
            'entry_time': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
        }
        
        positions.append(position)
    
    return positions

if __name__ == "__main__":
    test_advanced_risk_management()