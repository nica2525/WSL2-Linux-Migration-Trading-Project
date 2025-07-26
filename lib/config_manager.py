#!/usr/bin/env python3
"""
設定管理ライブラリ
YAML設定ファイルの統一管理
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """設定ファイル統一管理クラス"""
    
    def __init__(self, project_root: Optional[str] = None):
        if project_root:
            self.project_root = Path(project_root)
        else:
            # スクリプトの場所から推定
            self.project_root = Path(__file__).parent.parent
        
        self.config_dir = self.project_root / "Config"
        self._configs = {}
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        if config_name in self._configs:
            return self._configs[config_name]
        
        config_file = self.config_dir / f"{config_name}.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._configs[config_name] = config
            return config
        
        except yaml.YAMLError as e:
            raise ValueError(f"YAML読み込みエラー ({config_file}): {e}")
        except Exception as e:
            raise Exception(f"設定ファイル読み込みエラー ({config_file}): {e}")
    
    def get_mt5_config(self) -> Dict[str, Any]:
        """MT5設定取得"""
        return self.load_config("mt5_config")
    
    def get_ea_config(self) -> Dict[str, Any]:
        """EA設定取得"""
        return self.load_config("ea_config")
    
    def get_trading_config(self) -> Dict[str, Any]:
        """取引設定取得"""
        return self.load_config("trading_config")
    
    def get_system_config(self) -> Dict[str, Any]:
        """システム設定取得"""
        return self.load_config("system_config")
    
    def get_value(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """
        ネストした設定値取得
        例: get_value("mt5_config", "rpyc.port", 18812)
        """
        config = self.load_config(config_name)
        
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_mt5_terminal_path(self) -> str:
        """MT5ターミナルパス取得"""
        return self.get_value("mt5_config", "mt5.terminal_path")
    
    def get_rpyc_config(self) -> Dict[str, Any]:
        """RPYC設定取得"""
        return self.get_value("mt5_config", "rpyc", {})
    
    def get_log_config(self) -> Dict[str, Any]:
        """ログ設定取得"""
        return self.get_value("system_config", "logging", {})
    
    def get_cron_config(self) -> Dict[str, Any]:
        """cron設定取得"""
        return self.get_value("system_config", "cron", {})
    
    def expand_path(self, path: str) -> str:
        """パス展開（環境変数・相対パス解決）"""
        # 環境変数展開
        expanded = os.path.expandvars(path)
        
        # ホームディレクトリ展開
        expanded = os.path.expanduser(expanded)
        
        # 絶対パス化
        if not os.path.isabs(expanded):
            expanded = str(self.project_root / expanded)
        
        return expanded
    
    def reload_config(self, config_name: str):
        """設定リロード"""
        if config_name in self._configs:
            del self._configs[config_name]
        return self.load_config(config_name)
    
    def clear_cache(self):
        """設定キャッシュクリア"""
        self._configs.clear()


# グローバルインスタンス
config_manager = ConfigManager()


def get_config(config_name: str) -> Dict[str, Any]:
    """設定取得（簡易版）"""
    return config_manager.load_config(config_name)


def get_value(config_name: str, key_path: str, default: Any = None) -> Any:
    """設定値取得（簡易版）"""
    return config_manager.get_value(config_name, key_path, default)


if __name__ == "__main__":
    # テスト実行
    try:
        cm = ConfigManager()
        
        print("=== 設定テスト ===")
        print(f"MT5パス: {cm.get_mt5_terminal_path()}")
        print(f"RPYCポート: {cm.get_value('mt5_config', 'rpyc.port')}")
        print(f"ログレベル: {cm.get_value('system_config', 'logging.level')}")
        print(f"EA名: {cm.get_value('ea_config', 'ea.name')}")
        print("設定管理ライブラリテスト完了")
        
    except Exception as e:
        print(f"テストエラー: {e}")