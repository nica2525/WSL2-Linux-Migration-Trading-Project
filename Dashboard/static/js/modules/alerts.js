/**
 * アラートモジュール - Phase 2-B
 * アラート管理とユーザー設定機能
 */

import { config, userSettings } from './config.js';

export class AlertManager {
    constructor() {
        this.lastAlertTime = {};
        this.audioContext = null;
        this.settings = {
            soundEnabled: false,
            vibrationEnabled: true,
            ...this.loadSettings()
        };
    }
    
    /**
     * 設定を読み込み
     */
    loadSettings() {
        const soundEnabled = localStorage.getItem('soundNotification') === 'true';
        const vibrationEnabled = localStorage.getItem('vibrationEnabled') !== 'false';
        return { soundEnabled, vibrationEnabled };
    }
    
    /**
     * 設定を保存
     * @param {Object} settings - 設定オブジェクト
     */
    saveSettings(settings) {
        Object.assign(this.settings, settings);
        localStorage.setItem('soundNotification', this.settings.soundEnabled);
        localStorage.setItem('vibrationEnabled', this.settings.vibrationEnabled);
    }
    
    /**
     * アラートをチェック
     * @param {Object} accountData - 口座データ
     * @param {Array} positions - ポジション配列
     */
    check(accountData, positions) {
        if (!accountData) return;
        
        const now = Date.now();
        const alerts = [];
        
        // 証拠金維持率チェック
        if (accountData.margin_level) {
            const marginAlert = this.checkMarginLevel(accountData.margin_level, now);
            if (marginAlert) alerts.push(marginAlert);
        }
        
        // ドローダウンチェック（外部から渡される必要あり）
        if (accountData.currentDrawdown !== undefined) {
            const ddAlert = this.checkDrawdown(accountData.currentDrawdown, now);
            if (ddAlert) alerts.push(ddAlert);
        }
        
        // ポジション損失チェック
        if (positions && positions.length > 0) {
            const positionAlerts = this.checkPositionLoss(positions, now);
            alerts.push(...positionAlerts);
        }
        
        // アラート発火
        alerts.forEach(alert => this.trigger(alert));
        
        return alerts;
    }
    
    /**
     * 証拠金維持率をチェック
     * @param {number} marginLevel - 証拠金維持率
     * @param {number} now - 現在時刻
     * @returns {Object|null} アラートオブジェクト
     */
    checkMarginLevel(marginLevel, now) {
        const alertKey = 'marginLevel';
        
        if (marginLevel <= config.alerts.marginLevel.critical) {
            if (this.canAlert(alertKey + '_critical', now)) {
                return {
                    type: 'critical',
                    key: alertKey + '_critical',
                    message: `🚨 証拠金維持率が危険レベルです: ${marginLevel.toFixed(1)}%`,
                    value: marginLevel
                };
            }
        } else if (marginLevel <= config.alerts.marginLevel.warning) {
            if (this.canAlert(alertKey + '_warning', now)) {
                return {
                    type: 'warning',
                    key: alertKey + '_warning',
                    message: `⚠️ 証拠金維持率が低下しています: ${marginLevel.toFixed(1)}%`,
                    value: marginLevel
                };
            }
        }
        
        return null;
    }
    
    /**
     * ドローダウンをチェック
     * @param {number} drawdown - ドローダウン率
     * @param {number} now - 現在時刻
     * @returns {Object|null} アラートオブジェクト
     */
    checkDrawdown(drawdown, now) {
        const alertKey = 'drawdown';
        
        if (drawdown >= config.alerts.drawdown.critical) {
            if (this.canAlert(alertKey + '_critical', now)) {
                return {
                    type: 'critical',
                    key: alertKey + '_critical',
                    message: `🚨 ドローダウンが危険レベルです: ${drawdown.toFixed(1)}%`,
                    value: drawdown
                };
            }
        } else if (drawdown >= config.alerts.drawdown.warning) {
            if (this.canAlert(alertKey + '_warning', now)) {
                return {
                    type: 'warning',
                    key: alertKey + '_warning',
                    message: `⚠️ ドローダウンが増加しています: ${drawdown.toFixed(1)}%`,
                    value: drawdown
                };
            }
        }
        
        return null;
    }
    
    /**
     * ポジション損失をチェック
     * @param {Array} positions - ポジション配列
     * @param {number} now - 現在時刻
     * @returns {Array} アラート配列
     */
    checkPositionLoss(positions, now) {
        const alerts = [];
        
        positions.forEach(position => {
            const profit = position.profit || 0;
            
            if (profit <= config.alerts.positionLoss.critical) {
                const alertKey = `positionLoss_${position.ticket}_critical`;
                if (this.canAlert(alertKey, now)) {
                    alerts.push({
                        type: 'critical',
                        key: alertKey,
                        message: `🚨 大きな損失ポジション: ${position.symbol} ${this.formatCurrency(profit)}`,
                        value: profit,
                        position: position
                    });
                }
            } else if (profit <= config.alerts.positionLoss.warning) {
                const alertKey = `positionLoss_${position.ticket}_warning`;
                if (this.canAlert(alertKey, now)) {
                    alerts.push({
                        type: 'warning',
                        key: alertKey,
                        message: `⚠️ 損失拡大: ${position.symbol} ${this.formatCurrency(profit)}`,
                        value: profit,
                        position: position
                    });
                }
            }
        });
        
        return alerts;
    }
    
    /**
     * アラート発火可能かチェック
     * @param {string} key - アラートキー
     * @param {number} now - 現在時刻
     * @returns {boolean} 発火可能か
     */
    canAlert(key, now) {
        if (!this.lastAlertTime[key]) {
            this.lastAlertTime[key] = now;
            return true;
        }
        
        if (now - this.lastAlertTime[key] > config.alerts.cooldownPeriod) {
            this.lastAlertTime[key] = now;
            return true;
        }
        
        return false;
    }
    
    /**
     * アラートを発火
     * @param {Object} alert - アラートオブジェクト
     */
    trigger(alert) {
        // 通知表示
        this.showNotification(alert.message, alert.type);
        
        // 音声通知
        if (this.settings.soundEnabled) {
            this.playSound(alert.type);
        }
        
        // バイブレーション
        if (this.settings.vibrationEnabled && 'vibrate' in navigator) {
            this.vibrate(alert.type);
        }
        
        // コンソールログ
        console.log(`[ALERT ${alert.type.toUpperCase()}] ${alert.message}`);
        
        // カスタムイベント発火
        window.dispatchEvent(new CustomEvent('dashboardAlert', { detail: alert }));
    }
    
    /**
     * 通知を表示
     * @param {string} message - メッセージ
     * @param {string} type - タイプ
     */
    showNotification(message, type) {
        const notification = document.getElementById('notification');
        if (notification) {
            notification.textContent = message;
            notification.className = `notification ${type === 'critical' ? 'error' : 'warning'}`;
            notification.classList.add('show');
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
    }
    
    /**
     * アラート音を再生
     * @param {string} type - アラートタイプ
     */
    playSound(type) {
        try {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            if (type === 'critical') {
                oscillator.frequency.setValueAtTime(800, this.audioContext.currentTime);
                oscillator.frequency.setValueAtTime(400, this.audioContext.currentTime + 0.1);
                gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.5);
            } else {
                oscillator.frequency.setValueAtTime(600, this.audioContext.currentTime);
                gainNode.gain.setValueAtTime(0.2, this.audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.3);
            }
            
            oscillator.type = 'sine';
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + (type === 'critical' ? 0.5 : 0.3));
            
        } catch (error) {
            console.log('音声再生エラー:', error);
        }
    }
    
    /**
     * バイブレーション
     * @param {string} type - アラートタイプ
     */
    vibrate(type) {
        if (type === 'critical') {
            navigator.vibrate([200, 100, 200, 100, 200]);
        } else {
            navigator.vibrate([100, 50, 100]);
        }
    }
    
    /**
     * 通貨フォーマット
     * @param {number} num - 数値
     * @returns {string} フォーマット済み文字列
     */
    formatCurrency(num) {
        if (!num) return '¥0';
        const formatted = new Intl.NumberFormat('ja-JP').format(Math.round(num));
        return (num >= 0 ? '+' : '') + '¥' + formatted;
    }
    
    /**
     * アラート設定UI要素を生成
     * @returns {HTMLElement} 設定UI要素
     */
    createSettingsUI() {
        const container = document.createElement('div');
        container.className = 'alert-settings';
        container.innerHTML = `
            <h4>アラート設定</h4>
            <div class="setting-group">
                <h5>証拠金維持率</h5>
                <label>
                    危険レベル: <input type="number" id="marginCritical" value="${config.alerts.marginLevel.critical}" min="0" max="1000">%
                </label>
                <label>
                    警告レベル: <input type="number" id="marginWarning" value="${config.alerts.marginLevel.warning}" min="0" max="1000">%
                </label>
            </div>
            <div class="setting-group">
                <h5>ドローダウン</h5>
                <label>
                    危険レベル: <input type="number" id="ddCritical" value="${config.alerts.drawdown.critical}" min="0" max="100">%
                </label>
                <label>
                    警告レベル: <input type="number" id="ddWarning" value="${config.alerts.drawdown.warning}" min="0" max="100">%
                </label>
            </div>
            <div class="setting-group">
                <h5>ポジション損失</h5>
                <label>
                    危険レベル: <input type="number" id="lossCritical" value="${config.alerts.positionLoss.critical}" min="-1000000" max="0">円
                </label>
                <label>
                    警告レベル: <input type="number" id="lossWarning" value="${config.alerts.positionLoss.warning}" min="-1000000" max="0">円
                </label>
            </div>
            <button class="save-btn" onclick="window.alertManager.saveAlertSettings()">設定を保存</button>
        `;
        
        return container;
    }
    
    /**
     * アラート設定を保存
     */
    saveAlertSettings() {
        const newSettings = {
            alerts: {
                marginLevel: {
                    critical: Number(document.getElementById('marginCritical').value),
                    warning: Number(document.getElementById('marginWarning').value)
                },
                drawdown: {
                    critical: Number(document.getElementById('ddCritical').value),
                    warning: Number(document.getElementById('ddWarning').value)
                },
                positionLoss: {
                    critical: Number(document.getElementById('lossCritical').value),
                    warning: Number(document.getElementById('lossWarning').value)
                }
            }
        };
        
        userSettings.save(newSettings);
        this.showNotification('アラート設定を保存しました', 'info');
    }
}