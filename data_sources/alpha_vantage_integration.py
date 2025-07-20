#!/usr/bin/env python3
"""
Alpha Vantage API統合モジュール
- 高品質FXデータ取得
- センチメント分析
- 経済指標統合
- リアルタイム価格データ
"""

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import threading
import queue

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataInterval(Enum):
    """データ間隔"""
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    H1 = "60min"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class MarketSentiment(Enum):
    """市場センチメント"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"

@dataclass
class FXQuote:
    """FX価格データ"""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    volume: int = 0
    
    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid

@dataclass
class SentimentData:
    """センチメントデータ"""
    symbol: str
    sentiment: MarketSentiment
    sentiment_score: float
    relevance_score: float
    ticker_sentiment_score: float
    timestamp: datetime

@dataclass
class EconomicIndicator:
    """経済指標データ"""
    name: str
    country: str
    value: float
    previous_value: Optional[float]
    forecast: Optional[float]
    timestamp: datetime
    importance: str  # HIGH, MEDIUM, LOW

class AlphaVantageClient:
    """Alpha Vantage APIクライアント"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str, cache_dir: str = "data_cache"):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # レート制限管理（無料枠: 25 requests/day）
        self.request_count = 0
        self.last_request_time = 0
        self.daily_limit = 25
        self.min_request_interval = 12  # 5分間に1回
        
        # セッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MT4-Python-Integration/1.0'
        })
        
        logger.info(f"Alpha Vantage Client初期化完了: API Key設定済み")
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """API リクエスト実行（レート制限対応）"""
        current_time = time.time()
        
        # レート制限チェック
        if self.request_count >= self.daily_limit:
            logger.warning("Alpha Vantage 日次リクエスト制限に達しました")
            return None
        
        if current_time - self.last_request_time < self.min_request_interval:
            wait_time = self.min_request_interval - (current_time - self.last_request_time)
            logger.info(f"レート制限により {wait_time:.1f}秒待機")
            time.sleep(wait_time)
        
        # APIキー追加
        params['apikey'] = self.api_key
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            self.request_count += 1
            self.last_request_time = time.time()
            
            data = response.json()
            
            # エラーチェック
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API エラー: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                logger.warning(f"Alpha Vantage API 制限: {data['Note']}")
                return None
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Alpha Vantage API リクエストエラー: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Alpha Vantage API レスポンス解析エラー: {e}")
            return None
    
    def get_fx_intraday(self, from_symbol: str, to_symbol: str, 
                       interval: DataInterval = DataInterval.M5,
                       outputsize: str = "compact") -> Optional[pd.DataFrame]:
        """FX分足データ取得"""
        cache_key = f"fx_intraday_{from_symbol}_{to_symbol}_{interval.value}_{outputsize}"
        cached_data = self._load_cache(cache_key)
        
        if cached_data is not None:
            logger.info(f"キャッシュからデータ読み込み: {cache_key}")
            return cached_data
        
        params = {
            'function': 'FX_INTRADAY',
            'from_symbol': from_symbol,
            'to_symbol': to_symbol,
            'interval': interval.value,
            'outputsize': outputsize
        }
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            # タイムシリーズデータ抽出
            time_series_key = f'Time Series FX ({interval.value})'
            if time_series_key not in data:
                logger.error(f"タイムシリーズデータが見つかりません: {time_series_key}")
                return None
            
            time_series = data[time_series_key]
            
            # DataFrame変換
            df_data = []
            for timestamp_str, values in time_series.items():
                timestamp = pd.to_datetime(timestamp_str)
                df_data.append({
                    'timestamp': timestamp,
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # キャッシュ保存
            self._save_cache(cache_key, df)
            
            logger.info(f"FX分足データ取得成功: {from_symbol}/{to_symbol}, {len(df)}レコード")
            return df
            
        except (KeyError, ValueError) as e:
            logger.error(f"FX分足データ解析エラー: {e}")
            return None
    
    def get_fx_daily(self, from_symbol: str, to_symbol: str,
                    outputsize: str = "compact") -> Optional[pd.DataFrame]:
        """FX日足データ取得"""
        cache_key = f"fx_daily_{from_symbol}_{to_symbol}_{outputsize}"
        cached_data = self._load_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        params = {
            'function': 'FX_DAILY',
            'from_symbol': from_symbol,
            'to_symbol': to_symbol,
            'outputsize': outputsize
        }
        
        data = self._make_request(params)
        if not data:
            return None
        
        try:
            time_series = data['Time Series FX (Daily)']
            
            df_data = []
            for timestamp_str, values in time_series.items():
                timestamp = pd.to_datetime(timestamp_str)
                df_data.append({
                    'timestamp': timestamp,
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            self._save_cache(cache_key, df)
            
            logger.info(f"FX日足データ取得成功: {from_symbol}/{to_symbol}, {len(df)}レコード")
            return df
            
        except (KeyError, ValueError) as e:
            logger.error(f"FX日足データ解析エラー: {e}")
            return None
    
    def get_news_sentiment(self, tickers: Union[str, List[str]] = None,
                          topics: str = "forex",
                          time_from: str = None,
                          time_to: str = None,
                          limit: int = 50) -> List[SentimentData]:
        """ニュースセンチメント分析取得"""
        if isinstance(tickers, list):
            tickers = ','.join(tickers)
        
        params = {
            'function': 'NEWS_SENTIMENT',
            'topics': topics,
            'limit': limit
        }
        
        if tickers:
            params['tickers'] = tickers
        if time_from:
            params['time_from'] = time_from
        if time_to:
            params['time_to'] = time_to
        
        data = self._make_request(params)
        if not data:
            return []
        
        try:
            sentiment_data = []
            
            for item in data.get('feed', []):
                timestamp = pd.to_datetime(item['time_published'])
                
                # 全体センチメント
                overall_sentiment_score = float(item.get('overall_sentiment_score', 0))
                overall_sentiment_label = item.get('overall_sentiment_label', 'Neutral')
                
                # ティッカー別センチメント
                for ticker_sentiment in item.get('ticker_sentiment', []):
                    ticker = ticker_sentiment.get('ticker', '')
                    if not ticker:
                        continue
                    
                    sentiment_data.append(SentimentData(
                        symbol=ticker,
                        sentiment=MarketSentiment(overall_sentiment_label),
                        sentiment_score=overall_sentiment_score,
                        relevance_score=float(ticker_sentiment.get('relevance_score', 0)),
                        ticker_sentiment_score=float(ticker_sentiment.get('ticker_sentiment_score', 0)),
                        timestamp=timestamp
                    ))
            
            logger.info(f"ニュースセンチメント取得成功: {len(sentiment_data)}件")
            return sentiment_data
            
        except (KeyError, ValueError) as e:
            logger.error(f"ニュースセンチメント解析エラー: {e}")
            return []
    
    def get_economic_indicators(self, indicator: str = "GDP",
                              interval: str = "quarterly") -> List[EconomicIndicator]:
        """経済指標データ取得"""
        params = {
            'function': indicator,
            'interval': interval
        }
        
        data = self._make_request(params)
        if not data:
            return []
        
        try:
            indicators = []
            
            # データ構造は指標により異なるため、柔軟に処理
            data_key = None
            for key in data.keys():
                if 'data' in key.lower():
                    data_key = key
                    break
            
            if not data_key:
                logger.warning(f"経済指標データが見つかりません: {indicator}")
                return []
            
            for item in data[data_key]:
                timestamp = pd.to_datetime(item.get('date', ''))
                value = float(item.get('value', 0))
                
                indicators.append(EconomicIndicator(
                    name=indicator,
                    country="US",  # Alpha Vantageは主にUS指標
                    value=value,
                    previous_value=None,  # Alpha Vantageでは提供されない
                    forecast=None,
                    timestamp=timestamp,
                    importance="HIGH"  # デフォルト
                ))
            
            logger.info(f"経済指標取得成功: {indicator}, {len(indicators)}件")
            return indicators
            
        except (KeyError, ValueError) as e:
            logger.error(f"経済指標解析エラー: {e}")
            return []
    
    def _load_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """キャッシュデータ読み込み"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            # キャッシュの有効期限チェック（1時間）
            if time.time() - cache_file.stat().st_mtime > 3600:
                return None
            
            df = pd.read_pickle(cache_file)
            return df
            
        except Exception as e:
            logger.warning(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_cache(self, cache_key: str, df: pd.DataFrame):
        """キャッシュデータ保存"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            df.to_pickle(cache_file)
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {e}")

class MarketDataEnhancer:
    """Alpha Vantageデータでのマーケットデータ強化"""
    
    def __init__(self, alpha_vantage_client: AlphaVantageClient):
        self.client = alpha_vantage_client
        self.sentiment_cache = {}
        self.economic_cache = {}
        
    def enhance_price_data(self, symbol_pair: str, 
                          local_data: pd.DataFrame) -> pd.DataFrame:
        """ローカル価格データをAlpha Vantageデータで強化"""
        try:
            # シンボル分割 (例: EURUSD -> EUR, USD)
            if len(symbol_pair) == 6:
                from_symbol = symbol_pair[:3]
                to_symbol = symbol_pair[3:]
            else:
                logger.warning(f"無効なシンボル形式: {symbol_pair}")
                return local_data
            
            # Alpha Vantageから日足データ取得
            av_data = self.client.get_fx_daily(from_symbol, to_symbol)
            
            if av_data is None or av_data.empty:
                logger.warning("Alpha Vantageデータ取得失敗、ローカルデータをそのまま返す")
                return local_data
            
            # データマージ
            enhanced_data = local_data.copy()
            
            # Alpha Vantageデータから追加情報を抽出
            latest_av_date = av_data.index[-1].date()
            latest_local_date = enhanced_data.index[-1].date()
            
            if latest_av_date > latest_local_date:
                logger.info("Alpha Vantageにより新しいデータが存在")
                # 新しいデータを追加する処理をここに実装
            
            # ボラティリティ指標追加
            av_returns = av_data['close'].pct_change()
            av_volatility = av_returns.rolling(window=20).std()
            
            # 最新のボラティリティをローカルデータに追加
            if not av_volatility.empty:
                latest_volatility = av_volatility.iloc[-1]
                enhanced_data['alpha_vantage_volatility'] = latest_volatility
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"データ強化エラー: {e}")
            return local_data
    
    def get_market_sentiment_score(self, symbol: str) -> float:
        """市場センチメントスコア取得"""
        try:
            # キャッシュチェック
            if symbol in self.sentiment_cache:
                cache_time, sentiment_score = self.sentiment_cache[symbol]
                if time.time() - cache_time < 3600:  # 1時間キャッシュ
                    return sentiment_score
            
            # センチメントデータ取得
            sentiment_data = self.client.get_news_sentiment(tickers=symbol)
            
            if not sentiment_data:
                return 0.0  # ニュートラル
            
            # 最新のセンチメントスコア計算
            recent_sentiments = [s for s in sentiment_data 
                               if (datetime.now() - s.timestamp).days <= 1]
            
            if not recent_sentiments:
                return 0.0
            
            # 重み付き平均（関連度で重み付け）
            total_score = sum(s.ticker_sentiment_score * s.relevance_score 
                            for s in recent_sentiments)
            total_weight = sum(s.relevance_score for s in recent_sentiments)
            
            sentiment_score = total_score / total_weight if total_weight > 0 else 0.0
            
            # キャッシュ更新
            self.sentiment_cache[symbol] = (time.time(), sentiment_score)
            
            return sentiment_score
            
        except Exception as e:
            logger.error(f"センチメントスコア取得エラー: {e}")
            return 0.0

def create_sample_integration():
    """Alpha Vantage統合のサンプル実装"""
    print("🌟 Alpha Vantage API統合サンプル")
    print("=" * 50)
    
    # サンプル用のAPIキー（実際の使用時は環境変数から取得）
    api_key = "demo"  # 実際のAPIキーに置き換えてください
    
    try:
        # クライアント初期化
        client = AlphaVantageClient(api_key)
        
        # FXデータ取得テスト
        print("\n📊 EURUSD 5分足データ取得テスト...")
        fx_data = client.get_fx_intraday("EUR", "USD", DataInterval.M5)
        
        if fx_data is not None:
            print(f"✅ データ取得成功: {len(fx_data)}レコード")
            print(fx_data.tail())
        else:
            print("❌ データ取得失敗")
        
        # センチメント分析テスト
        print("\n📰 ニュースセンチメント分析テスト...")
        sentiment_data = client.get_news_sentiment(topics="forex", limit=10)
        
        if sentiment_data:
            print(f"✅ センチメント取得成功: {len(sentiment_data)}件")
            for s in sentiment_data[:3]:
                print(f"   {s.symbol}: {s.sentiment.value} (スコア: {s.sentiment_score:.3f})")
        else:
            print("❌ センチメント取得失敗")
        
        # データ強化テスト
        print("\n🚀 データ強化機能テスト...")
        enhancer = MarketDataEnhancer(client)
        
        # サンプルローカルデータ
        sample_data = pd.DataFrame({
            'open': [1.1000, 1.1010, 1.1005],
            'high': [1.1015, 1.1020, 1.1015],
            'low': [1.0995, 1.1005, 1.1000],
            'close': [1.1010, 1.1005, 1.1012]
        }, index=pd.date_range('2025-01-01', periods=3, freq='H'))
        
        enhanced_data = enhancer.enhance_price_data("EURUSD", sample_data)
        print(f"✅ データ強化完了: {enhanced_data.columns.tolist()}")
        
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}")

if __name__ == "__main__":
    create_sample_integration()