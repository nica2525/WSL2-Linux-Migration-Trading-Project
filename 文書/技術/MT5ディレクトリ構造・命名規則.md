# MT5ディレクトリ構造・命名規則

## ディレクトリ構造

```
MT5/
├── EA/                           # MT5 Expert Advisors
│   ├── JamesORB_v1.0.mq5       # 本番EA（バージョン管理）
│   ├── JamesORB_Dev.mq5        # 開発版EA
│   └── Backups/                # EAバックアップ
│       └── JamesORB_YYYYMMDD_HHMM.mq5
│
├── Include/                      # インクルードファイル
│   ├── OrderManagement.mqh      # 注文管理クラス
│   ├── RiskCalculation.mqh      # リスク計算クラス
│   └── TradeUtilities.mqh       # トレードユーティリティ
│
├── Scripts/                      # 分析・ユーティリティスクリプト
│   ├── mt5_trade_analyzer.py    # トレード分析スクリプト
│   ├── mt5_data_verifier.py     # データ検証スクリプト
│   └── mt5_statistics.py        # 統計計算スクリプト
│
├── Results/                      # バックテスト・実取引結果
│   ├── Backtest/                # バックテスト結果
│   │   ├── YYYYMMDD_HHMM/      # タイムスタンプ別フォルダ
│   │   │   ├── Report_Backtest_[ID].xlsx
│   │   │   ├── Report_Forward_[ID].xlsx
│   │   │   └── Operation_Log.txt
│   │   └── Summary.json         # 結果サマリー
│   │
│   └── Live/                    # 実取引結果
│       ├── Demo/                # デモ口座結果
│       └── Real/                # リアル口座結果
│
├── Config/                       # 設定ファイル
│   ├── ea_settings.json         # EA設定
│   ├── risk_parameters.json     # リスクパラメータ
│   └── symbol_config.json       # 通貨ペア別設定
│
├── Logs/                         # ログファイル
│   ├── ea_execution.log         # EA実行ログ
│   ├── trade_history.log        # トレード履歴ログ
│   └── error.log                # エラーログ
│
└── Documentation/                # MT5関連ドキュメント
    ├── Setup_Guide.md           # 環境構築ガイド
    ├── EA_Manual.md             # EA操作マニュアル
    └── API_Reference.md         # API仕様書

```

## ファイル命名規則

### 1. EA（Expert Advisor）ファイル
- **本番版**: `[EA名]_v[バージョン番号].mq5`
  - 例: `JamesORB_v1.0.mq5`, `BreakoutTrader_v2.3.mq5`
- **開発版**: `[EA名]_Dev.mq5`
  - 例: `JamesORB_Dev.mq5`
- **テスト版**: `[EA名]_Test_[機能名].mq5`
  - 例: `JamesORB_Test_RiskManagement.mq5`

### 2. バックテスト結果ファイル
- **Excelレポート**: `Report_[テストタイプ]_[ID].xlsx`
  - 例: `Report_Backtest_20250724.xlsx`
  - 例: `Report_Forward_20250724.xlsx`
- **操作ログ**: `Operation_Log.txt`（固定名）
- **サマリー**: `Summary_[YYYYMMDD].json`

### 3. スクリプトファイル
- **Python分析スクリプト**: `mt5_[機能名]_[動作].py`
  - 例: `mt5_trade_analyzer.py`
  - 例: `mt5_data_verifier.py`
  - 例: `mt5_statistics_calculator.py`

### 4. ログファイル
- **実行ログ**: `[プロセス名]_[YYYYMMDD].log`
  - 例: `ea_execution_20250724.log`
  - 例: `trade_history_20250724.log`

### 5. 設定ファイル
- **JSON形式**: `[設定カテゴリ]_[詳細].json`
  - 例: `ea_settings.json`
  - 例: `risk_parameters.json`
  - 例: `symbol_config_EURUSD.json`

## バージョン管理規則

### 1. セマンティックバージョニング
- **形式**: `v[メジャー].[マイナー].[パッチ]`
- **例**: `v1.0.0`, `v1.2.3`, `v2.0.0`

### 2. バージョンアップ基準
- **メジャー**: 大規模な仕様変更、後方互換性なし
- **マイナー**: 機能追加、後方互換性あり
- **パッチ**: バグ修正、小規模な改善

### 3. リリースタグ
- **形式**: `release-v[バージョン]-[YYYYMMDD]`
- **例**: `release-v1.0.0-20250724`

## フォルダ作成時の注意事項

1. **タイムスタンプフォルダ**
   - 形式: `YYYYMMDD_HHMM`（24時間表記）
   - 例: `20250724_1430`

2. **バックアップフォルダ**
   - 週次/月次でアーカイブ化
   - 3ヶ月以上経過したものは圧縮保存

3. **結果フォルダ**
   - バックテスト結果は日付別に整理
   - 実取引結果は月別に整理

## 移行作業チェックリスト

- [ ] 既存のMT5_EA/フォルダをMT5/EA/に移動
- [ ] 既存のMT5_Results/フォルダをMT5/Results/Backtest/に移動
- [ ] 既存のMT5_Git_Setup/フォルダの内容を確認し、必要なものをMT5/Config/に移動
- [ ] Scripts/内のmt5_*.pyファイルをMT5/Scripts/に移動
- [ ] 新しいディレクトリ構造に合わせてCLAUDE.mdを更新
- [ ] .gitignoreファイルを更新（ログファイル、一時ファイルの除外）
