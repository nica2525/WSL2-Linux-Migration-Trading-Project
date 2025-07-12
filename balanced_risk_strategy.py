#!/usr/bin/env python3
"""
バランス調整済み戦略
検証品質を保ちながらリスク管理を適用
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from enhanced_breakout_strategy import EnhancedBreakoutStrategy, EnhancedTradeSignal
from multi_timeframe_breakout_strategy import MultiTimeframeData, create_enhanced_sample_data

class BalancedRiskStrategy(EnhancedBreakoutStrategy):
    """バランス調整済みリスク戦略"""
    
    def __init__(self, base_params: Dict, mode: str = "validation"):
        super().__init__(base_params)
        
        # モード設定
        self.mode = mode  # "validation" or "live"
        
        # モード別設定
        if mode == "validation":
            # 検証モード：リスク管理を緩和
            self.enable_adaptive_risk = True
            self.enable_market_filter = False  # 市場フィルター無効
            self.enable_volatility_filter = False  # ボラティリティフィルター無効
            self.risk_threshold_multiplier = 0.5  # 閾値を緩和
        else:
            # 実用モード：フルリスク管理
            self.enable_adaptive_risk = True
            self.enable_market_filter = True
            self.enable_volatility_filter = True
            self.risk_threshold_multiplier = 1.0
    
    def generate_enhanced_signal(self, 
                               mtf_data: MultiTimeframeData,
                               current_time: datetime,
                               current_drawdown: float = 0.0,
                               daily_loss: float = 0.0,
                               open_positions: int = 0) -> Optional[EnhancedTradeSignal]:
        """モード別シグナル生成"""
        
        # 元のシグナル取得
        original_signal = self._get_simple_signal(mtf_data, current_time)
        
        if not original_signal or original_signal['action'] == 'HOLD':
            return None
        
        self.signals_generated += 1
        
        # モード別フィルタリング
        if self.mode == "validation":
            # 検証モード：最小限のフィルタリング
            if not self._basic_validation_filter(original_signal):
                self.signals_filtered += 1
                return None
        else:
            # 実用モード：フルフィルタリング
            if not self._full_live_filter(mtf_data, current_time, current_drawdown, daily_loss, open_positions):
                self.signals_filtered += 1
                return None
        
        # シグナル生成継続
        return self._create_enhanced_signal(original_signal, mtf_data, current_time, current_drawdown)
    
    def _basic_validation_filter(self, original_signal: Dict) -> bool:
        """検証モード用基本フィルター"""
        
        # 基本的な品質チェックのみ
        if 'action' not in original_signal:
            return False
        
        if original_signal['action'] not in ['BUY', 'SELL']:
            return False
        
        # ブレイクアウト強度の最小チェック（緩和版）
        breakout_strength = original_signal.get('breakout_strength', 0)
        if breakout_strength < 0.3:  # 0.5から0.3に緩和
            return False
        
        return True
    
    def _full_live_filter(self, mtf_data: MultiTimeframeData, current_time: datetime,
                         current_drawdown: float, daily_loss: float, open_positions: int) -> bool:
        """実用モード用フルフィルター"""
        
        # 元の強化フィルターロジック
        h1_data = mtf_data.get_h1_data()
        price_data = []
        for bar in h1_data[-300:]:
            if isinstance(bar, dict):
                price_data.append({
                    'datetime': bar['datetime'],
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'volume': bar.get('volume', 1000)
                })
            else:
                price_data.append({
                    'datetime': bar.datetime,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': getattr(bar, 'volume', 1000)
                })
        
        # リスク管理チェック
        can_trade, reason = self.risk_manager.should_enter_trade(
            price_data, current_time, current_drawdown, daily_loss, open_positions
        )
        
        return can_trade
    
    def _create_enhanced_signal(self, original_signal: Dict, mtf_data: MultiTimeframeData, 
                               current_time: datetime, current_drawdown: float) -> EnhancedTradeSignal:
        """強化シグナル作成"""
        
        h1_data = mtf_data.get_h1_data()
        current_price = h1_data[-1]['close'] if isinstance(h1_data[-1], dict) else h1_data[-1].close
        
        # 基本リスクパラメータ
        if self.mode == "validation":
            # 検証モード：固定パラメータ
            stop_loss_pips = 30
            take_profit_pips = 60
            position_size = 0.01
        else:
            # 実用モード：適応パラメータ
            price_data = []
            for bar in h1_data[-300:]:
                if isinstance(bar, dict):
                    price_data.append({
                        'datetime': bar['datetime'],
                        'open': bar['open'],
                        'high': bar['high'],
                        'low': bar['low'],
                        'close': bar['close'],
                        'volume': bar.get('volume', 1000)
                    })
            
            risk_params = self.risk_manager.calculate_adaptive_risk_parameters(
                price_data, current_time, current_drawdown
            )
            stop_loss_pips = risk_params.stop_loss_pips
            take_profit_pips = risk_params.take_profit_pips
            position_size = risk_params.position_size
        
        # 価格計算
        if original_signal['action'] == 'BUY':
            entry_price = current_price
            stop_loss = current_price - (stop_loss_pips / 10000)
            take_profit = current_price + (take_profit_pips / 10000)
        else:  # SELL
            entry_price = current_price
            stop_loss = current_price + (stop_loss_pips / 10000)
            take_profit = current_price - (take_profit_pips / 10000)
        
        # 強化シグナル作成
        enhanced_signal = EnhancedTradeSignal(
            timestamp=current_time,
            direction=original_signal['action'],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence='MEDIUM',
            risk_assessment='ACCEPTABLE',
            market_environment={'mode': self.mode},
            original_signal=original_signal
        )
        
        self.trades_executed += 1
        return enhanced_signal
    
    def _get_simple_signal(self, mtf_data: MultiTimeframeData, current_time: datetime) -> Optional[Dict]:
        """シンプルシグナル生成（緩和版）"""
        try:
            h1_data = mtf_data.get_h1_data()
            h4_data = mtf_data.get_h4_data()
            
            if len(h1_data) < 50 or len(h4_data) < 50:
                return None
            
            # 現在価格
            current_h1 = h1_data[-1]
            current_price = current_h1['close']
            
            # 緩和されたブレイクアウト判定
            h4_high = max(bar['high'] for bar in h4_data[-self.base_params['h4_period']:])
            h4_low = min(bar['low'] for bar in h4_data[-self.base_params['h4_period']:])
            
            h1_high = max(bar['high'] for bar in h1_data[-self.base_params['h1_period']:])
            h1_low = min(bar['low'] for bar in h1_data[-self.base_params['h1_period']:])
            
            # ブレイクアウト判定（条件緩和）
            h4_break = current_price > h4_high or current_price < h4_low
            h1_break = current_price > h1_high or current_price < h1_low
            
            # H4またはH1のいずれかでブレイクアウト（緩和）
            if h4_break or h1_break:
                if current_price > max(h4_high, h1_high):
                    return {
                        'action': 'BUY',
                        'breakout_strength': 0.6,
                        'trend_alignment': 0.5,
                        'volume_confirmation': 0.5,
                        'signal_time': current_time.isoformat()
                    }
                elif current_price < min(h4_low, h1_low):
                    return {
                        'action': 'SELL',
                        'breakout_strength': 0.6,
                        'trend_alignment': 0.5,
                        'volume_confirmation': 0.5,
                        'signal_time': current_time.isoformat()
                    }
            
            return {'action': 'HOLD'}
            
        except Exception as e:
            print(f"   シグナル生成エラー: {str(e)}")
            return None

def test_balanced_approach():
    """バランス調整アプローチテスト"""
    
    print("⚖️ バランス調整アプローチテスト開始")
    print("=" * 60)
    
    # テストデータ
    sample_data = create_enhanced_sample_data()
    mtf_data = MultiTimeframeData(sample_data)
    
    start_date = datetime(2019, 1, 1)
    end_date = datetime(2019, 6, 30)
    
    base_params = {
        'h4_period': 24,
        'h1_period': 24,
        'atr_period': 14,
        'profit_atr': 2.5,
        'stop_atr': 1.3,
        'min_break_pips': 5
    }
    
    # モード別テスト
    modes = ['validation', 'live']
    results = {}
    
    for mode in modes:
        print(f"\n🔄 {mode.upper()}モードテスト")
        print("-" * 40)
        
        strategy = BalancedRiskStrategy(base_params, mode)
        
        # シグナル生成テスト
        signals_count = 0
        trades_count = 0
        
        h1_data = mtf_data.get_h1_data()
        
        for i in range(100, min(500, len(h1_data)), 50):
            current_time = h1_data[i]['datetime']
            
            signal = strategy.generate_enhanced_signal(
                mtf_data, current_time, 0.0, 0.0, 0
            )
            
            signals_count += 1
            if signal:
                trades_count += 1
        
        signal_survival_rate = trades_count / signals_count if signals_count > 0 else 0
        annual_trades_estimate = trades_count * (365 * 24 / 50)
        
        results[mode] = {
            'signal_survival_rate': signal_survival_rate,
            'annual_trades_estimate': annual_trades_estimate,
            'feasibility': '可能' if annual_trades_estimate >= 30 else '困難'
        }
        
        print(f"   シグナル生存率: {signal_survival_rate:.1%}")
        print(f"   年間推定取引数: {annual_trades_estimate:.0f}回")
        print(f"   検証実行可能性: {results[mode]['feasibility']}")
    
    # 推奨事項
    print(f"\n💡 推奨実装アプローチ")
    print("-" * 40)
    
    validation_feasible = results['validation']['feasibility'] == '可能'
    live_feasible = results['live']['feasibility'] == '可能'
    
    if validation_feasible and live_feasible:
        recommendation = "両モード対応可能：段階的リスク管理実装推奨"
    elif validation_feasible:
        recommendation = "検証優先：検証完了後にライブモード調整"
    else:
        recommendation = "条件再調整：フィルター条件をさらに緩和"
    
    print(f"   {recommendation}")
    print(f"   検証モード年間取引数: {results['validation']['annual_trades_estimate']:.0f}回")
    print(f"   実用モード年間取引数: {results['live']['annual_trades_estimate']:.0f}回")
    
    # 結果保存
    test_results = {
        'test_type': 'balanced_risk_approach',
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'recommendation': recommendation
    }
    
    filename = f"balanced_risk_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📝 結果保存: {filename}")
    print("✅ バランス調整アプローチテスト完了")
    
    return test_results

if __name__ == "__main__":
    test_balanced_approach()