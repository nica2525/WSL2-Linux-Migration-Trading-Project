#!/usr/bin/env python3
"""
Phase 3.1: Position Tracking System
kiro設計tasks.md:93-99準拠 - ポジション追跡システム

参照設計書: .kiro/specs/breakout-trading-system/tasks.md
要件: 4.1 (requirements.md)
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
import sys
from pathlib import Path

# 既存システム統合
sys.path.append(str(Path(__file__).parent))
from realtime_signal_generator import SystemConstants, get_config_value, calculate_time_diff_seconds, CONFIG
from communication.tcp_bridge import TCPBridge
from communication.file_bridge import FileBridge

# ログ設定
logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    """ポジション状態"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"

class PositionType(Enum):
    """ポジション種別"""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Position:
    """
    ポジション情報クラス - kiro要件4.1準拠
    リアルタイムP&L計算付きポジション追跡
    """
    position_id: str
    symbol: str
    position_type: PositionType
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    current_price: Optional[float] = None
    status: PositionStatus = PositionStatus.PENDING
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    commission: float = 0.0
    swap: float = 0.0
    slippage: float = 0.0
    mt4_ticket: Optional[int] = None
    strategy_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.strategy_params is None:
            self.strategy_params = {}
        if self.current_price is None:
            self.current_price = self.entry_price
    
    def calculate_unrealized_pnl(self, current_price: Optional[float] = None) -> float:
        """未実現損益計算"""
        if current_price:
            self.current_price = current_price
        
        if self.status != PositionStatus.OPEN or not self.current_price:
            return 0.0
        
        price_diff = self.current_price - self.entry_price
        if self.position_type == PositionType.SELL:
            price_diff = -price_diff
        
        # 通貨ペア基準のlot size (0.1 lot = 10,000 units)
        lot_size = self.quantity * 100000
        unrealized_pnl = price_diff * lot_size
        
        return unrealized_pnl
    
    def calculate_realized_pnl(self) -> float:
        """実現損益計算"""
        if self.status != PositionStatus.CLOSED or not self.exit_price:
            return 0.0
        
        price_diff = self.exit_price - self.entry_price
        if self.position_type == PositionType.SELL:
            price_diff = -price_diff
        
        # 通貨ペア基準のlot size
        lot_size = self.quantity * 100000
        gross_pnl = price_diff * lot_size
        
        # 手数料・スワップ・スリッページ差し引き
        realized_pnl = gross_pnl - self.commission - abs(self.swap) - abs(self.slippage)
        
        return realized_pnl
    
    def get_position_duration_minutes(self) -> float:
        """ポジション保有時間（分）"""
        end_time = self.exit_time if self.exit_time else datetime.now()
        return (end_time - self.entry_time).total_seconds() / 60.0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式変換"""
        data = asdict(self)
        data['position_type'] = self.position_type.value
        data['status'] = self.status.value
        data['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            data['exit_time'] = self.exit_time.isoformat()
        return data

class PositionTracker:
    """
    ポジション追跡システム - kiro設計tasks.md:93-99準拠
    PythonとMT4間のポジション同期・履歴追跡・パフォーマンス分析
    """
    
    def __init__(self):
        self.active_positions: Dict[str, Position] = {}
        self.position_history: List[Position] = []
        self.is_running = False
        
        # 設定読み込み
        self.config = CONFIG
        
        # 通信ブリッジ初期化
        comm_config = self.config.get('communication', {})
        self.tcp_bridge = TCPBridge(
            host=comm_config.get('signal_tcp_host', 'localhost'),
            port=comm_config.get('signal_tcp_port', 9090)
        )
        self.file_bridge = FileBridge(
            message_dir=comm_config.get('file_bridge_dir', '/mnt/c/MT4_Bridge')
        )
        
        # データベース接続
        self.db_path = self.config.get('database', {}).get('path', './positions.db')
        self._db_initialized = False
        
        # 統計情報
        self.stats = {
            'total_positions': 0,
            'winning_positions': 0,
            'losing_positions': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0
        }
        
        logger.info("Position Tracker initialized")
    
    async def initialize(self):
        """システム初期化"""
        logger.info("Initializing Position Tracker...")
        
        # データベース初期化
        await self._init_database()
        
        # 通信接続
        try:
            if await self.tcp_bridge.connect():
                logger.info("Position tracker TCP connected")
            else:
                logger.warning("TCP connection failed, using file bridge")
        except Exception as e:
            logger.error(f"Position tracker connection error: {e}")
        
        # 過去ポジション復元
        await self._restore_positions()
        
        self.is_running = True
        logger.info("Position Tracker initialized successfully")
    
    async def _init_database(self):
        """ポジション管理データベース初期化"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # ポジションテーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        position_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        position_type TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        quantity REAL NOT NULL,
                        entry_time TEXT NOT NULL,
                        stop_loss REAL,
                        take_profit REAL,
                        current_price REAL,
                        status TEXT NOT NULL,
                        exit_price REAL,
                        exit_time TEXT,
                        commission REAL DEFAULT 0.0,
                        swap REAL DEFAULT 0.0,
                        slippage REAL DEFAULT 0.0,
                        mt4_ticket INTEGER,
                        strategy_params TEXT,
                        unrealized_pnl REAL DEFAULT 0.0,
                        realized_pnl REAL DEFAULT 0.0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # パフォーマンス分析テーブル
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS performance_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        snapshot_time TEXT NOT NULL,
                        total_positions INTEGER DEFAULT 0,
                        active_positions INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        unrealized_pnl REAL DEFAULT 0.0,
                        realized_pnl REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        current_drawdown REAL DEFAULT 0.0,
                        account_balance REAL DEFAULT 0.0,
                        daily_pnl REAL DEFAULT 0.0
                    )
                ''')
                
                await conn.commit()
            
            self._db_initialized = True
            logger.info("Position database initialized")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    async def _restore_positions(self):
        """システム再起動時のポジション復元"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # アクティブポジション復元
                cursor = await conn.execute('''
                    SELECT * FROM positions 
                    WHERE status = ? OR status = ?
                    ORDER BY entry_time DESC
                ''', (PositionStatus.OPEN.value, PositionStatus.PENDING.value))
                
                rows = await cursor.fetchall()
                
                for row in rows:
                    position = self._row_to_position(row)
                    self.active_positions[position.position_id] = position
                    logger.info(f"Restored position: {position.position_id} ({position.symbol})")
                
                # 統計情報復元
                await self._update_statistics()
                
                logger.info(f"Restored {len(self.active_positions)} active positions")
                
        except Exception as e:
            logger.error(f"Position restoration error: {e}")
    
    def _row_to_position(self, row) -> Position:
        """データベース行からPositionオブジェクト生成"""
        strategy_params = {}
        if row[16]:  # strategy_params
            try:
                strategy_params = json.loads(row[16])
            except:
                pass
        
        return Position(
            position_id=row[0],
            symbol=row[1],
            position_type=PositionType(row[2]),
            entry_price=row[3],
            quantity=row[4],
            entry_time=datetime.fromisoformat(row[5]),
            stop_loss=row[6],
            take_profit=row[7],
            current_price=row[8],
            status=PositionStatus(row[9]),
            exit_price=row[10],
            exit_time=datetime.fromisoformat(row[11]) if row[11] else None,
            commission=row[12],
            swap=row[13],
            slippage=row[14],
            mt4_ticket=row[15],
            strategy_params=strategy_params
        )
    
    async def open_position(self, symbol: str, position_type: str, entry_price: float, 
                          quantity: float, stop_loss: Optional[float] = None, 
                          take_profit: Optional[float] = None, 
                          strategy_params: Dict[str, Any] = None) -> Position:
        """新規ポジション開設"""
        try:
            # ポジションID生成
            position_id = f"{symbol}_{int(time.time() * 1000)}"
            
            # Positionオブジェクト作成
            position = Position(
                position_id=position_id,
                symbol=symbol,
                position_type=PositionType(position_type),
                entry_price=entry_price,
                quantity=quantity,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                current_price=entry_price,
                status=PositionStatus.PENDING,
                strategy_params=strategy_params or {}
            )
            
            # MT4に送信
            await self._send_position_to_mt4(position, 'OPEN')
            
            # ローカル追加
            self.active_positions[position_id] = position
            
            # データベース保存
            await self._save_position(position)
            
            logger.info(f"Position opened: {position_id} ({symbol} {position_type} {quantity}@{entry_price})")
            
            return position
            
        except Exception as e:
            logger.error(f"Position opening error: {e}")
            raise
    
    async def close_position(self, position_id: str, exit_price: float, 
                           commission: float = 0.0, swap: float = 0.0) -> Optional[Position]:
        """ポジション決済"""
        try:
            if position_id not in self.active_positions:
                logger.warning(f"Position not found: {position_id}")
                return None
            
            position = self.active_positions[position_id]
            
            # 決済情報更新
            position.exit_price = exit_price
            position.exit_time = datetime.now()
            position.commission = commission
            position.swap = swap
            position.status = PositionStatus.CLOSED
            
            # 実現損益計算
            realized_pnl = position.calculate_realized_pnl()
            
            # MT4に決済通知
            await self._send_position_to_mt4(position, 'CLOSE')
            
            # アクティブリストから削除・履歴に追加
            del self.active_positions[position_id]
            self.position_history.append(position)
            
            # データベース更新
            await self._save_position(position)
            
            # 統計更新
            await self._update_statistics()
            
            logger.info(f"Position closed: {position_id} (PnL: {realized_pnl:.2f})")
            
            return position
            
        except Exception as e:
            logger.error(f"Position closing error: {e}")
            return None
    
    async def update_position_price(self, symbol: str, current_price: float):
        """ポジションの現在価格更新"""
        try:
            updated_count = 0
            
            for position in self.active_positions.values():
                if position.symbol == symbol and position.status == PositionStatus.OPEN:
                    position.current_price = current_price
                    
                    # 未実現損益計算
                    unrealized_pnl = position.calculate_unrealized_pnl()
                    
                    # データベース更新（軽量化：価格のみ）
                    await self._update_position_price_only(position, unrealized_pnl)
                    
                    updated_count += 1
            
            if updated_count > 0:
                logger.debug(f"Updated {updated_count} positions for {symbol}@{current_price}")
                
        except Exception as e:
            logger.error(f"Position price update error: {e}")
    
    async def _send_position_to_mt4(self, position: Position, action: str):
        """MT4へのポジション情報送信"""
        try:
            message = {
                'type': 'position_action',
                'action': action,
                'data': {
                    'position_id': position.position_id,
                    'symbol': position.symbol,
                    'position_type': position.position_type.value,
                    'entry_price': position.entry_price,
                    'quantity': position.quantity,
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'exit_price': position.exit_price
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # TCP送信試行
            if self.tcp_bridge.is_connected():
                try:
                    success = await self.tcp_bridge.send_data(message)
                    if success:
                        return True
                except Exception as e:
                    logger.warning(f"TCP position send failed: {e}")
            
            # フォールバック: ファイル送信
            return await self.file_bridge.send_message(message, 'mt4')
            
        except Exception as e:
            logger.error(f"Position MT4 send error: {e}")
            return False
    
    async def _save_position(self, position: Position):
        """ポジションデータベース保存"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO positions (
                        position_id, symbol, position_type, entry_price, quantity,
                        entry_time, stop_loss, take_profit, current_price, status,
                        exit_price, exit_time, commission, swap, slippage,
                        mt4_ticket, strategy_params, unrealized_pnl, realized_pnl,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.position_id, position.symbol, position.position_type.value,
                    position.entry_price, position.quantity, position.entry_time.isoformat(),
                    position.stop_loss, position.take_profit, position.current_price,
                    position.status.value, position.exit_price,
                    position.exit_time.isoformat() if position.exit_time else None,
                    position.commission, position.swap, position.slippage,
                    position.mt4_ticket, json.dumps(position.strategy_params),
                    position.calculate_unrealized_pnl(), position.calculate_realized_pnl(),
                    datetime.now().isoformat()
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Position save error: {e}")
    
    async def _update_position_price_only(self, position: Position, unrealized_pnl: float):
        """価格のみの軽量更新"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    UPDATE positions 
                    SET current_price = ?, unrealized_pnl = ?, updated_at = ?
                    WHERE position_id = ?
                ''', (position.current_price, unrealized_pnl, 
                      datetime.now().isoformat(), position.position_id))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Position price update error: {e}")
    
    async def _update_statistics(self):
        """統計情報更新"""
        try:
            total_realized_pnl = 0.0
            total_unrealized_pnl = 0.0
            winning_count = 0
            losing_count = 0
            
            # 履歴ポジション統計
            for position in self.position_history:
                if position.status == PositionStatus.CLOSED:
                    realized_pnl = position.calculate_realized_pnl()
                    total_realized_pnl += realized_pnl
                    
                    if realized_pnl > 0:
                        winning_count += 1
                    else:
                        losing_count += 1
            
            # アクティブポジション統計
            for position in self.active_positions.values():
                if position.status == PositionStatus.OPEN:
                    total_unrealized_pnl += position.calculate_unrealized_pnl()
            
            # 統計更新
            self.stats.update({
                'total_positions': len(self.position_history) + len(self.active_positions),
                'winning_positions': winning_count,
                'losing_positions': losing_count,
                'total_pnl': total_realized_pnl + total_unrealized_pnl,
                'realized_pnl': total_realized_pnl,
                'unrealized_pnl': total_unrealized_pnl
            })
            
            # ドローダウン計算
            if self.stats['total_pnl'] < 0:
                self.stats['current_drawdown'] = abs(self.stats['total_pnl'])
                if self.stats['current_drawdown'] > self.stats['max_drawdown']:
                    self.stats['max_drawdown'] = self.stats['current_drawdown']
            else:
                self.stats['current_drawdown'] = 0.0
            
        except Exception as e:
            logger.error(f"Statistics update error: {e}")
    
    def get_active_positions(self) -> List[Position]:
        """アクティブポジション取得"""
        return list(self.active_positions.values())
    
    def get_position_by_id(self, position_id: str) -> Optional[Position]:
        """ID指定ポジション取得"""
        return self.active_positions.get(position_id)
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """シンボル別ポジション取得"""
        return [pos for pos in self.active_positions.values() if pos.symbol == symbol]
    
    def get_total_exposure(self, symbol: str) -> float:
        """シンボル別総エクスポージャー計算"""
        total_exposure = 0.0
        for position in self.get_positions_by_symbol(symbol):
            if position.status == PositionStatus.OPEN:
                exposure = position.quantity
                if position.position_type == PositionType.SELL:
                    exposure = -exposure
                total_exposure += exposure
        return total_exposure
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        stats = self.stats.copy()
        
        # 勝率計算
        total_closed = stats['winning_positions'] + stats['losing_positions']
        if total_closed > 0:
            stats['win_rate'] = stats['winning_positions'] / total_closed
        else:
            stats['win_rate'] = 0.0
        
        # アクティブポジション数
        stats['active_positions'] = len(self.active_positions)
        
        return stats
    
    async def stop(self):
        """システム停止"""
        logger.info("Stopping Position Tracker...")
        self.is_running = False
        
        # 最終統計保存
        await self._save_performance_snapshot()
        
        logger.info("Position Tracker stopped")
    
    async def _save_performance_snapshot(self):
        """パフォーマンススナップショット保存"""
        try:
            stats = self.get_statistics()
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO performance_snapshots (
                        snapshot_time, total_positions, active_positions,
                        total_pnl, unrealized_pnl, realized_pnl, win_rate,
                        max_drawdown, current_drawdown
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    stats['total_positions'],
                    stats['active_positions'],
                    stats['total_pnl'],
                    stats['unrealized_pnl'],
                    stats.get('realized_pnl', 0.0),
                    stats['win_rate'],
                    stats['max_drawdown'],
                    stats['current_drawdown']
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"Performance snapshot save error: {e}")

# テスト関数
async def test_position_tracker():
    """ポジション追跡システムテスト"""
    print("🧪 Position Tracker Test Starting...")
    
    tracker = PositionTracker()
    await tracker.initialize()
    
    try:
        # テストポジション開設
        position1 = await tracker.open_position(
            symbol="EURUSD",
            position_type="BUY",
            entry_price=1.1000,
            quantity=0.1,
            stop_loss=1.0950,
            take_profit=1.1100
        )
        
        position2 = await tracker.open_position(
            symbol="USDJPY",
            position_type="SELL", 
            entry_price=150.00,
            quantity=0.05,
            stop_loss=150.50,
            take_profit=149.00
        )
        
        # 価格更新テスト
        await tracker.update_position_price("EURUSD", 1.1025)
        await tracker.update_position_price("USDJPY", 149.75)
        
        # 統計表示
        stats = tracker.get_statistics()
        print(f"📊 Statistics: {stats}")
        
        # ポジション決済テスト
        await tracker.close_position(position1.position_id, 1.1025, commission=2.0)
        
        print("✅ Position Tracker Test Completed")
        
    finally:
        await tracker.stop()

if __name__ == "__main__":
    asyncio.run(test_position_tracker())