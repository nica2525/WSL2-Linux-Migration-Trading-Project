#!/usr/bin/env python3
"""
バックテスト自動化パイプライン
戦略ファイル変更検知→自動テスト実行→結果記録
"""

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path


class BacktestAutomation:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.strategy_dir = self.project_dir
        self.results_dir = self.project_dir / "results" / "automated_backtests"
        self.cache_file = self.project_dir / ".backtest_cache.json"
        self.log_file = self.project_dir / ".backtest_automation.log"

        # 結果ディレクトリ作成
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # ログ設定
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # 監視対象戦略ファイル（重要なもののみ）
        self.strategy_files = [
            "cost_resistant_wfa_execution_FINAL.py",
            "corrected_adaptive_wfa_system.py",
            "reality_enhanced_wfa.py",
            "market_regime_detector.py",
            "final_wfa_execution.py",
        ]

    def get_file_hash(self, file_path):
        """ファイルハッシュ値取得"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return None

    def load_cache(self):
        """キャッシュファイル読み込み"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file) as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}

    def save_cache(self, cache_data):
        """キャッシュファイル保存"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logging.error(f"キャッシュ保存エラー: {e}")

    def detect_changes(self):
        """戦略ファイル変更検知"""
        cache = self.load_cache()
        changed_files = []

        for strategy_file in self.strategy_files:
            file_path = self.strategy_dir / strategy_file
            if file_path.exists():
                current_hash = self.get_file_hash(file_path)
                cached_hash = cache.get(strategy_file)

                if current_hash != cached_hash:
                    changed_files.append(strategy_file)
                    cache[strategy_file] = current_hash

        if changed_files:
            self.save_cache(cache)

        return changed_files

    def run_strategy_test(self, strategy_file):
        """個別戦略テスト実行"""
        start_time = datetime.now()
        strategy_path = self.strategy_dir / strategy_file

        # テスト実行環境設定
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_dir)

        try:
            # 軽量テスト実行（短期間・少ないパラメータ）
            result = subprocess.run(
                ["python3", str(strategy_path)],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5分タイムアウト
                env=env,
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 結果記録
            test_result = {
                "strategy": strategy_file,
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:],  # 最後の1000文字のみ
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "success": result.returncode == 0,
            }

            # 結果ファイル保存
            result_file = (
                self.results_dir
                / f"{strategy_file}_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(result_file, "w") as f:
                json.dump(test_result, f, indent=2)

            return test_result

        except subprocess.TimeoutExpired:
            logging.error(f"戦略テストタイムアウト: {strategy_file}")
            return {
                "strategy": strategy_file,
                "timestamp": start_time.isoformat(),
                "duration_seconds": 300,
                "return_code": -1,
                "stdout": "",
                "stderr": "テストタイムアウト (5分)",
                "success": False,
            }
        except Exception as e:
            logging.error(f"戦略テストエラー: {strategy_file} - {e}")
            return {
                "strategy": strategy_file,
                "timestamp": start_time.isoformat(),
                "duration_seconds": 0,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
            }

    def generate_summary_report(self):
        """サマリーレポート生成"""
        # 最新のテスト結果を収集
        latest_results = {}

        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file) as f:
                    result = json.load(f)

                strategy = result["strategy"]
                timestamp = result["timestamp"]

                if (
                    strategy not in latest_results
                    or timestamp > latest_results[strategy]["timestamp"]
                ):
                    latest_results[strategy] = result
            except Exception:
                continue

        # レポート作成
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_strategies": len(self.strategy_files),
            "tested_strategies": len(latest_results),
            "successful_tests": sum(1 for r in latest_results.values() if r["success"]),
            "failed_tests": sum(1 for r in latest_results.values() if not r["success"]),
            "strategy_results": latest_results,
        }

        # レポート保存
        report_file = self.results_dir / "latest_summary.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def run_automation_cycle(self):
        """自動化サイクル実行"""
        logging.info("バックテスト自動化サイクル開始")

        # 変更検知
        changed_files = self.detect_changes()

        if not changed_files:
            logging.info("戦略ファイル変更なし")
            return

        logging.info(f"変更検知: {changed_files}")

        # 変更されたファイルのテスト実行
        for strategy_file in changed_files:
            logging.info(f"戦略テスト開始: {strategy_file}")
            result = self.run_strategy_test(strategy_file)

            if result["success"]:
                logging.info(
                    f"戦略テスト成功: {strategy_file} ({result['duration_seconds']:.1f}秒)"
                )
            else:
                logging.error(f"戦略テスト失敗: {strategy_file}")

        # サマリーレポート生成
        summary = self.generate_summary_report()
        logging.info(
            f"サマリー更新: {summary['successful_tests']}/{summary['tested_strategies']} 成功"
        )


def main():
    """メイン実行"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    automation = BacktestAutomation(project_dir)
    automation.run_automation_cycle()


if __name__ == "__main__":
    main()
