#!/usr/bin/env python3
"""
MetaTrader5モックモジュール - テスト・開発用
Wine環境でのMT5が利用できない場合のフォールバック
"""

import time
import random
from datetime import datetime
from typing import NamedTuple, List, Optional

# MT5定数のモック
POSITION_TYPE_BUY = 0
POSITION_TYPE_SELL = 1

class AccountInfo(NamedTuple):
    """口座情報モック"""
    login: int
    balance: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float
    profit: float
    currency: str
    server: str
    leverage: int

class PositionInfo(NamedTuple):
    """ポジション情報モック"""
    ticket: int
    symbol: str
    type: int
    volume: float
    price_open: float
    price_current: float
    profit: float
    swap: float
    time: int
    comment: str

class TickInfo(NamedTuple):
    """ティック情報モック"""
    bid: float
    ask: float
    time: int

# グローバル状態
_initialized = False
_demo_account = AccountInfo(
    login=12345678,
    balance=3000000.0,  # 300万円デモ口座
    equity=3000000.0,
    margin=0.0,
    margin_free=3000000.0,
    margin_level=0.0,
    profit=0.0,
    currency="USD",
    server="Demo-Server",
    leverage=1000
)

_demo_positions: List[PositionInfo] = []

def initialize() -> bool:
    """MT5初期化モック"""
    global _initialized
    _initialized = True
    print("📊 MT5モック: 初期化完了 (Wine環境テスト用)")
    return True

def shutdown():
    """MT5終了モック"""
    global _initialized
    _initialized = False
    print("📊 MT5モック: 終了")

def last_error():
    """最後のエラー取得モック"""
    return (0, "No error (mock)")

def account_info() -> Optional[AccountInfo]:
    """口座情報取得モック"""
    if not _initialized:
        return None
    
    # リアルタイム変動シミュレーション
    base_balance = 3000000.0
    variation = random.uniform(-1000, 1000)  # ±1000円の変動
    current_profit = sum(pos.profit for pos in _demo_positions)
    
    return AccountInfo(
        login=_demo_account.login,
        balance=base_balance,
        equity=base_balance + current_profit,
        margin=sum(pos.volume * 100000 * 0.01 for pos in _demo_positions),  # 1%マージン
        margin_free=base_balance - sum(pos.volume * 100000 * 0.01 for pos in _demo_positions),
        margin_level=base_balance / max(sum(pos.volume * 100000 * 0.01 for pos in _demo_positions), 1) * 100,
        profit=current_profit,
        currency="USD",
        server="Demo-Wine-Mock",
        leverage=1000
    )

def positions_get() -> List[PositionInfo]:
    """ポジション一覧取得モック"""
    if not _initialized:
        return []
    
    # デモポジションを動的生成（JamesORBが実際に稼働していると仮定）
    current_time = int(time.time())
    
    # 50%の確率でデモポジションを生成
    if random.random() < 0.3 and len(_demo_positions) == 0:
        demo_position = PositionInfo(
            ticket=random.randint(100000, 999999),
            symbol="EURUSD",
            type=POSITION_TYPE_BUY if random.random() > 0.5 else POSITION_TYPE_SELL,
            volume=0.01,  # 0.01ロット固定
            price_open=1.08500 + random.uniform(-0.001, 0.001),
            price_current=1.08500 + random.uniform(-0.002, 0.002),
            profit=random.uniform(-50, 100),  # -50～+100円
            swap=0.0,
            time=current_time - random.randint(300, 3600),  # 5分～1時間前
            comment="JamesORB_v1.0"
        )
        _demo_positions.append(demo_position)
    
    # 既存ポジションの価格更新
    updated_positions = []
    for pos in _demo_positions:
        # 価格変動シミュレーション
        price_change = random.uniform(-0.0005, 0.0005)
        new_current_price = pos.price_current + price_change
        
        # 利益計算
        if pos.type == POSITION_TYPE_BUY:
            new_profit = (new_current_price - pos.price_open) * pos.volume * 100000
        else:
            new_profit = (pos.price_open - new_current_price) * pos.volume * 100000
        
        updated_position = pos._replace(
            price_current=new_current_price,
            profit=new_profit
        )
        updated_positions.append(updated_position)
    
    # 20%の確率でポジションクローズ
    if _demo_positions and random.random() < 0.2:
        _demo_positions.clear()
        print("📊 MT5モック: デモポジションクローズ")
    else:
        _demo_positions[:] = updated_positions
    
    return _demo_positions

def symbol_info_tick(symbol: str) -> Optional[TickInfo]:
    """ティック情報取得モック"""
    if not _initialized or symbol != "EURUSD":
        return None
    
    # EURUSD価格シミュレーション
    base_price = 1.08500
    variation = random.uniform(-0.001, 0.001)
    bid = base_price + variation
    spread = random.uniform(0.00015, 0.00025)  # 1.5-2.5 pips
    ask = bid + spread
    
    return TickInfo(
        bid=round(bid, 5),
        ask=round(ask, 5),
        time=int(time.time())
    )

def print_mock_status():
    """モック状態表示"""
    print(f"📊 MT5モック状態:")
    print(f"   初期化: {_initialized}")
    print(f"   ポジション数: {len(_demo_positions)}")
    if _demo_positions:
        total_profit = sum(pos.profit for pos in _demo_positions)
        print(f"   合計利益: {total_profit:.2f}")

if __name__ == "__main__":
    # テスト実行
    print("=== MT5モック テスト ===")
    initialize()
    
    print("\n口座情報:")
    account = account_info()
    print(f"  残高: {account.balance:,.0f}")
    print(f"  有効証拠金: {account.equity:,.0f}")
    
    print("\nティック情報:")
    tick = symbol_info_tick("EURUSD")
    print(f"  EURUSD: {tick.bid}/{tick.ask}")
    
    print("\nポジション:")
    positions = positions_get()
    if positions:
        for pos in positions:
            print(f"  {pos.symbol} {pos.type} {pos.volume} | 利益: {pos.profit:.2f}")
    else:
        print("  ポジションなし")
    
    shutdown()