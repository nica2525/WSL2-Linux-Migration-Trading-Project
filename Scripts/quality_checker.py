#!/usr/bin/env python3
"""
品質チェックシステム（Cron統合対応）
既存のCron自動保存システムと連携して品質問題を検出・記録
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
import re


class QualityChecker:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.quality_log = self.project_dir / ".quality_issues.json"
        self.scan_patterns = {
            "random_generation": {
                "pattern": r"random\.random\(\)\s*<\s*0\.\d+",
                "severity": "HIGH", 
                "description": "バックテスト結果のランダム生成（偽装）"
            },
            "lookahead_bias": {
                "pattern": r"current_bar\[.close.\]",
                "severity": "HIGH",
                "description": "Look-ahead bias（未来データ参照）",
                "false_positive_contexts": [
                    r"exit_price\s*=\s*bar_close",  # 時間切れ決済
                    r"TIME_EXIT",  # 時間切れ決済コンテキスト
                    r"max_holding_hours",  # 最大保有時間関連
                    r"final_price\s*=.*\[.close.\]",  # 最終決済
                    r"FORCED_EXIT"  # 強制決済
                ]
            },
            "random_uniform_suspicious": {
                "pattern": r"random\.uniform\(.*return",
                "severity": "MEDIUM",
                "description": "戦略結果でのrandom.uniform使用"
            },
            "fixed_winrate": {
                "pattern": r"random\.random\(\)\s*<\s*0\.[34]\d+.*win",
                "severity": "HIGH", 
                "description": "固定勝率によるバックテスト偽装"
            },
            "future_price_access": {
                "pattern": r"current_price\s*=\s*current_bar\[.close.\]",
                "severity": "HIGH",
                "description": "シグナル生成時の未来価格参照"
            },
            "simulation_bias": {
                "pattern": r"if\s+random\.random\(\)\s*<\s*0\.[5-9]",
                "severity": "MEDIUM",
                "description": "シミュレーション結果の人工的操作"
            }
        }

    def scan_quality_issues(self):
        """品質問題スキャン実行"""
        issues = []
        
        # Python ファイルをスキャン
        py_files = list(self.project_dir.glob("**/*.py"))
        
        for py_file in py_files:
            # Archive/Skip ディレクトリは除外
            if "Archive" in str(py_file) or "Archive" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for issue_type, config in self.scan_patterns.items():
                    matches = re.finditer(config["pattern"], content, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # False positive チェック
                        if self._is_false_positive(match, content, config, line_num):
                            continue
                            
                        # コンテキスト情報取得
                        context_info = self._get_context_info(content, match.start(), line_num)
                        
                        issue = {
                            "timestamp": datetime.now().isoformat(),
                            "file": str(py_file.relative_to(self.project_dir)),
                            "line": line_num,
                            "type": issue_type,
                            "severity": config["severity"],
                            "description": config["description"],
                            "code_snippet": match.group(0)[:100],
                            "context": context_info,
                            "confidence": self._calculate_confidence(match, content, config)
                        }
                        issues.append(issue)
                        
            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
                
        return issues

    def load_previous_issues(self):
        """前回の品質問題記録を読み込み"""
        if not self.quality_log.exists():
            return []
            
        try:
            with open(self.quality_log, 'r') as f:
                return json.load(f)
        except:
            return []

    def save_issues(self, issues):
        """品質問題記録を保存"""
        with open(self.quality_log, 'w') as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)

    def generate_quality_report(self):
        """品質レポート生成"""
        issues = self.scan_quality_issues()
        previous_issues = self.load_previous_issues()
        
        # 前回からの変化を検出
        current_signatures = {f"{issue['file']}:{issue['line']}:{issue['type']}" for issue in issues}
        previous_signatures = {f"{issue['file']}:{issue['line']}:{issue['type']}" for issue in previous_issues}
        
        new_issues = [issue for issue in issues 
                     if f"{issue['file']}:{issue['line']}:{issue['type']}" not in previous_signatures]
        fixed_issues = previous_signatures - current_signatures
        
        # 重要度別統計
        high_issues = [issue for issue in issues if issue['severity'] == 'HIGH']
        medium_issues = [issue for issue in issues if issue['severity'] == 'MEDIUM']
        
        report = {
            "scan_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_issues": len(issues),
                "high_severity": len(high_issues),
                "medium_severity": len(medium_issues),
                "new_issues": len(new_issues),
                "fixed_issues": len(fixed_issues)
            },
            "new_issues": new_issues,
            "fixed_issues": list(fixed_issues),
            "all_issues": issues
        }
        
        # 記録を保存
        self.save_issues(issues)
        
        return report

    def create_session_quality_briefing(self):
        """セッション開始時用の品質概要作成"""
        report = self.generate_quality_report()
        
        briefing = []
        briefing.append("🔍 品質状況サマリー")
        briefing.append(f"   総問題数: {report['summary']['total_issues']}")
        briefing.append(f"   高重要度: {report['summary']['high_severity']}")
        briefing.append(f"   新規問題: {report['summary']['new_issues']}")
        briefing.append(f"   修正済み: {report['summary']['fixed_issues']}")
        
        if report['summary']['high_severity'] > 0:
            briefing.append("\n🚨 緊急修正要件:")
            for issue in report['all_issues']:
                if issue['severity'] == 'HIGH':
                    briefing.append(f"   {issue['file']}:{issue['line']} - {issue['description']}")
        
        if report['summary']['new_issues'] > 0:
            briefing.append("\n🆕 新規発見問題:")
            for issue in report['new_issues']:
                briefing.append(f"   {issue['file']}:{issue['line']} - {issue['description']}")
        
        if report['summary']['total_issues'] == 0:
            briefing.append("\n✅ 品質問題なし - 良好な状態を維持")
            
        return "\n".join(briefing)


def main():
    """メイン実行（Cron対応）"""
    project_dir = "/mnt/e/Trading-Development/2.ブレイクアウト手法プロジェクト"
    checker = QualityChecker(project_dir)
    
    # 品質レポート生成
    report = checker.generate_quality_report()
    
    # コンソール出力（Cronログ用）
    print(f"品質チェック完了: {report['summary']['total_issues']}件の問題を検出")
    
    if report['summary']['high_severity'] > 0:
        print(f"🚨 緊急対応要: {report['summary']['high_severity']}件の高重要度問題")
    
    # セッション用概要ファイル作成
    briefing = checker.create_session_quality_briefing()
    briefing_file = Path(project_dir) / "CURRENT_QUALITY_STATUS.md"
    
    with open(briefing_file, 'w', encoding='utf-8') as f:
        f.write(f"# 現在の品質状況\n\n{briefing}\n\n")
        f.write(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return report


if __name__ == "__main__":
    main()