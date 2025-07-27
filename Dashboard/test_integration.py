#!/usr/bin/env python3
"""
統合テスト - 実際のシステム動作確認
無意味な単体テストではなく、システム全体の動作を確認
"""

import requests
import sqlite3
import time
import json
from pathlib import Path

class IntegrationTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.auth = ("trader", "jamesorb2025")
        self.db_path = Path("dashboard.db")
        
    def test_auth_system(self):
        """認証システムテスト"""
        print("🔐 認証システムテスト...")
        
        # 認証なしアクセス（失敗想定）
        response = requests.get(f"{self.base_url}/mobile")
        if response.status_code == 401:
            print("✅ 認証なしアクセス拒否: OK")
        else:
            print(f"❌ 認証なしアクセス拒否失敗: {response.status_code}")
            
        # 正しい認証（成功想定）
        response = requests.get(f"{self.base_url}/mobile", auth=self.auth)
        if response.status_code == 200:
            print("✅ 正しい認証でアクセス成功: OK")
            return True
        else:
            print(f"❌ 正しい認証でアクセス失敗: {response.status_code}")
            return False
    
    def test_database_connection(self):
        """データベース接続テスト"""
        print("🗄️ データベース接続テスト...")
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM balance_history")
                count = cursor.fetchone()[0]
                print(f"✅ データベース接続成功、レコード数: {count}")
                
                # 最新レコード確認
                cursor.execute("SELECT * FROM balance_history ORDER BY timestamp DESC LIMIT 1")
                latest = cursor.fetchone()
                if latest:
                    print(f"✅ 最新レコード: {latest}")
                    return True
                else:
                    print("⚠️ データベースにレコードがありません")
                    return False
                    
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            return False
    
    def test_mt5_mock_data(self):
        """MT5モックデータテスト"""
        print("📊 MT5モックデータテスト...")
        
        try:
            response = requests.get(f"{self.base_url}/api/account", auth=self.auth)
            if response.status_code == 200:
                data = response.json()
                required_fields = ['balance', 'equity', 'margin', 'free_margin']
                
                for field in required_fields:
                    if field in data:
                        print(f"✅ {field}: {data[field]}")
                    else:
                        print(f"❌ 必須フィールド不足: {field}")
                        return False
                        
                return True
            else:
                print(f"❌ API応答エラー: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ MT5データテストエラー: {e}")
            return False
    
    def test_websocket_emulation(self):
        """WebSocket通信エミュレーション"""
        print("🔌 WebSocket通信エミュレーション...")
        
        # WebSocketライブラリがない場合のHTTPエミュレーション
        try:
            response = requests.get(f"{self.base_url}/api/positions", auth=self.auth)
            if response.status_code == 200:
                positions = response.json()
                print(f"✅ ポジション取得成功: {len(positions)}件")
                
                if positions:
                    pos = positions[0]
                    print(f"✅ サンプルポジション: {pos.get('symbol', 'N/A')} {pos.get('profit', 0)}")
                
                return True
            else:
                print(f"❌ ポジション取得エラー: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ WebSocket通信エラー: {e}")
            return False
    
    def test_performance(self):
        """パフォーマンステスト"""
        print("⚡ パフォーマンステスト...")
        
        start_time = time.time()
        
        # 複数リクエストの応答時間測定
        endpoints = ['/mobile', '/api/account', '/api/positions', '/api/balance_history']
        
        for endpoint in endpoints:
            req_start = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", auth=self.auth)
            req_time = (time.time() - req_start) * 1000
            
            if response.status_code == 200:
                print(f"✅ {endpoint}: {req_time:.1f}ms")
            else:
                print(f"❌ {endpoint}: エラー {response.status_code}")
        
        total_time = (time.time() - start_time) * 1000
        print(f"✅ 総実行時間: {total_time:.1f}ms")
        
        return total_time < 5000  # 5秒以内
    
    def run_all_tests(self):
        """全テスト実行"""
        print("=" * 60)
        print("🧪 統合テスト開始 - 実際のシステム動作確認")
        print("=" * 60)
        
        tests = [
            ("認証システム", self.test_auth_system),
            ("データベース接続", self.test_database_connection), 
            ("MT5モックデータ", self.test_mt5_mock_data),
            ("WebSocket通信", self.test_websocket_emulation),
            ("パフォーマンス", self.test_performance)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, result))
                print()
            except Exception as e:
                print(f"❌ {name}テスト例外: {e}")
                results.append((name, False))
                print()
        
        # 結果サマリー
        print("=" * 60)
        print("📋 テスト結果サマリー")
        print("=" * 60)
        
        passed = 0
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {name}")
            if result:
                passed += 1
        
        success_rate = (passed / len(results)) * 100
        print(f"\n🏆 成功率: {passed}/{len(results)} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 統合テスト合格 - システム正常動作確認")
            return True
        else:
            print("💥 統合テスト不合格 - システムに問題あり")
            return False

if __name__ == "__main__":
    tester = IntegrationTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)