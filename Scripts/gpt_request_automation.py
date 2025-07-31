#!/usr/bin/env python3
"""
GPT依頼文作成時の手順確認自動化システム
依頼文作成前に必須手順の確認・実行を自動化
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path


class GPTRequestAutomation:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.checklist_file = (
            self.project_dir
            / "3AI_collaboration"
            / "to_chatgpt"
            / ".request_checklist.json"
        )
        self.template_dir = self.project_dir / "3AI_collaboration" / "to_chatgpt"
        self.log_file = self.project_dir / ".gpt_request_automation.log"

        # ログ設定
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # 必須手順チェックリスト
        self.mandatory_steps = {
            "git_status_check": {
                "description": "Git状況確認（未コミット変更の確認）",
                "command": ["git", "status", "--porcelain"],
                "required": True,
                "auto_execute": True,
            },
            "backup_current_work": {
                "description": "現在の作業内容をバックアップ",
                "command": ["git", "add", ".", "&&", "git", "commit", "-m", "作業前自動保存"],
                "required": True,
                "auto_execute": False,  # ユーザー確認必要
            },
            "context_preparation": {
                "description": "コンテキスト準備（関連ファイル特定）",
                "command": None,
                "required": True,
                "auto_execute": False,
            },
            "expected_output_definition": {
                "description": "期待する出力形式の明確化",
                "command": None,
                "required": True,
                "auto_execute": False,
            },
            "quality_criteria_check": {
                "description": "品質基準・検証方法の確認",
                "command": ["python3", "Scripts/quality_checker.py"],
                "required": True,
                "auto_execute": True,
            },
        }

    def check_git_status(self):
        """Git状況確認"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                logging.warning(f"未コミット変更あり: {result.stdout.strip()}")
                return {
                    "status": "warning",
                    "message": "未コミット変更があります",
                    "details": result.stdout.strip(),
                    "recommendation": "作業前に変更をコミットすることを推奨",
                }
            else:
                logging.info("Git状況: クリーン")
                return {"status": "ok", "message": "Gitクリーン", "details": None}

        except subprocess.CalledProcessError as e:
            logging.error(f"Git状況確認エラー: {e}")
            return {"status": "error", "message": f"Git確認失敗: {e}", "details": None}

    def run_quality_check(self):
        """品質チェック実行"""
        try:
            result = subprocess.run(
                ["python3", "Scripts/quality_checker.py"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            logging.info("品質チェック完了")
            return {"status": "ok", "message": "品質チェック完了", "details": result.stdout}

        except subprocess.CalledProcessError as e:
            logging.error(f"品質チェックエラー: {e}")
            return {"status": "error", "message": f"品質チェック失敗: {e}", "details": e.stderr}

    def generate_request_template(self, task_type="general"):
        """依頼文テンプレート生成"""
        templates = {
            "refactoring": {
                "title": "Pythonリファクタリング最適化依頼",
                "sections": ["🎯 修正目的", "🔧 主な最適化要求", "📂 対象ファイル", "📄 利用手順", "💡 期待する学習成果"],
            },
            "analysis": {
                "title": "戦略分析・検証依頼",
                "sections": ["📊 分析目的", "🔍 検証項目", "📈 期待する結果", "⚠️ 注意事項"],
            },
            "implementation": {
                "title": "実装・機能追加依頼",
                "sections": ["🎯 実装目的", "⚙️ 要求仕様", "🧪 テスト要件", "📋 完了条件"],
            },
            "general": {
                "title": "作業依頼",
                "sections": ["📋 作業内容", "🎯 目的・背景", "📄 提供情報", "💡 期待する結果"],
            },
        }

        template = templates.get(task_type, templates["general"])

        content = f"""# ✅ {template['title']}

**作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}**

"""

        for section in template["sections"]:
            content += f"## {section}\n[TODO: 具体的な内容を記入]\n\n"

        content += """---

**ChatGPTへの具体的依頼文:**
「[TODO: 具体的な依頼内容を記入]」
"""

        return content

    def create_pre_commit_hook(self):
        """GPT依頼文作成時のpre-commitフック作成"""
        hook_content = '''#!/usr/bin/env python3
"""
GPT依頼文作成時の自動チェックフック
to_chatgpt/ディレクトリ内のファイル変更時に自動実行
"""

import sys
import subprocess
from pathlib import Path

def main():
    project_dir = Path(__file__).parent.parent.parent

    # to_chatgpt/ディレクトリの変更をチェック
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True
    )

    changed_files = result.stdout.strip().split("\\n")
    gpt_files = [f for f in changed_files if "3AI_collaboration/to_chatgpt/" in f]

    if gpt_files:
        print("🤖 GPT依頼文の変更を検出しました")
        print("📋 手順確認を実行中...")

        # 自動化システム実行
        automation_result = subprocess.run([
            "python3",
            str(project_dir / "Scripts" / "gpt_request_automation.py"),
            "--check-only"
        ])

        if automation_result.returncode != 0:
            print("❌ 手順確認で問題が検出されました")
            print("詳細は .gpt_request_automation.log を確認してください")
            return 1

        print("✅ 手順確認完了")

    return 0

if __name__ == "__main__":
    sys.exit(main())
'''

        hook_file = self.project_dir / ".git" / "hooks" / "pre-commit-gpt-check"
        hook_file.write_text(hook_content)
        hook_file.chmod(0o755)

        logging.info("GPT依頼文チェックフック作成完了")
        return hook_file

    def run_pre_request_check(self):
        """依頼文作成前チェック実行"""
        results = {}

        print("🤖 GPT依頼文作成前チェックを実行中...")

        # Git状況確認
        print("📋 Git状況確認...")
        results["git_status"] = self.check_git_status()

        # 品質チェック
        print("🔍 品質チェック実行...")
        results["quality_check"] = self.run_quality_check()

        # 結果表示
        print("\\n📊 チェック結果:")
        for check_name, result in results.items():
            status_icon = (
                "✅"
                if result["status"] == "ok"
                else "⚠️"
                if result["status"] == "warning"
                else "❌"
            )
            print(f"{status_icon} {check_name}: {result['message']}")

            if result["details"]:
                print(f"   詳細: {result['details'][:100]}...")

        # 推奨アクション表示
        print("\\n💡 推奨アクション:")
        if results["git_status"]["status"] == "warning":
            print("1. 現在の変更をコミット: git add . && git commit -m '作業前保存'")

        print(
            "2. 依頼文テンプレート使用: python3 Scripts/gpt_request_automation.py --template [type]"
        )
        print("3. コンテキスト準備: 関連ファイルの特定・整理")
        print("4. 期待結果明確化: 具体的な出力形式・品質基準の定義")

        return results

    def main(self):
        """メイン実行関数"""
        import argparse

        parser = argparse.ArgumentParser(description="GPT依頼文作成自動化")
        parser.add_argument("--check-only", action="store_true", help="チェックのみ実行")
        parser.add_argument(
            "--template",
            choices=["refactoring", "analysis", "implementation", "general"],
            help="テンプレート生成",
        )
        parser.add_argument(
            "--create-hook", action="store_true", help="pre-commitフック作成"
        )

        args = parser.parse_args()

        if args.create_hook:
            hook_file = self.create_pre_commit_hook()
            print(f"✅ Pre-commitフック作成完了: {hook_file}")

        elif args.template:
            template_content = self.generate_request_template(args.template)
            filename = (
                f"{args.template}_request_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            )
            output_file = self.template_dir / filename

            # フォルダ存在確認・作成
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(template_content, encoding="utf-8")
            print(f"✅ テンプレート生成完了: {output_file}")

        else:
            # 通常のチェック実行
            results = self.run_pre_request_check()

            # ログ記録
            logging.info(f"依頼文作成前チェック実行: {results}")

            return (
                0
                if all(r["status"] in ["ok", "warning"] for r in results.values())
                else 1
            )


if __name__ == "__main__":
    project_dir = "/home/trader/Trading-Development/2.ブレイクアウト手法プロジェクト"
    automation = GPTRequestAutomation(project_dir)
    exit(automation.main())
