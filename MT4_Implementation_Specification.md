# MT4ブレイクアウト戦略実装仕様書

## 概要
このドキュメントは、Pythonで実装されたブレイクアウト戦略をMT4 Expert Advisor (EA)として実装するための技術仕様を定義します。

## 1. コア戦略ロジック

### 1.1 ブレイクアウト検出ロジック
```python
# Python実装からの抽出
- ルックバック期間: 5-50バー（最適化可能）
- H4タイムフレーム: 24バー（4日間）のレンジ
- H1タイムフレーム: 24バー（1日間）のレンジ
- M5タイムフレーム: リアルタイムエントリー判定用
```

### 1.2 エントリー条件
**ロングエントリー:**
- 現在価格 > H4期間高値 + 最小ブレイク幅
- AND 現在価格 > H1期間高値 + 最小ブレイク幅
- AND セッションフィルター通過

**ショートエントリー:**
- 現在価格 < H4期間安値 - 最小ブレイク幅
- AND 現在価格 < H1期間安値 - 最小ブレイク幅
- AND セッションフィルター通過

### 1.3 エグジット条件
- **利確**: エントリー価格 ± (ATR × 利確倍率)
- **損切**: エントリー価格 ∓ (ATR × 損切倍率)
- **時間切れ**: 最大48時間保有

## 2. パラメータ定義

### 2.1 最適化可能パラメータ
```mql4
// 戦略パラメータ
extern int    H4_Period        = 24;     // H4レンジ期間（バー数）
extern int    H1_Period        = 24;     // H1レンジ期間（バー数）
extern int    ATR_Period       = 14;     // ATR計算期間
extern double Profit_ATR_Multi = 2.0;    // 利確ATR倍率
extern double Stop_ATR_Multi   = 1.5;    // 損切ATR倍率
extern double Min_Break_Pips   = 5;      // 最小ブレイク幅（pips）
```

### 2.2 リスク管理パラメータ
```mql4
// リスク管理
extern double Risk_Percent        = 1.5;     // 1取引あたりリスク（%）
extern int    Max_Consecutive_Loss = 4;      // 最大連続損失数
extern double Daily_Loss_Limit    = 2.0;     // 日次損失上限（%）
extern double Monthly_DD_Limit    = 12.0;    // 月次DD上限（%）
```

### 2.3 セッションフィルター
```mql4
// 取引時間設定
extern bool   Use_Session_Filter = true;
extern int    London_Start      = 7;     // ロンドンセッション開始時間(GMT)
extern int    London_End        = 16;    // ロンドンセッション終了時間
extern int    NY_Start          = 12;    // NYセッション開始時間
extern int    NY_End            = 21;    // NYセッション終了時間
extern int    Tokyo_Start       = 23;    // 東京セッション開始時間
extern int    Tokyo_End         = 8;     // 東京セッション終了時間
```

## 3. 主要関数の実装

### 3.1 ATR計算
```mql4
double CalculateATR(int period) {
    double atr = 0;
    for(int i = 1; i <= period; i++) {
        double tr = MathMax(High[i] - Low[i], 
                   MathMax(MathAbs(High[i] - Close[i+1]), 
                          MathAbs(Low[i] - Close[i+1])));
        atr += tr;
    }
    return atr / period;
}
```

### 3.2 レンジ計算
```mql4
void CalculateRange(int period, string timeframe, double &rangeHigh, double &rangeLow) {
    rangeHigh = iHigh(Symbol(), timeframe, iHighest(Symbol(), timeframe, MODE_HIGH, period, 1));
    rangeLow = iLow(Symbol(), timeframe, iLowest(Symbol(), timeframe, MODE_LOW, period, 1));
}
```

### 3.3 ブレイクアウト検出
```mql4
int CheckBreakout() {
    double h4High, h4Low, h1High, h1Low;
    double currentPrice = Bid;
    double minBreak = Min_Break_Pips * Point * 10; // pipsをPrice単位に変換
    
    // H4レンジ計算
    CalculateRange(H4_Period, PERIOD_H4, h4High, h4Low);
    
    // H1レンジ計算
    CalculateRange(H1_Period, PERIOD_H1, h1High, h1Low);
    
    // ロングブレイクアウト
    if(currentPrice > h4High + minBreak && currentPrice > h1High + minBreak) {
        return 1; // Buy signal
    }
    
    // ショートブレイクアウト
    if(currentPrice < h4Low - minBreak && currentPrice < h1Low - minBreak) {
        return -1; // Sell signal
    }
    
    return 0; // No signal
}
```

### 3.4 ポジションサイズ計算
```mql4
double CalculatePositionSize(double stopLossPips) {
    double accountRisk = AccountBalance() * Risk_Percent / 100;
    double pipValue = MarketInfo(Symbol(), MODE_TICKVALUE);
    double lotSize = accountRisk / (stopLossPips * pipValue * 10);
    
    // 最小・最大ロット制限
    lotSize = MathMax(MarketInfo(Symbol(), MODE_MINLOT), lotSize);
    lotSize = MathMin(MarketInfo(Symbol(), MODE_MAXLOT), lotSize);
    
    // ロットステップに丸める
    double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
    lotSize = MathFloor(lotSize / lotStep) * lotStep;
    
    return lotSize;
}
```

### 3.5 セッションフィルター
```mql4
bool IsInTradingSession() {
    if(!Use_Session_Filter) return true;
    
    int currentHour = TimeHour(TimeCurrent());
    
    // ロンドンセッション
    if(currentHour >= London_Start && currentHour < London_End) return true;
    
    // NYセッション
    if(currentHour >= NY_Start && currentHour < NY_End) return true;
    
    // 東京セッション（日付またぎ対応）
    if(currentHour >= Tokyo_Start || currentHour < Tokyo_End) return true;
    
    return false;
}
```

## 4. メインロジック構造

### 4.1 OnTick()関数
```mql4
void OnTick() {
    // リスク管理チェック
    if(!CheckRiskLimits()) return;
    
    // 既存ポジションチェック
    if(GetOpenPositions() > 0) {
        ManageOpenPositions();
        return;
    }
    
    // セッションフィルター
    if(!IsInTradingSession()) return;
    
    // ブレイクアウトシグナルチェック
    int signal = CheckBreakout();
    if(signal == 0) return;
    
    // ATR計算
    double atr = CalculateATR(ATR_Period);
    
    // エントリー実行
    if(signal == 1) {
        ExecuteBuyOrder(atr);
    } else if(signal == -1) {
        ExecuteSellOrder(atr);
    }
}
```

### 4.2 オーダー実行
```mql4
void ExecuteBuyOrder(double atr) {
    double stopLoss = Bid - (atr * Stop_ATR_Multi);
    double takeProfit = Bid + (atr * Profit_ATR_Multi);
    double stopLossPips = (Bid - stopLoss) / (Point * 10);
    double lotSize = CalculatePositionSize(stopLossPips);
    
    int ticket = OrderSend(Symbol(), OP_BUY, lotSize, Ask, 3, 
                          stopLoss, takeProfit, "Breakout EA", 
                          MagicNumber, 0, clrGreen);
    
    if(ticket < 0) {
        Print("Buy order failed: ", GetLastError());
    }
}
```

## 5. Python-MT4通信インターフェース

### 5.1 シグナル形式
```json
{
    "timestamp": "2025-01-19T12:00:00",
    "symbol": "EURUSD",
    "action": "BUY",
    "entry_price": 1.05000,
    "stop_loss": 1.04850,
    "take_profit": 1.05300,
    "position_size": 0.10,
    "signal_quality": 0.85,
    "strategy_params": {
        "h4_high": 1.04980,
        "h1_high": 1.04990,
        "atr": 0.00100
    }
}
```

### 5.2 実行レポート形式
```json
{
    "signal_id": "SIG_20250119_120000",
    "execution_time": "2025-01-19T12:00:01",
    "ticket_number": 12345678,
    "fill_price": 1.05002,
    "fill_quantity": 0.10,
    "slippage": 0.00002,
    "status": "FILLED"
}
```

## 6. 品質保証要件

### 6.1 バックテスト要件
- 最低2年間の履歴データ
- スプレッド・スリッページ考慮
- 99%モデリング品質

### 6.2 パフォーマンス目標
- 月次リターン: 3%以上
- 最大ドローダウン: 12%以下
- 最小取引数: 6回/月
- シャープレシオ: 0.15以上

### 6.3 リアルタイム監視
- ポジション状態
- 日次・月次P&L
- リスク指標
- システムヘルス

## 7. 実装優先順位

1. **Phase 1**: 基本ブレイクアウトロジック
   - レンジ計算
   - ブレイクアウト検出
   - 基本的なエントリー/エグジット

2. **Phase 2**: リスク管理機能
   - ポジションサイジング
   - 損失制限
   - セッションフィルター

3. **Phase 3**: Python連携
   - TCP/IPソケット通信
   - シグナル受信・実行
   - レポート送信

4. **Phase 4**: 高度な機能
   - パラメータ動的調整
   - マーケット適応
   - パフォーマンス最適化