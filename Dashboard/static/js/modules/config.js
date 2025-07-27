/**
 * 設定モジュール - Phase 2-B
 * グローバル設定と定数を管理
 */

export const config = {
    // WebSocket設定
    socket: {
        reconnectDelay: 5000,
        maxReconnectAttempts: 10
    },
    
    // 更新間隔設定
    update: {
        activeInterval: 5000,    // アクティブ時: 5秒
        inactiveInterval: 10000, // 非アクティブ時: 10秒
        inactiveThreshold: 60000 // 非アクティブ判定: 1分
    },
    
    // チャート設定
    chart: {
        maxDataPoints: 144,      // 24時間分（10分間隔想定）
        updateAnimation: 'none'  // パフォーマンス重視
    },
    
    // アラート設定（デフォルト値）
    alerts: {
        marginLevel: {
            critical: 150,
            warning: 300
        },
        drawdown: {
            critical: 25,
            warning: 15
        },
        positionLoss: {
            critical: -50000,
            warning: -20000
        },
        cooldownPeriod: 60000    // 1分間のクールダウン
    },
    
    // 統計色分け閾値
    statistics: {
        winRate: {
            good: 60,
            warning: 40
        },
        profitFactor: {
            good: 1.5,
            warning: 1.0
        },
        drawdown: {
            good: 10,
            warning: 25
        }
    }
};

// ユーザー設定の読み込み・保存
export const userSettings = {
    load() {
        const saved = localStorage.getItem('dashboardSettings');
        if (saved) {
            try {
                const settings = JSON.parse(saved);
                // アラート設定をマージ
                if (settings.alerts) {
                    Object.assign(config.alerts, settings.alerts);
                }
                return settings;
            } catch (e) {
                console.error('設定読み込みエラー:', e);
            }
        }
        return null;
    },
    
    save(settings) {
        try {
            localStorage.setItem('dashboardSettings', JSON.stringify(settings));
            // 設定をconfigにマージ
            if (settings.alerts) {
                Object.assign(config.alerts, settings.alerts);
            }
            return true;
        } catch (e) {
            console.error('設定保存エラー:', e);
            return false;
        }
    }
};

// 初期化時にユーザー設定を読み込み
userSettings.load();

// アラート設定の初期値をUIに反映する関数
export function loadSettingsToUI() {
    const marginCritical = document.getElementById('marginCritical');
    const marginWarning = document.getElementById('marginWarning');
    const ddCritical = document.getElementById('ddCritical');
    const ddWarning = document.getElementById('ddWarning');
    const lossCritical = document.getElementById('lossCritical');
    const lossWarning = document.getElementById('lossWarning');
    
    if (marginCritical) marginCritical.value = config.alerts.marginLevel.critical;
    if (marginWarning) marginWarning.value = config.alerts.marginLevel.warning;
    if (ddCritical) ddCritical.value = config.alerts.drawdown.critical;
    if (ddWarning) ddWarning.value = config.alerts.drawdown.warning;
    if (lossCritical) lossCritical.value = config.alerts.positionLoss.critical;
    if (lossWarning) lossWarning.value = config.alerts.positionLoss.warning;
}