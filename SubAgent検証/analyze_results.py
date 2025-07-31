#!/usr/bin/env python3
"""
Sub-Agent検証結果分析ツール
検証結果から境界線を可視化
"""

import json
import os
from datetime import datetime

import yaml


class TestResultAnalyzer:
    def __init__(self):
        self.results = []
        self.boundary_matrix = {}

    def load_results(self, result_dir="test_results"):
        """検証結果ファイルを読み込み"""
        for file in os.listdir(result_dir):
            if file.endswith(".yaml") or file.endswith(".json"):
                with open(os.path.join(result_dir, file)) as f:
                    if file.endswith(".yaml"):
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                    self.results.append(data)

    def analyze_boundaries(self):
        """境界線分析"""
        boundaries = {
            "file_size": {"safe": 0, "warning": 0, "danger": 0},
            "file_count": {"safe": 0, "warning": 0, "danger": 0},
            "execution_time": {"fast": 0, "normal": 0, "slow": 0, "freeze": 0},
        }

        for result in self.results:
            # ファイルサイズ境界
            size = result.get("file_size_kb", 0)
            if size < 10:
                boundaries["file_size"]["safe"] = max(
                    boundaries["file_size"]["safe"], size
                )
            elif size < 100:
                boundaries["file_size"]["warning"] = max(
                    boundaries["file_size"]["warning"], size
                )
            else:
                boundaries["file_size"]["danger"] = max(
                    boundaries["file_size"]["danger"], size
                )

            # 実行時間境界
            time = result.get("execution_time", 0)
            if time < 10:
                boundaries["execution_time"]["fast"] += 1
            elif time < 30:
                boundaries["execution_time"]["normal"] += 1
            elif time < 120:
                boundaries["execution_time"]["slow"] += 1
            else:
                boundaries["execution_time"]["freeze"] += 1

        return boundaries

    def generate_report(self):
        """境界線レポート生成"""
        report = f"""# Sub-Agent境界線検証結果レポート
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 検証サマリー
- 総テストケース数: {len(self.results)}
- 成功: {sum(1 for r in self.results if r.get('status') == 'success')}
- 警告: {sum(1 for r in self.results if r.get('status') == 'warning')}
- フリーズ: {sum(1 for r in self.results if r.get('status') == 'freeze')}

## 📊 境界線分析結果

### ファイルサイズ境界
| カテゴリ | 最大サイズ | 推奨事項 |
|---------|-----------|---------|
| 安全 | <10KB | 問題なく使用可能 |
| 注意 | 10-100KB | 監視しながら使用 |
| 危険 | >100KB | 使用を避ける |

### ファイル数境界
| カテゴリ | ファイル数 | 推奨事項 |
|---------|-----------|---------|
| 安全 | 1-5 | 問題なく使用可能 |
| 注意 | 5-20 | タスク分割推奨 |
| 危険 | >20 | 使用を避ける |

### 実行時間分布
| カテゴリ | 時間 | 件数 | 割合 |
|---------|-----|------|------|
| 高速 | <10秒 | {快速件数} | {快速割合}% |
| 通常 | 10-30秒 | {通常件数} | {通常割合}% |
| 遅延 | 30-120秒 | {遅延件数} | {遅延割合}% |
| フリーズ | >120秒 | {フリーズ件数} | {フリーズ割合}% |

## 🚨 推奨使用ガイドライン

### ✅ 安全な使用条件
- ファイルサイズ: 10KB以下
- ファイル数: 5個以下
- タスク種別: 読取・簡単な分析
- 複雑度: 単純な構造

### ⚠️ 注意が必要な条件
- ファイルサイズ: 10-50KB
- ファイル数: 5-10個
- タスク種別: 複雑な分析・編集
- 複雑度: 中程度の相互依存

### ❌ 避けるべき条件
- ファイルサイズ: 100KB以上
- ファイル数: 20個以上
- タスク種別: 大規模実装
- 複雑度: 高度な相互依存

## 💡 実用的アドバイス

1. **段階的アプローチ**
   - 最初は小さなタスクで動作確認
   - 成功したら徐々に規模拡大
   - フリーズ兆候があれば即座に縮小

2. **タスク分割戦略**
   - 大きなファイルは事前に分割
   - 複数ファイルタスクはバッチ処理
   - コンテキストを最小限に維持

3. **監視とリカバリー**
   - 30秒ルール: 応答なければ中断検討
   - プロセス監視の習慣化
   - リカバリー手順の事前準備
"""
        return report

    def visualize_boundaries(self):
        """境界線の可視化"""
        # 実装予定: matplotlib使用の境界線グラフ
        pass


def main():
    analyzer = TestResultAnalyzer()

    # サンプル結果（実際の検証後に置き換え）
    sample_results = [
        {
            "test_id": "T001",
            "file_size_kb": 0.1,
            "execution_time": 3,
            "status": "success",
        },
        {
            "test_id": "T002",
            "file_size_kb": 0.9,
            "execution_time": 8,
            "status": "success",
        },
        {
            "test_id": "T003",
            "file_size_kb": 45.8,
            "execution_time": 35,
            "status": "warning",
        },
        {
            "test_id": "T004",
            "file_size_kb": 98.5,
            "execution_time": 180,
            "status": "freeze",
        },
    ]

    analyzer.results = sample_results
    analyzer.analyze_boundaries()
    report = analyzer.generate_report()

    print(report)

    # レポート保存
    with open("boundary_analysis_report.md", "w") as f:
        f.write(report)


if __name__ == "__main__":
    main()
