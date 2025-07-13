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
                    r"bar_close\s*=\s*current_bar\[.close.\]",  # バー終値取得
                    r"exit_price\s*=\s*bar_close",  # 時間切れ決済
                    r"TIME_EXIT",  # 時間切れ決済コンテキスト
                    r"max_holding_hours",  # 最大保有時間関連
                    r"final_price\s*=.*\[.close.\]",  # 最終決済
                    r"FORCED_EXIT",  # 強制決済
                    r"check_exit.*def",  # 決済判定関数
                    r"hours_held.*>=.*max_holding"  # 時間制限チェック
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
    
    def _is_false_positive(self, match, content, config, line_num):
        """False positive 判定"""
        if "false_positive_contexts" not in config:
            return False
            
        # マッチ周辺のコンテキスト取得（前後5行）
        lines = content.split('\n')
        start_line = max(0, line_num - 6)
        end_line = min(len(lines), line_num + 5)
        context = '\n'.join(lines[start_line:end_line])
        
        # False positive パターンチェック
        for fp_pattern in config["false_positive_contexts"]:
            if re.search(fp_pattern, context, re.IGNORECASE):
                return True
                
        return False
    
    def _get_context_info(self, content, match_start, line_num):
        """コンテキスト情報取得"""
        lines = content.split('\n')
        current_line = lines[line_num - 1] if line_num > 0 else ""
        
        # 関数名検索
        function_name = "unknown"
        for i in range(line_num - 1, max(0, line_num - 20), -1):
            if i < len(lines):
                line = lines[i]
                func_match = re.search(r'def\s+(\w+)', line)
                if func_match:
                    function_name = func_match.group(1)
                    break
        
        # クラス名検索
        class_name = "unknown"
        for i in range(line_num - 1, max(0, line_num - 50), -1):
            if i < len(lines):
                line = lines[i]
                class_match = re.search(r'class\s+(\w+)', line)
                if class_match:
                    class_name = class_match.group(1)
                    break
        
        return {
            "function": function_name,
            "class": class_name,
            "line_content": current_line.strip()
        }
    
    def _calculate_confidence(self, match, content, config):
        """信頼度計算"""
        # 基本信頼度
        confidence = 0.8
        
        # シグナル生成関数内なら信頼度向上
        if "generate_signal" in content or "signal" in match.group(0).lower():
            confidence += 0.1
            
        # バックテスト関数内なら信頼度向上
        if "backtest" in content or "test_" in content:
            confidence += 0.1
            
        return min(1.0, confidence)

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
                    confidence_badge = "🔴" if issue.get('confidence', 0.8) > 0.9 else "🟡"
                    context = issue.get('context', {})
                    func_info = f" [{context.get('function', 'unknown')}]" if context.get('function') != 'unknown' else ""
                    briefing.append(f"   {confidence_badge} {issue['file']}:{issue['line']} - {issue['description']}{func_info}")
        
        if report['summary']['new_issues'] > 0:
            briefing.append("\n🆕 新規発見問題:")
            for issue in report['new_issues']:
                briefing.append(f"   {issue['file']}:{issue['line']} - {issue['description']}")
        
        if report['summary']['total_issues'] == 0:
            briefing.append("\n✅ 品質問題なし - 良好な状態を維持")
            
        return "\n".join(briefing)
    
    def generate_detailed_analysis(self):
        """詳細品質分析レポート生成"""
        report = self.generate_quality_report()
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "summary": report['summary'],
            "file_statistics": {},
            "severity_breakdown": {},
            "confidence_analysis": {},
            "pattern_frequency": {},
            "false_positive_rate": 0.0
        }
        
        # ファイル別統計
        file_issues = {}
        for issue in report['all_issues']:
            file_name = issue['file']
            if file_name not in file_issues:
                file_issues[file_name] = []
            file_issues[file_name].append(issue)
        
        analysis['file_statistics'] = {
            file: {
                "issue_count": len(issues),
                "high_severity": len([i for i in issues if i['severity'] == 'HIGH']),
                "avg_confidence": sum(i.get('confidence', 0.8) for i in issues) / len(issues) if issues else 0
            } for file, issues in file_issues.items()
        }
        
        # パターン頻度分析
        pattern_count = {}
        for issue in report['all_issues']:
            pattern = issue['type']
            pattern_count[pattern] = pattern_count.get(pattern, 0) + 1
        analysis['pattern_frequency'] = pattern_count
        
        # 信頼度分析
        confidences = [issue.get('confidence', 0.8) for issue in report['all_issues']]
        if confidences:
            analysis['confidence_analysis'] = {
                "avg_confidence": sum(confidences) / len(confidences),
                "high_confidence_issues": len([c for c in confidences if c > 0.9]),
                "low_confidence_issues": len([c for c in confidences if c < 0.7])
            }
        
        return analysis
    
    def create_improvement_suggestions(self):
        """改善提案生成"""
        analysis = self.generate_detailed_analysis()
        suggestions = []
        
        # 高重要度問題の提案
        if analysis['summary']['high_severity'] > 0:
            suggestions.append("🚨 高重要度問題の即座修正を推奨")
            suggestions.append("   - Look-ahead bias: ブレイクアウト判定をhigh/lowベースに変更")
            suggestions.append("   - Random generation: 実際の価格追跡ロジックに置換")
        
        # ファイル別提案
        worst_files = sorted(
            analysis['file_statistics'].items(),
            key=lambda x: x[1]['issue_count'],
            reverse=True
        )[:3]
        
        if worst_files:
            suggestions.append(f"\n📁 最優先修正ファイル:")
            for file, stats in worst_files:
                suggestions.append(f"   - {file}: {stats['issue_count']}件の問題")
        
        # パターン別提案
        frequent_patterns = sorted(
            analysis['pattern_frequency'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        if frequent_patterns:
            suggestions.append(f"\n🔍 最頻出パターン:")
            for pattern, count in frequent_patterns:
                suggestions.append(f"   - {pattern}: {count}件")
        
        return "\n".join(suggestions)


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
    
    # 改善提案生成
    suggestions = checker.create_improvement_suggestions()
    
    # 詳細分析生成
    analysis = checker.generate_detailed_analysis()
    
    with open(briefing_file, 'w', encoding='utf-8') as f:
        f.write(f"# 現在の品質状況\n\n{briefing}\n\n")
        
        if suggestions:
            f.write(f"## 🎯 改善提案\n{suggestions}\n\n")
        
        # 信頼度統計
        if 'confidence_analysis' in analysis and analysis['confidence_analysis']:
            conf = analysis['confidence_analysis']
            f.write(f"## 📊 検出精度\n")
            f.write(f"- 平均信頼度: {conf['avg_confidence']:.1%}\n")
            f.write(f"- 高信頼度問題: {conf['high_confidence_issues']}件\n")
            f.write(f"- 要確認問題: {conf['low_confidence_issues']}件\n\n")
        
        f.write(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 詳細分析をJSONで保存
    analysis_file = Path(project_dir) / ".quality_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    return report


if __name__ == "__main__":
    main()