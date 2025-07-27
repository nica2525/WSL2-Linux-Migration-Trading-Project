-- Phase 3 データベーススキーマ拡張
-- 実行日: 2025-07-28
-- 目的: 実データ統合・高度統計分析対応

-- 既存テーブルの拡張
ALTER TABLE account_history ADD COLUMN server_time DATETIME;
ALTER TABLE account_history ADD COLUMN trade_allowed BOOLEAN DEFAULT 1;
ALTER TABLE account_history ADD COLUMN trade_expert BOOLEAN DEFAULT 1;
ALTER TABLE account_history ADD COLUMN margin_so_mode INTEGER DEFAULT 0;
ALTER TABLE account_history ADD COLUMN margin_so_call REAL DEFAULT 0;
ALTER TABLE account_history ADD COLUMN margin_so_so REAL DEFAULT 0;
ALTER TABLE account_history ADD COLUMN currency_digits INTEGER DEFAULT 2;
ALTER TABLE account_history ADD COLUMN fifo_close BOOLEAN DEFAULT 0;

-- ポジション詳細履歴テーブル
CREATE TABLE IF NOT EXISTS position_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    symbol VARCHAR(10) NOT NULL,
    type INTEGER NOT NULL,
    volume REAL NOT NULL,
    price_open REAL NOT NULL,
    price_current REAL,
    sl REAL DEFAULT 0,
    tp REAL DEFAULT 0,
    profit REAL NOT NULL,
    swap REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    magic INTEGER DEFAULT 0,
    comment TEXT,
    identifier INTEGER,
    reason INTEGER DEFAULT 0,
    external_id VARCHAR(50)
);

-- 統計分析結果テーブル
CREATE TABLE IF NOT EXISTS statistics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculation_date DATE NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    gross_profit REAL DEFAULT 0,
    gross_loss REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    expected_payoff REAL DEFAULT 0,
    absolute_drawdown REAL DEFAULT 0,
    maximal_drawdown REAL DEFAULT 0,
    relative_drawdown REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    sortino_ratio REAL DEFAULT 0,
    calmar_ratio REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(calculation_date, period_type)
);

-- システム監視ログテーブル
CREATE TABLE IF NOT EXISTS system_monitoring (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    component VARCHAR(50) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value REAL NOT NULL,
    status VARCHAR(20) DEFAULT 'normal',
    message TEXT
);

-- インデックス最適化
CREATE INDEX IF NOT EXISTS idx_position_details_timestamp ON position_details(timestamp);
CREATE INDEX IF NOT EXISTS idx_position_details_ticket ON position_details(ticket);
CREATE INDEX IF NOT EXISTS idx_statistics_cache_date_type ON statistics_cache(calculation_date, period_type);
CREATE INDEX IF NOT EXISTS idx_system_monitoring_timestamp ON system_monitoring(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_monitoring_component ON system_monitoring(component);

-- 既存インデックスの確認・作成（重複エラー回避）
CREATE INDEX IF NOT EXISTS idx_account_timestamp ON account_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_position_timestamp ON position_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_ea_timestamp ON ea_status(timestamp);