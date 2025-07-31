#!/usr/bin/env python3
"""
kiro協働セッション開始スクリプト
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from Scripts.collaboration_tracker import CollaborationTracker


def main():
    tracker = CollaborationTracker()

    # Phase 1設計依頼の記録開始
    request_content = """
Phase 1: アーキテクチャ設計依頼
- MT5接続方式の技術選定（標準API vs PyTrader vs MetaApi）
- WebSocket vs REST API設計
- セキュリティ基本方針（認証・データ保護・アクセス制御）
詳細: .kiro/requests/phase1_architecture_design_request.md 参照
"""

    expected_outcome = """
1. システム構成図（全体アーキテクチャ・データフロー）
2. 技術選定理由書（各選択の根拠・リスク対策）
3. 実装優先順位（MVP定義・段階的計画）
"""

    collab_id = tracker.start_collaboration(
        request_type="architecture",
        request_content=request_content,
        expected_outcome=expected_outcome,
    )

    print("✅ 協働セッション開始")
    print(f"ID: {collab_id}")
    print("タイプ: アーキテクチャ設計")
    print("詳細依頼文: .kiro/requests/phase1_architecture_design_request.md")
    print("\nkiroからの設計受領後、以下のコマンドで記録:")
    print(f"python3 Scripts/record_design.py {collab_id}")


if __name__ == "__main__":
    main()
