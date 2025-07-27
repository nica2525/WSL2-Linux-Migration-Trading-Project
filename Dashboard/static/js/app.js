/**
 * JamesORBダッシュボード メインアプリケーション - Phase 2-B
 * モジュール統合とアプリケーション制御
 */

import { config, userSettings, loadSettingsToUI } from './modules/config.js';
import { ChartManager } from './modules/chart.js';
import { WebSocketManager } from './modules/websocket.js';
import { StatisticsManager } from './modules/statistics.js';
import { AlertManager } from './modules/alerts.js';
import { UIManager } from './modules/ui.js';

class DashboardApp {
    constructor() {
        this.chart = new ChartManager();
        this.websocket = new WebSocketManager();
        this.statistics = new StatisticsManager();
        this.alerts = new AlertManager();
        this.ui = new UIManager();
        
        this.lastData = null;
        this.autoRefreshEnabled = true;
        this.updateTimer = null;
        
        // グローバルアクセス用（アラート設定保存など）
        window.dashboardApp = this;
        window.alertManager = this.alerts;
    }
    
    /**
     * アプリケーションを初期化
     */
    async initialize() {
        console.log('JamesORB Mobile Dashboard v2.0 - Phase 2-B 初期化開始');
        
        try {
            // UI初期化
            this.ui.setupTabNavigation();
            this.ui.setupRefreshButton(() => this.refreshData());
            this.ui.setupSettings();
            this.ui.setupAlertSettings(
                () => this.alerts.saveAlertSettings(),
                () => this.alerts.resetAlertSettings(),
                () => loadSettingsToUI()
            );
            this.ui.trackActivity();
            
            // チャート初期化
            this.chart.initialize('balanceChart');
            
            // WebSocket初期化
            this.setupWebSocket();
            
            // PWA初期化
            this.setupPWA();
            
            // 自動更新設定
            this.setupAutoUpdate();
            
            // イベントリスナー設定
            this.setupEventListeners();
            
            console.log('初期化完了');
        } catch (error) {
            console.error('初期化エラー:', error);
            this.ui.showNotification('初期化エラーが発生しました', 'error');
        }
    }
    
    /**
     * WebSocketを設定
     */
    setupWebSocket() {
        // WebSocket初期化
        this.websocket.initialize();
        
        // 接続イベント
        this.websocket.on('connected', () => {
            this.ui.updateConnectionStatus(true);
        });
        
        this.websocket.on('disconnected', () => {
            this.ui.updateConnectionStatus(false);
        });
        
        // データイベント
        this.websocket.on('market_data', (data) => {
            console.log('リアルタイムデータ受信:', data);
            this.lastData = data;
            this.updateDisplay();
        });
        
        // 通知イベント
        this.websocket.on('notification', (data) => {
            this.ui.showNotification(data.message, data.type || 'info');
        });
        
        // エラーイベント
        this.websocket.on('error', (data) => {
            console.error('Socket error:', data);
            this.ui.showNotification('エラー: ' + data.message, 'error');
        });
        
        // 再接続失敗
        this.websocket.on('reconnect_failed', () => {
            this.ui.showNotification('接続を確立できません', 'error');
        });
    }
    
    /**
     * 画面表示を更新
     */
    updateDisplay() {
        if (!this.lastData) return;
        
        try {
            // アカウント情報
            if (this.lastData.account) {
                this.ui.updateAccount(this.lastData.account);
                
                // チャート更新
                this.chart.update(this.lastData.account);
            }
            
            // EA状態
            if (this.lastData.ea) {
                this.ui.updateEAStatus(this.lastData.ea);
            }
            
            // ポジション一覧
            if (this.lastData.positions) {
                this.ui.updatePositions(this.lastData.positions);
            }
            
            // 市場データ
            if (this.lastData.market) {
                this.ui.updateMarket(this.lastData.market);
            }
            
            // 統計更新
            if (this.lastData.positions && this.lastData.account) {
                const chartData = this.chart.getData();
                this.statistics.update(
                    this.lastData.positions, 
                    this.lastData.account,
                    chartData
                );
                
                // 現在のドローダウンを計算してアラートチェックに渡す
                if (chartData.length > 0) {
                    const stats = this.statistics.calculate(this.lastData.positions, chartData);
                    this.lastData.account.currentDrawdown = stats.maxDrawdown;
                }
            }
            
            // アラートチェック
            if (this.lastData.account && this.lastData.positions) {
                this.alerts.check(this.lastData.account, this.lastData.positions);
            }
            
            // 最終更新時刻
            this.ui.updateLastUpdate(this.lastData.timestamp);
            
        } catch (error) {
            console.error('画面更新エラー:', error);
            this.ui.showNotification('画面更新エラーが発生しました', 'error');
        }
    }
    
    /**
     * データを手動更新
     */
    refreshData() {
        if (!this.websocket.getConnectionStatus()) {
            this.ui.showNotification('接続されていません', 'error');
            return;
        }
        
        this.websocket.requestRefresh();
    }
    
    /**
     * 自動更新を設定
     */
    setupAutoUpdate() {
        // 設定読み込み
        const autoRefresh = localStorage.getItem('autoRefresh');
        this.autoRefreshEnabled = autoRefresh !== 'false';
        
        // 定期更新ループ
        this.startUpdateLoop();
    }
    
    /**
     * 更新ループを開始
     */
    startUpdateLoop() {
        // 既存のタイマーをクリア
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        this.updateTimer = setInterval(() => {
            if (this.autoRefreshEnabled && 
                this.websocket.getConnectionStatus() && 
                !document.hidden) {
                
                // 非アクティブ時間に基づく更新頻度調整
                const inactiveTime = this.ui.getInactiveTime();
                const interval = inactiveTime > config.update.inactiveThreshold 
                    ? config.update.inactiveInterval 
                    : config.update.activeInterval;
                
                // 次回の更新間隔を調整
                if (this.currentInterval !== interval) {
                    this.currentInterval = interval;
                    console.log(`更新間隔を${interval}msに調整`);
                    this.startUpdateLoop(); // 新しい間隔で再開
                    return;
                }
                
                this.websocket.requestData();
            }
        }, this.currentInterval || config.update.activeInterval);
    }
    
    /**
     * イベントリスナーを設定
     */
    setupEventListeners() {
        // タブ変更
        window.addEventListener('tabChanged', (event) => {
            const { tabId } = event.detail;
            if (tabId === 'positions' || tabId === 'market') {
                this.updateDisplay();
            }
        });
        
        // 自動更新設定変更
        window.addEventListener('autoRefreshChanged', (event) => {
            this.autoRefreshEnabled = event.detail.enabled;
            this.ui.showNotification(
                this.autoRefreshEnabled ? '自動更新を有効にしました' : '自動更新を無効にしました',
                'info'
            );
        });
        
        // 音声通知設定変更
        window.addEventListener('soundNotificationChanged', (event) => {
            this.alerts.saveSettings({ soundEnabled: event.detail.enabled });
            this.ui.showNotification('設定を保存しました', 'info');
        });
        
        // バイブレーション通知設定変更
        window.addEventListener('vibrationNotificationChanged', (event) => {
            this.alerts.saveSettings({ vibrationEnabled: event.detail.enabled });
            this.ui.showNotification('設定を保存しました', 'info');
        });
        
        // アラート設定変更
        window.addEventListener('alertSettingsChanged', (event) => {
            console.log('アラート設定が更新されました:', event.detail);
            // 必要に応じて追加処理
        });
        
        // バックグラウンド復帰
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.websocket.getConnectionStatus()) {
                this.ui.lastActivityTime = Date.now();
                this.websocket.requestData();
            }
        });
        
    }
    
    /**
     * PWAを設定
     */
    setupPWA() {
        // Service Worker登録
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/js/service-worker.js')
                .then(registration => console.log('Service Worker登録成功'))
                .catch(error => console.log('Service Worker登録失敗:', error));
        }
        
        // インストール促進
        let deferredPrompt = null;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            
            const installPrompt = document.getElementById('installPrompt');
            if (installPrompt) {
                installPrompt.style.display = 'block';
            }
        });
        
        // インストール関数
        window.installPWA = () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('PWAインストール受諾');
                        const installPrompt = document.getElementById('installPrompt');
                        if (installPrompt) {
                            installPrompt.style.display = 'none';
                        }
                    }
                    deferredPrompt = null;
                });
            }
        };
    }
    
    /**
     * アプリケーションを破棄
     */
    destroy() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        this.websocket.destroy();
        this.chart.destroy();
        
        console.log('Dashboard app destroyed');
    }
}

// アプリケーション起動
document.addEventListener('DOMContentLoaded', () => {
    const app = new DashboardApp();
    app.initialize();
});

// エラーハンドリング
window.addEventListener('error', (event) => {
    console.error('グローバルエラー:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('未処理のPromise拒否:', event.reason);
});