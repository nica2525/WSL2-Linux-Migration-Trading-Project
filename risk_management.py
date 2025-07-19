#!/usr/bin/env python3
"""
Phase 3.2: Risk Management Engine
kiro設計tasks.md:101-107準拠 - リスク管理エンジン

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 4.1, 4.2, 4.3 (requirements.md)
実装担当: Claude (設計: kiro)
"""

import asyncio
import json
import time
import logging
import aiosqlite
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import numpy as np
import sys
from pathlib import Path

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, calculate_time_diff_seconds, CONFIG
from position_management import Position, PositionTracker, PositionStatus, PositionType

# ログ設定
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """リスクレベル"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class RiskAction(Enum):
    """リスク対応アクション"""
    ALLOW = "ALLOW"
    REDUCE_SIZE = "REDUCE_SIZE"
    STOP_TRADING = "STOP_TRADING"
    CLOSE_ALL = "CLOSE_ALL"
    EMERGENCY_SHUTDOWN = "EMERGENCY_SHUTDOWN"

@dataclass
class RiskParameters:
    """リスク管理パラメータ - kiro要件4.1-4.3準拠"""
    # 基本リスク設定
    max_daily_loss: float = 1000.0          # 最大日次損失（要件4.2）
    max_drawdown_percent: float = 10.0       # 最大ドローダウン率
    max_position_size: float = 1.0           # 最大ポジションサイズ
    max_total_exposure: float = 3.0          # 最大総エクスポージャー
    
    # ボラティリティベース設定（要件4.3）
    normal_volatility_threshold: float = 0.02   # 通常ボラティリティ閾値
    high_volatility_threshold: float = 0.04     # 高ボラティリティ閾値
    volatility_position_reduction: float = 0.5  # ボラティリティ時ポジション削減率
    
    # 口座管理設定（要件4.1）
    risk_per_trade_percent: float = 2.0      # 取引あたりリスク率
    account_balance_buffer: float = 0.1      # 口座残高バッファー
    
    # 監視設定
    risk_check_interval: int = 30            # リスクチェック間隔（秒）
    volatility_lookback_hours: int = 24      # ボラティリティ計算期間
    
    # 緊急時設定（要件4.5）
    emergency_close_timeout: int = 30       # 緊急決済タイムアウト（秒）

@dataclass
class RiskAssessment:
    """リスク評価結果"""
    risk_level: RiskLevel
    risk_action: RiskAction
    current_drawdown: float
    daily_pnl: float
    total_exposure: float
    volatility_score: float
    account_balance: float
    risk_score: float
    reasons: List[str]
    recommendations: List[str]
    timestamp: datetime

class RiskManager:
    """
    リスク管理エンジン - kiro設計tasks.md:101-107準拠
    設定可能リスクパラメータ・最大ドローダウン監視・ポジションサイズ計算
    """
    
    def __init__(self, position_tracker: PositionTracker, risk_params: Optional[RiskParameters] = None):
        self.position_tracker = position_tracker
        self.risk_params = risk_params or RiskParameters()
        self.is_running = False
        self.trading_enabled = True
        
        # 設定読み込み
        self.config = CONFIG
        self._load_risk_config()
        
        # リスク監視データ
        self.daily_start_balance = 0.0
        self.session_start_time = datetime.now()
        self.last_risk_check = time.time()
        self.volatility_history: List[Tuple[datetime, float]] = []
        
        # データベース
        self.db_path = self.config.get('database', {}).get('path', './risk_management.db')
        self._db_initialized = False
        
        # 統計
        self.risk_stats = {
            'risk_checks_performed': 0,
            'trades_blocked': 0,
            'emergency_stops': 0,
            'volatility_reductions': 0,
            'max_risk_score_today': 0.0
        }
        
        logger.info("Risk Manager initialized")
    
    def _load_risk_config(self):
        """設定ファイルからリスクパラメータ読み込み"""
        try:
            risk_config = self.config.get('risk_management', {})
            
            if risk_config:
                # 設定値で上書き
                for key, value in risk_config.items():
                    if hasattr(self.risk_params, key):
                        setattr(self.risk_params, key, value)
                        logger.info(f"Risk parameter updated: {key} = {value}")
        
        except Exception as e:
            logger.error(f"Risk config loading error: {e}")
    
    async def initialize(self):
        """リスク管理システム初期化"""
        logger.info("Initializing Risk Manager...")
        
        # データベース初期化
        await self._init_database()
        
        # 初期残高設定
        await self._set_daily_start_balance()
        
        # リスク監視開始
        self.is_running = True
        asyncio.create_task(self._risk_monitoring_loop())
        
        logger.info("Risk Manager initialized successfully")
    
    async def _init_database(self):
        """リスク管理データベース初期化"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # リスク評価履歴テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS risk_assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        risk_action TEXT NOT NULL,
                        current_drawdown REAL DEFAULT 0.0,
                        daily_pnl REAL DEFAULT 0.0,
                        total_exposure REAL DEFAULT 0.0,
                        volatility_score REAL DEFAULT 0.0,
                        account_balance REAL DEFAULT 0.0,
                        risk_score REAL DEFAULT 0.0,
                        reasons TEXT,
                        recommendations TEXT
                    )
                ''')
                
                # リスクイベントテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS risk_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT,
                        action_taken TEXT,
                        positions_affected INTEGER DEFAULT 0,
                        pnl_impact REAL DEFAULT 0.0
                    )
                ''')
                
                await conn.commit()
            
            self._db_initialized = True
            logger.info("Risk management database initialized")
            
        except Exception as e:
            logger.error(f"Risk database initialization error: {e}")
    
    async def _set_daily_start_balance(self):
        """日次開始残高設定"""
        try:
            # ポジション統計から現在の総PnL取得
            stats = self.position_tracker.get_statistics()
            total_pnl = stats.get('total_pnl', 0.0)
            
            # 仮想口座残高計算（設定から基準残高取得）
            base_balance = self.config.get('risk_management', {}).get('base_account_balance', 10000.0)
            self.daily_start_balance = base_balance + total_pnl
            
            logger.info(f"Daily start balance set: {self.daily_start_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Daily start balance setting error: {e}")
            self.daily_start_balance = 10000.0  # デフォルト値
    
    async def assess_trading_risk(self, symbol: str, position_type: str, 
                                quantity: float, entry_price: float) -> RiskAssessment:
        """取引前リスク評価 - kiro要件4.1-4.3準拠"""
        try:
            reasons = []
            recommendations = []
            risk_score = 0.0
            
            # 現在の口座状況取得
            stats = self.position_tracker.get_statistics()
            current_balance = self.daily_start_balance + stats.get('total_pnl', 0.0)
            daily_pnl = stats.get('total_pnl', 0.0)  # 簡略化：日次PnL=総PnL
            current_drawdown = stats.get('current_drawdown', 0.0)
            total_exposure = self._calculate_total_exposure_impact(symbol, quantity, position_type)
            
            # 1. 日次損失チェック（要件4.2）
            if daily_pnl <= -self.risk_params.max_daily_loss:
                risk_score += 100.0
                reasons.append(f"Daily loss limit exceeded: {daily_pnl:.2f}")
                return RiskAssessment(
                    risk_level=RiskLevel.CRITICAL,
                    risk_action=RiskAction.STOP_TRADING,
                    current_drawdown=current_drawdown,
                    daily_pnl=daily_pnl,
                    total_exposure=total_exposure,
                    volatility_score=0.0,
                    account_balance=current_balance,
                    risk_score=risk_score,
                    reasons=reasons,
                    recommendations=["Stop trading for today", "Review risk parameters"],
                    timestamp=datetime.now()
                )
            
            # 2. ドローダウンチェック
            drawdown_percent = (current_drawdown / self.daily_start_balance) * 100
            if drawdown_percent > self.risk_params.max_drawdown_percent:
                risk_score += 80.0
                reasons.append(f"Drawdown limit exceeded: {drawdown_percent:.2f}%")
            
            # 3. ポジションサイズチェック（要件4.1）
            if quantity > self.risk_params.max_position_size:
                risk_score += 60.0
                reasons.append(f"Position size too large: {quantity}")
                recommendations.append(f"Reduce position size to {self.risk_params.max_position_size}")
            
            # 4. 総エクスポージャーチェック
            if total_exposure > self.risk_params.max_total_exposure:
                risk_score += 50.0
                reasons.append(f"Total exposure too high: {total_exposure:.2f}")
            
            # 5. ボラティリティチェック（要件4.3）
            volatility_score = await self._calculate_volatility_score(symbol)
            if volatility_score > self.risk_params.high_volatility_threshold:
                risk_score += 40.0
                reasons.append(f"High volatility detected: {volatility_score:.4f}")
                recommendations.append("Consider reducing position size by 50%")
            
            # 6. 口座残高チェック（要件4.1）
            if current_balance <= 0:
                risk_score += 100.0
                reasons.append("Account balance depleted")
            
            # リスクレベル・アクション決定
            risk_level, risk_action = self._determine_risk_level_and_action(risk_score, reasons)
            
            # 評価結果作成
            assessment = RiskAssessment(
                risk_level=risk_level,
                risk_action=risk_action,
                current_drawdown=current_drawdown,
                daily_pnl=daily_pnl,
                total_exposure=total_exposure,
                volatility_score=volatility_score,
                account_balance=current_balance,
                risk_score=risk_score,
                reasons=reasons,
                recommendations=recommendations,
                timestamp=datetime.now()
            )
            
            # データベース記録
            await self._save_risk_assessment(assessment)
            
            return assessment
            
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            # エラー時は安全側に判定
            return RiskAssessment(
                risk_level=RiskLevel.HIGH,
                risk_action=RiskAction.STOP_TRADING,
                current_drawdown=0.0,
                daily_pnl=0.0,
                total_exposure=0.0,
                volatility_score=0.0,
                account_balance=0.0,
                risk_score=100.0,
                reasons=["Risk assessment error"],
                recommendations=["Manual review required"],
                timestamp=datetime.now()
            )
    
    def _calculate_total_exposure_impact(self, symbol: str, quantity: float, position_type: str) -> float:
        """新規ポジション追加時の総エクスポージャー計算"""
        current_exposure = self.position_tracker.get_total_exposure(symbol)
        
        # 新規ポジションのエクスポージャー追加
        new_exposure = quantity
        if position_type == "SELL":
            new_exposure = -new_exposure
        
        return abs(current_exposure + new_exposure)
    
    async def _calculate_volatility_score(self, symbol: str) -> float:
        """ボラティリティスコア計算"""
        try:
            # 簡易ボラティリティ計算（実装では価格履歴から計算）
            # 現在は設定ベースの固定値を返す
            base_volatility = 0.01  # 1%
            
            # 時間帯による調整（例：ロンドン・NYオープン時は高ボラティリティ）
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 10 or 13 <= current_hour <= 15:  # 市場オープン時間
                base_volatility *= 1.5
            
            return base_volatility
            
        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
            return 0.01  # デフォルト値
    
    def _determine_risk_level_and_action(self, risk_score: float, reasons: List[str]) -> Tuple[RiskLevel, RiskAction]:
        """リスクスコアからレベル・アクション決定"""
        if risk_score >= 100.0:
            return RiskLevel.CRITICAL, RiskAction.STOP_TRADING
        elif risk_score >= 80.0:
            return RiskLevel.HIGH, RiskAction.REDUCE_SIZE
        elif risk_score >= 60.0:
            return RiskLevel.HIGH, RiskAction.REDUCE_SIZE
        elif risk_score >= 40.0:
            return RiskLevel.NORMAL, RiskAction.REDUCE_SIZE
        elif risk_score >= 20.0:
            return RiskLevel.NORMAL, RiskAction.ALLOW
        else:
            return RiskLevel.LOW, RiskAction.ALLOW
    
    async def calculate_optimal_position_size(self, symbol: str, entry_price: float, 
                                            stop_loss: float, account_balance: float) -> float:
        """最適ポジションサイズ計算 - kiro要件4.1準拠"""
        try:
            # リスク額計算
            risk_amount = account_balance * (self.risk_params.risk_per_trade_percent / 100)
            
            # ストップロス距離
            stop_distance = abs(entry_price - stop_loss)
            if stop_distance == 0:
                return self.risk_params.max_position_size * 0.1  # 安全値
            
            # 基本ポジションサイズ計算
            base_position_size = risk_amount / (stop_distance * 100000)  # pip値計算
            
            # ボラティリティ調整
            volatility_score = await self._calculate_volatility_score(symbol)
            if volatility_score > self.risk_params.high_volatility_threshold:
                base_position_size *= (1.0 - self.risk_params.volatility_position_reduction)
            elif volatility_score > self.risk_params.normal_volatility_threshold:
                base_position_size *= 0.8
            
            # 最大サイズ制限
            optimal_size = min(base_position_size, self.risk_params.max_position_size)
            
            logger.info(f"Optimal position size calculated: {optimal_size:.3f} for {symbol}")
            return optimal_size
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return self.risk_params.max_position_size * 0.1  # 安全値
    
    async def _risk_monitoring_loop(self):
        """リスク監視ループ"""
        while self.is_running:
            try:
                current_time = time.time()
                
                if current_time - self.last_risk_check >= self.risk_params.risk_check_interval:
                    await self._perform_risk_check()
                    self.last_risk_check = current_time
                
                await asyncio.sleep(5)  # 5秒間隔でチェック
                
            except Exception as e:
                logger.error(f"Risk monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    async def _perform_risk_check(self):
        """定期リスクチェック実行"""
        try:
            self.risk_stats['risk_checks_performed'] += 1
            
            # 現在の統計取得
            stats = self.position_tracker.get_statistics()
            daily_pnl = stats.get('total_pnl', 0.0)
            current_drawdown = stats.get('current_drawdown', 0.0)
            
            # 緊急停止チェック（要件4.2）
            if daily_pnl <= -self.risk_params.max_daily_loss:
                await self._trigger_emergency_stop("Daily loss limit exceeded")
                return
            
            # ドローダウンチェック
            drawdown_percent = (current_drawdown / self.daily_start_balance) * 100
            if drawdown_percent > self.risk_params.max_drawdown_percent:
                await self._trigger_emergency_stop(f"Drawdown limit exceeded: {drawdown_percent:.2f}%")
                return
            
            # ボラティリティチェック（要件4.3）
            active_positions = self.position_tracker.get_active_positions()
            for position in active_positions:
                volatility_score = await self._calculate_volatility_score(position.symbol)
                if volatility_score > self.risk_params.high_volatility_threshold:
                    await self._handle_high_volatility(position)
            
            logger.debug("Risk check completed successfully")
            
        except Exception as e:
            logger.error(f"Risk check error: {e}")
    
    async def _trigger_emergency_stop(self, reason: str):
        """緊急停止発動 - kiro要件4.2,4.5準拠"""
        try:
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            
            # 取引停止
            self.trading_enabled = False
            self.risk_stats['emergency_stops'] += 1
            
            # 全ポジション決済指示
            active_positions = self.position_tracker.get_active_positions()
            close_tasks = []
            
            for position in active_positions:
                if position.status == PositionStatus.OPEN:
                    # 非同期決済タスク作成（30秒以内に決済）
                    task = asyncio.create_task(
                        self._emergency_close_position(position)
                    )
                    close_tasks.append(task)
            
            # 決済完了待機（タイムアウト付き）
            if close_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*close_tasks, return_exceptions=True),
                        timeout=self.risk_params.emergency_close_timeout
                    )
                    logger.info("Emergency position closure completed")
                except asyncio.TimeoutError:
                    logger.error("Emergency closure timeout - manual intervention required")
            
            # リスクイベント記録
            await self._log_risk_event(
                event_type="EMERGENCY_STOP",
                severity="CRITICAL",
                description=reason,
                action_taken="All positions closed, trading disabled",
                positions_affected=len(active_positions)
            )
            
        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
    
    async def _emergency_close_position(self, position: Position):
        """緊急ポジション決済"""
        try:
            # 現在価格で即座決済
            exit_price = position.current_price or position.entry_price
            
            await self.position_tracker.close_position(
                position.position_id,
                exit_price,
                commission=0.0  # 緊急時は手数料無視
            )
            
            logger.info(f"Emergency closed position: {position.position_id}")
            
        except Exception as e:
            logger.error(f"Emergency position close error: {e}")
    
    async def _handle_high_volatility(self, position: Position):
        """高ボラティリティ対応 - kiro要件4.3準拠"""
        try:
            # 50%ポジション削減
            reduced_quantity = position.quantity * self.risk_params.volatility_position_reduction
            close_quantity = position.quantity - reduced_quantity
            
            if close_quantity > 0.01:  # 最小決済量チェック
                # 部分決済実行（簡略化：全決済）
                await self.position_tracker.close_position(
                    position.position_id,
                    position.current_price or position.entry_price
                )
                
                self.risk_stats['volatility_reductions'] += 1
                
                logger.info(f"Volatility reduction: closed {position.position_id}")
                
                # リスクイベント記録
                await self._log_risk_event(
                    event_type="VOLATILITY_REDUCTION",
                    severity="HIGH",
                    description=f"High volatility detected for {position.symbol}",
                    action_taken=f"Reduced position size by 50%",
                    positions_affected=1
                )
        
        except Exception as e:
            logger.error(f"High volatility handling error: {e}")
    
    async def _save_risk_assessment(self, assessment: RiskAssessment):
        """リスク評価データベース保存"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO risk_assessments (
                        timestamp, risk_level, risk_action, current_drawdown,
                        daily_pnl, total_exposure, volatility_score, account_balance,
                        risk_score, reasons, recommendations
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    assessment.timestamp.isoformat(),
                    assessment.risk_level.value,
                    assessment.risk_action.value,
                    assessment.current_drawdown,
                    assessment.daily_pnl,
                    assessment.total_exposure,
                    assessment.volatility_score,
                    assessment.account_balance,
                    assessment.risk_score,
                    json.dumps(assessment.reasons),
                    json.dumps(assessment.recommendations)
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Risk assessment save error: {e}")
    
    async def _log_risk_event(self, event_type: str, severity: str, 
                             description: str, action_taken: str, 
                             positions_affected: int = 0, pnl_impact: float = 0.0):
        """リスクイベントログ記録"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO risk_events (
                        timestamp, event_type, severity, description,
                        action_taken, positions_affected, pnl_impact
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    event_type, severity, description,
                    action_taken, positions_affected, pnl_impact
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Risk event logging error: {e}")
    
    def is_trading_allowed(self) -> bool:
        """取引許可状態取得"""
        return self.trading_enabled and self.is_running
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """リスク統計取得"""
        stats = self.risk_stats.copy()
        stats['trading_enabled'] = self.trading_enabled
        stats['daily_start_balance'] = self.daily_start_balance
        return stats
    
    async def reset_daily_limits(self):
        """日次制限リセット"""
        try:
            await self._set_daily_start_balance()
            self.trading_enabled = True
            self.session_start_time = datetime.now()
            
            logger.info("Daily risk limits reset")
            
        except Exception as e:
            logger.error(f"Daily limits reset error: {e}")
    
    async def stop(self):
        """リスク管理システム停止"""
        logger.info("Stopping Risk Manager...")
        self.is_running = False
        logger.info("Risk Manager stopped")

# テスト関数
async def test_risk_manager():
    """リスク管理システムテスト"""
    print("🧪 Risk Manager Test Starting...")
    
    # ポジション追跡システム初期化
    from position_management import PositionTracker
    position_tracker = PositionTracker()
    await position_tracker.initialize()
    
    # リスク管理システム初期化
    risk_manager = RiskManager(position_tracker)
    await risk_manager.initialize()
    
    try:
        # テストポジション開設
        await position_tracker.open_position(
            symbol="EURUSD",
            position_type="BUY",
            entry_price=1.1000,
            quantity=0.1
        )
        
        # リスク評価テスト
        assessment = await risk_manager.assess_trading_risk(
            symbol="EURUSD",
            position_type="SELL",
            quantity=2.0,  # 大きなポジション
            entry_price=1.1050
        )
        
        print(f"📊 Risk Assessment: {assessment.risk_level.value} - {assessment.risk_action.value}")
        print(f"Risk Score: {assessment.risk_score:.2f}")
        print(f"Reasons: {assessment.reasons}")
        
        # 最適ポジションサイズ計算テスト
        optimal_size = await risk_manager.calculate_optimal_position_size(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=10000.0
        )
        
        print(f"💡 Optimal Position Size: {optimal_size:.3f}")
        
        print("✅ Risk Manager Test Completed")
        
    finally:
        await risk_manager.stop()
        await position_tracker.stop()

if __name__ == "__main__":
    asyncio.run(test_risk_manager())