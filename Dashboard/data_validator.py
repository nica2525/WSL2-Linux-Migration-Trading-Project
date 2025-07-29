#!/usr/bin/env python3
"""
Phase 2統計機能追加 - データバリデーション層
MT5データ品質チェック・不正データ検知・エラーハンドリング強化
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re

class MT5DataValidator:
    """MT5データバリデーション・品質チェック"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._load_validation_rules()
        self.error_history = []
        
    def _load_validation_rules(self) -> Dict[str, Any]:
        """バリデーションルール定義"""
        return {
            'account': {
                'balance': {'min': 0, 'max': 100000000, 'type': (int, float)},
                'equity': {'min': 0, 'max': 100000000, 'type': (int, float)},
                'profit': {'min': -10000000, 'max': 10000000, 'type': (int, float)}
            },
            'positions': {
                'ticket': {'min': 1, 'max': 999999999, 'type': int},
                'symbol': {'pattern': r'^[A-Z]{6}$', 'type': str},
                'type': {'values': ['buy', 'sell'], 'type': str},
                'volume': {'min': 0.01, 'max': 100.0, 'type': (int, float)},
                'profit': {'min': -100000, 'max': 100000, 'type': (int, float)},
                'open_price': {'min': 0.0001, 'max': 10.0, 'type': (int, float)},
                'current_price': {'min': 0.0001, 'max': 10.0, 'type': (int, float)}
            },
            'timestamp': {
                'format': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}$',
                'max_age_minutes': 5
            }
        }
    
    def validate_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """メインバリデーション実行"""
        errors = []
        
        try:
            # 基本構造チェック
            structure_errors = self._validate_structure(data)
            errors.extend(structure_errors)
            
            # タイムスタンプチェック
            timestamp_errors = self._validate_timestamp(data.get('timestamp'))
            errors.extend(timestamp_errors)
            
            # 口座データチェック
            if 'account' in data:
                account_errors = self._validate_account(data['account'])
                errors.extend(account_errors)
            
            # ポジションデータチェック
            if 'positions' in data:
                position_errors = self._validate_positions(data['positions'])
                errors.extend(position_errors)
            
            # データ整合性チェック
            consistency_errors = self._validate_consistency(data)
            errors.extend(consistency_errors)
            
            is_valid = len(errors) == 0
            
            # エラー履歴記録
            if errors:
                self.error_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'errors': errors,
                    'data_sample': str(data)[:200]
                })
                
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"バリデーション実行エラー: {str(e)}"
            self.logger.error(error_msg)
            return False, [error_msg]
    
    def _validate_structure(self, data: Dict[str, Any]) -> List[str]:
        """基本データ構造チェック"""
        errors = []
        
        # 必須フィールドチェック
        required_fields = ['timestamp', 'account', 'positions']
        for field in required_fields:
            if field not in data:
                errors.append(f"必須フィールド不足: {field}")
        
        # データタイプチェック
        if 'account' in data and not isinstance(data['account'], dict):
            errors.append("accountフィールドは辞書である必要があります")
            
        if 'positions' in data and not isinstance(data['positions'], list):
            errors.append("positionsフィールドはリストである必要があります")
        
        return errors
    
    def _validate_timestamp(self, timestamp: Optional[str]) -> List[str]:
        """タイムスタンプバリデーション"""
        errors = []
        
        if not timestamp:
            return ["タイムスタンプが設定されていません"]
        
        # フォーマットチェック
        pattern = self.validation_rules['timestamp']['format']
        if not re.match(pattern, timestamp):
            errors.append(f"タイムスタンプフォーマット不正: {timestamp}")
            return errors
        
        try:
            # 時刻解析・古さチェック
            ts_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now()
            age_minutes = (now - ts_time).total_seconds() / 60
            
            max_age = self.validation_rules['timestamp']['max_age_minutes']
            if age_minutes > max_age:
                errors.append(f"データが古すぎます: {age_minutes:.1f}分前 (制限: {max_age}分)")
                
        except ValueError as e:
            errors.append(f"タイムスタンプ解析エラー: {str(e)}")
        
        return errors
    
    def _validate_account(self, account: Dict[str, Any]) -> List[str]:
        """口座データバリデーション"""
        errors = []
        rules = self.validation_rules['account']
        
        for field, rule in rules.items():
            if field not in account:
                errors.append(f"口座データに{field}が不足")
                continue
                
            value = account[field]
            
            # データタイプチェック
            if not isinstance(value, rule['type']):
                errors.append(f"口座データ{field}のタイプが不正: {type(value)} (期待: {rule['type']})")
                continue
            
            # 数値範囲チェック
            if 'min' in rule and value < rule['min']:
                errors.append(f"口座データ{field}が最小値未満: {value} < {rule['min']}")
                
            if 'max' in rule and value > rule['max']:
                errors.append(f"口座データ{field}が最大値超過: {value} > {rule['max']}")
        
        return errors
    
    def _validate_positions(self, positions: List[Dict[str, Any]]) -> List[str]:
        """ポジションデータバリデーション"""
        errors = []
        rules = self.validation_rules['positions']
        
        if len(positions) > 100:
            errors.append(f"ポジション数が異常: {len(positions)}件 (制限: 100件)")
        
        for i, position in enumerate(positions):
            for field, rule in rules.items():
                if field not in position:
                    errors.append(f"ポジション{i+1}に{field}が不足")
                    continue
                    
                value = position[field]
                
                # データタイプチェック
                if not isinstance(value, rule['type']):
                    errors.append(f"ポジション{i+1}の{field}タイプが不正: {type(value)}")
                    continue
                
                # 文字列パターンチェック
                if 'pattern' in rule and isinstance(value, str):
                    if not re.match(rule['pattern'], value):
                        errors.append(f"ポジション{i+1}の{field}フォーマット不正: {value}")
                
                # 値リストチェック
                if 'values' in rule and value not in rule['values']:
                    errors.append(f"ポジション{i+1}の{field}値が不正: {value}")
                
                # 数値範囲チェック
                if isinstance(value, (int, float)):
                    if 'min' in rule and value < rule['min']:
                        errors.append(f"ポジション{i+1}の{field}が最小値未満: {value}")
                        
                    if 'max' in rule and value > rule['max']:
                        errors.append(f"ポジション{i+1}の{field}が最大値超過: {value}")
        
        return errors
    
    def _validate_consistency(self, data: Dict[str, Any]) -> List[str]:
        """データ整合性チェック"""
        errors = []
        
        try:
            account = data.get('account', {})
            positions = data.get('positions', [])
            
            # 口座残高とエクイティの関係チェック
            balance = account.get('balance', 0)
            equity = account.get('equity', 0)
            profit = account.get('profit', 0)
            
            # MT5固有の誤差を許容した整合性チェック
            expected_equity = balance + profit
            equity_diff = abs(equity - expected_equity)
            # MT5の計算精度・スプレッド・手数料を考慮した許容範囲
            tolerance = max(balance * 0.001, 10.0)  # 0.1%または10ドル
            if equity_diff > tolerance:
                errors.append(f"口座データ整合性エラー: equity({equity}) != balance({balance}) + profit({profit}), 差額{equity_diff:.2f} > 許容値{tolerance:.2f}")
            
            # ポジション利益合計チェック（部分的ポジション表示を考慮）
            if positions and len(positions) > 1:  # 複数ポジションの場合のみチェック
                position_profit_total = sum(pos.get('profit', 0) for pos in positions)
                profit_diff = abs(profit - position_profit_total)
                # スワップ・手数料・未実現損益を考慮した許容範囲
                position_tolerance = max(abs(profit) * 0.2, 100.0)  # 20%または100ドル
                if profit_diff > position_tolerance:
                    errors.append(f"ポジション利益合計不一致: 口座利益({profit}) vs ポジション合計({position_profit_total}), 差額{profit_diff:.2f} > 許容値{position_tolerance:.2f}")
            # 注意: 単一ポジション表示の場合は口座全体利益と異なるため比較しない
            
            # 価格整合性チェック（buy/sellの利益方向）
            for i, position in enumerate(positions):
                pos_type = position.get('type')
                open_price = position.get('open_price', 0)
                current_price = position.get('current_price', 0)
                pos_profit = position.get('profit', 0)
                
                if pos_type == 'buy':
                    expected_positive = current_price > open_price
                    actual_positive = pos_profit > 0
                    if expected_positive != actual_positive and abs(pos_profit) > 1:
                        errors.append(f"ポジション{i+1} buy利益方向不整合: 価格{open_price}->{current_price}, 利益{pos_profit}")
                
                elif pos_type == 'sell':
                    expected_positive = current_price < open_price
                    actual_positive = pos_profit > 0
                    if expected_positive != actual_positive and abs(pos_profit) > 1:
                        errors.append(f"ポジション{i+1} sell利益方向不整合: 価格{open_price}->{current_price}, 利益{pos_profit}")
        
        except Exception as e:
            errors.append(f"整合性チェック実行エラー: {str(e)}")
        
        return errors
    
    def sanitize_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """データ修正・サニタイズ"""
        sanitized = data.copy()
        fixes = []
        
        try:
            # タイムスタンプ修正
            if 'timestamp' not in sanitized or not sanitized['timestamp']:
                sanitized['timestamp'] = datetime.now().isoformat()
                fixes.append("タイムスタンプを現在時刻で補完")
            
            # 口座データ修正
            if 'account' in sanitized:
                account_fixes = self._sanitize_account(sanitized['account'])
                fixes.extend(account_fixes)
            
            # ポジションデータ修正
            if 'positions' in sanitized:
                position_fixes = self._sanitize_positions(sanitized['positions'])
                fixes.extend(position_fixes)
            
            return sanitized, fixes
            
        except Exception as e:
            self.logger.error(f"データサニタイズエラー: {e}")
            return data, [f"サニタイズ失敗: {str(e)}"]
    
    def _sanitize_account(self, account: Dict[str, Any]) -> List[str]:
        """口座データサニタイズ"""
        fixes = []
        rules = self.validation_rules['account']
        
        for field, rule in rules.items():
            if field not in account:
                account[field] = 0.0
                fixes.append(f"口座データ{field}をデフォルト値で補完")
                continue
            
            value = account[field]
            
            # 数値型変換
            if not isinstance(value, rule['type']):
                try:
                    account[field] = float(value) if isinstance(rule['type'], tuple) else rule['type'](value)
                    fixes.append(f"口座データ{field}をタイプ変換")
                except:
                    account[field] = 0.0
                    fixes.append(f"口座データ{field}を変換失敗によりデフォルト値設定")
            
            # 範囲修正
            if 'min' in rule and account[field] < rule['min']:
                account[field] = rule['min']
                fixes.append(f"口座データ{field}を最小値に修正")
                
            if 'max' in rule and account[field] > rule['max']:
                account[field] = rule['max']
                fixes.append(f"口座データ{field}を最大値に修正")
        
        return fixes
    
    def _sanitize_positions(self, positions: List[Dict[str, Any]]) -> List[str]:
        """ポジションデータサニタイズ"""
        fixes = []
        
        # ポジション数制限
        if len(positions) > 100:
            positions = positions[:100]
            fixes.append("ポジション数を100件に制限")
        
        # 無効ポジション除去
        valid_positions = []
        for i, position in enumerate(positions):
            if self._is_valid_position_structure(position):
                valid_positions.append(position)
            else:
                fixes.append(f"無効ポジション{i+1}を除去")
        
        positions[:] = valid_positions
        return fixes
    
    def _is_valid_position_structure(self, position: Dict[str, Any]) -> bool:
        """ポジション基本構造チェック"""
        required_fields = ['ticket', 'symbol', 'type', 'volume', 'profit']
        return all(field in position for field in required_fields)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """バリデーション統計取得"""
        if not self.error_history:
            return {'total_validations': 0, 'error_count': 0, 'error_rate': 0.0}
        
        total_errors = sum(len(entry['errors']) for entry in self.error_history)
        
        return {
            'total_validations': len(self.error_history),
            'error_count': total_errors,
            'error_rate': total_errors / len(self.error_history),
            'recent_errors': self.error_history[-5:],
            'last_validation': self.error_history[-1]['timestamp'] if self.error_history else None
        }

# 使用例・テスト関数
def test_validator():
    """バリデーター動作テスト"""
    validator = MT5DataValidator()
    
    # テストデータ（正常）
    valid_data = {
        "timestamp": datetime.now().isoformat(),
        "account": {
            "balance": 3000000.0,
            "equity": 2990000.0,
            "profit": -10000.0
        },
        "positions": [
            {
                "ticket": 123456,
                "symbol": "EURUSD",
                "type": "buy",
                "volume": 0.01,
                "profit": -50.0,
                "open_price": 1.0850,
                "current_price": 1.0840
            }
        ]
    }
    
    is_valid, errors = validator.validate_data(valid_data)
    print(f"正常データ: valid={is_valid}, errors={len(errors)}")
    
    # テストデータ（異常）
    invalid_data = {
        "timestamp": "invalid-timestamp",
        "account": {
            "balance": -1000000,  # 負の残高
            "equity": "invalid",  # 文字列
        },
        "positions": [
            {
                "ticket": "abc",  # 文字列チケット
                "symbol": "EUR",  # 不正シンボル
                "type": "invalid_type",
                "volume": -0.01,  # 負のボリューム
                "profit": 999999999  # 異常な利益
            }
        ]
    }
    
    is_valid, errors = validator.validate_data(invalid_data)
    print(f"異常データ: valid={is_valid}, errors={len(errors)}")
    for error in errors:
        print(f"  - {error}")
    
    # サニタイズテスト
    sanitized, fixes = validator.sanitize_data(invalid_data)
    print(f"サニタイズ: {len(fixes)}件の修正")
    for fix in fixes:
        print(f"  - {fix}")

if __name__ == "__main__":
    test_validator()