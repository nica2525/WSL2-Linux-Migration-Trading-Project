# EA開発とFX取引支援ツール調査報告

## 1. EA開発支援ツール

### 1.1 EA31337 Framework
- **概要**: MT4/MT5対応の包括的なオブジェクト指向ライブラリ
- **特徴**:
  - クロスプラットフォーム対応（最小限のコード変更でMT4/MT5両対応）
  - 35以上の組み込み戦略
  - カスタム戦略作成支援
- **GitHub**: https://github.com/EA31337
- **メリット**: 
  - 完全無料・オープンソース
  - 活発なコミュニティ
  - 豊富なドキュメント
- **デメリット**: 学習曲線が急

### 1.2 MQL_Easy
- **概要**: MQL開発を高速化・簡素化するクロスプラットフォームライブラリ
- **特徴**:
  - エラーハンドリング自動化
  - 一般的なタスクの簡素化
  - 安全性重視の設計
- **メリット**: 初心者にも使いやすい
- **デメリット**: カスタマイズ性に制限

### 1.3 Visual Studio Code + MQL Tools拡張
- **概要**: VS Codeを使用したMQL開発環境
- **機能**:
  - シンタックスハイライト
  - コード補完
  - エディタから直接コンパイル
  - GitHub Copilot統合可能
- **導入方法**: VS Code拡張機能から「MQL Tools」をインストール
- **メリット**: 
  - モダンな開発環境
  - AI支援開発可能
  - Git統合

### 1.4 mql4-lib
- **概要**: Java風のオブジェクト指向アプローチを採用したライブラリ
- **特徴**:
  - 再利用可能なコンポーネント
  - エレガントなコード構造
- **GitHub**: https://github.com/dingmaotu/mql4-lib

## 2. FX取引データ・API

### 2.1 Alpha Vantage
- **概要**: 包括的な金融データAPI
- **無料枠**: 
  - 1分あたり5リクエスト
  - 1日500リクエスト
- **提供データ**:
  - リアルタイム・履歴FXデータ
  - 50以上のテクニカル指標
  - ニュースセンチメント分析
- **統合例**:
```python
import requests

API_KEY = 'YOUR_API_KEY'
url = f'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=EUR&to_symbol=USD&interval=5min&apikey={API_KEY}'
response = requests.get(url)
data = response.json()
```

### 2.2 Finnhub
- **概要**: AI搭載の金融データプロバイダー
- **無料枠**: 1分あたり60リクエスト
- **特徴**:
  - リアルタイムFXデータ
  - 経済指標カレンダー
  - AIセンチメント分析
- **API例**:
```python
import finnhub
finnhub_client = finnhub.Client(api_key="YOUR_API_KEY")
print(finnhub_client.forex_candles('OANDA:EUR_USD', 'D', 1590988249, 1591852249))
```

### 2.3 Twelve Data
- **概要**: 高品質な市場データAPI
- **無料枠**: 1分あたり8リクエスト、1日800リクエスト
- **特徴**:
  - リアルタイム・履歴データ
  - WebSocket対応
  - 豊富なテクニカル指標

### 2.4 無料経済指標API
- **Trading Economics API**: 196カ国の2000万指標
- **Forex Factory Free News API**: 機械学習によるブル/ベアセンチメント
- **Marketaux**: 5000以上のソースからのニュースセンチメント

## 3. 分析・可視化ツール

### 3.1 NautilusTrader
- **概要**: 高性能オープンソース取引プラットフォーム
- **特徴**:
  - イベント駆動アーキテクチャ
  - バックテスト・ライブ取引対応
  - Python API
- **GitHub**: https://github.com/nautechsystems/nautilus_trader
- **統合例**:
```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.identifiers import Venue

engine = BacktestEngine()
engine.add_venue(Venue("FOREX"))
# カスタム戦略を追加
engine.run()
```

### 3.2 Backtrader
- **概要**: Python製の人気バックテストフレームワーク
- **特徴**:
  - 戦略開発に集中できる設計
  - 豊富な分析ツール
  - MT5統合可能（backtrader-mql5-api経由）
- **GitHub**: https://github.com/mementum/backtrader

### 3.3 pp_chartvisual
- **概要**: D3.jsベースのFX取引可視化ツール
- **特徴**:
  - MT4ボット連携
  - インタラクティブなチャート
- **GitHub**: https://github.com/immanual-t/pp_chartvisual

### 3.4 react-financial-charts
- **概要**: React用金融チャートライブラリ
- **機能**:
  - ローソク足チャート
  - テクニカル指標オーバーレイ
  - カスタマイズ可能

## 4. Claude Code活用方法

### 4.1 MCP (Model Context Protocol) 統合
- **概要**: AIとツールを接続する標準化プロトコル
- **利点**:
  - 自然言語でのデータアクセス
  - 複雑なタスクの自動化
  - プラグアンドプレイ統合

### 4.2 利用可能なMCPサーバー
1. **Alpha Vantage MCP Server**
   - リアルタイム・履歴FXレート
   - 自然言語クエリ対応

2. **Twelve Data MCP Server**
   - 市場データアクセス
   - 時系列分析サポート

3. **FrankfurterMCP**
   - 為替レートデータ特化
   - シンプルなAPI

### 4.3 Claude Codeでの実装例
```python
# MCPを使用した市場データ取得（疑似コード）
async def get_market_analysis():
    # MCPサーバーに接続
    mcp_client = MCPClient("alpha-vantage-server")
    
    # 自然言語でデータリクエスト
    result = await mcp_client.query(
        "EUR/USDの過去1週間の価格データを取得し、
         ボリンジャーバンドを計算してください"
    )
    
    return result
```

## 5. MT4/MT5 Python統合

### 5.1 MT5公式Python統合
- **パッケージ**: MetaTrader5
- **インストール**: `pip install MetaTrader5`
- **機能**:
  - ターミナル接続
  - 履歴・リアルタイムデータ取得
  - 取引操作
- **実装例**:
```python
import MetaTrader5 as mt5

# MT5に接続
mt5.initialize()

# シンボル情報取得
symbol_info = mt5.symbol_info("EURUSD")

# 履歴データ取得
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 1000)

# 注文送信
order = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "EURUSD",
    "volume": 0.1,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick("EURUSD").ask,
}
mt5.order_send(order)
```

### 5.2 MT4サードパーティ統合
1. **PyTrader**
   - WebSocket通信
   - ドラッグ&ドロップ接続
   
2. **metaapi-python-sdk**
   - クラウドベースソリューション
   - 高度な機能（コピートレードなど）

## 6. ブレイクアウト取引システムへの統合提案

### 6.1 推奨アーキテクチャ
```
[MT4/MT5 EA] <-> [Python Bridge] <-> [分析エンジン]
                                         |
                                    [MCP Server]
                                         |
                                    [Claude Code]
```

### 6.2 実装ステップ
1. **データ収集層**
   - Alpha Vantage/Finnhub APIで複数時間枠データ取得
   - MCPサーバー経由でClaude Codeからアクセス

2. **分析層**
   - NautilusTrader/Backtraderでバックテスト
   - pp_chartvisualで結果可視化

3. **実行層**
   - MT5 Python APIで取引実行
   - リアルタイム監視・アラート

### 6.3 開発効率化
- VS Code + MQL Tools + GitHub Copilot
- EA31337 Frameworkでコア機能実装
- Claude Codeで戦略ロジック生成

## 7. 推奨ツールセット（無料・高品質）

### 初級者向け
1. **データ**: Alpha Vantage (無料枠)
2. **開発**: VS Code + MQL Tools
3. **分析**: Backtrader
4. **統合**: MT5公式Python API

### 上級者向け
1. **データ**: Finnhub + 複数API組み合わせ
2. **開発**: EA31337 Framework
3. **分析**: NautilusTrader
4. **統合**: カスタムMCPサーバー開発

## まとめ

EA開発とFX取引の効率化には、適切なツール選択が不可欠です。オープンソースコミュニティは豊富なリソースを提供しており、無料で高品質なソリューションが多数存在します。特にMCPとClaude Codeの組み合わせは、自然言語での複雑なタスク実行を可能にし、開発効率を大幅に向上させます。

ブレイクアウト取引システムには、データ収集から分析、実行まで一貫したパイプラインを構築することが重要です。提案したアーキテクチャとツールセットを活用することで、堅牢で拡張性の高いシステムを実現できるでしょう。