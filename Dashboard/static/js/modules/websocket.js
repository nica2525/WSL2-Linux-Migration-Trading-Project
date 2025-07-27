/**
 * WebSocketモジュール - Phase 2-B
 * SocketIO通信の管理と再接続処理
 */

import { config } from './config.js';

export class WebSocketManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.handlers = new Map();
        this.reconnectTimer = null;
    }
    
    /**
     * WebSocket接続を初期化
     * @param {Object} options - 接続オプション
     */
    initialize(options = {}) {
        try {
            this.socket = io(options);
            this.setupEventHandlers();
            console.log('WebSocket初期化完了');
        } catch (error) {
            console.error('WebSocket初期化エラー:', error);
            this.scheduleReconnect();
        }
    }
    
    /**
     * 基本イベントハンドラーのセットアップ
     */
    setupEventHandlers() {
        this.socket.on('connect', () => {
            console.log('WebSocket接続成功');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.clearReconnectTimer();
            this.emit('connected', { timestamp: new Date().toISOString() });
            
            // 初期データ要求
            this.socket.emit('request_data');
        });
        
        this.socket.on('disconnect', () => {
            console.log('WebSocket接続切断');
            this.isConnected = false;
            this.emit('disconnected', { timestamp: new Date().toISOString() });
            this.scheduleReconnect();
        });
        
        this.socket.on('error', (error) => {
            console.error('WebSocketエラー:', error);
            this.emit('error', error);
        });
        
        // 再接続処理の改善
        this.socket.on('connect_error', (error) => {
            console.error('接続エラー:', error.message);
            this.isConnected = false;
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`再接続成功 (試行${attemptNumber}回目)`);
            this.reconnectAttempts = 0;
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('再接続エラー:', error);
        });
    }
    
    /**
     * カスタムイベントハンドラーを登録
     * @param {string} event - イベント名
     * @param {Function} handler - ハンドラー関数
     */
    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, new Set());
            
            // SocketIOイベントリスナーを設定
            if (this.socket && !['connected', 'disconnected', 'error'].includes(event)) {
                this.socket.on(event, (data) => {
                    this.emit(event, data);
                });
            }
        }
        this.handlers.get(event).add(handler);
    }
    
    /**
     * イベントハンドラーを削除
     * @param {string} event - イベント名
     * @param {Function} handler - ハンドラー関数
     */
    off(event, handler) {
        if (this.handlers.has(event)) {
            this.handlers.get(event).delete(handler);
        }
    }
    
    /**
     * イベントを発火
     * @param {string} event - イベント名
     * @param {*} data - イベントデータ
     */
    emit(event, data) {
        if (this.handlers.has(event)) {
            this.handlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Event handler error for ${event}:`, error);
                }
            });
        }
    }
    
    /**
     * サーバーにイベントを送信
     * @param {string} event - イベント名
     * @param {*} data - 送信データ
     * @param {Function} callback - コールバック関数
     */
    send(event, data, callback) {
        if (!this.isConnected) {
            console.warn('WebSocket未接続: イベント送信をスキップ', event);
            if (callback) callback({ error: 'Not connected' });
            return;
        }
        
        try {
            if (callback) {
                this.socket.emit(event, data, callback);
            } else {
                this.socket.emit(event, data);
            }
        } catch (error) {
            console.error('送信エラー:', error);
            if (callback) callback({ error: error.message });
        }
    }
    
    /**
     * データリクエスト送信
     */
    requestData() {
        this.send('request_data');
    }
    
    /**
     * 履歴データリクエスト
     * @param {string} period - 期間指定
     */
    requestHistory(period) {
        this.send('request_history', { period });
    }
    
    /**
     * データ更新リクエスト（強制更新）
     */
    requestRefresh() {
        this.send('request_refresh');
    }
    
    /**
     * 再接続をスケジュール
     */
    scheduleReconnect() {
        if (this.reconnectTimer) return;
        
        if (this.reconnectAttempts >= config.socket.maxReconnectAttempts) {
            console.error('最大再接続試行回数に到達');
            this.emit('reconnect_failed', { attempts: this.reconnectAttempts });
            return;
        }
        
        this.reconnectAttempts++;
        const delay = config.socket.reconnectDelay * Math.min(this.reconnectAttempts, 5);
        
        console.log(`${delay}ms後に再接続を試行 (${this.reconnectAttempts}回目)`);
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            if (!this.isConnected && this.socket) {
                this.socket.connect();
            }
        }, delay);
    }
    
    /**
     * 再接続タイマーをクリア
     */
    clearReconnectTimer() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }
    
    /**
     * 接続状態を取得
     * @returns {boolean} 接続状態
     */
    getConnectionStatus() {
        return this.isConnected;
    }
    
    /**
     * 接続を切断
     */
    disconnect() {
        this.clearReconnectTimer();
        if (this.socket) {
            this.socket.disconnect();
            this.isConnected = false;
        }
    }
    
    /**
     * リソースをクリーンアップ
     */
    destroy() {
        this.disconnect();
        this.handlers.clear();
        this.socket = null;
    }
}