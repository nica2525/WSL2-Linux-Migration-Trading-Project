#!/usr/bin/env python3
"""
リスク管理システム
市場環境適応型のリスク管理機能を実装
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class MarketEnvironment:
    """市場環境データ"""
    volatility: float
    trend_strength: float
    volume_profile: str
    session_type: str
    is_high_impact_news: bool

@dataclass
class RiskParameters:
    """リスク管理パラメータ"""
    position_size: float
    stop_loss_pips: float
    take_profit_pips: float
    max_drawdown_limit: float
    daily_loss_limit: float
    volatility_multiplier: float
    
    # 新強化項目
    max_consecutive_losses: int = 3      # 最大連続損失回数
    correlation_limit: float = 0.7       # 相関限界
    exposure_limit: float = 0.02         # 最大エクスポージャー
    heat_index_limit: float = 0.5        # ヒートインデックス限界
    kelly_fraction: float = 0.25         # ケリー基準適用率

class VolatilityAnalyzer:
    """ボラティリティ分析器"""
    
    def __init__(self, atr_period: int = 14):
        self.atr_period = atr_period
        self.volatility_thresholds = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'extreme': 2.0
        }
    
    def calculate_atr(self, price_data: List[Dict]) -> float:
        """ATR計算"""
        if len(price_data) < self.atr_period:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(price_data)):
            high = price_data[i]['high']
            low = price_data[i]['low']
            prev_close = price_data[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # 最新のATR期間でのATR計算
        recent_trs = true_ranges[-self.atr_period:]
        return sum(recent_trs) / len(recent_trs)
    
    def classify_volatility(self, current_atr: float, historical_atr: float) -> str:
        """ボラティリティ分類"""
        if historical_atr == 0:
            return 'medium'
        
        volatility_ratio = current_atr / historical_atr
        
        if volatility_ratio >= self.volatility_thresholds['extreme']:
            return 'extreme'
        elif volatility_ratio >= self.volatility_thresholds['high']:
            return 'high'
        elif volatility_ratio >= self.volatility_thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def get_volatility_multiplier(self, volatility_level: str) -> float:
        """ボラティリティ倍率"""
        multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'extreme': 2.0
        }
        return multipliers.get(volatility_level, 1.0)

class MarketEnvironmentDetector:
    """市場環境検知器"""
    
    def __init__(self):
        self.session_times = {
            'tokyo': {'start': 9, 'end': 15},
            'london': {'start': 16, 'end': 24},
            'ny': {'start': 22, 'end': 6}  # 次の日の6時
        }
    
    def detect_market_environment(self, 
                                price_data: List[Dict],
                                current_time: datetime) -> MarketEnvironment:
        """市場環境検知"""
        
        # ボラティリティ分析
        analyzer = VolatilityAnalyzer()
        current_atr = analyzer.calculate_atr(price_data[-50:])
        historical_atr = analyzer.calculate_atr(price_data[-200:])
        volatility_level = analyzer.classify_volatility(current_atr, historical_atr)
        
        # トレンド強度
        trend_strength = self._calculate_trend_strength(price_data[-20:])
        
        # 出来高プロファイル
        volume_profile = self._analyze_volume_profile(price_data[-10:])
        
        # セッション判定
        session_type = self._detect_session(current_time)
        
        # 重要指標発表チェック（簡易版）
        is_high_impact_news = self._check_high_impact_news(current_time)
        
        return MarketEnvironment(
            volatility=current_atr,
            trend_strength=trend_strength,
            volume_profile=volume_profile,
            session_type=session_type,
            is_high_impact_news=is_high_impact_news
        )
    
    def _calculate_trend_strength(self, price_data: List[Dict]) -> float:
        """トレンド強度計算"""
        if len(price_data) < 10:
            return 0.0
        
        # 単純移動平均の傾き
        closes = [bar['close'] for bar in price_data]
        sma_short = sum(closes[-5:]) / 5
        sma_long = sum(closes[-10:]) / 10
        
        # 傾きの正規化
        trend_strength = abs(sma_short - sma_long) / sma_long if sma_long > 0 else 0
        
        return min(trend_strength * 100, 1.0)  # 0-1の範囲に正規化
    
    def _analyze_volume_profile(self, price_data: List[Dict]) -> str:
        """出来高プロファイル分析"""
        if len(price_data) < 5:
            return 'normal'
        
        # 簡易版：最新5バーの出来高平均
        volumes = [bar.get('volume', 0) for bar in price_data]
        avg_volume = sum(volumes) / len(volumes)
        
        # 仮想的な閾値
        if avg_volume > 1000:
            return 'high'
        elif avg_volume > 500:
            return 'normal'
        else:
            return 'low'
    
    def _detect_session(self, current_time: datetime) -> str:
        """セッション検知"""
        hour = current_time.hour
        
        if 9 <= hour <= 15:
            return 'tokyo'
        elif 16 <= hour <= 21:
            return 'london'
        elif 22 <= hour <= 23 or 0 <= hour <= 5:
            return 'ny'
        else:
            return 'overlap'
    
    def _check_high_impact_news(self, current_time: datetime) -> bool:
        """重要指標発表チェック（簡易版）"""
        # 金曜日の21:30（米雇用統計想定）
        if current_time.weekday() == 4 and current_time.hour == 21 and current_time.minute == 30:
            return True
        
        # 毎月第一金曜日の21:30
        if (current_time.weekday() == 4 and 
            1 <= current_time.day <= 7 and 
            current_time.hour == 21 and 
            current_time.minute == 30):
            return True
        
        return False

class AdaptiveRiskManager:
    """適応型リスク管理システム"""
    
    def __init__(self, base_params: Dict):
        self.base_params = base_params
        self.environment_detector = MarketEnvironmentDetector()
        self.volatility_analyzer = VolatilityAnalyzer()
        
        # 基本設定
        self.account_balance = 100000  # 仮想残高
        self.max_risk_per_trade = 0.02  # 2%リスク
        self.max_daily_risk = 0.06  # 6%日次リスク
        self.max_drawdown_limit = 0.20  # 20%最大ドローダウン
        
        # 市場環境別調整係数
        self.environment_adjustments = {
            'volatility': {
                'low': {'size': 1.2, 'stop': 0.8, 'profit': 0.9},
                'medium': {'size': 1.0, 'stop': 1.0, 'profit': 1.0},
                'high': {'size': 0.8, 'stop': 1.2, 'profit': 1.1},
                'extreme': {'size': 0.5, 'stop': 1.5, 'profit': 1.3}
            },
            'session': {
                'tokyo': {'size': 1.0, 'stop': 1.0, 'profit': 1.0},
                'london': {'size': 1.2, 'stop': 1.0, 'profit': 1.1},
                'ny': {'size': 1.1, 'stop': 1.0, 'profit': 1.0},
                'overlap': {'size': 0.9, 'stop': 1.1, 'profit': 1.0}
            },
            'news': {
                'high_impact': {'size': 0.5, 'stop': 1.5, 'profit': 1.2},
                'normal': {'size': 1.0, 'stop': 1.0, 'profit': 1.0}
            }
        }
    
    def calculate_adaptive_risk_parameters(self, 
                                         price_data: List[Dict],
                                         current_time: datetime,
                                         current_drawdown: float = 0.0) -> RiskParameters:
        """適応型リスク管理パラメータ計算"""
        
        # 市場環境検知
        market_env = self.environment_detector.detect_market_environment(price_data, current_time)
        
        # ボラティリティ分類
        current_atr = self.volatility_analyzer.calculate_atr(price_data[-50:])
        historical_atr = self.volatility_analyzer.calculate_atr(price_data[-200:])
        volatility_level = self.volatility_analyzer.classify_volatility(current_atr, historical_atr)
        
        # 基本パラメータ
        base_position_size = self._calculate_base_position_size(current_atr)
        base_stop_loss = self.base_params['stop_atr'] * current_atr
        base_take_profit = self.base_params['profit_atr'] * current_atr
        
        # 環境別調整
        vol_adj = self.environment_adjustments['volatility'][volatility_level]
        session_adj = self.environment_adjustments['session'][market_env.session_type]
        news_adj = self.environment_adjustments['news']['high_impact' if market_env.is_high_impact_news else 'normal']
        
        # 調整後パラメータ
        adjusted_position_size = base_position_size * vol_adj['size'] * session_adj['size'] * news_adj['size']
        adjusted_stop_loss = base_stop_loss * vol_adj['stop'] * session_adj['stop'] * news_adj['stop']
        adjusted_take_profit = base_take_profit * vol_adj['profit'] * session_adj['profit'] * news_adj['profit']
        
        # ドローダウン調整
        if current_drawdown > 0.10:  # 10%以上のドローダウン
            drawdown_multiplier = 1.0 - (current_drawdown - 0.10) * 2
            adjusted_position_size *= max(drawdown_multiplier, 0.3)
        
        # 最終パラメータ
        return RiskParameters(
            position_size=max(adjusted_position_size, 0.01),  # 最小0.01ロット
            stop_loss_pips=adjusted_stop_loss * 10000,  # pips変換
            take_profit_pips=adjusted_take_profit * 10000,
            max_drawdown_limit=self.max_drawdown_limit,
            daily_loss_limit=self.max_daily_risk * self.account_balance,
            volatility_multiplier=self.volatility_analyzer.get_volatility_multiplier(volatility_level),
            # 新強化項目
            max_consecutive_losses=3,
            correlation_limit=0.7,
            exposure_limit=0.02,
            heat_index_limit=0.5,
            kelly_fraction=0.25
        )
    
    def _calculate_base_position_size(self, current_atr: float) -> float:
        """基本ポジションサイズ計算"""
        if current_atr == 0:
            return 0.01
        
        # 2%リスクベースでのポジションサイズ
        risk_amount = self.account_balance * self.max_risk_per_trade
        stop_loss_amount = self.base_params['stop_atr'] * current_atr
        
        # 1pip = 10USDと仮定（USD/JPY 100円レート）
        pip_value = 10
        stop_loss_pips = stop_loss_amount * 10000
        
        if stop_loss_pips > 0:
            position_size = risk_amount / (stop_loss_pips * pip_value)
            return min(position_size, 1.0)  # 最大1.0ロット
        
        return 0.01
    
    def should_enter_trade(self, 
                          price_data: List[Dict],
                          current_time: datetime,
                          current_drawdown: float,
                          daily_loss: float,
                          open_positions: int) -> Tuple[bool, str]:
        """トレード実行判定"""
        
        # 最大ドローダウンチェック
        if current_drawdown >= self.max_drawdown_limit:
            return False, "最大ドローダウン到達"
        
        # 日次損失限度チェック
        if daily_loss >= self.max_daily_risk * self.account_balance:
            return False, "日次損失限度到達"
        
        # 最大ポジション数チェック
        if open_positions >= 3:
            return False, "最大ポジション数到達"
        
        # 市場環境チェック
        market_env = self.environment_detector.detect_market_environment(price_data, current_time)
        
        # 極端なボラティリティ時の制限
        current_atr = self.volatility_analyzer.calculate_atr(price_data[-50:])
        historical_atr = self.volatility_analyzer.calculate_atr(price_data[-200:])
        volatility_level = self.volatility_analyzer.classify_volatility(current_atr, historical_atr)
        
        if volatility_level == 'extreme':
            return False, "極端なボラティリティ"
        
        # 重要指標発表時の制限
        if market_env.is_high_impact_news:
            return False, "重要指標発表時"
        
        return True, "取引可能"
    
    def get_market_analysis(self, 
                           price_data: List[Dict],
                           current_time: datetime) -> Dict:
        """市場分析レポート"""
        
        market_env = self.environment_detector.detect_market_environment(price_data, current_time)
        
        current_atr = self.volatility_analyzer.calculate_atr(price_data[-50:])
        historical_atr = self.volatility_analyzer.calculate_atr(price_data[-200:])
        volatility_level = self.volatility_analyzer.classify_volatility(current_atr, historical_atr)
        
        risk_params = self.calculate_adaptive_risk_parameters(price_data, current_time)
        
        return {
            'timestamp': current_time.isoformat(),
            'market_environment': {
                'volatility_level': volatility_level,
                'current_atr': current_atr,
                'historical_atr': historical_atr,
                'trend_strength': market_env.trend_strength,
                'session_type': market_env.session_type,
                'is_high_impact_news': market_env.is_high_impact_news
            },
            'risk_parameters': {
                'position_size': risk_params.position_size,
                'stop_loss_pips': risk_params.stop_loss_pips,
                'take_profit_pips': risk_params.take_profit_pips,
                'volatility_multiplier': risk_params.volatility_multiplier
            },
            'trading_conditions': {
                'recommended_action': 'ENTER' if volatility_level in ['low', 'medium'] else 'WAIT',
                'confidence_level': 'HIGH' if volatility_level == 'medium' else 'LOW',
                'risk_assessment': 'ACCEPTABLE' if volatility_level != 'extreme' else 'HIGH'
            }
        }
    
    def calculate_advanced_risk_metrics(self, 
                                      trade_history: List[Dict],
                                      current_positions: List[Dict] = None) -> Dict:
        """高度なリスク指標計算"""
        
        if current_positions is None:
            current_positions = []
        
        # 連続損失回数
        consecutive_losses = self._calculate_consecutive_losses(trade_history)
        
        # ヒートインデックス（パフォーマンス低下指標）
        heat_index = self._calculate_heat_index(trade_history)
        
        # 相関分析（複数ポジション間）
        correlation_risk = self._calculate_correlation_risk(current_positions)
        
        # エクスポージャー計算
        total_exposure = self._calculate_total_exposure(current_positions)
        
        # ケリー基準ベース推奨ポジションサイズ
        kelly_size = self._calculate_kelly_position_size(trade_history)
        
        return {
            'advanced_metrics': {
                'consecutive_losses': consecutive_losses,
                'heat_index': heat_index,
                'correlation_risk': correlation_risk,
                'total_exposure': total_exposure,
                'kelly_recommended_size': kelly_size
            },
            'risk_alerts': {
                'consecutive_loss_alert': consecutive_losses >= 3,
                'heat_index_alert': heat_index > 0.5,
                'correlation_alert': correlation_risk > 0.7,
                'exposure_alert': total_exposure > 0.02
            },
            'recommended_actions': self._generate_risk_recommendations(
                consecutive_losses, heat_index, correlation_risk, total_exposure
            )
        }
    
    def _calculate_consecutive_losses(self, trade_history: List[Dict]) -> int:
        """連続損失回数計算"""
        if not trade_history:
            return 0
        
        consecutive_losses = 0
        for trade in reversed(trade_history):
            if trade.get('pnl', 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        return consecutive_losses
    
    def _calculate_heat_index(self, trade_history: List[Dict]) -> float:
        """ヒートインデックス計算（パフォーマンス低下指標）"""
        if len(trade_history) < 10:
            return 0.0
        
        # 直近20取引と過去20取引の比較
        recent_trades = trade_history[-20:]
        historical_trades = trade_history[-40:-20] if len(trade_history) >= 40 else trade_history[:-20]
        
        recent_avg = sum(t.get('pnl', 0) for t in recent_trades) / len(recent_trades)
        historical_avg = sum(t.get('pnl', 0) for t in historical_trades) / len(historical_trades) if historical_trades else 0
        
        if historical_avg == 0:
            return 0.0
        
        # パフォーマンス低下率
        performance_decline = (historical_avg - recent_avg) / abs(historical_avg)
        return max(0.0, min(1.0, performance_decline))
    
    def _calculate_correlation_risk(self, current_positions: List[Dict]) -> float:
        """相関リスク計算"""
        if len(current_positions) < 2:
            return 0.0
        
        # 簡易相関（同方向ポジション比率）
        long_positions = sum(1 for p in current_positions if p.get('direction') == 'BUY')
        short_positions = sum(1 for p in current_positions if p.get('direction') == 'SELL')
        total_positions = len(current_positions)
        
        if total_positions == 0:
            return 0.0
        
        # 一方向集中度
        max_direction_ratio = max(long_positions, short_positions) / total_positions
        return max_direction_ratio
    
    def _calculate_total_exposure(self, current_positions: List[Dict]) -> float:
        """総エクスポージャー計算"""
        if not current_positions:
            return 0.0
        
        total_exposure = sum(p.get('position_size', 0) for p in current_positions)
        return total_exposure / self.account_balance
    
    def _calculate_kelly_position_size(self, trade_history: List[Dict]) -> float:
        """ケリー基準ベースポジションサイズ"""
        if len(trade_history) < 30:
            return 0.01
        
        # 勝率計算
        winning_trades = [t for t in trade_history if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trade_history if t.get('pnl', 0) < 0]
        
        if not winning_trades or not losing_trades:
            return 0.01
        
        win_rate = len(winning_trades) / len(trade_history)
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
        avg_loss = abs(sum(t['pnl'] for t in losing_trades) / len(losing_trades))
        
        if avg_loss == 0:
            return 0.01
        
        # ケリー基準
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # 安全係数適用（25%）
        safe_kelly = kelly_fraction * 0.25
        
        return max(0.01, min(safe_kelly, 0.10))  # 最大10%
    
    def _generate_risk_recommendations(self, 
                                     consecutive_losses: int,
                                     heat_index: float,
                                     correlation_risk: float,
                                     total_exposure: float) -> List[str]:
        """リスク推奨事項生成"""
        recommendations = []
        
        if consecutive_losses >= 3:
            recommendations.append("連続損失により取引サイズを50%削減")
        
        if heat_index > 0.5:
            recommendations.append("パフォーマンス低下により戦略見直し推奨")
        
        if correlation_risk > 0.7:
            recommendations.append("ポジション相関が高いため分散化必要")
        
        if total_exposure > 0.02:
            recommendations.append("総エクスポージャーが上限超過、ポジション削減")
        
        if not recommendations:
            recommendations.append("リスクレベル正常、取引継続可能")
        
        return recommendations

def main():
    """メイン実行"""
    print("🛡️ リスク管理システムテスト開始")
    
    # サンプルデータ作成
    sample_data = []
    base_price = 110.0
    
    for i in range(300):
        price = base_price + (i % 20 - 10) * 0.01
        sample_data.append({
            'datetime': datetime.now() - timedelta(hours=300-i),
            'open': price,
            'high': price + 0.02,
            'low': price - 0.02,
            'close': price + 0.01,
            'volume': 1000 + (i % 100) * 10
        })
    
    # リスク管理システム初期化
    base_params = {
        'stop_atr': 1.3,
        'profit_atr': 2.5,
        'atr_period': 14
    }
    
    risk_manager = AdaptiveRiskManager(base_params)
    
    # 市場分析実行
    current_time = datetime.now()
    analysis = risk_manager.get_market_analysis(sample_data, current_time)
    
    print(f"   市場環境: {analysis['market_environment']['volatility_level']}")
    print(f"   推奨ポジションサイズ: {analysis['risk_parameters']['position_size']:.3f}")
    print(f"   ストップロス: {analysis['risk_parameters']['stop_loss_pips']:.1f}pips")
    print(f"   推奨アクション: {analysis['trading_conditions']['recommended_action']}")
    
    # 結果保存
    with open('risk_management_system_test.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print("✅ リスク管理システムテスト完了")

if __name__ == "__main__":
    main()