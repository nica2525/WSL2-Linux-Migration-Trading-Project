# 機械学習による取引予測システム仕様
**🚫 開発保留中**: Sub-Agent機能問題により開発作業休止中

## 🧠 基本コンセプト

### 🎯 目的
```
静的ルールベース（現在のJamesORB）
↓
動的学習ベース（AI予測）
- 市場パターンの自動学習
- リアルタイム予測更新
- 環境変化への自動適応
```

### 📊 従来との違い

#### 現在のJamesORB（静的）
```python
# 固定ルール
if price > orb_high + offset:
    signal = "BUY"
elif price < orb_low - offset:
    signal = "SELL"
```

#### AI予測システム（動的）
```python
# 学習ベース
market_features = extract_features(price_data, volume, sentiment)
prediction = model.predict(market_features)
confidence = model.predict_proba(market_features)

if prediction == "UP" and confidence > 0.75:
    signal = "BUY"
```

## 🛠️ 技術アーキテクチャ

### データソース
```python
# 多次元市場データ
market_data = {
    # 価格データ（基本）
    "ohlcv": get_ohlcv_data(timeframes=["1m", "5m", "15m", "1h"]),
    
    # テクニカル指標
    "indicators": {
        "sma": [20, 50, 200],
        "rsi": 14,
        "macd": (12, 26, 9),
        "bollinger": (20, 2),
        "atr": 14,
        "volume_profile": True
    },
    
    # 市場構造
    "market_structure": {
        "support_resistance": get_sr_levels(),
        "trend_direction": get_trend(),
        "volatility": get_volatility(),
        "session_bias": get_session_characteristics()
    },
    
    # 外部要因
    "external": {
        "economic_calendar": get_news_events(),
        "sentiment": get_market_sentiment(),
        "correlations": get_asset_correlations(),
        "flow_data": get_institutional_flow()
    }
}
```

### 機械学習パイプライン
```python
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb
import tensorflow as tf

class MarketPredictionEngine:
    def __init__(self):
        # アンサンブルモデル
        self.models = {
            "xgboost": xgb.XGBClassifier(),
            "random_forest": RandomForestClassifier(),
            "neural_network": self.build_lstm_model(),
            "gradient_boost": GradientBoostingClassifier()
        }
        
        self.feature_scaler = StandardScaler()
        self.prediction_history = []
    
    def build_lstm_model(self):
        """LSTM時系列予測モデル"""
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(50, return_sequences=False),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(25),
            tf.keras.layers.Dense(3, activation='softmax')  # BUY/SELL/HOLD
        ])
        return model
    
    def extract_features(self, market_data):
        """特徴量エンジニアリング"""
        features = []
        
        # 価格特徴量
        features.extend(self.get_price_features(market_data["ohlcv"]))
        
        # テクニカル特徴量
        features.extend(self.get_technical_features(market_data["indicators"]))
        
        # 市場構造特徴量
        features.extend(self.get_structure_features(market_data["market_structure"]))
        
        # 時間特徴量
        features.extend(self.get_time_features())
        
        # センチメント特徴量
        features.extend(self.get_sentiment_features(market_data["external"]))
        
        return np.array(features)
    
    def get_price_features(self, ohlcv):
        """価格ベース特徴量"""
        return [
            # リターン特徴量
            (ohlcv["close"] / ohlcv["close"].shift(1) - 1),  # 1期間リターン
            (ohlcv["close"] / ohlcv["close"].shift(5) - 1),  # 5期間リターン
            (ohlcv["close"] / ohlcv["close"].shift(20) - 1), # 20期間リターン
            
            # ボラティリティ特徴量
            ohlcv["high"] / ohlcv["low"] - 1,  # 期間内レンジ
            (ohlcv["high"] / ohlcv["close"].shift(1) - 1),  # 上髭
            (ohlcv["low"] / ohlcv["close"].shift(1) - 1),   # 下髭
            
            # 出来高特徴量
            ohlcv["volume"] / ohlcv["volume"].rolling(20).mean(),  # 相対出来高
        ]
    
    def predict_next_move(self, current_data):
        """次の動きを予測"""
        features = self.extract_features(current_data)
        predictions = {}
        
        # 各モデルで予測
        for name, model in self.models.items():
            pred = model.predict_proba(features.reshape(1, -1))[0]
            predictions[name] = {
                "BUY": pred[0],
                "SELL": pred[1], 
                "HOLD": pred[2]
            }
        
        # アンサンブル予測
        ensemble_pred = self.ensemble_prediction(predictions)
        
        # 信頼度計算
        confidence = self.calculate_confidence(predictions)
        
        return {
            "prediction": ensemble_pred,
            "confidence": confidence,
            "individual_models": predictions,
            "features_importance": self.get_feature_importance()
        }
    
    def online_learning(self, new_data, actual_result):
        """オンライン学習（リアルタイム更新）"""
        features = self.extract_features(new_data)
        
        # 実際の結果でモデル更新
        for model in self.models.values():
            if hasattr(model, 'partial_fit'):
                model.partial_fit(features.reshape(1, -1), [actual_result])
        
        # 予測精度追跡
        self.track_prediction_accuracy(new_data, actual_result)
```

### リアルタイム実装
```python
class RealtimeMLTrader:
    def __init__(self):
        self.prediction_engine = MarketPredictionEngine()
        self.data_collector = MarketDataCollector()
        self.position_manager = PositionManager()
        
    async def run_prediction_loop(self):
        """リアルタイム予測ループ"""
        while True:
            # 最新データ取得
            current_data = await self.data_collector.get_realtime_data()
            
            # 予測実行
            prediction = self.prediction_engine.predict_next_move(current_data)
            
            # トレード判断
            if prediction["confidence"] > 0.75:  # 高信頼度のみ
                await self.execute_trade_signal(prediction)
            
            # 5分間隔で実行
            await asyncio.sleep(300)
    
    async def execute_trade_signal(self, prediction):
        """AI予測に基づくトレード実行"""
        signal = prediction["prediction"]
        confidence = prediction["confidence"]
        
        # リスク管理
        position_size = self.calculate_position_size(confidence)
        
        if signal == "BUY" and not self.position_manager.has_buy_position():
            await self.position_manager.open_buy(
                size=position_size,
                stop_loss=self.calculate_stop_loss(prediction),
                take_profit=self.calculate_take_profit(prediction)
            )
        elif signal == "SELL" and not self.position_manager.has_sell_position():
            await self.position_manager.open_sell(
                size=position_size,
                stop_loss=self.calculate_stop_loss(prediction),
                take_profit=self.calculate_take_profit(prediction)
            )
```

## 📊 学習データ・特徴量

### 入力特徴量（100+次元）
```python
feature_categories = {
    # 価格・出来高（20次元）
    "price": ["returns", "volatility", "range", "gaps", "volume_profile"],
    
    # テクニカル指標（30次元）
    "technical": ["sma", "ema", "rsi", "macd", "bollinger", "stochastic", "atr"],
    
    # 市場構造（25次元）
    "structure": ["support_resistance", "trend", "pattern", "breakout", "momentum"],
    
    # 時間特徴量（15次元）
    "temporal": ["session", "day_of_week", "hour", "seasonal", "holiday"],
    
    # センチメント（10次元）
    "sentiment": ["news_sentiment", "social_sentiment", "fear_greed", "flows"]
}
```

### 予測ターゲット
```python
# 分類問題
target_classes = {
    "BUY": "次の30分で+20pips以上上昇",
    "SELL": "次の30分で-20pips以上下落", 
    "HOLD": "±20pips範囲内で推移"
}

# 回帰問題（高度版）
target_regression = {
    "price_change": "30分後の価格変化（pips）",
    "volatility": "30分後のボラティリティ",
    "duration": "トレンド継続時間"
}
```

## 🎯 JamesORBとの統合

### ハイブリッドアプローチ
```python
class HybridTradingSystem:
    def __init__(self):
        self.james_orb = JamesORBStrategy()
        self.ml_predictor = MarketPredictionEngine()
    
    def generate_signal(self, market_data):
        # 1. JamesORBシグナル
        orb_signal = self.james_orb.get_signal(market_data)
        
        # 2. AI予測
        ai_prediction = self.ml_predictor.predict_next_move(market_data)
        
        # 3. 統合判断
        if orb_signal and ai_prediction["prediction"] == orb_signal:
            # 両方が一致 → 高信頼度
            if ai_prediction["confidence"] > 0.8:
                return {
                    "signal": orb_signal,
                    "confidence": "HIGH",
                    "source": "ORB+AI_CONSENSUS"
                }
        
        elif ai_prediction["confidence"] > 0.9:
            # AI単独で高信頼度
            return {
                "signal": ai_prediction["prediction"],
                "confidence": "MEDIUM",
                "source": "AI_ONLY"
            }
        
        return {"signal": "HOLD", "confidence": "LOW"}
```

## 🚀 実装ロードマップ

### Phase 1: データ収集・前処理 (1-2週間)
- 過去データ収集・整理
- 特徴量エンジニアリング
- データパイプライン構築

### Phase 2: モデル開発・学習 (2-3週間)
- ベースラインモデル開発
- 各種アルゴリズム比較
- アンサンブル最適化

### Phase 3: バックテスト・検証 (1-2週間)
- 過去データでのバックテスト
- JamesORBとの性能比較
- リスク分析

### Phase 4: リアルタイム統合 (1-2週間)
- システム統合
- デモ取引テスト
- パフォーマンス最適化

## 💡 期待される効果

### 定量的改善
- **勝率**: 60% → 70-75%
- **プロフィットファクター**: 1.2 → 1.5-2.0
- **最大ドローダウン**: 20% → 15%
- **シャープレシオ**: 0.8 → 1.2-1.5

### 定性的改善
- 市場環境変化への自動適応
- パターン認識の高度化
- エントリータイミングの精度向上
- リスク管理の最適化