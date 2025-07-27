# リアルタイムダッシュボード仕様書

## 📱 UI/UX設計

### メイン画面（スマホ最適化）
```
┌─────────────────────────┐
│ 🔴 JamesORB EA - LIVE   │ ← ステータス
├─────────────────────────┤
│ EURUSD: 1.0845 ↗️ +12    │ ← 現在価格
│ Position: BUY 0.01      │ ← ポジション
│ P&L: +$15.30 📈         │ ← 損益
├─────────────────────────┤
│ 📊 [今日] [週] [月]      │ ← 期間選択
│                         │
│ ▲ Trades: 3             │ ← 統計
│ ▲ Win Rate: 66.7%       │
│ ▲ Profit: $45.20        │
├─────────────────────────┤
│ 🔔 Alerts (2)           │ ← アラート
│ • New position opened   │
│ • Stop loss triggered   │
└─────────────────────────┘
```

### デスクトップ画面（フル機能）
```
┌────────────────┬────────────────┬────────────────┐
│ EA Status      │ Current Price  │ Quick Stats    │
│ 🟢 JamesORB    │ EURUSD        │ Today: +$25    │
│ 🟢 AutoStart   │ 1.0845 ↗️      │ Week: +$120    │
│ 🟢 Monitor     │ Spread: 1.2    │ Month: +$450   │
└────────────────┼────────────────┼────────────────┤
│ Live Chart                     │ Position List  │
│ ╭─EURUSD M5 Chart──────────╮   │ BUY EURUSD    │
│ │                          │   │ 0.01 lot      │
│ │     📈                   │   │ +$15.30       │
│ │  ORB Lines               │   │ [Close]       │
│ │                          │   │               │
│ ╰──────────────────────────╯   │               │
├────────────────────────────────┼────────────────┤
│ Recent Trades                  │ System Logs    │
│ [Time] [Type] [Price] [P&L]    │ 09:15 Position│
│ 09:23  BUY   1.0840  +$12.50  │       opened   │
│ 08:45  SELL  1.0855  +$18.20  │ 09:10 System   │
│ 07:30  BUY   1.0830  -$5.10   │       check OK │
└────────────────────────────────┴────────────────┘
```

## 🛠️ 技術スタック

### Backend (Python)
```python
# FastAPI + WebSocket
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
import asyncio
import json

app = FastAPI()

# リアルタイムデータ配信
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # MT5からデータ取得
        data = await get_realtime_data()
        await websocket.send_json(data)
        await asyncio.sleep(1)  # 1秒更新

# RESTful API
@app.get("/api/positions")
async def get_positions():
    return get_current_positions()

@app.post("/api/positions/{id}/close")
async def close_position(id: int):
    return close_position_by_id(id)
```

### Frontend (JavaScript)
```javascript
// React + Chart.js
import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';

const Dashboard = () => {
  const [data, setData] = useState({});
  
  // WebSocket接続
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onmessage = (event) => {
      setData(JSON.parse(event.data));
    };
  }, []);

  return (
    <div className="dashboard">
      <StatusCard data={data.status} />
      <PriceCard data={data.price} />
      <ChartCard data={data.chart} />
      <PositionList positions={data.positions} />
    </div>
  );
};
```

## 📊 データ構造

### リアルタイムデータ
```json
{
  "timestamp": "2025-07-27T10:30:15Z",
  "ea_status": {
    "name": "JamesORB_v1.0",
    "status": "RUNNING",
    "magic": 20250727,
    "uptime": "15h 30m"
  },
  "market": {
    "symbol": "EURUSD",
    "bid": 1.0845,
    "ask": 1.0847,
    "spread": 1.2,
    "change": "+0.0012",
    "change_percent": "+0.11%"
  },
  "positions": [
    {
      "ticket": 12345,
      "type": "BUY",
      "volume": 0.01,
      "open_price": 1.0840,
      "current_price": 1.0845,
      "profit": 15.30,
      "open_time": "2025-07-27T09:23:45Z"
    }
  ],
  "statistics": {
    "today": {"trades": 3, "profit": 25.40, "win_rate": 66.7},
    "week": {"trades": 12, "profit": 120.50, "win_rate": 75.0},
    "month": {"trades": 45, "profit": 450.20, "win_rate": 68.9}
  },
  "alerts": [
    {
      "id": 1,
      "type": "POSITION_OPENED",
      "message": "New BUY position opened",
      "timestamp": "2025-07-27T09:23:45Z",
      "severity": "INFO"
    }
  ]
}
```

## 🔐 セキュリティ機能

### 認証・認可
```python
# JWT認証
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTAuthentication

# Basic認証（簡易版）
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# アクセス制限
ALLOWED_IPS = ["192.168.1.0/24", "YOUR_MOBILE_IP"]
```

### HTTPS対応
```python
# SSL証明書（Let's Encrypt）
import ssl
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8443,
        ssl_keyfile="./key.pem",
        ssl_certfile="./cert.pem"
    )
```

## 📱 モバイル最適化

### PWA対応
```javascript
// Progressive Web App
// manifest.json
{
  "name": "JamesORB Dashboard",
  "short_name": "EA Monitor",
  "start_url": "/",
  "display": "standalone",
  "icons": [
    {
      "src": "icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}

// Service Worker
self.addEventListener('fetch', event => {
  // オフライン対応
});
```

### タッチ操作対応
```css
/* スマホ最適化CSS */
.dashboard {
  touch-action: manipulation;
  -webkit-overflow-scrolling: touch;
}

.card {
  min-height: 44px; /* iOSタッチターゲット */
  padding: 12px;
  border-radius: 8px;
}

@media (max-width: 768px) {
  .grid { grid-template-columns: 1fr; }
  .chart { height: 200px; }
}
```

## 🚀 機能一覧

### Core機能
- ✅ リアルタイム価格表示
- ✅ ポジション一覧・詳細
- ✅ P&L計算・表示
- ✅ EA稼働状態監視
- ✅ アラート・通知

### Advanced機能
- 📊 インタラクティブチャート
- 📱 プッシュ通知
- 🔄 ワンタッチポジション決済
- 📈 統計・レポート機能
- ⚙️ 設定変更（パラメータ調整）

### 運用機能
- 🔐 セキュア認証
- 📱 PWA（アプリライク）
- 🌐 マルチデバイス対応
- 💾 データ永続化
- 🔄 自動復旧

## 🛣️ 実装ロードマップ

### Phase 1: MVP (1-2週間)
- 基本ダッシュボード
- リアルタイム表示
- モバイル対応

### Phase 2: Advanced (2-3週間)
- チャート機能
- アラートシステム
- 操作機能

### Phase 3: Production (1-2週間)
- セキュリティ強化
- パフォーマンス最適化
- 運用機能

## 💰 想定コスト
- **開発**: 無料（自作）
- **サーバー**: $5-10/月（VPS）
- **ドメイン**: $10/年
- **SSL証明書**: 無料（Let's Encrypt）

**総計**: 月額$5-10程度で運用可能