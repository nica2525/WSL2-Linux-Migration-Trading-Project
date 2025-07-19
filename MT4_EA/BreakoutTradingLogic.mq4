//+------------------------------------------------------------------+
//|                                          BreakoutTradingLogic.mq4 |
//|                       Pythonブレイクアウト戦略のMT4実装            |
//|                    マルチタイムフレーム・ATRベースリスク管理       |
//+------------------------------------------------------------------+

#property strict
#property copyright "Claude Code"
#property link      "https://claude.ai"
#property version   "1.00"

//--- 入力パラメータ（Python実装に準拠）
// レンジ計算パラメータ
input int    H4_RangePeriod = 24;              // H4レンジ期間（バー数）
input int    H1_RangePeriod = 24;              // H1レンジ期間（バー数）
input double MinBreakDistance = 5.0;            // 最小ブレイク幅（pips）
input int    ATR_Period = 14;                   // ATR期間

// リスク管理パラメータ
input double RiskPercent = 1.5;                 // リスク割合（%）
input double ATR_MultiplierTP = 2.0;            // 利確ATR倍率
input double ATR_MultiplierSL = 1.5;            // 損切ATR倍率
input double MaxDailyLoss = 2.0;                // 最大日次損失（%）
input double MaxMonthlyDrawdown = 12.0;         // 最大月次ドローダウン（%）
input int    MaxConsecutiveLosses = 4;          // 最大連続損失数

// セッションフィルター
input bool   UseLondonSession = true;          // ロンドンセッション使用
input bool   UseNewYorkSession = true;          // ニューヨークセッション使用
input bool   UseTokyoSession = false;           // 東京セッション使用
input int    LondonStart = 7;                   // ロンドン開始（GMT）
input int    LondonEnd = 16;                    // ロンドン終了（GMT）
input int    NewYorkStart = 12;                 // ニューヨーク開始（GMT）
input int    NewYorkEnd = 21;                   // ニューヨーク終了（GMT）
input int    TokyoStart = 23;                   // 東京開始（GMT）
input int    TokyoEnd = 8;                      // 東京終了（GMT）

// デバッグパラメータ
input bool   EnableDebugPrint = true;           // デバッグ出力有効

//--- グローバル変数
double H4_RangeHigh = 0.0;
double H4_RangeLow = 0.0;
double H1_RangeHigh = 0.0;
double H1_RangeLow = 0.0;
datetime LastH4CalculationTime = 0;
datetime LastH1CalculationTime = 0;
bool H4_BreakoutDetected = false;
bool H1_BreakoutDetected = false;
int BreakoutDirection = 0;  // 1: 上方向, -1: 下方向, 0: なし

// リスク管理変数
double DailyLoss = 0.0;
double MonthlyDrawdown = 0.0;
int ConsecutiveLosses = 0;
datetime LastTradeDate = 0;
datetime LastMonthStart = 0;
double MonthStartBalance = 0.0;

//+------------------------------------------------------------------+
//| ATR計算関数                                                      |
//+------------------------------------------------------------------+
double CalculateATR(int timeframe, int period)
{
    double atr = iATR(Symbol(), timeframe, period, 0);
    return NormalizeDouble(atr, Digits);
}

//+------------------------------------------------------------------+
//| レンジ計算関数                                                   |
//+------------------------------------------------------------------+
void CalculateRange(int timeframe, int period, double &rangeHigh, double &rangeLow)
{
    rangeHigh = 0.0;
    rangeLow = 999999.0;
    
    for(int i = 1; i <= period; i++)
    {
        double high = iHigh(Symbol(), timeframe, i);
        double low = iLow(Symbol(), timeframe, i);
        
        if(high > rangeHigh) rangeHigh = high;
        if(low < rangeLow) rangeLow = low;
    }
    
    rangeHigh = NormalizeDouble(rangeHigh, Digits);
    rangeLow = NormalizeDouble(rangeLow, Digits);
}

//+------------------------------------------------------------------+
//| ブレイクアウト検出関数                                           |
//+------------------------------------------------------------------+
bool CheckBreakout(double currentPrice, double rangeHigh, double rangeLow, 
                   double minBreakDistance, int &direction)
{
    double pipSize = MarketInfo(Symbol(), MODE_POINT);
    if(Digits == 3 || Digits == 5) pipSize *= 10;
    
    double breakDistance = minBreakDistance * pipSize;
    
    // 上方向ブレイクアウト
    if(currentPrice > rangeHigh + breakDistance)
    {
        direction = 1;
        return true;
    }
    
    // 下方向ブレイクアウト
    if(currentPrice < rangeLow - breakDistance)
    {
        direction = -1;
        return true;
    }
    
    direction = 0;
    return false;
}

//+------------------------------------------------------------------+
//| 取引セッション確認関数                                           |
//+------------------------------------------------------------------+
bool IsInTradingSession()
{
    datetime currentGMT = TimeGMT();
    int currentHour = TimeHour(currentGMT);
    
    // ロンドンセッション
    if(UseLondonSession && currentHour >= LondonStart && currentHour < LondonEnd)
        return true;
    
    // ニューヨークセッション
    if(UseNewYorkSession && currentHour >= NewYorkStart && currentHour < NewYorkEnd)
        return true;
    
    // 東京セッション（日をまたぐ）
    if(UseTokyoSession)
    {
        if(TokyoStart > TokyoEnd)  // 23:00-08:00のような場合
        {
            if(currentHour >= TokyoStart || currentHour < TokyoEnd)
                return true;
        }
        else
        {
            if(currentHour >= TokyoStart && currentHour < TokyoEnd)
                return true;
        }
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| ポジションサイズ計算関数                                         |
//+------------------------------------------------------------------+
double CalculatePositionSize(double stopLossDistance)
{
    double accountBalance = AccountBalance();
    double riskAmount = accountBalance * (RiskPercent / 100.0);
    
    double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
    double pipValue = tickValue;
    if(Digits == 3 || Digits == 5) pipValue = tickValue * 10;
    
    double lotSize = riskAmount / (stopLossDistance / MarketInfo(Symbol(), MODE_POINT) * pipValue);
    
    // ロットサイズの正規化
    double minLot = MarketInfo(Symbol(), MODE_MINLOT);
    double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
    double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
    
    lotSize = MathFloor(lotSize / lotStep) * lotStep;
    lotSize = MathMax(lotSize, minLot);
    lotSize = MathMin(lotSize, maxLot);
    
    return NormalizeDouble(lotSize, 2);
}

//+------------------------------------------------------------------+
//| リスク管理チェック関数                                           |
//+------------------------------------------------------------------+
bool CheckRiskLimits()
{
    // 日次損失チェック
    if(DailyLoss >= MaxDailyLoss)
    {
        if(EnableDebugPrint) Print("❌ 日次損失限界到達: ", DailyLoss, "%");
        return false;
    }
    
    // 月次ドローダウンチェック
    if(MonthlyDrawdown >= MaxMonthlyDrawdown)
    {
        if(EnableDebugPrint) Print("❌ 月次ドローダウン限界到達: ", MonthlyDrawdown, "%");
        return false;
    }
    
    // 連続損失チェック
    if(ConsecutiveLosses >= MaxConsecutiveLosses)
    {
        if(EnableDebugPrint) Print("❌ 連続損失限界到達: ", ConsecutiveLosses, "回");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| リスク統計更新関数                                               |
//+------------------------------------------------------------------+
void UpdateRiskStatistics()
{
    datetime currentDate = TimeLocal();
    
    // 日付が変わった場合
    if(TimeDay(currentDate) != TimeDay(LastTradeDate))
    {
        DailyLoss = 0.0;
        LastTradeDate = currentDate;
    }
    
    // 月が変わった場合
    if(TimeMonth(currentDate) != TimeMonth(LastMonthStart))
    {
        MonthlyDrawdown = 0.0;
        MonthStartBalance = AccountBalance();
        LastMonthStart = currentDate;
    }
    
    // 月次ドローダウン計算
    if(MonthStartBalance > 0)
    {
        double currentDrawdown = (MonthStartBalance - AccountBalance()) / MonthStartBalance * 100.0;
        if(currentDrawdown > MonthlyDrawdown)
            MonthlyDrawdown = currentDrawdown;
    }
}

//+------------------------------------------------------------------+
//| エントリーシグナル生成関数                                       |
//+------------------------------------------------------------------+
void GenerateEntrySignal()
{
    // セッションチェック
    if(!IsInTradingSession())
    {
        if(EnableDebugPrint) Print("📍 取引セッション外");
        return;
    }
    
    // リスク管理チェック
    if(!CheckRiskLimits())
    {
        return;
    }
    
    // 既存ポジションチェック
    if(OrdersTotal() > 0)
    {
        if(EnableDebugPrint) Print("📍 既存ポジションあり");
        return;
    }
    
    double currentPrice = Bid;
    
    // H4タイムフレームでのブレイクアウトチェック
    int h4Direction = 0;
    H4_BreakoutDetected = CheckBreakout(currentPrice, H4_RangeHigh, H4_RangeLow, 
                                        MinBreakDistance, h4Direction);
    
    // H1タイムフレームでのブレイクアウトチェック
    int h1Direction = 0;
    H1_BreakoutDetected = CheckBreakout(currentPrice, H1_RangeHigh, H1_RangeLow, 
                                        MinBreakDistance, h1Direction);
    
    // 両タイムフレームでブレイクアウトが確認された場合
    if(H4_BreakoutDetected && H1_BreakoutDetected && h4Direction == h1Direction)
    {
        BreakoutDirection = h4Direction;
        
        // ATR計算
        double atr = CalculateATR(PERIOD_H1, ATR_Period);
        double stopLossDistance = atr * ATR_MultiplierSL;
        double takeProfitDistance = atr * ATR_MultiplierTP;
        
        // ポジションサイズ計算
        double lotSize = CalculatePositionSize(stopLossDistance);
        
        if(EnableDebugPrint)
        {
            Print("🎯 ブレイクアウトシグナル検出");
            Print("  方向: ", (BreakoutDirection > 0 ? "BUY" : "SELL"));
            Print("  ATR: ", atr);
            Print("  ロットサイズ: ", lotSize);
            Print("  SL距離: ", stopLossDistance);
            Print("  TP距離: ", takeProfitDistance);
        }
        
        // エントリー注文（実際の注文は通信システム経由で実行）
        SendEntrySignal(BreakoutDirection, lotSize, stopLossDistance, takeProfitDistance);
    }
}

//+------------------------------------------------------------------+
//| エントリーシグナル送信関数（プレースホルダー）                   |
//+------------------------------------------------------------------+
void SendEntrySignal(int direction, double lotSize, double slDistance, double tpDistance)
{
    // この関数は実際の通信システムと統合される
    // 現時点ではログ出力のみ
    
    string signal = "BREAKOUT_SIGNAL|";
    signal += "SYMBOL=" + Symbol() + "|";
    signal += "DIRECTION=" + (direction > 0 ? "BUY" : "SELL") + "|";
    signal += "LOT=" + DoubleToString(lotSize, 2) + "|";
    signal += "SL_DISTANCE=" + DoubleToString(slDistance, Digits) + "|";
    signal += "TP_DISTANCE=" + DoubleToString(tpDistance, Digits) + "|";
    signal += "TIMESTAMP=" + TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS);
    
    Print("📤 シグナル送信: ", signal);
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== BreakoutTradingLogic EA 初期化開始 ===");
    
    // 初期設定
    MonthStartBalance = AccountBalance();
    LastMonthStart = TimeLocal();
    LastTradeDate = TimeLocal();
    
    // レンジ計算
    CalculateRange(PERIOD_H4, H4_RangePeriod, H4_RangeHigh, H4_RangeLow);
    CalculateRange(PERIOD_H1, H1_RangePeriod, H1_RangeHigh, H1_RangeLow);
    
    Print("初期H4レンジ: High=", H4_RangeHigh, " Low=", H4_RangeLow);
    Print("初期H1レンジ: High=", H1_RangeHigh, " Low=", H1_RangeLow);
    
    Print("=== BreakoutTradingLogic EA 初期化完了 ===");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== BreakoutTradingLogic EA 終了 ===");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // リスク統計更新
    UpdateRiskStatistics();
    
    // H4レンジ更新（4時間ごと）
    datetime currentH4Time = iTime(Symbol(), PERIOD_H4, 0);
    if(currentH4Time != LastH4CalculationTime)
    {
        CalculateRange(PERIOD_H4, H4_RangePeriod, H4_RangeHigh, H4_RangeLow);
        LastH4CalculationTime = currentH4Time;
        if(EnableDebugPrint) Print("H4レンジ更新: High=", H4_RangeHigh, " Low=", H4_RangeLow);
    }
    
    // H1レンジ更新（1時間ごと）
    datetime currentH1Time = iTime(Symbol(), PERIOD_H1, 0);
    if(currentH1Time != LastH1CalculationTime)
    {
        CalculateRange(PERIOD_H1, H1_RangePeriod, H1_RangeHigh, H1_RangeLow);
        LastH1CalculationTime = currentH1Time;
        if(EnableDebugPrint) Print("H1レンジ更新: High=", H1_RangeHigh, " Low=", H1_RangeLow);
    }
    
    // エントリーシグナル生成
    GenerateEntrySignal();
}

//+------------------------------------------------------------------+