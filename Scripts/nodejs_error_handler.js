#!/usr/bin/env node
/**
 * Node.js Global Error Handler
 * Sub-Agent安定性向上のための統一エラーハンドリング
 *
 * 使用方法:
 * require('./Scripts/nodejs_error_handler.js');
 * または
 * node -r ./Scripts/nodejs_error_handler.js your_script.js
 */

const fs = require('fs');
const path = require('path');

// ログファイル設定
const LOG_DIR = path.join(__dirname, '..', 'Logs');
const ERROR_LOG = path.join(LOG_DIR, 'nodejs_errors.log');

// ログディレクトリが存在しない場合作成
if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
}

/**
 * エラーログ記録関数
 */
function logError(type, error, additionalInfo = {}) {
    const timestamp = new Date().toISOString();
    const errorInfo = {
        timestamp,
        type,
        message: error.message || error,
        stack: error.stack || 'No stack trace',
        pid: process.pid,
        memory: process.memoryUsage(),
        ...additionalInfo
    };

    const logEntry = `[${timestamp}] [${type}] ${JSON.stringify(errorInfo, null, 2)}\n`;

    // ファイルに非同期書き込み
    fs.appendFile(ERROR_LOG, logEntry, (err) => {
        if (err) {
            console.error('Failed to write error log:', err);
        }
    });

    // 重要なエラーはコンソールにも出力
    if (type === 'UNHANDLED_REJECTION' || type === 'UNCAUGHT_EXCEPTION') {
        console.error(`[${type}]`, errorInfo);
    }
}

/**
 * 未処理のPromise拒否ハンドラ
 */
process.on('unhandledRejection', (reason, promise) => {
    logError('UNHANDLED_REJECTION', reason, {
        promise: promise.toString(),
        nodeVersion: process.version,
        platform: process.platform
    });

    // 開発環境では警告表示
    if (process.env.NODE_ENV !== 'production') {
        console.warn('🚨 Unhandled Promise Rejection detected:', reason);
        console.warn('Promise:', promise);
    }
});

/**
 * 未捕捉例外ハンドラ
 */
process.on('uncaughtException', (error) => {
    logError('UNCAUGHT_EXCEPTION', error, {
        nodeVersion: process.version,
        platform: process.platform,
        uptime: process.uptime()
    });

    console.error('🚨 Uncaught Exception:', error);

    // 重大なエラーのため、プロセス終了
    process.exit(1);
});

/**
 * 警告ハンドラ（メモリリーク検知等）
 */
process.on('warning', (warning) => {
    logError('WARNING', warning, {
        warningName: warning.name,
        warningCode: warning.code
    });

    // MaxListenersExceededWarningは特に重要
    if (warning.name === 'MaxListenersExceededWarning') {
        console.warn('🚨 Memory leak potential detected:', warning.message);
    }
});

/**
 * SIGTERM/SIGINTハンドラ（グレースフルシャットダウン）
 */
process.on('SIGTERM', () => {
    logError('PROCESS_SIGNAL', { signal: 'SIGTERM' }, {
        message: 'Process termination requested'
    });
    process.exit(0);
});

process.on('SIGINT', () => {
    logError('PROCESS_SIGNAL', { signal: 'SIGINT' }, {
        message: 'Process interrupted by user'
    });
    process.exit(0);
});

/**
 * プロセス終了ハンドラ
 */
process.on('exit', (code) => {
    const timestamp = new Date().toISOString();
    const exitInfo = `[${timestamp}] [PROCESS_EXIT] Code: ${code}, PID: ${process.pid}\n`;

    // 同期書き込み（プロセス終了前に確実に記録）
    try {
        fs.appendFileSync(ERROR_LOG, exitInfo);
    } catch (err) {
        console.error('Failed to write exit log:', err);
    }
});

/**
 * メモリ使用量監視（開発環境）
 */
if (process.env.NODE_ENV !== 'production') {
    setInterval(() => {
        const usage = process.memoryUsage();
        const heapUsedMB = Math.round(usage.heapUsed / 1024 / 1024);
        const heapTotalMB = Math.round(usage.heapTotal / 1024 / 1024);

        // メモリ使用量が500MB を超えた場合警告
        if (heapUsedMB > 500) {
            logError('MEMORY_WARNING', {
                message: `High memory usage detected: ${heapUsedMB}MB used of ${heapTotalMB}MB total`
            }, usage);
        }
    }, 30000); // 30秒間隔
}

console.log('✅ Node.js Global Error Handler initialized');
console.log(`📝 Error logs will be written to: ${ERROR_LOG}`);

module.exports = {
    logError,
    ERROR_LOG
};
