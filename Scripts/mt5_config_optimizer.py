#!/usr/bin/env python3
"""
MT5設定ファイル直接最適化ツール
ポップアップ抑制・自動化設定をファイルレベルで実行
"""

import os
import shutil
from datetime import datetime

class MT5ConfigOptimizer:
    """MT5設定ファイル最適化クラス"""
    
    def __init__(self):
        self.config_dir = "/home/trader/.wine/drive_c/Program Files/MetaTrader 5/Config"
        self.common_ini = os.path.join(self.config_dir, "common.ini")
        self.terminal_ini = os.path.join(self.config_dir, "terminal.ini")
        
    def backup_configs(self):
        """設定ファイルバックアップ"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト/MT5_Results/config_backup_{timestamp}"
            os.makedirs(backup_dir, exist_ok=True)
            
            if os.path.exists(self.common_ini):
                shutil.copy2(self.common_ini, os.path.join(backup_dir, "common.ini"))
                print(f"✅ Backed up common.ini to {backup_dir}")
            
            if os.path.exists(self.terminal_ini):
                shutil.copy2(self.terminal_ini, os.path.join(backup_dir, "terminal.ini"))
                print(f"✅ Backed up terminal.ini to {backup_dir}")
                
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def read_utf16_config(self, file_path):
        """UTF-16設定ファイル読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-16le') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"❌ Failed to read {file_path}: {e}")
            return None
    
    def write_utf16_config(self, file_path, content):
        """UTF-16設定ファイル書き込み"""
        try:
            with open(file_path, 'w', encoding='utf-16le') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ Failed to write {file_path}: {e}")
            return False
    
    def optimize_common_ini(self):
        """common.ini最適化"""
        try:
            print("🔧 Optimizing common.ini...")
            
            content = self.read_utf16_config(self.common_ini)
            if not content:
                return False
            
            # ポップアップ抑制設定追加
            optimizations = {
                # Expert Advisors確認無効化
                "ConfirmDllCalls": "0",
                "ConfirmTrade": "0",
                "ConfirmOrder": "0",
                "ConfirmClose": "0",
                
                # 通知音無効化
                "NewsEnable": "0",
                "EmailNotifyEnable": "0",
                "AlertEnable": "0",
                "RequoteEnable": "0",
                
                # WebRequest許可
                "WebRequest": "1",
            }
            
            # [Experts]セクションに設定追加
            if "[Experts]" in content:
                # 既存のExpertsセクションを更新
                lines = content.split('\n')
                new_lines = []
                in_experts_section = False
                
                for line in lines:
                    if line.strip().startswith('[Experts]'):
                        in_experts_section = True
                        new_lines.append(line)
                        continue
                    elif line.strip().startswith('[') and in_experts_section:
                        # 新しいセクション開始 - Experts設定を追加
                        new_lines.append("ConfirmDllCalls=0")
                        new_lines.append("ConfirmTrade=0") 
                        new_lines.append("ConfirmOrder=0")
                        new_lines.append("ConfirmClose=0")
                        in_experts_section = False
                        new_lines.append(line)
                        continue
                    
                    new_lines.append(line)
                
                # ファイル末尾の場合
                if in_experts_section:
                    new_lines.append("ConfirmDllCalls=0")
                    new_lines.append("ConfirmTrade=0")
                    new_lines.append("ConfirmOrder=0") 
                    new_lines.append("ConfirmClose=0")
                
                content = '\n'.join(new_lines)
            
            # WebRequest設定更新
            content = content.replace("WebRequest=0", "WebRequest=1")
            
            # ファイルに書き込み
            if self.write_utf16_config(self.common_ini, content):
                print("✅ common.ini optimization completed")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ common.ini optimization failed: {e}")
            return False
    
    def add_trading_section(self):
        """Trading設定セクション追加"""
        try:
            print("🔧 Adding Trading configuration section...")
            
            content = self.read_utf16_config(self.common_ini)
            if not content:
                return False
            
            # Trading設定セクションを追加
            trading_section = """
[Trading]
ConfirmManualTrade=0
ConfirmOrderDeletion=0
ConfirmCloseByOpposite=0
OneClickTrading=1
"""
            
            # ファイル末尾に追加
            if not "[Trading]" in content:
                content += trading_section
                
                if self.write_utf16_config(self.common_ini, content):
                    print("✅ Trading section added successfully")
                    return True
            else:
                print("✅ Trading section already exists")
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ Trading section addition failed: {e}")
            return False
    
    def run_optimization(self):
        """最適化実行"""
        print("🚀 Starting MT5 Config File Optimization")
        print("=" * 50)
        
        # バックアップ作成
        if not self.backup_configs():
            print("❌ Backup failed - aborting optimization")
            return False
        
        # common.ini最適化
        if not self.optimize_common_ini():
            print("❌ common.ini optimization failed")
            return False
        
        # Trading設定追加
        if not self.add_trading_section():
            print("❌ Trading section addition failed")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 MT5 Configuration Optimization COMPLETED!")
        print("✅ Popup prevention settings applied")
        print("✅ Automatic trading optimized")
        print("🔄 MT5 restart recommended to apply changes")
        
        return True

def main():
    optimizer = MT5ConfigOptimizer()
    success = optimizer.run_optimization()
    
    if success:
        print("\n🏆 Configuration optimization successful!")
        print("🔄 Please restart MT5 to apply the changes")
    else:
        print("\n❌ Configuration optimization failed")

if __name__ == "__main__":
    main()