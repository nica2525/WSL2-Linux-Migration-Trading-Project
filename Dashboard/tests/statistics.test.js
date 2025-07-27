/**
 * StatisticsManagerテスト - Phase 2-B単体テスト
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { StatisticsManager } from '../static/js/modules/statistics.js';

// config.jsのモック
vi.mock('../static/js/modules/config.js', () => ({
  config: {
    statistics: {
      winRate: { good: 60, warning: 40 },
      profitFactor: { good: 1.5, warning: 1.0 },
      drawdown: { good: 10, warning: 25 }
    }
  }
}));

describe('StatisticsManager', () => {
  let statsManager;

  beforeEach(() => {
    statsManager = new StatisticsManager();
    
    // DOM要素のモック
    document.getElementById = vi.fn((id) => ({
      textContent: '',
      className: '',
      setAttribute: vi.fn()
    }));
    
    document.querySelector = vi.fn(() => ({
      appendChild: vi.fn()
    }));
  });

  describe('勝率計算', () => {
    it('利益ポジションのみの場合100%を返す', () => {
      const positions = [
        { profit: 1000 },
        { profit: 500 },
        { profit: 200 }
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.winRate).toBe(100);
      expect(stats.profitablePositions).toBe(3);
    });

    it('損失ポジションのみの場合0%を返す', () => {
      const positions = [
        { profit: -1000 },
        { profit: -500 },
        { profit: -200 }
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.winRate).toBe(0);
      expect(stats.profitablePositions).toBe(0);
    });

    it('混在ポジションの場合正しい勝率を計算する', () => {
      const positions = [
        { profit: 1000 },  // 利益
        { profit: -500 },  // 損失
        { profit: 200 },   // 利益
        { profit: -100 },  // 損失
        { profit: 300 }    // 利益
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.winRate).toBe(60); // 3/5 = 60%
      expect(stats.profitablePositions).toBe(3);
      expect(stats.totalTrades).toBe(5);
    });

    it('ポジションが0件の場合0%を返す', () => {
      const stats = statsManager.calculate([], []);
      expect(stats.winRate).toBe(0);
      expect(stats.totalTrades).toBe(0);
    });
  });

  describe('プロフィットファクター計算', () => {
    it('利益のみの場合は無限大を適切に処理する', () => {
      const positions = [
        { profit: 1000 },
        { profit: 500 }
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.profitFactor).toBe(999); // 無限大の代替値
      expect(stats.totalProfit).toBe(1500);
      expect(stats.totalLoss).toBe(0);
    });

    it('損失のみの場合は0を返す', () => {
      const positions = [
        { profit: -1000 },
        { profit: -500 }
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.profitFactor).toBe(0);
      expect(stats.totalProfit).toBe(0);
      expect(stats.totalLoss).toBe(1500);
    });

    it('利益と損失が混在する場合正しく計算する', () => {
      const positions = [
        { profit: 3000 },  // 利益
        { profit: -1000 }, // 損失
        { profit: 1500 },  // 利益
        { profit: -500 }   // 損失
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.profitFactor).toBe(3.0); // 4500 / 1500 = 3.0
      expect(stats.totalProfit).toBe(4500);
      expect(stats.totalLoss).toBe(1500);
    });
  });

  describe('最大ドローダウン計算', () => {
    it('残高履歴から正しくドローダウンを計算する', () => {
      const balanceHistory = [
        { balance: 1000000 },  // ピーク
        { balance: 950000 },   // -5%
        { balance: 900000 },   // -10% (最大)
        { balance: 950000 },   // 回復
        { balance: 1100000 }   // 新ピーク
      ];
      
      const stats = statsManager.calculate([], balanceHistory);
      expect(stats.maxDrawdown).toBe(10); // 10%のドローダウン
    });

    it('単調増加の残高履歴では0%を返す', () => {
      const balanceHistory = [
        { balance: 1000000 },
        { balance: 1100000 },
        { balance: 1200000 },
        { balance: 1300000 }
      ];
      
      const stats = statsManager.calculate([], balanceHistory);
      expect(stats.maxDrawdown).toBe(0);
    });

    it('履歴が空の場合0%を返す', () => {
      const stats = statsManager.calculate([], []);
      expect(stats.maxDrawdown).toBe(0);
    });

    it('残高が0まで下がる場合100%を返す', () => {
      const balanceHistory = [
        { balance: 1000000 },
        { balance: 500000 },
        { balance: 0 }
      ];
      
      const stats = statsManager.calculate([], balanceHistory);
      expect(stats.maxDrawdown).toBe(100);
    });
  });

  describe('色分け判定', () => {
    it('勝率の色分けを正しく判定する', () => {
      expect(statsManager.getWinRateClass(70)).toBe('profit-positive'); // 60%以上
      expect(statsManager.getWinRateClass(50)).toBe(''); // 40-60%
      expect(statsManager.getWinRateClass(30)).toBe('profit-negative'); // 40%未満
    });

    it('プロフィットファクターの色分けを正しく判定する', () => {
      expect(statsManager.getProfitFactorClass(2.0)).toBe('profit-positive'); // 1.5以上
      expect(statsManager.getProfitFactorClass(1.2)).toBe(''); // 1.0-1.5
      expect(statsManager.getProfitFactorClass(0.8)).toBe('profit-negative'); // 1.0未満
    });

    it('ドローダウンの色分けを正しく判定する', () => {
      expect(statsManager.getDrawdownClass(5)).toBe('profit-positive'); // 10%以下
      expect(statsManager.getDrawdownClass(15)).toBe(''); // 10-25%
      expect(statsManager.getDrawdownClass(30)).toBe('profit-negative'); // 25%超
    });
  });

  describe('信頼性インジケーター', () => {
    beforeEach(() => {
      // DOM要素のモックをより詳細に設定
      const mockContainer = {
        id: '',
        style: { cssText: '', borderLeftColor: '', color: '' },
        innerHTML: ''
      };
      
      document.getElementById = vi.fn((id) => {
        if (id === 'statisticsReliability') return null; // 初回は存在しない
        return mockContainer;
      });
      
      document.createElement = vi.fn(() => mockContainer);
      document.querySelector = vi.fn(() => ({
        appendChild: vi.fn()
      }));
    });

    it('ポジション0件で信頼性なしを表示する', () => {
      statsManager.updateReliabilityIndicator(0);
      // DOM操作のモックなので実際の検証は限定的
      expect(document.createElement).toHaveBeenCalledWith('div');
    });

    it('ポジション5件未満で信頼性低を判定する', () => {
      statsManager.updateReliabilityIndicator(3);
      expect(document.createElement).toHaveBeenCalledWith('div');
    });

    it('ポジション20件以上で信頼性高を判定する', () => {
      statsManager.updateReliabilityIndicator(25);
      expect(document.createElement).toHaveBeenCalledWith('div');
    });
  });

  describe('エッジケース', () => {
    it('profit値がundefinedのポジションを適切に処理する', () => {
      const positions = [
        { profit: undefined },
        { profit: 1000 },
        { /* profitプロパティなし */ }
      ];
      
      const stats = statsManager.calculate(positions, []);
      expect(stats.totalTrades).toBe(3);
      expect(stats.profitablePositions).toBe(1); // profit: 1000のみ
      expect(stats.totalProfit).toBe(1000);
    });

    it('異常な残高値を適切に処理する', () => {
      const balanceHistory = [
        { balance: -1000 },    // 負の値
        { balance: 1000000 },
        { balance: null },     // null値
        { balance: 500000 }
      ];
      
      const stats = statsManager.calculate([], balanceHistory);
      // エラーが発生せず、何らかの値が返されることを確認
      expect(typeof stats.maxDrawdown).toBe('number');
      expect(stats.maxDrawdown).toBeGreaterThanOrEqual(0);
    });
  });
});