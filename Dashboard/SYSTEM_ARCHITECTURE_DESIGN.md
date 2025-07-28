# 📐 システムアーキテクチャ設計書

**作成日**: 2025-07-29  
**バージョン**: v1.0  
**Phase**: 1追加タスク（Gemini改善提案対応）

---

## 🏗️ 全体アーキテクチャ

```
┌─────────────────┐    JSON File    ┌──────────────────┐    WebSocket    ┌─────────────────┐
│                 │    Exchange     │                  │    Real-time    │                 │
│   MT5 + EA      │ =============>  │  Flask Dashboard │ =============>  │   Web Browser   │
│  (PositionExp.) │    /tmp/mt5_data│   (File Watch)   │    Updates      │   (Dashboard)   │
│                 │                 │                  │                 │                 │
└─────────────────┘                 └──────────────────┘                 └─────────────────┘
                                               │
                                               │ SQLite
                                               ▼
                                    ┌──────────────────┐
                                    │                  │
                                    │  Data Storage    │
                                    │   (Statistics)   │
                                    │                  │
                                    └──────────────────┘
```

## 📊 データフロー設計

### Phase 1: 基本フロー（現行）
```
MT5 EA → positions.json → watchdog → WebSocket → Browser
```

### Phase 2以降: 拡張フロー
```
MT5 EA → positions.json → Data Validator → SQLite → Statistics Engine → WebSocket → Enhanced UI
```

### データフロー詳細

#### 1. データ生成層 (MT5)
- **MT5 Expert Advisor**: `PositionExporter.mq5`
- **出力形式**: JSON
- **出力先**: `/tmp/mt5_data/positions.json`
- **更新頻度**: 1秒間隔

#### 2. データ取得層 (Python)
- **監視**: `watchdog.FileSystemEventHandler`
- **検知**: ファイル変更イベント
- **読込**: JSON パース

#### 3. データ処理層 (Phase 2+)
- **バリデーション**: 不正データ検知・処理
- **永続化**: SQLite データベース
- **統計計算**: NumPy/Pandas

#### 4. 配信層 (WebSocket)
- **プロトコル**: python-socketio
- **イベント**: position_update, error
- **配信先**: 接続済みクライアント

#### 5. 表示層 (Web UI)
- **フレームワーク**: HTML + JavaScript
- **リアルタイム**: WebSocket受信
- **チャート**: Chart.js (Phase 3+)

---

## 🗃️ データベース設計（SQLite）

### Phase 2導入予定スキーマ

#### 1. positions テーブル
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    ticket INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    type TEXT NOT NULL,           -- 'buy' or 'sell'
    volume REAL NOT NULL,
    profit REAL NOT NULL,
    open_price REAL NOT NULL,
    current_price REAL NOT NULL,
    open_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. account_snapshots テーブル
```sql
CREATE TABLE account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    balance REAL NOT NULL,
    equity REAL NOT NULL,
    profit REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. daily_statistics テーブル
```sql
CREATE TABLE daily_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_profit REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. system_logs テーブル（Phase 3+）
```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    level TEXT NOT NULL,          -- 'INFO', 'WARNING', 'ERROR'
    component TEXT NOT NULL,      -- 'FileWatcher', 'DataValidator', etc.
    message TEXT NOT NULL,
    details TEXT,                 -- JSON詳細情報
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### インデックス設計
```sql
-- パフォーマンス最適化
CREATE INDEX idx_positions_timestamp ON positions(timestamp);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_account_snapshots_timestamp ON account_snapshots(timestamp);
CREATE INDEX idx_daily_statistics_date ON daily_statistics(date);
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_level ON system_logs(level);
```

---

## 🔧 技術スタック

### Phase 1 (現行)
- **Backend**: Python 3.10+
- **Web Framework**: Flask 3.1+
- **WebSocket**: python-socketio 5.13+
- **File Monitoring**: watchdog 6.0+
- **WSGI Server**: eventlet 0.40+

### Phase 2+ (拡張)
- **Database**: SQLite 3
- **Data Processing**: NumPy, Pandas
- **Validation**: Cerberus/Marshmallow
- **Configuration**: PyYAML
- **Logging**: Python logging + JSON

### Phase 3+ (高度機能)
- **Charts**: Chart.js 4.0+
- **Statistics**: SciPy
- **Notifications**: smtplib, requests (webhook)

---

## 📁 ディレクトリ構造

```
Dashboard/
├── app.py                      # メインアプリケーション
├── requirements.txt            # 依存関係
├── config/
│   ├── system_config.yaml     # システム設定（Phase 3+）
│   └── database_schema.sql    # DB初期化スクリプト（Phase 2+）
├── lib/
│   ├── __init__.py
│   ├── data_validator.py      # データ検証（Phase 2+）
│   ├── database.py            # DB操作（Phase 2+）
│   ├── statistics.py          # 統計計算（Phase 2+）
│   └── logger_setup.py        # ログ設定（Phase 3+）
├── static/
│   ├── css/
│   │   └── dashboard.css
│   ├── js/
│   │   ├── dashboard.js
│   │   └── charts.js          # チャート（Phase 3+）
│   └── favicon.ico
├── templates/
│   ├── dashboard.html
│   ├── statistics.html        # 統計ページ（Phase 2+）
│   └── charts.html            # チャートページ（Phase 3+）
├── tests/
│   ├── test_data_validator.py
│   ├── test_database.py
│   └── test_statistics.py
├── legacy_scripts/            # 過去スクリプト（整理後）
│   ├── README.md              # インデックス
│   ├── mt5_analysis/
│   ├── wine_integration/
│   └── statistical_tools/
└── docs/
    ├── SYSTEM_ARCHITECTURE_DESIGN.md  # 本文書
    ├── API_DOCUMENTATION.md           # API仕様（Phase 2+）
    └── DEPLOYMENT_GUIDE.md            # デプロイ手順
```

---

## 🔒 セキュリティ・運用考慮事項

### セキュリティ
- **認証**: 基本認証（Phase 3+）
- **アクセス制御**: IP制限（運用設定）
- **データ保護**: SQLite ファイル権限制限
- **ログ**: 機密情報のマスキング

### 運用
- **モニタリング**: システムリソース監視
- **バックアップ**: SQLite 自動バックアップ（Phase 2+）
- **ローテーション**: ログファイルローテーション
- **ヘルスチェック**: 死活監視エンドポイント

### パフォーマンス
- **メモリ**: 最大使用量制限
- **ディスク**: ログ・DB サイズ制限
- **ネットワーク**: WebSocket接続数制限
- **CPU**: 統計計算の分散処理（Phase 3+）

---

## 🔄 拡張性設計

### 水平拡張
- **マルチEA対応**: 複数EA統合（Phase 4a+）
- **マルチブローカー**: 複数MT5アカウント
- **クラスタリング**: 複数サーバー負荷分散

### 機能拡張
- **API化**: RESTful API（Phase 3+）
- **モバイル**: レスポンシブ対応
- **通知**: 多様な通知チャネル
- **AI統合**: 機械学習分析（Phase 4b）

---

## ✅ 設計完了チェックリスト

- [x] 全体アーキテクチャ図
- [x] データフロー設計
- [x] データベーススキーマ
- [x] 技術スタック選定
- [x] ディレクトリ構造
- [x] セキュリティ考慮事項
- [x] 拡張性設計
- [ ] API仕様書（Phase 2で作成）
- [ ] デプロイ手順書（Phase 1追加で作成）

**設計者**: Claude  
**査読**: Gemini（予定）  
**承認**: kiro（予定）