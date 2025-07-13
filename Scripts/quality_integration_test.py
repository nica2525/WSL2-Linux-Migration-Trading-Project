#!/usr/bin/env python3
"""
品質チェッカー統合テスト
実際のプロジェクトファイルに対する動作検証
"""

import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from quality_checker import QualityChecker


def test_actual_project_files():
    """実際のプロジェクトファイルでのテスト"""
    print("🔍 実プロジェクトファイル品質検証開始")

    project_root = Path(__file__).parent.parent
    checker = QualityChecker(project_root)

    # 実際のスキャン実行
    issues = checker.scan_quality_issues()

    print("\n📊 検出結果:")
    print(f"   総問題数: {len(issues)}")

    # ファイル別集計
    file_counts = {}
    pattern_counts = {}
    confidence_sum = 0

    for issue in issues:
        file_name = Path(issue["file"]).name
        file_counts[file_name] = file_counts.get(file_name, 0) + 1

        pattern = issue["type"]
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        confidence_sum += issue["confidence"]

    print("\n📁 ファイル別問題数:")
    for file_name, count in sorted(file_counts.items()):
        print(f"   {file_name}: {count}件")

    print("\n🔍 パターン別頻度:")
    for pattern, count in sorted(pattern_counts.items()):
        print(f"   {pattern}: {count}件")

    avg_confidence = confidence_sum / len(issues) if issues else 0
    print("\n📈 検出品質:")
    print(f"   平均信頼度: {avg_confidence:.1%}")

    # 高信頼度問題の確認
    high_confidence_issues = [i for i in issues if i["confidence"] >= 0.9]
    print(f"   高信頼度問題: {len(high_confidence_issues)}件")

    # False positive可能性のチェック
    potential_fps = []
    for issue in issues:
        if any(
            fp_pattern in issue.get("description", "")
            for fp_pattern in ["時間切れ", "TIME_EXIT", "FORCED_EXIT", "強制決済"]
        ):
            potential_fps.append(issue)

    print(f"   False positive候補: {len(potential_fps)}件")

    # 問題のある検出があるかチェック
    validation_results = {
        "total_issues": len(issues),
        "avg_confidence": avg_confidence,
        "high_confidence_count": len(high_confidence_issues),
        "potential_false_positives": len(potential_fps),
        "file_coverage": len(file_counts),
        "pattern_diversity": len(pattern_counts),
    }

    return validation_results


def validate_detection_accuracy():
    """検出精度の妥当性検証"""
    print("\n🎯 検出精度妥当性検証")

    results = test_actual_project_files()

    # 品質基準チェック
    checks = {
        "平均信頼度 >= 80%": results["avg_confidence"] >= 0.8,
        "高信頼度問題 >= 1件": results["high_confidence_count"] >= 1,
        "False positive率 < 20%": (
            results["potential_false_positives"] / max(results["total_issues"], 1)
        )
        < 0.2,
        "パターン多様性 >= 2種類": results["pattern_diversity"] >= 2,
        "ファイルカバレッジ >= 2件": results["file_coverage"] >= 2,
    }

    passed_checks = sum(checks.values())
    total_checks = len(checks)

    print(f"\n✅ 品質基準チェック結果: {passed_checks}/{total_checks}")
    for criterion, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {criterion}")

    # 総合判定
    quality_score = passed_checks / total_checks
    if quality_score >= 0.8:
        print(f"\n🎊 品質チェッカー動作保証: 合格 ({quality_score:.1%})")
        return True
    else:
        print(f"\n⚠️ 品質チェッカー動作保証: 要改善 ({quality_score:.1%})")
        return False


def generate_validation_report():
    """検証レポート生成"""
    print("📝 品質チェッカー検証レポート生成")

    results = test_actual_project_files()
    validation_passed = validate_detection_accuracy()

    report = {
        "validation_timestamp": "2025-07-13T19:35:00JST",
        "validation_status": "PASSED" if validation_passed else "FAILED",
        "detection_results": results,
        "validation_criteria": {
            "min_avg_confidence": 0.8,
            "min_high_confidence_issues": 1,
            "max_false_positive_rate": 0.2,
            "min_pattern_diversity": 2,
            "min_file_coverage": 2,
        },
        "recommendations": [
            "Gemini査読での精度向上検討" if not validation_passed else "現状の検出精度で運用可能",
            "定期的な検証テスト実行",
            "新パターン追加時の検証強化",
        ],
    }

    # レポート保存
    report_file = (
        Path(__file__).parent.parent / "quality_checker_validation_report.json"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 検証レポート保存: {report_file.name}")
    return validation_passed


if __name__ == "__main__":
    success = generate_validation_report()
    print(f"\n🔬 品質チェッカー動作保証: {'✅ 完了' if success else '❌ 要改善'}")
    exit(0 if success else 1)
