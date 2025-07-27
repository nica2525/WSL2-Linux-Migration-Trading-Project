# ローカル・サーバーレス ダッシュボード設計

## 🎯 設計方針転換

### ❌ 従来案（要サーバー）
```
VPS/クラウドサーバー + ドメイン + SSL
月額コスト: $5-10
```

### ✅ 新方針（サーバーレス）
```
ローカルFlaskサーバー + ngrok/Tailscale
月額コスト: $0（基本無料）
```

## 🏗️ アーキテクチャ

### システム構成
```
┌─────────────────┬─────────────────┬─────────────────┐
│ MT5 (Wine)      │ Python Backend  │ Web Frontend    │
│                 │                 │                 │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────┐ │
│ │ JamesORB EA │◄┼─┤ PyTrader    │ │ │ React UI    │ │
│ │             │ │ │ WebSocket   │ │ │ + Chart.js  │ │
│ │ WebSocket   │ │ │ Server      │ │ │             │ │
│ │ Server      │ │ └─────────────┘ │ └─────────────┘ │
│ └─────────────┘ │        ▲        │        ▲        │
│                 │        │        │        │        │
└─────────────────┼────────┼────────┼────────┼────────┘
                  │        │        │        │
                  │ ┌─────────────┐ │ ┌─────────────┐
                  │ │ Flask App   │ │ │ ngrok       │
                  │ │ + SocketIO  │ │ │ Tunnel      │
                  │ │             │◄┼─┤ (外部接続)  │
                  │ └─────────────┘ │ └─────────────┘
                  └─────────────────┴─────────────────┘
                     localhost:5000    https://xxx.ngrok.io
```

### データフロー
```
1. MT5 → PyTrader WebSocket → Flask Backend
2. Flask → SocketIO → React Frontend  
3. React → ngrok → スマホ（外出先）
```

## 🛠️ 技術実装

### ベースプロジェクト統合
```python
# mt5_flask をベースに改良
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import MetaTrader5 as mt5
import asyncio
import json

# PyTrader WebSocket通信を統合
from pytrader_client import PyTraderClient

class LocalDashboardServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.mt5_client = PyTraderClient()
        
        # ルート設定
        self.setup_routes()
        self.setup_websocket_handlers()
    
    def setup_routes(self):
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
        
        @self.app.route('/mobile')
        def mobile_dashboard():
            return render_template('mobile_dashboard.html')
        
        @self.app.route('/api/positions')
        def get_positions():
            return self.mt5_client.get_positions()
    
    def setup_websocket_handlers(self):
        @self.socketio.on('request_data')
        def handle_data_request():
            # リアルタイムデータ送信
            data = self.get_realtime_data()
            emit('market_data', data)
        
        @self.socketio.on('close_position')
        def handle_close_position(data):
            result = self.mt5_client.close_position(data['ticket'])
            emit('position_closed', result)
    
    def get_realtime_data(self):
        return {
            'timestamp': datetime.now().isoformat(),
            'positions': self.mt5_client.get_positions(),
            'account_info': self.mt5_client.get_account_info(),
            'market_data': self.mt5_client.get_market_data()
        }
    
    def run(self):
        # ngrok統合
        from pyngrok import ngrok
        
        # ローカルサーバー起動
        public_url = ngrok.connect(5000)
        print(f"Dashboard URL: {public_url}")
        print(f"Local URL: http://localhost:5000")
        
        self.socketio.run(self.app, host='0.0.0.0', port=5000)
```

### フロントエンド（タブ切り替え対応）
```javascript
// React + Socket.IO
import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [data, setData] = useState({});
  
  useEffect(() => {
    const socket = io();
    
    socket.on('market_data', (newData) => {
      setData(newData);
    });
    
    // 1秒間隔でデータ要求
    const interval = setInterval(() => {
      socket.emit('request_data');
    }, 1000);
    
    return () => {
      clearInterval(interval);
      socket.disconnect();
    };
  }, []);
  
  // スマホ画面（タブ切り替え）
  if (isMobile) {
    return (
      <div className="mobile-dashboard">
        {/* タブナビゲーション */}
        <nav className="tab-nav">
          <button 
            className={activeTab === 'overview' ? 'active' : ''}
            onClick={() => setActiveTab('overview')}
          >
            📊 概要
          </button>
          <button 
            className={activeTab === 'positions' ? 'active' : ''}
            onClick={() => setActiveTab('positions')}
          >
            💼 ポジション
          </button>
          <button 
            className={activeTab === 'chart' ? 'active' : ''}
            onClick={() => setActiveTab('chart')}
          >
            📈 チャート
          </button>
          <button 
            className={activeTab === 'full' ? 'active' : ''}
            onClick={() => setActiveTab('full')}
          >
            🖥️ フル画面
          </button>
        </nav>
        
        {/* タブコンテンツ */}
        <div className="tab-content">
          {activeTab === 'overview' && <OverviewTab data={data} />}
          {activeTab === 'positions' && <PositionsTab data={data} />}
          {activeTab === 'chart' && <ChartTab data={data} />}
          {activeTab === 'full' && <FullDesktopView data={data} />}
        </div>
      </div>
    );
  }
  
  // デスクトップ画面（フル機能）
  return <DesktopDashboard data={data} />;
};

// スマホ用コンパクトビュー
const OverviewTab = ({ data }) => (
  <div className="overview-tab">
    <div className="status-card">
      <h3>🔴 JamesORB EA - LIVE</h3>
      <p>EURUSD: {data.market?.price} {data.market?.trend}</p>
    </div>
    
    <div className="stats-grid">
      <div className="stat">
        <span>ポジション</span>
        <strong>{data.positions?.length || 0}</strong>
      </div>
      <div className="stat">
        <span>今日の利益</span>
        <strong className="profit">+${data.stats?.daily_profit}</strong>
      </div>
      <div className="stat">
        <span>勝率</span>
        <strong>{data.stats?.win_rate}%</strong>
      </div>
    </div>
  </div>
);

// フル機能ビュー（スマホでも表示可能）
const FullDesktopView = ({ data }) => (
  <div className="full-desktop-view">
    <div className="desktop-grid">
      <StatusPanel data={data} />
      <PricePanel data={data} />
      <ChartPanel data={data} />
      <PositionsPanel data={data} />
      <TradesPanel data={data} />
      <LogsPanel data={data} />
    </div>
  </div>
);
```

## 🌐 外部アクセス（サーバーレス）

### 1. ngrok（推奨）
```python
# 無料プラン
from pyngrok import ngrok

# HTTPSトンネル自動作成
public_url = ngrok.connect(5000)
print(f"外部URL: {public_url}")  # https://abc123.ngrok.io

# QRコード生成してスマホで簡単アクセス
import qrcode
qr = qrcode.make(public_url)
qr.save('dashboard_qr.png')
```

### 2. Tailscale（高セキュリティ）
```bash
# VPN経由での安全アクセス
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# プライベートIP経由でアクセス
# http://100.64.1.2:5000
```

### 3. LocalTunnel（代替案）
```bash
npm install -g localtunnel
lt --port 5000 --subdomain my-trading-dashboard
# https://my-trading-dashboard.loca.lt
```

## 📱 スマホ対応仕様

### PWA化
```javascript
// manifest.json
{
  "name": "JamesORB Dashboard",
  "short_name": "EA Monitor",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#1976d2",
  "background_color": "#ffffff",
  "icons": [
    {
      "src": "icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}

// Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('dashboard-v1').then(cache => {
      return cache.addAll([
        '/',
        '/static/css/dashboard.css',
        '/static/js/dashboard.js'
      ]);
    })
  );
});
```

### レスポンシブCSS
```css
/* スマホ最適化 */
.mobile-dashboard {
  height: 100vh;
  overflow: hidden;
}

.tab-nav {
  display: flex;
  justify-content: space-around;
  background: #f5f5f5;
  padding: 8px;
}

.tab-nav button {
  flex: 1;
  padding: 12px 8px;
  border: none;
  background: transparent;
  font-size: 12px;
}

.tab-nav button.active {
  background: #1976d2;
  color: white;
  border-radius: 8px;
}

/* デスクトップ時はタブ非表示 */
@media (min-width: 768px) {
  .tab-nav { display: none; }
  .full-desktop-view { display: block !important; }
}
```

## 🚀 実装ロードマップ

### Phase 1: ローカル基盤 (1週間)
1. PyTrader統合でMT5通信確立
2. Flask + SocketIO基本実装
3. 基本的なWeb UI作成

### Phase 2: モバイル対応 (1週間)
1. レスポンシブデザイン実装
2. タブ切り替え機能
3. PWA化

### Phase 3: 外部アクセス (2-3日)
1. ngrok統合・自動化
2. QRコード生成
3. セキュリティ設定

## 💰 コスト
- **開発**: 無料（既存プロジェクト活用）
- **運用**: 無料（ngrok無料プラン）
- **月額**: $0

## 🔒 セキュリティ
- ngrok Basic認証
- ローカル実行（データ外部流出なし）
- VPN経由アクセス（Tailscale）

---

**結論**: 既存プロジェクトをベースに、サーバーレスでコスト0の実用的ダッシュボードが構築可能！