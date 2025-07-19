#!/usr/bin/env python3
"""
MCP互換性テストスクリプト
既存のMCPサービスが正常に動作することを確認
"""

import subprocess
import json
import time
import sys

def test_mcp_service(service_name):
    """個別MCPサービスのテスト"""
    print(f"\n=== {service_name} テスト開始 ===")
    
    # settings.jsonから設定を読み込み
    with open('/home/trader/.claude/settings.json', 'r') as f:
        settings = json.load(f)
    
    if service_name not in settings['mcpServers']:
        print(f"❌ {service_name} が設定に見つかりません")
        return False
    
    service_config = settings['mcpServers'][service_name]
    cmd = [service_config['command']] + service_config.get('args', [])
    
    print(f"実行コマンド: {' '.join(cmd)}")
    
    try:
        # プロセスを起動（タイムアウト付き）
        process = subprocess.Popen(
            cmd,
            env={**subprocess.os.environ, **service_config.get('env', {})},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 3秒待機して起動確認
        time.sleep(3)
        
        if process.poll() is None:
            print(f"✅ {service_name} 起動成功")
            process.terminate()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {service_name} 起動失敗")
            if stderr:
                print(f"エラー: {stderr.decode()[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ {service_name} テスト中にエラー: {str(e)}")
        return False

def main():
    """全MCPサービスの互換性テスト"""
    print("🔍 MCP互換性テスト開始")
    
    # テスト対象サービス（重要度順）
    test_services = [
        'gemini-cli',     # 現在使用中
        'sqlite',         # データベース系
        'duckdb',         # データベース系
        'context7'        # 新規追加
    ]
    
    results = {}
    
    for service in test_services:
        results[service] = test_mcp_service(service)
        time.sleep(1)  # サービス間の待機
    
    # 結果サマリー
    print("\n\n=== テスト結果サマリー ===")
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for service, success in results.items():
        status = "✅ 正常" if success else "❌ 異常"
        print(f"{service}: {status}")
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)")
    
    if success_count == total_count:
        print("\n🎉 すべてのMCPサービスが正常に動作しています")
        return 0
    else:
        print("\n⚠️ 一部のMCPサービスに問題があります")
        return 1

if __name__ == "__main__":
    sys.exit(main())