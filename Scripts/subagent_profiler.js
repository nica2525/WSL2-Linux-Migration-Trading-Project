#!/usr/bin/env node
/**
 * Sub-Agent実行プロファイラー
 * clinic.jsを使用してSub-Agent実行時のメモリ・CPU使用量を監視
 * 循環参照・メモリリーク検出機能付き
 */

const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');
const { promisify } = require('util');

// エラーハンドラをロード
require('./nodejs_error_handler.js');

const execAsync = promisify(exec);

// 設定
const CONFIG = {
    PROJECT_DIR: path.join(__dirname, '..'),
    PROFILE_DIR: path.join(__dirname, '..', 'Logs', 'profiles'),
    LOG_FILE: path.join(__dirname, '..', 'Logs', 'subagent_profiler.log'),
    TIMEOUT_MS: 300000, // 5分タイムアウト
    MEMORY_THRESHOLD_MB: 500, // メモリ警告閥値
    HEAP_DUMP_THRESHOLD_MB: 1000 // ヒープダンプ作成閾値
};

// ログ出力関数
function log(level, message, data = {}) {
    const timestamp = new Date().toISOString();
    const logEntry = {
        timestamp,
        level,
        message,
        pid: process.pid,
        memoryUsage: process.memoryUsage(),
        ...data
    };

    const logLine = `[${timestamp}] [${level}] ${message} ${JSON.stringify(data)}\n`;

    // ファイルログ
    fs.appendFileSync(CONFIG.LOG_FILE, logLine);

    // コンソール出力
    if (level === 'ERROR' || level === 'WARNING') {
        console.error(logLine.trim());
    } else {
        console.log(logLine.trim());
    }
}

// プロファイルディレクトリ作成
function ensureProfileDir() {
    if (!fs.existsSync(CONFIG.PROFILE_DIR)) {
        fs.mkdirSync(CONFIG.PROFILE_DIR, { recursive: true });
        log('INFO', 'Profile directory created', { dir: CONFIG.PROFILE_DIR });
    }
}

// メモリ使用量監視
function startMemoryMonitoring(targetPid) {
    const interval = setInterval(() => {
        try {
            const usage = process.memoryUsage();
            const heapUsedMB = Math.round(usage.heapUsed / 1024 / 1024);
            const heapTotalMB = Math.round(usage.heapTotal / 1024 / 1024);

            log('INFO', 'Memory usage', {
                pid: targetPid,
                heapUsedMB,
                heapTotalMB,
                rss: Math.round(usage.rss / 1024 / 1024),
                external: Math.round(usage.external / 1024 / 1024)
            });

            // メモリ警告
            if (heapUsedMB > CONFIG.MEMORY_THRESHOLD_MB) {
                log('WARNING', 'High memory usage detected', {
                    heapUsedMB,
                    threshold: CONFIG.MEMORY_THRESHOLD_MB
                });
            }

            // ヒープダンプ作成
            if (heapUsedMB > CONFIG.HEAP_DUMP_THRESHOLD_MB) {
                createHeapDump(targetPid);
            }

        } catch (error) {
            log('ERROR', 'Memory monitoring error', { error: error.message });
        }
    }, 10000); // 10秒間隔

    return interval;
}

// ヒープダンプ作成
async function createHeapDump(pid) {
    try {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const dumpFile = path.join(CONFIG.PROFILE_DIR, `heap-${pid}-${timestamp}.heapsnapshot`);

        // Node.js内蔵のheapdump機能を使用
        const heapdump = require('v8').writeHeapSnapshot;
        const filename = heapdump(dumpFile);

        log('INFO', 'Heap dump created', {
            file: filename,
            pid: pid,
            size: fs.statSync(filename).size
        });

        return filename;
    } catch (error) {
        log('ERROR', 'Failed to create heap dump', { error: error.message });
        return null;
    }
}

// プロセス監視
function monitorProcess(pid, timeout = CONFIG.TIMEOUT_MS) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        let isResolved = false;

        // メモリ監視開始
        const memoryInterval = startMemoryMonitoring(pid);

        // プロセス存在確認
        const checkInterval = setInterval(() => {
            try {
                process.kill(pid, 0); // プロセス存在確認（シグナル送信なし）

                const elapsed = Date.now() - startTime;
                if (elapsed > timeout) {
                    clearInterval(checkInterval);
                    clearInterval(memoryInterval);

                    if (!isResolved) {
                        isResolved = true;
                        log('WARNING', 'Process monitoring timeout', {
                            pid,
                            elapsed,
                            timeout
                        });
                        resolve({ status: 'timeout', elapsed });
                    }
                }
            } catch (error) {
                // プロセス終了
                clearInterval(checkInterval);
                clearInterval(memoryInterval);

                if (!isResolved) {
                    isResolved = true;
                    const elapsed = Date.now() - startTime;
                    log('INFO', 'Process completed', {
                        pid,
                        elapsed,
                        exitReason: error.code
                    });
                    resolve({ status: 'completed', elapsed });
                }
            }
        }, 1000); // 1秒間隔

        // 緊急停止用タイムアウト
        setTimeout(() => {
            clearInterval(checkInterval);
            clearInterval(memoryInterval);

            if (!isResolved) {
                isResolved = true;
                log('ERROR', 'Hard timeout reached', { pid, timeout });
                reject(new Error(`Process monitoring hard timeout: ${timeout}ms`));
            }
        }, timeout + 30000); // タイムアウト + 30秒
    });
}

// Clinic.js Doctor実行
async function runClinicDoctor(command, args = []) {
    return new Promise((resolve, reject) => {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const outputDir = path.join(CONFIG.PROFILE_DIR, `doctor-${timestamp}`);

        log('INFO', 'Starting clinic doctor', {
            command,
            args,
            outputDir
        });

        const clinicArgs = [
            'doctor',
            '--dest', outputDir,
            '--on-port', 'echo Profile started on port',
            command,
            ...args
        ];

        const clinicProcess = spawn('clinic', clinicArgs, {
            stdio: ['pipe', 'pipe', 'pipe'],
            cwd: CONFIG.PROJECT_DIR
        });

        let stdout = '';
        let stderr = '';

        clinicProcess.stdout.on('data', (data) => {
            stdout += data.toString();
            log('INFO', 'Clinic stdout', { data: data.toString().trim() });
        });

        clinicProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            log('WARNING', 'Clinic stderr', { data: data.toString().trim() });
        });

        clinicProcess.on('close', (code) => {
            log('INFO', 'Clinic doctor completed', {
                code,
                outputDir,
                stdoutLength: stdout.length,
                stderrLength: stderr.length
            });

            resolve({
                code,
                stdout,
                stderr,
                outputDir
            });
        });

        clinicProcess.on('error', (error) => {
            log('ERROR', 'Clinic doctor error', { error: error.message });
            reject(error);
        });

        // タイムアウト監視
        setTimeout(() => {
            if (clinicProcess.pid) {
                log('WARNING', 'Clinic doctor timeout, killing process', {
                    pid: clinicProcess.pid
                });
                clinicProcess.kill('SIGKILL');
                reject(new Error('Clinic doctor timeout'));
            }
        }, CONFIG.TIMEOUT_MS);
    });
}

// メイン実行関数
async function main() {
    log('INFO', 'Sub-Agent Profiler started', {
        config: CONFIG,
        nodeVersion: process.version,
        platform: process.platform
    });

    ensureProfileDir();

    // 使用例: Node.jsスクリプトのプロファイリング
    if (process.argv.length > 2) {
        const targetScript = process.argv[2];
        const scriptArgs = process.argv.slice(3);

        try {
            log('INFO', 'Starting profiling session', {
                script: targetScript,
                args: scriptArgs
            });

            const result = await runClinicDoctor('node', [targetScript, ...scriptArgs]);

            log('INFO', 'Profiling completed', {
                result: {
                    code: result.code,
                    outputDir: result.outputDir
                }
            });

            console.log(`\n✅ Profiling completed!`);
            console.log(`📊 Results: ${result.outputDir}`);
            console.log(`📝 Log: ${CONFIG.LOG_FILE}`);

        } catch (error) {
            log('ERROR', 'Profiling failed', { error: error.message });
            console.error(`❌ Profiling failed: ${error.message}`);
            process.exit(1);
        }
    } else {
        console.log('Usage: node subagent_profiler.js <script> [args...]');
        console.log('Example: node subagent_profiler.js test_script.js');
        process.exit(1);
    }
}

// エラーハンドリング
process.on('uncaughtException', (error) => {
    log('ERROR', 'Uncaught exception in profiler', { error: error.message, stack: error.stack });
    process.exit(1);
});

process.on('unhandledRejection', (reason) => {
    log('ERROR', 'Unhandled rejection in profiler', { reason: reason?.message || reason });
    process.exit(1);
});

// 実行
if (require.main === module) {
    main().catch(error => {
        log('ERROR', 'Main execution failed', { error: error.message });
        process.exit(1);
    });
}

module.exports = {
    runClinicDoctor,
    monitorProcess,
    createHeapDump,
    log
};
