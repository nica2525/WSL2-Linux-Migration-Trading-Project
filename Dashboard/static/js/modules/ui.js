/**
 * UIモジュール - Phase 2-B
 * UI要素の管理と更新
 */

export class UIManager {
    constructor() {
        this.lastActivityTime = Date.now();
        this.updateInterval = 5000;
        this.elements = {};
        this.initializeElements();
    }
    
    /**
     * DOM要素を初期化
     */
    initializeElements() {
        // 主要な要素をキャッシュ
        this.elements = {
            // 接続状態
            connectionStatus: document.getElementById('connectionStatus'),
            connectionText: document.getElementById('connectionText'),
            connectionInfo: document.getElementById('connectionInfo'),
            
            // アカウント情報
            balance: document.getElementById('balance'),
            equity: document.getElementById('equity'),
            profit: document.getElementById('profit'),
            marginLevel: document.getElementById('marginLevel'),
            
            // 今日の結果
            todayProfit: document.getElementById('todayProfit'),
            positionCount: document.getElementById('positionCount'),
            
            // 市場データ
            bid: document.getElementById('bid'),
            ask: document.getElementById('ask'),
            spread: document.getElementById('spread'),
            priceTime: document.getElementById('priceTime'),
            
            // その他
            lastUpdate: document.getElementById('lastUpdate'),
            positionsList: document.getElementById('positionsList'),
            notification: document.getElementById('notification')
        };
    }
    
    /**
     * 接続状態を更新
     * @param {boolean} connected - 接続状態
     */
    updateConnectionStatus(connected) {
        if (!this.elements.connectionStatus) return;
        
        if (connected) {
            this.elements.connectionStatus.classList.remove('error');
            this.setText('connectionText', 'オンライン');
            this.setText('connectionInfo', 'WebSocket接続済み');
        } else {
            this.elements.connectionStatus.classList.add('error');
            this.setText('connectionText', 'オフライン');
            this.setText('connectionInfo', '接続エラー');
        }
    }
    
    /**
     * アカウント情報を更新
     * @param {Object} account - アカウントデータ
     */
    updateAccount(account) {
        if (!account) return;
        
        // 残高
        this.setText('balance', this.formatNumber(account.balance));
        
        // 有効証拠金
        this.setText('equity', this.formatNumber(account.equity));
        
        // 含み損益
        const profit = account.profit || 0;
        const profitElement = this.elements.profit;
        if (profitElement) {
            profitElement.textContent = this.formatCurrency(profit);
            profitElement.className = 'account-value ' + (profit >= 0 ? 'profit-positive' : 'profit-negative');
        }
        
        // 証拠金維持率
        const marginLevel = account.margin_level;
        this.setText('marginLevel', marginLevel ? marginLevel.toFixed(2) + '%' : '-');
    }
    
    /**
     * EA情報を更新
     * @param {Object} ea - EA情報
     */
    updateEAStatus(ea) {
        if (!ea) return;
        
        // 今日の利益
        const todayProfit = ea.today_profit || 0;
        const todayProfitElement = this.elements.todayProfit;
        if (todayProfitElement) {
            todayProfitElement.textContent = this.formatCurrency(todayProfit);
            todayProfitElement.className = 'account-value ' + (todayProfit >= 0 ? 'profit-positive' : 'profit-negative');
        }
        
        // ポジション数
        this.setText('positionCount', ea.active_positions || 0);
    }
    
    /**
     * 市場データを更新
     * @param {Object} market - 市場データ
     */
    updateMarket(market) {
        if (!market) return;
        
        this.setText('bid', market.bid || '-');
        this.setText('ask', market.ask || '-');
        this.setText('spread', market.spread || '-');
        this.setText('priceTime', market.server_time || '-');
    }
    
    /**
     * ポジション一覧を更新
     * @param {Array} positions - ポジション配列
     */
    updatePositions(positions) {
        const positionsList = this.elements.positionsList;
        if (!positionsList) return;
        
        if (!positions || positions.length === 0) {
            positionsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📈</div>
                    <div>現在ポジションはありません</div>
                </div>
            `;
            return;
        }
        
        let html = '';
        positions.forEach(position => {
            const profitClass = position.profit >= 0 ? 'profit-positive' : 'profit-negative';
            const typeClass = position.type.toLowerCase();
            
            html += `
                <div class="position-item">
                    <div class="position-left">
                        <div>
                            <span class="position-symbol">${position.symbol}</span>
                            <span class="position-type ${typeClass}">${position.type}</span>
                        </div>
                        <div class="position-details">
                            ${position.volume} lot | 開始: ${position.open_price} | 期間: ${position.duration}
                        </div>
                    </div>
                    <div class="position-right">
                        <div class="position-profit ${profitClass}">
                            ${this.formatCurrency(position.profit)}
                        </div>
                        <div class="position-pips">
                            ${position.profit_pips > 0 ? '+' : ''}${position.profit_pips} pips
                        </div>
                    </div>
                </div>
            `;
        });
        
        positionsList.innerHTML = html;
    }
    
    /**
     * 最終更新時刻を更新
     * @param {string} timestamp - タイムスタンプ
     */
    updateLastUpdate(timestamp) {
        if (timestamp) {
            const time = new Date(timestamp).toLocaleTimeString('ja-JP');
            this.setText('lastUpdate', time);
        }
    }
    
    /**
     * タブナビゲーションをセットアップ
     */
    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabId = button.getAttribute('data-tab');
                
                // アクティブ状態の更新
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                button.classList.add('active');
                const targetTab = document.getElementById(tabId);
                if (targetTab) {
                    targetTab.classList.add('active');
                }
                
                // カスタムイベント発火
                window.dispatchEvent(new CustomEvent('tabChanged', { detail: { tabId } }));
            });
        });
    }
    
    /**
     * ユーザーアクティビティを追跡
     */
    trackActivity() {
        document.addEventListener('touchstart', () => {
            this.lastActivityTime = Date.now();
        });
        
        document.addEventListener('click', () => {
            this.lastActivityTime = Date.now();
        });
    }
    
    /**
     * 非アクティブ時間を取得
     * @returns {number} 非アクティブ時間（ミリ秒）
     */
    getInactiveTime() {
        return Date.now() - this.lastActivityTime;
    }
    
    /**
     * リフレッシュボタンをセットアップ
     * @param {Function} refreshCallback - リフレッシュ時のコールバック
     */
    setupRefreshButton(refreshCallback) {
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                refreshBtn.classList.add('loading');
                
                if (refreshCallback) {
                    refreshCallback();
                }
                
                setTimeout(() => {
                    refreshBtn.classList.remove('loading');
                }, 1000);
            });
        }
    }
    
    /**
     * 設定チェックボックスをセットアップ
     */
    setupSettings() {
        // 自動更新設定
        const autoRefresh = document.getElementById('autoRefresh');
        if (autoRefresh) {
            const saved = localStorage.getItem('autoRefresh');
            if (saved !== null) {
                autoRefresh.checked = saved === 'true';
            }
            
            autoRefresh.addEventListener('change', function() {
                localStorage.setItem('autoRefresh', this.checked);
                window.dispatchEvent(new CustomEvent('autoRefreshChanged', { 
                    detail: { enabled: this.checked } 
                }));
            });
        }
        
        // 音声通知設定
        const soundNotification = document.getElementById('soundNotification');
        if (soundNotification) {
            const saved = localStorage.getItem('soundNotification');
            if (saved !== null) {
                soundNotification.checked = saved === 'true';
            }
            
            soundNotification.addEventListener('change', function() {
                localStorage.setItem('soundNotification', this.checked);
                window.dispatchEvent(new CustomEvent('soundNotificationChanged', { 
                    detail: { enabled: this.checked } 
                }));
            });
        }
    }
    
    /**
     * テキストを安全に設定
     * @param {string} elementId - 要素ID
     * @param {string} text - テキスト
     */
    setText(elementId, text) {
        const element = this.elements[elementId];
        if (element) {
            element.textContent = text;
        }
    }
    
    /**
     * 数値をフォーマット
     * @param {number} num - 数値
     * @returns {string} フォーマット済み文字列
     */
    formatNumber(num) {
        if (!num && num !== 0) return '-';
        return new Intl.NumberFormat('ja-JP').format(Math.round(num));
    }
    
    /**
     * 通貨をフォーマット
     * @param {number} num - 数値
     * @returns {string} フォーマット済み文字列
     */
    formatCurrency(num) {
        if (!num && num !== 0) return '¥0';
        const formatted = new Intl.NumberFormat('ja-JP').format(Math.round(num));
        return (num >= 0 ? '+' : '') + '¥' + formatted;
    }
    
    /**
     * 通知を表示
     * @param {string} message - メッセージ
     * @param {string} type - タイプ
     */
    showNotification(message, type = 'info') {
        const notification = this.elements.notification;
        if (!notification) return;
        
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.add('show');
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }
}