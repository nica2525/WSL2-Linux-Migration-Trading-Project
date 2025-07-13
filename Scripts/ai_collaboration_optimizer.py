#!/usr/bin/env python3
"""
3AI協働最適化システム
Claude-Gemini-ChatGPT協働の自動化・効率化
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class AICollaborationOptimizer:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.collaboration_log = self.project_dir / "docs" / "AI_COLLABORATION_LOG.md"
        self.task_queue = self.project_dir / ".ai_task_queue.json"
        self.context_cache = self.project_dir / ".ai_context_cache.json"
        self.log_file = self.project_dir / ".ai_collaboration.log"

        # ログ設定
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # 各AIの得意分野定義
        self.ai_specialties = {
            "claude": ["システム構築・実装", "コード品質管理", "プロジェクト管理", "ファイル整理・構造化", "エラー解決・デバッグ"],
            "gemini": ["戦略理論分析", "数学的最適化", "統計解析・バックテスト", "リスク管理理論", "アルゴリズム設計"],
            "chatgpt": ["創発的アイデア生成", "バイアス分析・防止", "異なる視点の提供", "問題の根本原因分析", "コード最適化提案"],
        }

    def analyze_task_complexity(self, task_description):
        """タスク複雑度分析"""
        keywords_complex = [
            "最適化",
            "戦略開発",
            "数学的",
            "統計",
            "アルゴリズム",
            "バックテスト",
            "リスク管理",
            "パフォーマンス分析",
        ]
        keywords_medium = ["実装", "修正", "改善", "テスト", "検証", "分析"]
        keywords_simple = ["移動", "削除", "追加", "確認", "表示", "リスト"]

        task_lower = task_description.lower()

        complex_score = sum(1 for kw in keywords_complex if kw in task_lower)
        medium_score = sum(1 for kw in keywords_medium if kw in task_lower)
        simple_score = sum(1 for kw in keywords_simple if kw in task_lower)

        if complex_score >= 2:
            return "complex"
        elif complex_score >= 1 or medium_score >= 2:
            return "medium"
        elif simple_score >= 1:
            return "simple"
        else:
            return "medium"  # デフォルト

    def recommend_ai_collaboration(self, task_description, complexity):
        """AI協働推奨"""
        recommendations = {
            "primary_ai": "claude",  # デフォルト（実装AI）
            "collaboration_needed": False,
            "recommended_ais": [],
            "collaboration_type": "none",
            "reasoning": "",
        }

        task_lower = task_description.lower()

        # 複雑なタスクは複数AI協働推奨
        if complexity == "complex":
            recommendations["collaboration_needed"] = True
            recommendations["collaboration_type"] = "parallel"

            # 戦略・最適化関連ならGemini主導
            if any(kw in task_lower for kw in ["戦略", "最適化", "バックテスト", "統計", "数学"]):
                recommendations["primary_ai"] = "gemini"
                recommendations["recommended_ais"] = ["claude", "chatgpt"]
                recommendations[
                    "reasoning"
                ] = "複雑な戦略最適化のため、Gemini主導でClaude(実装)・ChatGPT(バイアス検証)と協働"

            # システム構築ならClaude主導
            elif any(kw in task_lower for kw in ["システム", "実装", "構築", "パイプライン"]):
                recommendations["primary_ai"] = "claude"
                recommendations["recommended_ais"] = ["gemini"]
                recommendations["reasoning"] = "複雑なシステム実装のため、Claude主導でGemini(理論設計)と協働"

        # 中程度タスクは必要に応じて協働
        elif complexity == "medium":
            # バイアス・品質確認が重要なタスク
            if any(kw in task_lower for kw in ["分析", "評価", "検証", "品質"]):
                recommendations["collaboration_needed"] = True
                recommendations["collaboration_type"] = "review"
                recommendations["recommended_ais"] = ["chatgpt"]
                recommendations["reasoning"] = "分析・評価タスクのため、ChatGPTによるバイアス検証推奨"

        return recommendations

    def save_collaboration_decision(
        self, task_description, recommendations, executed=False
    ):
        """協働判断記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")

        decision_record = {
            "timestamp": timestamp,
            "task": task_description,
            "complexity": recommendations.get("complexity", "unknown"),
            "primary_ai": recommendations["primary_ai"],
            "collaboration_needed": recommendations["collaboration_needed"],
            "recommended_ais": recommendations["recommended_ais"],
            "collaboration_type": recommendations["collaboration_type"],
            "reasoning": recommendations["reasoning"],
            "executed": executed,
        }

        # 協働ログに追記
        try:
            log_entry = f"""
## {timestamp} - AI協働判断

**タスク**: {task_description}
**複雑度**: {recommendations.get('complexity', 'unknown')}
**主導AI**: {recommendations['primary_ai']}
**協働必要**: {'要' if recommendations['collaboration_needed'] else '不要'}
**推奨AI**: {', '.join(recommendations['recommended_ais']) if recommendations['recommended_ais'] else 'なし'}
**協働タイプ**: {recommendations['collaboration_type']}
**判断根拠**: {recommendations['reasoning']}
**実行状況**: {'実行済み' if executed else '提案のみ'}

---
"""

            with open(self.collaboration_log, "a", encoding="utf-8") as f:
                f.write(log_entry)

        except Exception as e:
            logging.error(f"協働ログ記録エラー: {e}")

        return decision_record

    def generate_collaboration_prompt(
        self, task_description, target_ai, collaboration_type
    ):
        """協働プロンプト生成"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")

        if target_ai == "gemini":
            prompt = f"""[{timestamp}] Claude→Gemini協働要請

**依頼タスク**: {task_description}

**協働タイプ**: {collaboration_type}

**期待する出力**:
- 数学的・統計的観点からの分析
- 最適化アルゴリズムの提案
- 理論的根拠の説明
- 実装における注意点

**Claude実装方針**: Geminiの理論設計を基に具体的実装を行います

---
このタスクについて、Geminiの専門知識をお聞かせください。
"""

        elif target_ai == "chatgpt":
            prompt = f"""[{timestamp}] Claude→ChatGPT協働要請

**検証タスク**: {task_description}

**協働タイプ**: {collaboration_type}

**期待する出力**:
- 現在のアプローチの潜在的バイアス分析
- 代替アプローチの提案
- 見落としている観点の指摘
- 最適化・改善提案

**Claude実装状況**: [実装内容の概要を記載]

---
このアプローチについて、客観的な視点からフィードバックをお願いします。
"""

        else:
            prompt = f"""[{timestamp}] AI協働プロンプト

**タスク**: {task_description}
**対象AI**: {target_ai}
**協働タイプ**: {collaboration_type}

詳細な要件と期待する出力を記載してください。
"""

        return prompt

    def analyze_current_task(self, task_description):
        """現在タスクの分析・協働推奨"""
        complexity = self.analyze_task_complexity(task_description)
        recommendations = self.recommend_ai_collaboration(task_description, complexity)
        recommendations["complexity"] = complexity

        # 判断記録
        decision = self.save_collaboration_decision(task_description, recommendations)

        logging.info(
            f"タスク分析完了: {task_description[:50]}... - 複雑度:{complexity}, 協働:{'要' if recommendations['collaboration_needed'] else '不要'}"
        )

        return recommendations, decision

    def run_collaboration_analysis(self, task_description):
        """協働分析実行"""
        print("=== AI協働最適化分析 ===")
        print(f"タスク: {task_description}")

        recommendations, decision = self.analyze_current_task(task_description)

        print(f"複雑度: {recommendations['complexity']}")
        print(f"主導AI: {recommendations['primary_ai']}")
        print(f"協働必要: {'要' if recommendations['collaboration_needed'] else '不要'}")

        if recommendations["collaboration_needed"]:
            print(f"推奨AI: {', '.join(recommendations['recommended_ais'])}")
            print(f"協働タイプ: {recommendations['collaboration_type']}")
            print(f"判断根拠: {recommendations['reasoning']}")

            # 協働プロンプト生成
            for ai in recommendations["recommended_ais"]:
                prompt = self.generate_collaboration_prompt(
                    task_description, ai, recommendations["collaboration_type"]
                )
                prompt_file = self.project_dir / f".collaboration_prompt_{ai}.md"
                with open(prompt_file, "w", encoding="utf-8") as f:
                    f.write(prompt)
                print(f"✅ {ai.title()}協働プロンプト生成: {prompt_file}")

        else:
            print("📝 単独実行推奨 - Claude単独で効率的に実行可能")

        return recommendations


def main():
    """メイン実行"""
    import sys

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    if len(sys.argv) < 2:
        task_description = "システム監視の改善とパフォーマンス最適化"  # テスト用
    else:
        task_description = " ".join(sys.argv[1:])

    optimizer = AICollaborationOptimizer(project_dir)
    recommendations = optimizer.run_collaboration_analysis(task_description)

    return recommendations


if __name__ == "__main__":
    main()
