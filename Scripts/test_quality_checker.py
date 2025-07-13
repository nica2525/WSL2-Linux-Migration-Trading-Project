#!/usr/bin/env python3
"""
品質チェッカーの動作検証テスト
False positive/negative検出の正確性を検証
"""

import tempfile
from pathlib import Path

from quality_checker import QualityChecker


class TestQualityChecker:
    """品質チェッカーテストクラス"""

    def setup_method(self):
        """テスト前準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.checker = QualityChecker(self.temp_dir)

    def create_test_file(self, filename, content):
        """テスト用ファイル作成"""
        file_path = Path(self.temp_dir) / filename
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def test_lookahead_bias_detection(self):
        """Look-ahead bias検出テスト"""
        # TRUE POSITIVE: 実際のLook-ahead bias
        bad_code = """
def generate_signal(data):
    current_bar = data.iloc[-1]
    signal_price = current_bar['close']  # Look-ahead bias
    return {'action': 'BUY', 'price': signal_price}
"""

        # FALSE POSITIVE回避: 時間切れ決済（正当なケース）
        good_code = """
def time_exit_logic(position, current_bar):
    if hours_held >= max_holding_hours:
        bar_close = current_bar['close']  # 時間切れ決済
        exit_price = bar_close
        return exit_price  # 正当な決済
"""

        # テストファイル作成
        self.create_test_file("bad_strategy.py", bad_code)
        self.create_test_file("good_strategy.py", good_code)

        # 品質チェック実行
        issues = self.checker.scan_quality_issues()

        # 検証
        bad_file_issues = [i for i in issues if "bad_strategy.py" in i["file"]]
        good_file_issues = [i for i in issues if "good_strategy.py" in i["file"]]

        assert len(bad_file_issues) > 0, "Look-ahead biasを検出できていない"
        assert len(good_file_issues) == 0, "False positiveが発生している"

        print("✅ Look-ahead bias検出テスト成功")
        print(f"   True positive: {len(bad_file_issues)}件")
        print(f"   False positive: {len(good_file_issues)}件")

    def test_random_generation_detection(self):
        """ランダム生成検出テスト"""
        # TRUE POSITIVE: ランダム結果生成
        bad_code = """
def calculate_backtest_results():
    if random.random() < 0.4:
        return {'pf': 1.8, 'trades': 150}  # 偽装結果
"""

        # FALSE POSITIVE回避: 正当なランダム使用
        good_code = """
def generate_test_data():
    noise = random.random() * 0.001  # 価格ノイズ生成
    return base_price + noise
"""

        self.create_test_file("fake_results.py", bad_code)
        self.create_test_file("data_generator.py", good_code)

        issues = self.checker.scan_quality_issues()

        fake_issues = [i for i in issues if "fake_results.py" in i["file"]]
        data_issues = [i for i in issues if "data_generator.py" in i["file"]]

        assert len(fake_issues) > 0, "ランダム生成を検出できていない"
        assert len(data_issues) == 0, "正当なランダム使用でFalse positive"

        print("✅ ランダム生成検出テスト成功")
        print(f"   True positive: {len(fake_issues)}件")
        print(f"   False positive: {len(data_issues)}件")

    def test_confidence_scoring(self):
        """信頼度スコアテスト"""
        test_code = """
def generate_signal(data):
    signal_price = data.iloc[-1]['close']  # 高信頼度
    return signal_price

def some_function():
    price = current_bar['close']  # 中信頼度
    return price
"""

        self.create_test_file("confidence_test.py", test_code)
        issues = self.checker.scan_quality_issues()

        if issues:
            # generate_signal内の問題は高信頼度であるべき
            signal_issues = [
                i
                for i in issues
                if "generate_signal" in i.get("context", {}).get("function", "")
            ]
            [
                i
                for i in issues
                if "generate_signal" not in i.get("context", {}).get("function", "")
            ]

            if signal_issues:
                assert signal_issues[0]["confidence"] > 0.8, "generate_signal内の信頼度が低い"

            print("✅ 信頼度スコアテスト成功")
            print(
                f"   Signal関数内: {signal_issues[0]['confidence']:.2f}"
                if signal_issues
                else "   Signal関数内: なし"
            )

    def test_false_positive_contexts(self):
        """False positive回避テスト"""
        # 時間切れ決済の正当なケース
        time_exit_code = """
def check_time_exit(position, current_bar):
    if position['hours_held'] >= max_holding_hours:
        # TIME_EXIT - 強制決済
        bar_close = current_bar['close']
        final_price = bar_close
        return final_price
"""

        # 強制決済の正当なケース
        forced_exit_code = """
def emergency_exit(position, current_bar):
    # FORCED_EXIT
    exit_price = current_bar['close']
    return exit_price
"""

        self.create_test_file("time_exit.py", time_exit_code)
        self.create_test_file("forced_exit.py", forced_exit_code)

        issues = self.checker.scan_quality_issues()

        time_issues = [i for i in issues if "time_exit.py" in i["file"]]
        forced_issues = [i for i in issues if "forced_exit.py" in i["file"]]

        assert len(time_issues) == 0, f"時間切れ決済でFalse positive: {len(time_issues)}件"
        assert len(forced_issues) == 0, f"強制決済でFalse positive: {len(forced_issues)}件"

        print("✅ False positive回避テスト成功")
        print(f"   時間切れ決済: {len(time_issues)}件（期待値: 0）")
        print(f"   強制決済: {len(forced_issues)}件（期待値: 0）")

    def test_pattern_frequency_analysis(self):
        """パターン頻度分析テスト"""
        # 複数パターンのテストファイル
        mixed_code = """
def bad_strategy():
    price = current_bar['close']  # lookahead_bias
    if random.random() < 0.5:     # random_generation
        return price

def another_bad():
    future_price = data.iloc[i+1]['close']  # future_price_access
    return future_price
"""

        self.create_test_file("mixed_issues.py", mixed_code)
        issues = self.checker.scan_quality_issues()

        # パターン頻度計算
        pattern_counts = {}
        for issue in issues:
            pattern = issue["type"]
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        assert "lookahead_bias" in pattern_counts, "lookahead_biasパターンが検出されていない"

        print("✅ パターン頻度分析テスト成功")
        for pattern, count in pattern_counts.items():
            print(f"   {pattern}: {count}件")

    def run_comprehensive_test(self):
        """包括的テスト実行"""
        print("🧪 品質チェッカー包括テスト開始")

        try:
            self.test_lookahead_bias_detection()
            self.test_random_generation_detection()
            self.test_confidence_scoring()
            self.test_false_positive_contexts()
            self.test_pattern_frequency_analysis()

            print("\n🎯 全テスト合格 - 品質チェッカーの動作が検証されました")
            return True

        except AssertionError as e:
            print(f"\n❌ テスト失敗: {e}")
            return False
        except Exception as e:
            print(f"\n💥 テストエラー: {e}")
            return False


def run_validation():
    """品質チェッカー検証実行"""
    tester = TestQualityChecker()
    tester.setup_method()
    return tester.run_comprehensive_test()


if __name__ == "__main__":
    success = run_validation()
    exit(0 if success else 1)
