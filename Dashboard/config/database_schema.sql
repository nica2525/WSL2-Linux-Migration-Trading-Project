-- =====================================================
-- Trading Dashboard Database Schema
-- Version: 1.0
-- Created: 2025-07-29
-- Phase: 2+ (SQLite Integration)
-- =====================================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- =====================================================
-- Core Trading Data Tables
-- =====================================================

-- Position data from MT5
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    ticket INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('buy', 'sell')),
    volume REAL NOT NULL CHECK (volume > 0),
    profit REAL NOT NULL,
    open_price REAL NOT NULL CHECK (open_price > 0),
    current_price REAL NOT NULL CHECK (current_price > 0),
    open_time DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Account snapshots for equity curve tracking
CREATE TABLE IF NOT EXISTS account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    balance REAL NOT NULL CHECK (balance >= 0),
    equity REAL NOT NULL CHECK (equity >= 0),
    profit REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Daily aggregated statistics
CREATE TABLE IF NOT EXISTS daily_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    total_trades INTEGER DEFAULT 0 CHECK (total_trades >= 0),
    winning_trades INTEGER DEFAULT 0 CHECK (winning_trades >= 0),
    losing_trades INTEGER DEFAULT 0 CHECK (losing_trades >= 0),
    total_profit REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0 CHECK (max_drawdown <= 0),
    win_rate REAL DEFAULT 0 CHECK (win_rate >= 0 AND win_rate <= 1),
    profit_factor REAL DEFAULT 0 CHECK (profit_factor >= 0),
    sharpe_ratio REAL DEFAULT 0,
    sortino_ratio REAL DEFAULT 0,
    calmar_ratio REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- System Management Tables (Phase 3+)
-- =====================================================

-- System logs for monitoring and debugging
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    component TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT, -- JSON formatted detailed information
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Configuration parameters
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('string', 'integer', 'float', 'boolean', 'json')),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alert configurations and history
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('drawdown', 'profit_threshold', 'loss_threshold', 'system_error')),
    threshold_value REAL,
    is_active BOOLEAN DEFAULT 1,
    last_triggered DATETIME,
    trigger_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alert history log
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    triggered_at DATETIME NOT NULL,
    trigger_value REAL,
    message TEXT,
    notified BOOLEAN DEFAULT 0,
    FOREIGN KEY (alert_id) REFERENCES alerts (id)
);

-- =====================================================
-- Performance Optimization Indexes
-- =====================================================

-- Positions table indexes
CREATE INDEX IF NOT EXISTS idx_positions_timestamp ON positions(timestamp);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_type ON positions(type);
CREATE INDEX IF NOT EXISTS idx_positions_open_time ON positions(open_time);
CREATE INDEX IF NOT EXISTS idx_positions_ticket ON positions(ticket);

-- Account snapshots indexes
CREATE INDEX IF NOT EXISTS idx_account_snapshots_timestamp ON account_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_account_snapshots_date ON account_snapshots(date(timestamp));

-- Daily statistics indexes
CREATE INDEX IF NOT EXISTS idx_daily_statistics_date ON daily_statistics(date);

-- System logs indexes
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);

-- System config indexes
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(key);

-- Alert indexes
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at ON alert_history(triggered_at);

-- =====================================================
-- Initial Configuration Data
-- =====================================================

-- Default system configuration
INSERT OR IGNORE INTO system_config (key, value, data_type, description) VALUES
('app_version', '1.0.0', 'string', 'Application version'),
('max_log_retention_days', '30', 'integer', 'Maximum days to retain system logs'),
('statistics_calculation_interval', '3600', 'integer', 'Statistics calculation interval in seconds'),
('websocket_heartbeat_interval', '30', 'integer', 'WebSocket heartbeat interval in seconds'),
('default_drawdown_threshold', '0.05', 'float', 'Default maximum drawdown threshold (5%)'),
('default_profit_threshold', '1000', 'float', 'Default profit alert threshold'),
('enable_email_notifications', 'false', 'boolean', 'Enable email notifications for alerts'),
('enable_webhook_notifications', 'false', 'boolean', 'Enable webhook notifications for alerts');

-- Default alert configurations
INSERT OR IGNORE INTO alerts (alert_type, threshold_value, is_active) VALUES
('drawdown', 0.05, 1),           -- 5% drawdown alert
('profit_threshold', 1000, 1),   -- 1000 profit alert
('loss_threshold', -500, 1);     -- -500 loss alert

-- =====================================================
-- Views for Common Queries
-- =====================================================

-- Current position summary
CREATE VIEW IF NOT EXISTS v_current_positions AS
SELECT 
    p.*,
    (current_price - open_price) * volume * 
    CASE WHEN type = 'buy' THEN 1 ELSE -1 END as unrealized_pnl
FROM positions p
WHERE timestamp = (
    SELECT MAX(timestamp) 
    FROM positions p2 
    WHERE p2.ticket = p.ticket
);

-- Daily performance summary
CREATE VIEW IF NOT EXISTS v_daily_performance AS
SELECT 
    DATE(timestamp) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    MAX(profit) as best_trade,
    MIN(profit) as worst_trade,
    CAST(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as win_rate
FROM positions 
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;

-- Weekly performance summary
CREATE VIEW IF NOT EXISTS v_weekly_performance AS
SELECT 
    strftime('%Y-W%W', timestamp) as week,
    COUNT(*) as total_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    CAST(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as win_rate
FROM positions 
GROUP BY strftime('%Y-W%W', timestamp)
ORDER BY week DESC;

-- Monthly performance summary
CREATE VIEW IF NOT EXISTS v_monthly_performance AS
SELECT 
    strftime('%Y-%m', timestamp) as month,
    COUNT(*) as total_trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    CAST(SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as win_rate
FROM positions 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY month DESC;

-- =====================================================
-- Triggers for Data Integrity
-- =====================================================

-- Update daily_statistics when positions are inserted/updated
CREATE TRIGGER IF NOT EXISTS update_daily_stats_on_position_insert
AFTER INSERT ON positions
BEGIN
    INSERT OR REPLACE INTO daily_statistics (
        date, total_trades, winning_trades, losing_trades, total_profit, updated_at
    )
    SELECT 
        DATE(NEW.timestamp),
        COUNT(*),
        SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END),
        SUM(profit),
        CURRENT_TIMESTAMP
    FROM positions 
    WHERE DATE(timestamp) = DATE(NEW.timestamp);
END;

-- Update updated_at timestamp on system_config changes
CREATE TRIGGER IF NOT EXISTS update_system_config_timestamp
AFTER UPDATE ON system_config
BEGIN
    UPDATE system_config 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE key = NEW.key;
END;

-- =====================================================
-- Utility Functions (Phase 3+)
-- =====================================================

-- Note: SQLite doesn't support stored procedures
-- The following functions should be implemented in Python:
-- - calculate_sharpe_ratio()
-- - calculate_sortino_ratio()
-- - calculate_calmar_ratio()
-- - calculate_maximum_drawdown()
-- - calculate_profit_factor()

-- =====================================================
-- Database Maintenance
-- =====================================================

-- Log cleanup (to be executed periodically)
-- DELETE FROM system_logs WHERE created_at < datetime('now', '-30 days');

-- Vacuum command for database optimization
-- VACUUM;

-- Analyze command for query optimization
-- ANALYZE;

-- =====================================================
-- Schema Version Management
-- =====================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT OR IGNORE INTO schema_migrations (version, description) VALUES
('1.0.0', 'Initial schema creation with core trading tables'),
('1.1.0', 'Added system management tables and alerts'),
('1.2.0', 'Added views and triggers for data integrity');

-- =====================================================
-- End of Schema Definition
-- =====================================================