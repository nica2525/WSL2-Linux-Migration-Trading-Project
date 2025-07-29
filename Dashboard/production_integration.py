#!/usr/bin/env python3
"""
実運用統合システム
MT5データ → バリデーション → データベース → 統計計算 → ダッシュボード表示
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from data_validator import MT5DataValidator
from database_manager import DatabaseManager
from statistics_calculator import StatisticsCalculator

class ProductionMT5Integration:
    """実運用MT5統合システム"""
    
    def __init__(self):
        self.setup_logging()
        self.validator = MT5DataValidator()
        self.db = DatabaseManager()  
        self.stats_calc = StatisticsCalculator(self.db)
        self.data_file = Path("/tmp/mt5_data/positions.json")
        
        # 実運用設定
        self.last_processed_timestamp = None
        self.error_count = 0
        self.max_errors = 10  # エラー上限
        self.processing_timeout = 30  # 処理タイムアウト（秒）
        
    def setup_logging(self):
        """本番用ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/Dashboard/production.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def process_mt5_data(self) -> Dict[str, Any]:
        """MT5データ処理メインフロー"""
        start_time = time.time()
        
        try:
            # 1. データ読み込み
            raw_data = self._read_mt5_data()
            if not raw_data:
                return self._create_result('no_data', 'MT5データなし')
            
            # 重複処理回避
            if self._is_duplicate_data(raw_data):
                return self._create_result('duplicate', 'データ重複')
            
            # 2. バリデーション（実運用対応版）
            is_valid, validation_errors = self.validator.validate_data(raw_data)
            if not is_valid:
                # 重大エラーのみ処理停止、軽微なエラーは警告のみ
                critical_errors = self._filter_critical_errors(validation_errors)
                if critical_errors:
                    self.error_count += 1
                    return self._create_result('validation_failed', f'重大エラー: {critical_errors}')
                else:
                    self.logger.warning(f'軽微なバリデーションエラー: {validation_errors}')
            
            # 3. データ永続化
            if not self.db.store_mt5_data(raw_data):
                self.error_count += 1
                return self._create_result('db_error', 'データベース保存失敗')
            
            # 4. 統計計算（非ブロッキング）
            stats = self._calculate_statistics_safe()
            
            # 5. 成功記録
            self.last_processed_timestamp = raw_data.get('timestamp')
            self.error_count = max(0, self.error_count - 1)  # エラーカウント減算
            
            processing_time = time.time() - start_time
            
            return self._create_result('success', '処理完了', {
                'processing_time_ms': processing_time * 1000,
                'validation_errors': validation_errors,
                'statistics': stats
            })
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f'処理中の予期しないエラー: {e}')
            return self._create_result('error', f'システムエラー: {str(e)}')
        
        finally:
            # 処理時間監視
            total_time = time.time() - start_time
            if total_time > self.processing_timeout:
                self.logger.warning(f'処理時間超過: {total_time:.2f}秒')
    
    def _read_mt5_data(self) -> Optional[Dict[str, Any]]:
        """MT5データ読み込み（実運用対応）"""
        try:
            if not self.data_file.exists():
                return None
                
            # ファイルロック対応の読み込み
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    with open(self.data_file, 'r') as f:
                        data = json.load(f)
                        return data
                except (json.JSONDecodeError, IOError) as e:
                    if attempt < max_attempts - 1:
                        time.sleep(0.1)  # 短時間待機
                        continue
                    raise e
                    
        except Exception as e:
            self.logger.error(f'MT5データ読み込みエラー: {e}')
            return None
    
    def _is_duplicate_data(self, data: Dict[str, Any]) -> bool:
        """重複データチェック"""
        current_timestamp = data.get('timestamp')
        if current_timestamp and current_timestamp == self.last_processed_timestamp:
            return True
        return False
    
    def _filter_critical_errors(self, errors: list) -> list:
        """重大エラーフィルタリング"""
        critical_keywords = ['必須フィールド不足', 'タイムスタンプ解析エラー', 'データタイプが不正']
        critical_errors = []
        
        for error in errors:
            if any(keyword in error for keyword in critical_keywords):
                critical_errors.append(error)
                
        return critical_errors
    
    def _calculate_statistics_safe(self) -> Dict[str, Any]:
        """統計計算（安全実行）"""
        try:
            # 軽量な統計のみ計算（実運用考慮）
            win_rate_stats = self.stats_calc.calculate_win_rate_stats(days=1)
            daily_stats = self.db.calculate_daily_stats()
            
            return {
                'win_rate': win_rate_stats.get('win_rate', 0),
                'total_trades': win_rate_stats.get('total_trades', 0),
                'daily_profit': daily_stats.get('net_profit', 0),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f'統計計算エラー（継続実行）: {e}')
            return {'error': str(e), 'calculated_at': datetime.now().isoformat()}
    
    def _create_result(self, status: str, message: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """処理結果作成"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'message': message,
            'error_count': self.error_count
        }
        
        if data:
            result.update(data)
            
        return result
    
    def get_system_health(self) -> Dict[str, Any]:
        """システムヘルスチェック"""
        try:
            # データベース統計
            db_stats = self.db.get_database_stats()
            
            # バリデーション統計
            validation_stats = self.validator.get_validation_stats()
            
            # ファイル状態
            data_file_status = {
                'exists': self.data_file.exists(),
                'size': self.data_file.stat().st_size if self.data_file.exists() else 0,
                'modified': datetime.fromtimestamp(self.data_file.stat().st_mtime).isoformat() if self.data_file.exists() else None
            }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'healthy' if self.error_count < self.max_errors else 'degraded',
                'error_count': self.error_count,
                'last_processed': self.last_processed_timestamp,
                'database': db_stats,
                'validation': validation_stats,
                'data_file': data_file_status
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def run_continuous_processing(self, interval_seconds: int = 5):
        """連続処理実行（実運用モード）"""
        self.logger.info(f'実運用連続処理開始 (間隔: {interval_seconds}秒)')
        
        try:
            while True:
                # システム健全性チェック
                if self.error_count >= self.max_errors:
                    self.logger.error(f'エラー数上限到達: {self.error_count}/{self.max_errors}')
                    break
                
                # データ処理実行
                result = self.process_mt5_data()
                
                # 結果ログ
                if result['status'] == 'success':
                    self.logger.debug(f"処理成功: {result['processing_time_ms']:.1f}ms")
                else:
                    self.logger.warning(f"処理結果: {result['status']} - {result['message']}")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            self.logger.info('処理が手動停止されました')
        except Exception as e:
            self.logger.error(f'連続処理エラー: {e}')

def main():
    """メイン実行"""
    integration = ProductionMT5Integration()
    
    # システムヘルスチェック
    health = integration.get_system_health()
    print(f"システム状態: {health['status']}")
    print(f"エラー数: {health['error_count']}")
    
    # 単発処理テスト
    result = integration.process_mt5_data()
    print(f"処理結果: {result['status']} - {result['message']}")
    
    if result['status'] == 'success':
        print(f"処理時間: {result['processing_time_ms']:.1f}ms")
        if 'statistics' in result:
            stats = result['statistics']
            print(f"勝率: {stats.get('win_rate', 0):.1f}%")
            print(f"取引数: {stats.get('total_trades', 0)}")

if __name__ == "__main__":
    main()