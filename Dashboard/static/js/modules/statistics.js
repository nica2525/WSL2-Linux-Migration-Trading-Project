/**
 * 統計モジュール - Phase 2-B
 * 統計計算と表示更新を管理
 */

import { config } from './config.js';

export class StatisticsManager {
    constructor() {
        this.lastDrawdownPeak = 0;
        this.annotations = {
            winRate: 'オープンポジションベース',
            profitFactor: 'リアルタイム簡易計算',
            drawdown: '24時間データベース',
            totalTrades: '現在のポジション数'
        };
    }
    
    /**
     * 統計データを更新
     * @param {Array} positions - ポジション配列
     * @param {Object} accountData - 口座データ
     * @param {Array} balanceHistory - 残高履歴（チャートデータ）
     */
    update(positions, accountData, balanceHistory) {
        if (!positions || !accountData) return;
        
        try {
            // 基本統計計算
            const stats = this.calculate(positions, balanceHistory);
            
            // DOM更新
            this.updateDisplay(stats);
            
            // 色分け適用
            this.applyColorCoding(stats);
            
            return stats;
        } catch (error) {
            console.error('統計更新エラー:', error);
            return null;
        }
    }
    
    /**
     * 統計値を計算
     * @param {Array} positions - ポジション配列
     * @param {Array} balanceHistory - 残高履歴
     * @returns {Object} 計算された統計値
     */
    calculate(positions, balanceHistory) {
        const stats = {
            winRate: 0,
            profitFactor: 0,
            maxDrawdown: 0,
            totalTrades: positions.length,
            totalProfit: 0,
            totalLoss: 0,
            profitablePositions: 0,
            losingPositions: 0
        };
        
        // ポジション統計
        if (positions.length > 0) {
            positions.forEach(pos => {
                const profit = pos.profit || 0;
                if (profit > 0) {
                    stats.profitablePositions++;
                    stats.totalProfit += profit;
                } else if (profit < 0) {
                    stats.losingPositions++;
                    stats.totalLoss += Math.abs(profit);
                }
            });
            
            // 勝率計算
            stats.winRate = (stats.profitablePositions / positions.length) * 100;
            
            // プロフィットファクター計算
            if (stats.totalLoss > 0) {
                stats.profitFactor = stats.totalProfit / stats.totalLoss;
            } else if (stats.totalProfit > 0) {
                stats.profitFactor = 999; // 損失なし
            }
        }
        
        // ドローダウン計算（残高履歴から）
        if (balanceHistory && balanceHistory.length > 1) {
            let peak = balanceHistory[0].balance;
            
            balanceHistory.forEach(data => {
                if (data.balance > peak) {
                    peak = data.balance;
                }
                const drawdown = ((peak - data.balance) / peak) * 100;
                if (drawdown > stats.maxDrawdown) {
                    stats.maxDrawdown = drawdown;
                }
            });
            
            this.lastDrawdownPeak = peak;
        }
        
        return stats;
    }
    
    /**
     * 統計表示を更新
     * @param {Object} stats - 統計データ
     */
    updateDisplay(stats) {
        // 勝率
        const winRateEl = document.getElementById('winRate');
        if (winRateEl) {
            winRateEl.textContent = `${stats.winRate.toFixed(1)}%`;
            winRateEl.setAttribute('title', this.annotations.winRate);
        }
        
        // プロフィットファクター
        const pfEl = document.getElementById('profitFactor');
        if (pfEl) {
            pfEl.textContent = stats.profitFactor.toFixed(2);
            pfEl.setAttribute('title', this.annotations.profitFactor);
        }
        
        // 最大ドローダウン
        const ddEl = document.getElementById('maxDrawdown');
        if (ddEl) {
            ddEl.textContent = `${stats.maxDrawdown.toFixed(1)}%`;
            ddEl.setAttribute('title', this.annotations.drawdown);
        }
        
        // 総取引数
        const tradesEl = document.getElementById('totalTrades');
        if (tradesEl) {
            tradesEl.textContent = stats.totalTrades.toString();
            tradesEl.setAttribute('title', this.annotations.totalTrades);
        }
        
        // 統計信頼性表示を更新
        this.updateReliabilityIndicator(stats.totalTrades);
    }
    
    /**
     * 色分けを適用
     * @param {Object} stats - 統計データ
     */
    applyColorCoding(stats) {
        // 勝率の色分け
        const winRateEl = document.getElementById('winRate');
        if (winRateEl) {
            winRateEl.className = 'account-value ' + this.getWinRateClass(stats.winRate);
        }
        
        // プロフィットファクターの色分け
        const pfEl = document.getElementById('profitFactor');
        if (pfEl) {
            pfEl.className = 'account-value ' + this.getProfitFactorClass(stats.profitFactor);
        }
        
        // ドローダウンの色分け
        const ddEl = document.getElementById('maxDrawdown');
        if (ddEl) {
            ddEl.className = 'account-value ' + this.getDrawdownClass(stats.maxDrawdown);
        }
    }
    
    /**
     * 勝率の色クラスを取得
     * @param {number} winRate - 勝率
     * @returns {string} CSSクラス名
     */
    getWinRateClass(winRate) {
        if (winRate >= config.statistics.winRate.good) {
            return 'profit-positive';
        } else if (winRate >= config.statistics.winRate.warning) {
            return '';
        } else {
            return 'profit-negative';
        }
    }
    
    /**
     * プロフィットファクターの色クラスを取得
     * @param {number} profitFactor - PF値
     * @returns {string} CSSクラス名
     */
    getProfitFactorClass(profitFactor) {
        if (profitFactor >= config.statistics.profitFactor.good) {
            return 'profit-positive';
        } else if (profitFactor >= config.statistics.profitFactor.warning) {
            return '';
        } else {
            return 'profit-negative';
        }
    }
    
    /**
     * ドローダウンの色クラスを取得
     * @param {number} drawdown - DD値
     * @returns {string} CSSクラス名
     */
    getDrawdownClass(drawdown) {
        if (drawdown <= config.statistics.drawdown.good) {
            return 'profit-positive';
        } else if (drawdown <= config.statistics.drawdown.warning) {
            return '';
        } else {
            return 'profit-negative';
        }
    }
    
    /**
     * 統計情報の説明を表示
     */
    showAnnotations() {
        const container = document.createElement('div');
        container.className = 'statistics-info';
        container.innerHTML = `
            <h4>統計情報について</h4>
            <ul>
                <li><strong>勝率</strong>: ${this.annotations.winRate}</li>
                <li><strong>プロフィットファクター</strong>: ${this.annotations.profitFactor}</li>
                <li><strong>最大ドローダウン</strong>: ${this.annotations.drawdown}</li>
                <li><strong>総取引数</strong>: ${this.annotations.totalTrades}</li>
            </ul>
            <p class="note">※ これらは参考値です。正確な統計は取引履歴全体から計算されます。</p>
        `;
        
        // モーダルやツールチップとして表示
        return container;
    }
    
    /**
     * 統計信頼性インジケーターを更新
     * @param {number} totalTrades - 取引数
     */
    updateReliabilityIndicator(totalTrades) {
        let reliabilityContainer = document.getElementById('statisticsReliability');
        
        if (!reliabilityContainer) {
            // 初回作成
            reliabilityContainer = document.createElement('div');
            reliabilityContainer.id = 'statisticsReliability';
            reliabilityContainer.style.cssText = `
                margin-top: 8px;
                padding: 6px 10px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                font-size: 11px;
                text-align: center;
                border-left: 3px solid;
            `;
            
            const statsCard = document.querySelector('.card .account-grid').parentNode;
            if (statsCard) {
                statsCard.appendChild(reliabilityContainer);
            }
        }
        
        // 信頼性レベルの判定
        let level, message, color;
        
        if (totalTrades === 0) {
            level = 'なし';
            message = 'ポジション未保有 - 統計なし';
            color = '#9E9E9E';
        } else if (totalTrades < 5) {
            level = '低';
            message = `サンプル数${totalTrades}件 - 参考程度`;
            color = '#FF9800';
        } else if (totalTrades < 20) {
            level = '中';
            message = `サンプル数${totalTrades}件 - 暫定統計`;
            color = '#2196F3';
        } else {
            level = '高';
            message = `サンプル数${totalTrades}件 - 信頼性良好`;
            color = '#4CAF50';
        }
        
        reliabilityContainer.innerHTML = `
            <span style="font-weight: 600;">統計信頼性: ${level}</span> - ${message}
        `;
        reliabilityContainer.style.borderLeftColor = color;
        reliabilityContainer.style.color = '#ffffff';
    }
}