/**
 * チャートモジュール - Phase 2-B
 * Chart.jsの初期化と更新を管理
 */

import { config } from './config.js';

export class ChartManager {
    constructor() {
        this.chart = null;
        this.data = [];
    }
    
    /**
     * チャート初期化
     * @param {string} canvasId - キャンバス要素のID
     */
    initialize(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element ${canvasId} not found`);
            return;
        }
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '残高',
                        data: [],
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: '有効証拠金',
                        data: [],
                        borderColor: '#FF9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { 
                            font: { size: 10 },
                            usePointStyle: true,
                            padding: 10,
                            color: '#ffffff'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = new Intl.NumberFormat('ja-JP').format(Math.round(context.parsed.y));
                                return `${label}: ¥${value}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        ticks: { 
                            font: { size: 9 },
                            maxTicksLimit: 6,
                            color: '#ffffff'
                        }
                    },
                    y: {
                        display: true,
                        ticks: { 
                            font: { size: 9 },
                            color: '#ffffff',
                            callback: function(value) {
                                return '¥' + new Intl.NumberFormat('ja-JP').format(value);
                            }
                        }
                    }
                },
                elements: {
                    point: { radius: 2, hoverRadius: 4 }
                }
            }
        });
        
        console.log('Chart initialized');
    }
    
    /**
     * チャートデータ更新
     * @param {Object} accountData - 口座データ
     */
    update(accountData) {
        if (!this.chart || !accountData) return;
        
        const now = new Date();
        const timeLabel = now.toLocaleTimeString('ja-JP', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        // データ追加
        this.data.push({
            time: timeLabel,
            balance: accountData.balance || 0,
            equity: accountData.equity || 0,
            timestamp: now
        });
        
        // データ上限管理
        if (this.data.length > config.chart.maxDataPoints) {
            this.data.shift();
        }
        
        // チャート更新
        const labels = this.data.map(d => d.time);
        const balanceValues = this.data.map(d => d.balance);
        const equityValues = this.data.map(d => d.equity);
        
        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = balanceValues;
        this.chart.data.datasets[1].data = equityValues;
        this.chart.update(config.chart.updateAnimation);
    }
    
    /**
     * 現在のチャートデータを取得
     * @returns {Array} チャートデータ配列
     */
    getData() {
        return this.data;
    }
    
    /**
     * チャートをクリア
     */
    clear() {
        if (this.chart) {
            this.data = [];
            this.chart.data.labels = [];
            this.chart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            this.chart.update('none');
        }
    }
    
    /**
     * チャートを破棄
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
            this.data = [];
        }
    }
}