/**
 * AlertManagerテスト - Phase 2-B単体テスト
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AlertManager } from '../static/js/modules/alerts.js';

// config.jsのモック
vi.mock('../static/js/modules/config.js', () => ({
  config: {
    alerts: {
      marginLevel: { critical: 150, warning: 300 },
      drawdown: { critical: 25, warning: 15 },
      positionLoss: { critical: -50000, warning: -20000 },
      cooldownPeriod: 60000
    }
  },
  userSettings: {
    save: vi.fn(),
    load: vi.fn()
  }
}));

describe('AlertManager', () => {
  let alertManager;
  let mockNotificationElement;

  beforeEach(() => {
    alertManager = new AlertManager();
    
    // DOM要素のモック
    mockNotificationElement = {
      textContent: '',
      className: '',
      classList: {
        add: vi.fn(),
        remove: vi.fn()
      }
    };
    
    document.getElementById = vi.fn((id) => {
      if (id === 'notification') return mockNotificationElement;
      return null;
    });
    
    // 時間のモック
    vi.useFakeTimers();
  });

  describe('証拠金維持率チェック', () => {
    it('危険レベルでアラートを発生させる', () => {
      const now = Date.now();
      const result = alertManager.checkMarginLevel(100, now); // 150以下
      
      expect(result).toBeTruthy();
      expect(result.type).toBe('critical');
      expect(result.message).toContain('証拠金維持率が危険レベル');
      expect(result.value).toBe(100);
    });

    it('警告レベルでアラートを発生させる', () => {
      const now = Date.now();
      const result = alertManager.checkMarginLevel(200, now); // 150-300の間
      
      expect(result).toBeTruthy();
      expect(result.type).toBe('warning');
      expect(result.message).toContain('証拠金維持率が低下');
      expect(result.value).toBe(200);
    });

    it('正常レベルではアラートを発生させない', () => {
      const now = Date.now();
      const result = alertManager.checkMarginLevel(400, now); // 300超
      
      expect(result).toBeNull();
    });
  });

  describe('ドローダウンチェック', () => {
    it('危険レベルでアラートを発生させる', () => {
      const now = Date.now();
      const result = alertManager.checkDrawdown(30, now); // 25以上
      
      expect(result).toBeTruthy();
      expect(result.type).toBe('critical');
      expect(result.message).toContain('ドローダウンが危険レベル');
    });

    it('警告レベルでアラートを発生させる', () => {
      const now = Date.now();
      const result = alertManager.checkDrawdown(20, now); // 15-25の間
      
      expect(result).toBeTruthy();
      expect(result.type).toBe('warning');
      expect(result.message).toContain('ドローダウンが増加');
    });

    it('正常レベルではアラートを発生させない', () => {
      const now = Date.now();
      const result = alertManager.checkDrawdown(10, now); // 15未満
      
      expect(result).toBeNull();
    });
  });

  describe('ポジション損失チェック', () => {
    it('危険レベルの損失でアラートを発生させる', () => {
      const positions = [
        { ticket: '123', symbol: 'EURUSD', profit: -60000 } // -50000以下
      ];
      const now = Date.now();
      
      const results = alertManager.checkPositionLoss(positions, now);
      
      expect(results).toHaveLength(1);
      expect(results[0].type).toBe('critical');
      expect(results[0].message).toContain('大きな損失ポジション');
    });

    it('警告レベルの損失でアラートを発生させる', () => {
      const positions = [
        { ticket: '124', symbol: 'EURUSD', profit: -30000 } // -20000以下
      ];
      const now = Date.now();
      
      const results = alertManager.checkPositionLoss(positions, now);
      
      expect(results).toHaveLength(1);
      expect(results[0].type).toBe('warning');
      expect(results[0].message).toContain('損失拡大');
    });

    it('利益ポジションではアラートを発生させない', () => {
      const positions = [
        { ticket: '125', symbol: 'EURUSD', profit: 10000 }
      ];
      const now = Date.now();
      
      const results = alertManager.checkPositionLoss(positions, now);
      
      expect(results).toHaveLength(0);
    });
  });

  describe('クールダウン機能', () => {
    it('同じアラートを短時間内に重複発生させない', () => {
      const now = Date.now();
      
      // 1回目
      const result1 = alertManager.checkMarginLevel(100, now);
      expect(result1).toBeTruthy();
      
      // 30秒後（クールダウン期間内）
      const result2 = alertManager.checkMarginLevel(100, now + 30000);
      expect(result2).toBeNull();
      
      // 70秒後（クールダウン期間外）
      const result3 = alertManager.checkMarginLevel(100, now + 70000);
      expect(result3).toBeTruthy();
    });
  });

  describe('設定値妥当性チェック', () => {
    it('正常な設定値を受け入れる', () => {
      const validSettings = {
        marginLevel: { critical: 100, warning: 200 },
        drawdown: { critical: 30, warning: 20 },
        positionLoss: { critical: -60000, warning: -30000 }
      };
      
      const result = alertManager.validateSettings(validSettings);
      expect(result).toBe(true);
    });

    it('証拠金維持率の逆転設定を拒否する', () => {
      const invalidSettings = {
        marginLevel: { critical: 300, warning: 200 }, // 危険 > 警告
        drawdown: { critical: 30, warning: 20 },
        positionLoss: { critical: -60000, warning: -30000 }
      };
      
      const result = alertManager.validateSettings(invalidSettings);
      expect(result).toBe(false);
    });

    it('ドローダウンの逆転設定を拒否する', () => {
      const invalidSettings = {
        marginLevel: { critical: 100, warning: 200 },
        drawdown: { critical: 20, warning: 30 }, // 危険 < 警告
        positionLoss: { critical: -60000, warning: -30000 }
      };
      
      const result = alertManager.validateSettings(invalidSettings);
      expect(result).toBe(false);
    });

    it('負値範囲外のドローダウンを拒否する', () => {
      const invalidSettings = {
        marginLevel: { critical: 100, warning: 200 },
        drawdown: { critical: 150, warning: 20 }, // 100%超
        positionLoss: { critical: -60000, warning: -30000 }
      };
      
      const result = alertManager.validateSettings(invalidSettings);
      expect(result).toBe(false);
    });
  });

  describe('音声・バイブレーション機能', () => {
    it('criticalアラートで音声を再生する', () => {
      alertManager.settings.soundEnabled = true;
      const playSoundSpy = vi.spyOn(alertManager, 'playSound');
      
      const alert = { type: 'critical', message: 'Test' };
      alertManager.trigger(alert);
      
      expect(playSoundSpy).toHaveBeenCalledWith('critical');
    });

    it('バイブレーション設定時にvibrateを実行する', () => {
      alertManager.settings.vibrationEnabled = true;
      const vibrateSpy = vi.spyOn(alertManager, 'vibrate');
      
      const alert = { type: 'warning', message: 'Test' };
      alertManager.trigger(alert);
      
      expect(vibrateSpy).toHaveBeenCalledWith('warning');
    });

    it('設定無効時は音声・バイブレーションを実行しない', () => {
      alertManager.settings.soundEnabled = false;
      alertManager.settings.vibrationEnabled = false;
      
      const playSoundSpy = vi.spyOn(alertManager, 'playSound');
      const vibrateSpy = vi.spyOn(alertManager, 'vibrate');
      
      const alert = { type: 'critical', message: 'Test' };
      alertManager.trigger(alert);
      
      expect(playSoundSpy).not.toHaveBeenCalled();
      expect(vibrateSpy).not.toHaveBeenCalled();
    });
  });
});