#!/usr/bin/env python3
"""
kiro-Claude協働学習システム
設計→実装→学習のサイクルを記録・分析
"""

import json
import os
from datetime import datetime
from pathlib import Path
import sys

# プロジェクト共通ライブラリ
sys.path.append(str(Path(__file__).parent.parent))
from lib.logger_setup import get_logger

class CollaborationTracker:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.learning_dir = self.project_root / "文書" / "学習"
        self.data_file = self.learning_dir / "collaboration_data.json"
        self.logger = get_logger(__name__)
        
        # データファイル初期化
        self.ensure_data_file()
        
    def ensure_data_file(self):
        """学習データファイルの初期化"""
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.data_file.exists():
            initial_data = {
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_collaborations": 0,
                    "system_version": "1.0"
                },
                "kiro_patterns": {
                    "strengths": {},
                    "improvement_areas": {},
                    "design_evolution": []
                },
                "request_optimization": {
                    "successful_patterns": [],
                    "unsuccessful_patterns": [],
                    "templates": {}
                },
                "collaboration_history": []
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("学習データファイル初期化完了")
    
    def load_data(self):
        """学習データ読み込み"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"データ読み込みエラー: {e}")
            return {}
    
    def save_data(self, data):
        """学習データ保存"""
        try:
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("学習データ保存完了")
            return True
        except Exception as e:
            self.logger.error(f"データ保存エラー: {e}")
            return False
    
    def start_collaboration(self, request_type, request_content, expected_outcome):
        """協働セッション開始記録"""
        data = self.load_data()
        
        collaboration_id = f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        collaboration = {
            "id": collaboration_id,
            "start_time": datetime.now().isoformat(),
            "request_type": request_type,
            "request_content": request_content,
            "expected_outcome": expected_outcome,
            "status": "in_progress",
            "kiro_design": None,
            "implementation_result": None,
            "learning_points": {}
        }
        
        data["collaboration_history"].append(collaboration)
        data["metadata"]["total_collaborations"] += 1
        
        if self.save_data(data):
            self.logger.info(f"協働セッション開始: {collaboration_id}")
            return collaboration_id
        return None
    
    def record_kiro_design(self, collaboration_id, design_content, design_quality_assessment):
        """kiro設計結果記録"""
        data = self.load_data()
        
        # 該当協働セッション検索
        for collab in data["collaboration_history"]:
            if collab["id"] == collaboration_id:
                collab["kiro_design"] = {
                    "content": design_content,
                    "quality_assessment": design_quality_assessment,
                    "received_time": datetime.now().isoformat()
                }
                
                # kiroパターン分析
                self._analyze_kiro_patterns(data, collab)
                break
        
        if self.save_data(data):
            self.logger.info(f"kiro設計記録完了: {collaboration_id}")
            return True
        return False
    
    def record_implementation_result(self, collaboration_id, implementation_data):
        """実装結果記録"""
        data = self.load_data()
        
        for collab in data["collaboration_history"]:
            if collab["id"] == collaboration_id:
                collab["implementation_result"] = implementation_data
                collab["status"] = "completed"
                collab["end_time"] = datetime.now().isoformat()
                
                # 学習ポイント抽出
                self._extract_learning_points(data, collab)
                break
        
        if self.save_data(data):
            self.logger.info(f"実装結果記録完了: {collaboration_id}")
            return True
        return False
    
    def _analyze_kiro_patterns(self, data, collaboration):
        """kiro設計パターン分析"""
        design = collaboration["kiro_design"]
        request_type = collaboration["request_type"]
        
        # 強み領域の分析
        if design["quality_assessment"].get("overall_score", 0) >= 7:
            if request_type not in data["kiro_patterns"]["strengths"]:
                data["kiro_patterns"]["strengths"][request_type] = {
                    "score": [],
                    "successful_features": [],
                    "examples": []
                }
            
            data["kiro_patterns"]["strengths"][request_type]["score"].append(
                design["quality_assessment"]["overall_score"]
            )
            data["kiro_patterns"]["strengths"][request_type]["examples"].append(
                collaboration["id"]
            )
    
    def _extract_learning_points(self, data, collaboration):
        """学習ポイント抽出"""
        if not collaboration["implementation_result"]:
            return
        
        impl = collaboration["implementation_result"]
        design = collaboration.get("kiro_design", {})
        
        # 実装困難度と設計品質の関係分析
        if impl.get("difficulty_score") and design.get("quality_assessment", {}).get("overall_score"):
            gap = abs(impl["difficulty_score"] - design["quality_assessment"]["overall_score"])
            
            collaboration["learning_points"] = {
                "design_implementation_gap": gap,
                "identified_constraints": impl.get("discovered_constraints", []),
                "effective_request_elements": self._identify_effective_elements(collaboration),
                "improvement_suggestions": impl.get("improvement_suggestions", [])
            }
    
    def _identify_effective_elements(self, collaboration):
        """効果的な依頼要素の特定"""
        # 依頼文から効果的だった要素を抽出
        effective_elements = []
        
        request_content = collaboration["request_content"]
        
        # 具体的制約が含まれていたか
        if "制約" in request_content or "環境" in request_content:
            effective_elements.append("具体的制約明示")
        
        # 参考例が含まれていたか
        if "参考" in request_content or "例" in request_content:
            effective_elements.append("参考実装例提示")
        
        # 段階的要求が含まれていたか
        if "段階" in request_content or "Phase" in request_content:
            effective_elements.append("段階的実装計画要求")
        
        return effective_elements
    
    def generate_optimized_request(self, request_type):
        """最適化された依頼文生成"""
        data = self.load_data()
        
        # 過去の成功パターンから最適な依頼文を生成
        successful_patterns = []
        
        for collab in data["collaboration_history"]:
            if (collab["request_type"] == request_type and 
                collab["status"] == "completed" and
                collab.get("learning_points", {}).get("design_implementation_gap", 10) < 3):
                
                successful_patterns.append(collab["learning_points"]["effective_request_elements"])
        
        if not successful_patterns:
            return self._get_default_template(request_type)
        
        # 最も多く使われた効果的要素を抽出
        element_counts = {}
        for pattern in successful_patterns:
            for element in pattern:
                element_counts[element] = element_counts.get(element, 0) + 1
        
        top_elements = sorted(element_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return self._build_request_template(request_type, [elem[0] for elem in top_elements])
    
    def _get_default_template(self, request_type):
        """デフォルト依頼文テンプレート"""
        templates = {
            "architecture": """
## アーキテクチャ設計依頼

### 設計対象
[設計対象の詳細]

### 技術的制約
- 現在の環境: MT5 on Wine, Python 3.x
- 既存ライブラリ: [使用可能ライブラリ一覧]
- パフォーマンス要件: [具体的要件]

### 期待する成果物
- システム構成図
- 技術選定理由
- 実装段階の優先順位

### 参考情報
[関連する実装例や制約情報]
            """,
            "ui_ux": """
## UI/UX設計依頼

### 対象ユーザー
[想定ユーザー・利用シーン]

### 技術的制約
- モバイル対応: 必須/任意
- ブラウザ対応: [対象ブラウザ]
- レスポンシブ要件: [具体的要件]

### 期待する成果物
- ワイヤーフレーム
- 画面遷移設計
- モバイル最適化方針

### 参考デザイン
[参考にしたいUI/UX例]
            """
        }
        
        return templates.get(request_type, "詳細な設計依頼内容を記載してください。")
    
    def _build_request_template(self, request_type, effective_elements):
        """効果的要素を含む依頼文構築"""
        base_template = self._get_default_template(request_type)
        
        enhancements = []
        
        if "具体的制約明示" in effective_elements:
            enhancements.append("\n### 重要制約事項\n[実装時に影響する具体的制約を詳細に記載]")
        
        if "参考実装例提示" in effective_elements:
            enhancements.append("\n### 参考実装例\n[類似実装例のURL・概要・採用したい要素]")
        
        if "段階的実装計画要求" in effective_elements:
            enhancements.append("\n### 実装段階計画\n[MVP→本格版の段階的計画を含む設計]")
        
        return base_template + "\n".join(enhancements)
    
    def get_kiro_collaboration_stats(self):
        """kiro協働統計情報取得"""
        data = self.load_data()
        
        completed_collaborations = [c for c in data["collaboration_history"] if c["status"] == "completed"]
        
        if not completed_collaborations:
            return {"message": "協働データが不足しています", "collaborations": 0}
        
        # 設計品質平均
        design_scores = []
        implementation_difficulties = []
        gaps = []
        
        for collab in completed_collaborations:
            if collab.get("kiro_design", {}).get("quality_assessment", {}).get("overall_score"):
                design_scores.append(collab["kiro_design"]["quality_assessment"]["overall_score"])
            
            if collab.get("implementation_result", {}).get("difficulty_score"):
                implementation_difficulties.append(collab["implementation_result"]["difficulty_score"])
            
            if collab.get("learning_points", {}).get("design_implementation_gap"):
                gaps.append(collab["learning_points"]["design_implementation_gap"])
        
        stats = {
            "total_collaborations": len(completed_collaborations),
            "average_design_quality": sum(design_scores) / len(design_scores) if design_scores else 0,
            "average_implementation_difficulty": sum(implementation_difficulties) / len(implementation_difficulties) if implementation_difficulties else 0,
            "average_design_gap": sum(gaps) / len(gaps) if gaps else 0,
            "identified_strengths": list(data["kiro_patterns"]["strengths"].keys()),
            "improvement_trends": self._calculate_improvement_trends(completed_collaborations)
        }
        
        return stats
    
    def _calculate_improvement_trends(self, collaborations):
        """改善トレンド計算"""
        if len(collaborations) < 3:
            return "データ不足"
        
        # 最新3件と初期3件の比較
        recent = collaborations[-3:]
        initial = collaborations[:3]
        
        recent_gaps = [c.get("learning_points", {}).get("design_implementation_gap", 5) for c in recent]
        initial_gaps = [c.get("learning_points", {}).get("design_implementation_gap", 5) for c in initial]
        
        recent_avg = sum(recent_gaps) / len(recent_gaps)
        initial_avg = sum(initial_gaps) / len(initial_gaps)
        
        improvement = initial_avg - recent_avg
        
        if improvement > 1:
            return "顕著な改善"
        elif improvement > 0.5:
            return "改善傾向"
        elif improvement > -0.5:
            return "安定"
        else:
            return "要改善"

def main():
    """CLI実行用メイン関数"""
    tracker = CollaborationTracker()
    
    import argparse
    parser = argparse.ArgumentParser(description="kiro-Claude協働学習システム")
    parser.add_argument("--stats", action="store_true", help="統計情報表示")
    parser.add_argument("--generate", type=str, help="最適化依頼文生成 (architecture/ui_ux)")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = tracker.get_kiro_collaboration_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.generate:
        template = tracker.generate_optimized_request(args.generate)
        print(template)
    
    else:
        print("使用方法: python collaboration_tracker.py --stats または --generate <type>")

if __name__ == "__main__":
    main()