# 開発標準書

**作成日時**: 2025年7月18日 07:32 JST  
**作成者**: Kiro AI IDE  
**プロジェクト**: ブレイクアウト手法実運用システム統合プロジェクト

## コーディング規約

### Python コーディング規約

#### 基本方針
- **PEP 8準拠**: Python標準コーディングスタイルに準拠
- **型ヒント必須**: すべての関数・メソッドに型ヒントを記述
- **docstring必須**: すべてのクラス・関数にdocstringを記述
- **既存コード保護**: Gemini満点システムのコーディングスタイルを尊重

#### 命名規則
```python
# クラス名: PascalCase
class TradingSignalGenerator:
    pass

# 関数・変数名: snake_case
def generate_trading_signal(market_data: pd.DataFrame) -> TradingSignal:
    signal_quality = calculate_signal_quality()
    return signal_quality

# 定数: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_MS = 5000

# プライベート属性: 先頭アンダースコア
class SignalProcessor:
    def __init__(self):
        self._internal_state = {}
        self.__private_data = []
```

#### ファイル構成規則
```python
#!/usr/bin/env python3
"""
モジュール説明
機能概要と使用目的を記述
"""

# 標準ライブラリ
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# サードパーティライブラリ
import pandas as pd
import numpy as np

# プロジェクト内モジュール
from .existing_module import ExistingClass
from .communication import BridgeInterface

# 定数定義
DEFAULT_CONFIG = {...}

# クラス定義
class NewComponent:
    """新規コンポーネントクラス"""
    pass

# 関数定義
def utility_function() -> bool:
    """ユーティリティ関数"""
    pass

# メイン実行部
if __name__ == "__main__":
    main()
```

#### エラーハンドリング規約
```python
# 具体的例外クラスの使用
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error(f"通信エラー: {e}")
    raise CommunicationException(f"MT4接続失敗: {e}") from e
except ValueError as e:
    logger.warning(f"データ検証エラー: {e}")
    return default_value
except Exception as e:
    logger.critical(f"予期しないエラー: {e}")
    raise SystemException("システム異常") from e
finally:
    cleanup_resources()

# カスタム例外の定義
class TradingSystemException(Exception):
    """取引システム基底例外"""
    pass

class CommunicationException(TradingSystemException):
    """通信関連例外"""
    pass
```

### MQL4 コーディング規約

#### 基本方針
- **MT4標準準拠**: MetaTrader 4標準コーディングスタイルに準拠
- **関数分割**: 機能ごとの関数分割による可読性向上
- **エラーハンドリング**: 全操作でエラーチェック実施
- **ログ出力**: 重要操作のログ出力必須

#### 命名規則
```mql4
// 関数名: PascalCase
bool ReceivePythonSignal()
{
    return true;
}

// 変数名: camelCase
double currentPrice = 0.0;
int maxRetryCount = 3;
string signalData = "";

// 定数: UPPER_SNAKE_CASE
#define MAX_POSITIONS 10
#define DEFAULT_TIMEOUT 5000

// グローバル変数: g_prefix
double g_accountBalance = 0.0;
bool g_systemEnabled = true;
```

#### ファイル構成規則
```mql4
//+------------------------------------------------------------------+
//| Expert Advisor Name                                              |
//| Copyright 2025, Trading System Project                          |
//+------------------------------------------------------------------+
#property copyright "Trading System Project"
#property version   "1.00"
#property strict

// インクルードファイル
#include <stdlib.mqh>
#include <stderror.mqh>

// 定数定義
#define SIGNAL_FILE_PATH "C:\\MT4_Bridge\\signals.json"
#define MAX_RETRY_ATTEMPTS 3

// グローバル変数
double g_lastSignalTime = 0;
bool g_communicationActive = false;

// 初期化関数
int OnInit()
{
    // 初期化処理
    return INIT_SUCCEEDED;
}

// メイン処理関数
void OnTick()
{
    // メイン処理
}

// 終了処理関数
void OnDeinit(const int reason)
{
    // 終了処理
}

// カスタム関数群
bool InitializeCommunication()
{
    // 通信初期化
    return true;
}
```

#### エラーハンドリング規約
```mql4
// エラーチェック必須
bool ExecuteTrade(string symbol, double volume)
{
    int ticket = OrderSend(symbol, OP_BUY, volume, Ask, 3, 0, 0);
    if(ticket < 0)
    {
        int error = GetLastError();
        Print("取引実行エラー: ", ErrorDescription(error));
        return false;
    }
    
    Print("取引実行成功: チケット番号 ", ticket);
    return true;
}

// リトライ機構
bool SendSignalWithRetry(string signalData)
{
    for(int i = 0; i < MAX_RETRY_ATTEMPTS; i++)
    {
        if(SendSignal(signalData))
        {
            return true;
        }
        Print("送信失敗、リトライ中... (", i+1, "/", MAX_RETRY_ATTEMPTS, ")");
        Sleep(1000);
    }
    
    Print("送信失敗: 最大リトライ回数に達しました");
    return false;
}
```

## テスト戦略

### テスト分類と方針

#### 単体テスト（Unit Test）
**対象**: 個別関数・クラスメソッド
**方針**: 
- 全パブリック関数のテストケース作成必須
- エッジケース・異常系テストの充実
- モック使用による外部依存関係の分離
- カバレッジ90%以上を目標

```python
# テスト例
import unittest
from unittest.mock import Mock, patch
import pytest

class TestSignalGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = SignalGenerator()
        self.mock_data = create_mock_market_data()
    
    def test_generate_signal_normal_case(self):
        """正常ケースのシグナル生成テスト"""
        signal = self.generator.generate_signal(self.mock_data)
        self.assertIsInstance(signal, TradingSignal)
        self.assertGreater(signal.quality, 0.0)
    
    def test_generate_signal_empty_data(self):
        """空データでの異常系テスト"""
        with self.assertRaises(ValueError):
            self.generator.generate_signal(pd.DataFrame())
    
    @patch('communication.tcp_bridge.socket')
    def test_communication_failure(self, mock_socket):
        """通信失敗時のテスト"""
        mock_socket.side_effect = ConnectionError()
        result = self.generator.send_signal(mock_signal)
        self.assertFalse(result)
```

#### 統合テスト（Integration Test）
**対象**: コンポーネント間連携
**方針**:
- 実際の通信プロトコルを使用したテスト
- データフロー全体の検証
- パフォーマンス要件の検証
- 障害シナリオでの動作確認

```python
class TestSystemIntegration(unittest.TestCase):
    def test_end_to_end_signal_flow(self):
        """エンドツーエンドシグナルフローテスト"""
        # 1. シグナル生成
        signal = self.signal_generator.generate_signal(test_data)
        
        # 2. 通信ブリッジ経由送信
        success = self.bridge.send_signal(signal)
        self.assertTrue(success)
        
        # 3. MT4での受信確認
        received_signal = self.mt4_stub.get_last_signal()
        self.assertEqual(signal.action, received_signal.action)
        
        # 4. レイテンシ検証
        latency = received_signal.timestamp - signal.timestamp
        self.assertLess(latency.total_seconds() * 1000, 50)  # 50ms以下
```

#### システムテスト（System Test）
**対象**: システム全体
**方針**:
- 本番環境に近い条件でのテスト
- 長時間稼働テスト
- 負荷テスト・ストレステスト
- 復旧テスト

```python
class TestSystemPerformance(unittest.TestCase):
    def test_high_frequency_signal_processing(self):
        """高頻度シグナル処理テスト"""
        signals = generate_test_signals(1000)  # 1000シグナル
        
        start_time = time.time()
        for signal in signals:
            self.system.process_signal(signal)
        end_time = time.time()
        
        # スループット検証
        throughput = len(signals) / (end_time - start_time)
        self.assertGreater(throughput, 100)  # 100シグナル/秒以上
    
    def test_system_recovery_after_crash(self):
        """システムクラッシュ後の復旧テスト"""
        # 1. 正常状態でのスナップショット作成
        self.system.create_snapshot()
        
        # 2. システムクラッシュシミュレーション
        self.system.simulate_crash()
        
        # 3. システム再起動と復旧
        self.system.restart()
        recovery_time = self.system.get_recovery_time()
        
        # 4. 復旧時間検証
        self.assertLess(recovery_time, 180)  # 3分以内
```

### 品質基準

#### コード品質基準
- **複雑度**: サイクロマティック複雑度10以下
- **重複**: コード重複率5%以下
- **カバレッジ**: テストカバレッジ90%以上
- **静的解析**: pylint, mypy エラー0件

#### パフォーマンス基準
- **レイテンシ**: 通信レイテンシ50ms以下
- **スループット**: シグナル処理100件/分以上
- **可用性**: システム稼働率99%以上
- **復旧時間**: 障害からの復旧3分以内

#### セキュリティ基準
- **脆弱性**: 既知脆弱性0件
- **アクセス制御**: 最小権限原則遵守
- **データ保護**: 機密データ暗号化100%
- **監査**: 全重要操作のログ記録

## ドキュメント標準

### ドキュメント分類

#### 技術ドキュメント
- **API仕様書**: 全インターフェースの詳細仕様
- **アーキテクチャ図**: システム構成の視覚的表現
- **データベース設計書**: テーブル構造とリレーション
- **通信プロトコル仕様**: メッセージ形式と手順

#### 運用ドキュメント
- **インストールガイド**: システム導入手順
- **設定マニュアル**: 各種設定項目の説明
- **トラブルシューティング**: 問題解決手順
- **メンテナンスガイド**: 定期保守作業手順

#### 開発ドキュメント
- **開発環境構築**: 開発環境セットアップ手順
- **コーディングガイド**: 本標準書の詳細版
- **テスト手順書**: テスト実行とレポート作成
- **リリース手順書**: 本番環境への展開手順

### ドキュメント品質基準

#### 内容品質
- **正確性**: 技術的内容の正確性100%
- **完全性**: 必要情報の網羅性
- **一貫性**: 用語・表記の統一
- **最新性**: 実装との同期維持

#### 形式品質
- **可読性**: 構造化された読みやすい文書
- **検索性**: 目次・索引による情報検索容易性
- **保守性**: 更新・修正の容易性
- **アクセス性**: 関係者による容易なアクセス

## ログ標準

### ログレベル定義

#### CRITICAL
- システム停止を伴う致命的エラー
- データ破損・セキュリティ侵害
- 即座の対応が必要な事象

#### ERROR
- 機能停止を伴うエラー
- 取引実行失敗・通信断絶
- 自動復旧不可能な異常

#### WARNING
- 機能継続可能な警告
- パフォーマンス劣化・リソース不足
- 注意が必要な状況

#### INFO
- 正常な動作状況の記録
- システム開始・終了・設定変更
- 重要な処理の完了通知

#### DEBUG
- 開発・デバッグ用詳細情報
- 変数値・処理フロー
- 本番環境では通常無効

### ログ形式標準

```python
# ログ設定例
import logging

# フォーマット定義
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ハンドラー設定
handler = logging.FileHandler('trading_system.log')
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(handler)

# 使用例
logger.info("システム開始")
logger.warning(f"通信レイテンシ高: {latency}ms")
logger.error(f"取引実行失敗: {error_message}")
logger.critical("システム緊急停止")
```

### ログ管理方針

#### ローテーション
- **日次ローテーション**: 毎日0時にログファイル切り替え
- **サイズ制限**: 1ファイル最大100MB
- **保存期間**: 30日間保存後自動削除
- **圧縮**: 7日経過後gzip圧縮

#### セキュリティ
- **機密情報マスキング**: パスワード・APIキー等の自動マスキング
- **アクセス制限**: ログファイルの読み取り権限制限
- **改ざん防止**: ログファイルの書き込み専用権限設定
- **監査証跡**: ログアクセス履歴の記録