# 📚 Legacy Scripts インデックス

**整理日**: 2025-07-29  
**目的**: 過去開発スクリプトの整理・参照用アーカイブ  
**Phase 1**: 新アーキテクチャへの移行に伴う整理

---

## 📁 ディレクトリ構成

### mt5_analysis/ - MT5データ分析スクリプト群
**概要**: MT5取引データの各種分析・検証ツール  
**移行候補**: Phase 2-3での統計機能実装時に参考

#### 高精度分析系
- `mt5_accurate_trade_analyzer.py` - 高精度取引分析
- `mt5_professional_analyzer.py` - プロフェッショナル分析ツール
- `mt5_corrected_analyzer.py` - 修正版分析ツール

#### データ検証系  
- `mt5_data_structure_analyzer.py` - データ構造解析
- `mt5_data_corruption_verification.py` - データ破損検証
- `mt5_data_verification_system.py` - データ検証システム
- `mt5_extended_verification.py` - 拡張検証ツール
- `mt5_final_verification.py` - 最終検証ツール

#### 時系列問題対応系
- `mt5_time_reversal_analyzer.py` - 時系列逆転分析
- `mt5_timezone_hypothesis_verification.py` - タイムゾーン仮説検証

### wine_integration/ - Wine環境統合スクリプト群  
**概要**: LinuxでのMT5 Wine統合関連（廃止済み技術）  
**移行候補**: なし（新アーキテクチャでは不要）

#### Wine接続系
- `mt5_wine_server.py` - Wine環境サーバー
- `test_wine_mt5_basic.py` - Wine MT5基本テスト

#### 自動化系
- `mt5_auto_start_fixed.py` - MT5自動起動（修正版）
- `mt5_trading_enabler.py` - 取引有効化ツール
- `mt5_popup_prevention_optimizer.py` - ポップアップ防止最適化

### statistical_tools/ - 統計計算ツール群
**概要**: 取引統計・リスク計算関連  
**移行候補**: Phase 2-3での統計エンジン実装時に活用

#### 監視・分析系
- `mt5_realtime_monitoring_system.py` - リアルタイム監視システム
- `mt5_trading_monitor_fixed.py` - 取引監視（修正版）

#### 設定最適化系
- `mt5_config_optimizer.py` - 設定最適化ツール

### connection_tests/ - 接続テスト関連
**概要**: MT5接続テスト・検証スクリプト  
**移行候補**: Phase 1での連続稼働テスト参考

#### 接続テスト系
- `mt5_connection_test.py` - 基本接続テスト
- `mt5_full_connection_test.py` - 完全接続テスト  
- `test_mt5_connection_simple.py` - シンプル接続テスト
- `mt5_linux_client.py` - Linux クライアント

#### Git・自動化系
- `mt5_git_auto_commit.py` - Git自動コミット
- `check_mt5_ea_status.py` - EA状態チェック

---

## 🔄 移行・活用計画

### Phase 2での活用予定

#### データバリデーション実装時
**参考スクリプト**:
- `mt5_data_verification_system.py` → データ検証ロジック参考
- `mt5_data_structure_analyzer.py` → データ構造チェック参考

#### 統計計算実装時  
**参考スクリプト**:
- `mt5_professional_analyzer.py` → 高度統計指標の算出ロジック
- `mt5_accurate_trade_analyzer.py` → 精密な分析手法

### Phase 3での活用予定

#### 監視機能強化時
**参考スクリプト**:
- `mt5_realtime_monitoring_system.py` → リアルタイム監視の実装手法
- `mt5_trading_monitor_fixed.py` → 安定した監視ロジック

#### 設定管理実装時
**参考スクリプト**:
- `mt5_config_optimizer.py` → 設定最適化の手法

---

## 📋 スクリプト詳細情報

### 実装品質評価

#### A級（高品質・移行価値高）
- `mt5_professional_analyzer.py` - 包括的な分析機能
- `mt5_data_verification_system.py` - 堅牢なデータ検証
- `mt5_realtime_monitoring_system.py` - 実用的な監視システム

#### B級（特定機能で価値あり）  
- `mt5_accurate_trade_analyzer.py` - 高精度計算ロジック
- `mt5_corrected_analyzer.py` - 修正済み安定版
- `mt5_config_optimizer.py` - 設定管理手法

#### C級（参考程度）
- 接続テスト系 - 基本的な接続確認手法
- Wine統合系 - 技術的参考のみ（実用性なし）

### 技術的特記事項

#### データ処理の工夫
- **メモリ効率**: 大量データの分割処理手法
- **精度担保**: 浮動小数点演算の精度管理
- **エラー処理**: 堅牢な例外ハンドリング

#### 統計計算の手法
- **シャープレシオ**: 年率換算での正確な計算
- **ドローダウン**: リアルタイム最大値追跡
- **勝率分析**: 時間帯・通貨ペア別の詳細分析

---

## 🎯 新アーキテクチャとの関係

### 継承する概念
1. **データ検証**: 品質チェックの重要性
2. **リアルタイム処理**: 効率的な更新手法  
3. **統計計算**: 正確な指標算出手法
4. **エラー処理**: 堅牢性の確保手法

### 新規に改善する部分
1. **アーキテクチャ**: ファイル監視ベースのシンプル設計
2. **依存関係**: Wine環境からの完全脱却
3. **保守性**: モジュール化・テスト可能性の向上
4. **拡張性**: 段階的機能追加への対応

---

## 📝 利用ガイドライン

### 新機能実装時の参考手順
1. **該当カテゴリ確認**: 実装予定機能に関連するディレクトリを確認
2. **品質評価確認**: A級スクリプトを優先的に参考
3. **ロジック抽出**: 有用な処理ロジックを新アーキテクチャに適合
4. **改善実装**: 依存関係・エラー処理を新基準で再実装

### 注意事項
- **そのまま移植禁止**: 新アーキテクチャに合わせて再設計必須
- **依存関係確認**: 旧環境特有の依存関係を排除
- **テスト追加**: 移植ロジックには必ず単体テスト追加

---

**整理責任者**: Claude  
**承認**: kiro（予定）  
**次回更新**: Phase 2実装時（移行実績を記録）