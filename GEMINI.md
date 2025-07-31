# Trading Development Project - Gemini Configuration

## プロジェクト概要
- **名称**: ブレイクアウト手法プロジェクト
- **目的**: MQL5 EA開発・最適化
- **主力EA**: JamesORB_v1.0.mq5

## 開発体制・役割分担
- **kiro**: 設計者・計画立案者（設計書・要件定義・アーキテクチャ担当）
- **Claude**: 実装担当者（kiroの設計に基づく実装のみ）
- **Gemini**: 査読・検証担当（品質管理・バグ検出）

## プロジェクト固有ルール
1. **MQL5開発**: 必ず3段階品質管理
   - mql5-technical-validator（実装前検証）
   - Claude実装
   - mql5-code-reviewer（実装後レビュー）
   - Gemini最終品質確認

2. **システム分析**: SubAgent + MCP連携
   - 複雑度分析: general-purpose
   - 依存関係解析: filesystem MCP
   - 技術調査: context7 + fetch MCP

## 現在の開発状況
- **SubAgent機能**: 完全復旧済み
- **MCP統合**: 4サーバー稼働中
- **品質管理**: 3層チェック体制確立
- **次期実装**: JamesORB EA改善（ATRハンドル・エラーハンドリング等）

## ファイル構造
- MT5/EA/: MQL5 Expert Advisors
- Scripts/: Python分析・監視スクリプト
- 文書/記録/: セッション記録・品質管理文書
