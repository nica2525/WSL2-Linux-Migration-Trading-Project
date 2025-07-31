# Python依存関係包括分析レポート - 完全版

**生成日時**: 2025-07-31 08:15:00 JST
**プロジェクト**: ブレイクアウト手法プロジェクト
**分析ファイル数**: 149個のPythonファイル
**分析完了**: 包括的システム依存関係解析完了

## 📊 分析サマリー

| 項目 | 値 |
|------|-----|
| 総Pythonファイル数 | 150 |
| インポートありファイル数 | 139 |
| 外部ライブラリ数 | 90 |
| 内部モジュール数 | 14 |
| 循環依存検出数 | 0 |

## 📚 外部ライブラリ使用頻度

| 順位 | ライブラリ | 使用ファイル数 | 使用率 |
|------|-----------|---------------|--------|
| 1 | `datetime` | 118 | 84.9% |
| 2 | `json` | 104 | 74.8% |
| 3 | `typing` | 92 | 66.2% |
| 4 | `os` | 70 | 50.4% |
| 5 | `sys` | 49 | 35.3% |
| 6 | `pathlib` | 46 | 33.1% |
| 7 | `logging` | 43 | 30.9% |
| 8 | `pandas` | 35 | 25.2% |
| 9 | `time` | 35 | 25.2% |
| 10 | `numpy` | 28 | 20.1% |
| 11 | `dataclasses` | 20 | 14.4% |
| 12 | `re` | 17 | 12.2% |
| 13 | `enum` | 16 | 11.5% |
| 14 | `asyncio` | 15 | 10.8% |
| 15 | `threading` | 11 | 7.9% |
| 16 | `subprocess` | 11 | 7.9% |
| 17 | `aiosqlite` | 10 | 7.2% |
| 18 | `math` | 10 | 7.2% |
| 19 | `multi_timeframe_breakout_strategy` | 8 | 5.8% |
| 20 | `random` | 7 | 5.0% |

## 🔗 内部モジュール依存関係

### realtime_signal_generator
- **使用ファイル数**: 11
- **使用ファイル**: emergency_protection, position_management, database_manager, performance_reporter, performance_benchmark など（他6ファイル）

### position_management
- **使用ファイル数**: 9
- **使用ファイル**: emergency_protection, database_manager, performance_reporter, health_monitor, automation_compatibility など（他4ファイル）

### risk_management
- **使用ファイル数**: 8
- **使用ファイル**: emergency_protection, database_manager, performance_reporter, health_monitor, automation_compatibility など（他3ファイル）

### database_manager
- **使用ファイル数**: 7
- **使用ファイル**: performance_reporter, health_monitor, automation_compatibility, system_state_manager, statistics_calculator など（他2ファイル）

### emergency_protection
- **使用ファイル数**: 5
- **使用ファイル**: health_monitor, automation_compatibility, system_state_manager, phase3_integrated_system, integrated_system_test

### communication.tcp_bridge
- **使用ファイル数**: 2
- **使用ファイル**: position_management, realtime_signal_generator

### communication.file_bridge
- **使用ファイル数**: 2
- **使用ファイル**: position_management, realtime_signal_generator

### performance_reporter
- **使用ファイル数**: 2
- **使用ファイル**: automation_compatibility, integrated_system_test

### health_monitor
- **使用ファイル数**: 2
- **使用ファイル**: automation_compatibility, integrated_system_test

### Scripts.collaboration_tracker
- **使用ファイル数**: 2
- **使用ファイル**: start_collaboration, record_design

### mcp_database_connector
- **使用ファイル数**: 1
- **使用ファイル**: enhanced_mcp_database_integration

### lib.logger_setup
- **使用ファイル数**: 1
- **使用ファイル**: collaboration_tracker

### automation_compatibility
- **使用ファイル数**: 1
- **使用ファイル**: integrated_system_test

### phase3_integrated_system
- **使用ファイル数**: 1
- **使用ファイル**: integrated_system_test



## 📋 依存関係マトリックス（主要ファイル×主要ライブラリ）

| ファイル | datetime | json | typing | os | sys | pathlib | logging | pandas | time | numpy | dataclasses | re | enum | asyncio | threading | 合計 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| automation_compatibility |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |  ✓  | 25 |
| performance_reporter |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |  ✓  |     | 22 |
| health_monitor |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |  ✓  | 22 |
| system_state_manager |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |     | 21 |
| realtime_signal_generator |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |     |  ✓  |  ✓  | 18 |
| file_bridge |     |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |     |     |  ✓  | 18 |
| integrated_system_test |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |  ✓  |     |     |     |     |     |     |  ✓  |     | 17 |
| emergency_protection |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |  ✓  | 16 |
| database_manager |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |     | 15 |
| position_management |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |     | 14 |
| risk_management |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |     | 14 |
| enhanced_csv_prototype |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  | 14 |
| alpha_vantage_integration |  ✓  |  ✓  |  ✓  |     |     |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |     |  ✓  | 13 |
| mt5_realtime_monitoring_s |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |  ✓  |     |     |     |     |  ✓  | 13 |
| phase3_integrated_system |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |  ✓  |     |  ✓  |     |     |     |     |  ✓  |     | 12 |
| app |  ✓  |  ✓  |     |  ✓  |     |  ✓  |  ✓  |     |  ✓  |     |     |     |     |     |  ✓  | 12 |
| parallel_wfa_optimization |  ✓  |  ✓  |  ✓  |     |     |  ✓  |     |  ✓  |  ✓  |  ✓  |     |     |     |     |     | 12 |
| mt5_connection |     |     |  ✓  |  ✓  |     |  ✓  |     |     |  ✓  |     |     |     |     |     |     | 11 |
| enhanced_parallel_wfa_wit |  ✓  |  ✓  |  ✓  |     |     |  ✓  |     |  ✓  |  ✓  |  ✓  |     |     |     |     |     | 11 |
| tcp_bridge |     |  ✓  |  ✓  |     |     |     |  ✓  |     |  ✓  |     |  ✓  |     |  ✓  |  ✓  |  ✓  | 10 |


## 🔄 循環依存分析

☑️ 循環依存は検出されませんでした。コードベースの依存関係は健全です。


## パフォーマンス分析結果

### 依存関係の深さ
- **最大依存深度**: 0
- **最多依存ファイル**: 25個の依存関係
- **依存クラスター数**: 10

### 重いライブラリの影響
**中影響ライブラリ** (9個):
- `datetime`: 84.9%のファイルで使用
- `json`: 74.8%のファイルで使用
- `typing`: 66.2%のファイルで使用
- `os`: 50.4%のファイルで使用
- `pandas`: 25.2%のファイルで使用

### 予想インポート時間影響
- 重いライブラリ総使用数: 454
- 推定起動時間影響: 高



## 🎯 最適化推奨事項

## 🟡 中優先度最適化項目

### 1. 共通インポートの統合
**問題**: import json を104ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 104

### 2. 共通インポートの統合
**問題**: import pandas を35ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 35

### 3. 共通インポートの統合
**問題**: from datetime import datetime を116ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 116

### 4. 共通インポートの統合
**問題**: from typing import Dict を90ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 90

### 5. 共通インポートの統合
**問題**: from typing import List を76ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 76

### 6. 共通インポートの統合
**問題**: from typing import Optional を68ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 68

### 7. 共通インポートの統合
**問題**: from typing import Any を26ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 26

### 8. 共通インポートの統合
**問題**: import os を70ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 70

### 9. 共通インポートの統合
**問題**: import asyncio を15ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 15

### 10. 共通インポートの統合
**問題**: import time を36ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 36

### 11. 共通インポートの統合
**問題**: import logging を43ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 43

### 12. 共通インポートの統合
**問題**: from datetime import timedelta を36ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 36

### 13. 共通インポートの統合
**問題**: from dataclasses import dataclass を20ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 20

### 14. 共通インポートの統合
**問題**: from dataclasses import asdict を11ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 11

### 15. 共通インポートの統合
**問題**: from typing import Tuple を30ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 30

### 16. 共通インポートの統合
**問題**: from typing import Union を13ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 13

### 17. 共通インポートの統合
**問題**: from enum import Enum を16ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 16

### 18. 共通インポートの統合
**問題**: import sys を49ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 49

### 19. 共通インポートの統合
**問題**: from pathlib import Path を46ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 46

### 20. 共通インポートの統合
**問題**: from position_management import PositionTracker を12ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 12

### 21. 共通インポートの統合
**問題**: import numpy を28ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 28

### 22. 共通インポートの統合
**問題**: import math を11ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 11

### 23. 共通インポートの統合
**問題**: import re を17ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 17

### 24. 共通インポートの統合
**問題**: from database_manager import DatabaseManager を11ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 11

### 25. 共通インポートの統合
**問題**: import subprocess を11ファイルで使用

**推奨対策**: 共通ユーティリティモジュールの作成

**影響ファイル数**: 11

## 🟢 低優先度最適化項目

### 1. 大規模クラスター最適化 (Cluster 1)
**問題**: 80ファイルの密結合クラスター

**推奨対策**: モジュール分割、インターフェース定義の検討

**影響ファイル数**: 80

### 2. 大規模クラスター最適化 (Cluster 2)
**問題**: 19ファイルの密結合クラスター

**推奨対策**: モジュール分割、インターフェース定義の検討

**影響ファイル数**: 19



## 📈 詳細統計

### ファイル別依存関係統計（上位10）

| ファイル | 直接依存数 | 総依存数 | 最大深度 |
|---------|-----------|---------|---------|
| automation_compatibility | 25 | 25 | 0 |
| performance_reporter | 22 | 22 | 0 |
| health_monitor | 22 | 22 | 0 |
| system_state_manager | 21 | 21 | 0 |
| realtime_signal_generator | 18 | 18 | 0 |
| file_bridge | 18 | 18 | 0 |
| integrated_system_test | 17 | 17 | 0 |
| emergency_protection | 16 | 16 | 0 |
| database_manager | 15 | 15 | 0 |
| position_management | 14 | 14 | 0 |


### 依存関係クラスター分析

クラスター数: 10

**クラスター1** (80ファイル):
- ファイル例: mcp_database_connector, reality_cost_analyzer, risk_management_theoretical_analysis, reality_enhanced_wfa, quality_management_protocol
- その他75ファイル
- 共通依存関係数: 0

**クラスター2** (19ファイル):
- ファイル例: emergency_protection, position_management, database_manager, performance_reporter, performance_benchmark
- その他14ファイル
- 共通依存関係数: 0

**クラスター7** (6ファイル):
- ファイル例: simple_dashboard, mt5_full_connection_test, record_design, mt5_auto_start_fixed, mt5_linux_client
- その他1ファイル
- 共通依存関係数: 1

**クラスター9** (3ファイル):
- ファイル例: cron_git_auto_save, logger_setup, mt5_git_auto_commit
- 共通依存関係数: 1

**クラスター10** (3ファイル):
- ファイル例: error_handler, mt5_connection, __init__
- 共通依存関係数: 3


## 🏆 結論・総合評価

### 依存関係健全性スコア

| 評価項目 | スコア | 評価 |
|----------|--------|------|
| 循環依存 | 100/100 | 優秀 |
| 依存深度 | 130/100 | 優秀 |
| ライブラリ多様性 | 100/100 | 優秀 |
| **総合スコア** | **110/100** | **優秀** |


### 推奨アクション

1. **即座に対応**:
   - 高優先度最適化項目の実施
   - 重いライブラリの使用量削減

2. **段階的改善**:
   - 中優先度項目の計画的実施
   - コードベースのモジュール化推進

3. **継続監視**:
   - 定期的な依存関係分析実行
   - 新規追加ライブラリの影響評価

---

*このレポートは自動生成されました。詳細な分析データは以下ファイルを参照してください:*
- `import_dependency_analysis.json`
- `dependency_network_analysis.json`
