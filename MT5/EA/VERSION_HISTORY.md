# JamesORB EA Version History

## v2.01 (2025-07-27)
**追加機能:**
- マジックナンバー追加: 20250727
- EA初期化時のマジックナンバー設定
- 取引監視システム対応

**変更点:**
- trade.SetExpertMagicNumber(MAGIC_NUMBER) 追加
- Print文でマジックナンバー確認追加

**次期予定 (v2.02):**
- London Session対応 (08:00 JST)
- 30分ORB実装
- 1:1.5リスクリワード
- 動的ポジションサイズ計算
- ボリューム・リテスト確認

## v2.00 (Original)
**基本機能:**
- Opening Range Breakout戦略
- CTrade クラス使用
- 基本的なリスク管理

**パラメータ:**
- OBR_PIP_OFFSET: 0.0002 (20 pips)
- EET_START: 10 (10:00 JST)
- OBR_RATIO: 1.9
- ATR_PERIOD: 72