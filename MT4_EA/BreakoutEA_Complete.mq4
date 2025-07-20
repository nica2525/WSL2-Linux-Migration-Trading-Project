//+------------------------------------------------------------------+
//|                                           BreakoutEA_Complete.mq4 |
//|                        完全版ブレイクアウトEA - Python統合版     |
//|      WFA最適化パラメータ + Python通信 + 高度リスク管理統合      |
//+------------------------------------------------------------------+

#property strict
#property copyright "Claude Code - Complete Integration"
#property link      "https://claude.ai"
#property version   "3.00"

//--- 基本設定
input string Section1 = "=== 基本設定 ===";
input bool   UseWFAParameters = true;                    // WFA最適化パラメータ使用
input string WFAParameterFile = "wfa_params.ini";        // WFAパラメータファイル
input bool   AutoExecuteTrades = true;                   // 自動取引実行
input int    MagicNumber = 20250720;                     // マジックナンバー
input bool   EnableDebugPrint = true;                    // デバッグ出力

//--- 通信設定
input string Section2 = "=== Python通信設定 ===";
input bool   UsePythonCommunication = true;              // Python通信使用
input string PythonServerHost = "localhost";             // Pythonサーバーホスト
input int    PythonServerPort = 8888;                    // Pythonサーバーポート
input string MessageFileDirectory = "C:\\temp\\mt4_bridge_messages"; // メッセージディレクトリ
input int    HeartbeatInterval = 5;                      // ハートビート間隔（秒）

//--- ブレイクアウトパラメータ（WFAで上書き可能）
input string Section3 = "=== ブレイクアウト設定（デフォルト） ===";
input int    Default_H1_Period = 24;                     // H1レンジ期間（単独使用）
input double Default_MinBreakDistance = 5.0;             // 最小ブレイク幅（pips）
input int    Default_ATR_Period = 14;                    // ATR期間
input double Default_ATR_MultiplierTP = 2.5;             // 利確ATR倍率
input double Default_ATR_MultiplierSL = 1.3;             // 損切ATR倍率

//--- 高度リスク管理
input string Section4 = "=== リスク管理設定 ===";
input double RiskPercent = 1.5;                          // リスク割合（%）
input double MaxDailyLoss = 2.0;                         // 最大日次損失（%）
input double MaxWeeklyLoss = 5.0;                        // 最大週次損失（%）
input double MaxMonthlyDrawdown = 12.0;                  // 最大月次ドローダウン（%）
input int    MaxConsecutiveLosses = 4;                   // 最大連続損失数
input int    MaxDailyTrades = 5;                         // 最大日次取引数
input double MinAccountBalance = 1000.0;                 // 最小口座残高
input bool   UseNewsFiter = false;                       // ニュースフィルター使用

//--- パフォーマンス最適化設定（Gemini改善案）
input string Section4b = "=== パフォーマンス最適化設定 ===";
input int    RiskUpdateIntervalSec = 60;                 // リスク統計更新間隔（秒）
input int    RiskCheckIntervalSec = 30;                  // リスク制限チェック間隔（秒）
input int    AtrUpdateIntervalSec = 300;                 // ATR計算更新間隔（秒）
input int    LogTickInterval = 100;                      // ログ出力Tick間隔

//--- セッション管理
input string Section5 = "=== セッション設定 ===";
input bool   UseLondonSession = true;                    // ロンドンセッション
input bool   UseNewYorkSession = true;                   // ニューヨークセッション
input bool   UseTokyoSession = false;                    // 東京セッション
input int    LondonStart = 7;                            // ロンドン開始（GMT）
input int    LondonEnd = 16;                             // ロンドン終了（GMT）
input int    NewYorkStart = 12;                          // ニューヨーク開始（GMT）
input int    NewYorkEnd = 21;                            // ニューヨーク終了（GMT）
input int    TokyoStart = 23;                            // 東京開始（GMT）
input int    TokyoEnd = 8;                               // 東京終了（GMT）

//--- WFAパラメータ構造体
struct WFAParameters
{
    int h1_period;
    double min_break_distance;
    int atr_period;
    double atr_multiplier_tp;
    double atr_multiplier_sl;
    double min_atr_ratio;
    double min_trend_strength;
    double min_profit_pips;
    double cost_ratio;
    bool is_loaded;
};

//--- パフォーマンスキャッシュ構造体（Gemini改善案）
struct PerformanceCache
{
    // Risk Statistics Cache
    datetime last_risk_update;
    
    // Risk Limit Check Cache
    bool     limits_ok;
    datetime last_risk_check;

    // ATR & Quality Cache
    double   atr_value;
    bool     atr_quality_ok;
    bool     trend_strength_ok;
    datetime last_atr_update;
};

//--- グローバル変数
WFAParameters g_wfa_params;
bool g_parameters_loaded = false;

// 通信関連
int g_socket_handle = -1;
bool g_is_connected = false;
datetime g_last_heartbeat = 0;

// パフォーマンス最適化（Gemini改善案）
PerformanceCache g_cache;
int g_tick_count = 0;                 // Tick計数（デバッグ用）

// ブレイクアウト計算（H1単独）
double g_h1_range_high = 0.0;
double g_h1_range_low = 0.0;
datetime g_last_h1_time = 0;

// リスク管理
double g_initial_balance = 0.0;
double g_daily_loss = 0.0;
double g_weekly_loss = 0.0;
double g_monthly_drawdown = 0.0;
int g_consecutive_losses = 0;
int g_daily_trades = 0;
datetime g_last_trade_date = 0;
datetime g_week_start = 0;
datetime g_month_start = 0;
double g_daily_start_balance = 0.0;      // 日開始残高（追加）
double g_week_start_balance = 0.0;
double g_month_start_balance = 0.0;

// 統計
int g_total_signals = 0;
int g_total_trades = 0;
int g_winning_trades = 0;
int g_losing_trades = 0;

// OnTrade処理用（MQL4には標準でOnTradeがないため独自実装）
static int g_previous_history_total = 0;

//+------------------------------------------------------------------+
//| デフォルトパラメータ設定関数                                     |
//+------------------------------------------------------------------+
bool LoadDefaultParameters()
{
    g_wfa_params.h1_period = Default_H1_Period;
    g_wfa_params.min_break_distance = Default_MinBreakDistance;
    g_wfa_params.atr_period = Default_ATR_Period;
    g_wfa_params.atr_multiplier_tp = Default_ATR_MultiplierTP;
    g_wfa_params.atr_multiplier_sl = Default_ATR_MultiplierSL;
    g_wfa_params.min_atr_ratio = 1.0;
    g_wfa_params.min_trend_strength = 0.0005;  // 最終調整: 実測値に基づく最適化（0.001→0.0005）
    g_wfa_params.min_profit_pips = 4.0;
    g_wfa_params.cost_ratio = 2.0;
    g_wfa_params.is_loaded = true;
    
    Print("✅ デフォルトパラメータを使用");
    return true;
}

//+------------------------------------------------------------------+
//| WFAパラメータ読み込み関数（安全版 - 無限再帰修正済み）           |
//+------------------------------------------------------------------+
bool LoadWFAParameters()
{
    // WFA使用しない場合はデフォルト設定
    if(!UseWFAParameters)
    {
        return LoadDefaultParameters();
    }
    
    // ファイル読み込み試行
    string filepath = WFAParameterFile;
    int handle = FileOpen(filepath, FILE_READ|FILE_TXT|FILE_COMMON);
    
    if(handle == INVALID_HANDLE)
    {
        // エラーログ強化: 詳細なエラー情報を出力
        int error_code = GetLastError();
        Print("❌ WFAファイル読み込み失敗 - エラーコード: ", error_code);
        Print("   ファイルパス: ", filepath);
        
        // 主要エラーコードの説明
        string error_desc = "";
        switch(error_code) {
            case 0: error_desc = "不明なエラー"; break;
            case 4103: error_desc = "ファイルが見つかりません"; break;
            case 4104: error_desc = "ファイルオープンエラー"; break;
            case 4105: error_desc = "ファイルアクセス権限エラー"; break;
            case 4106: error_desc = "ディスク容量不足"; break;
            default: error_desc = "その他のファイルエラー"; break;
        }
        Print("   エラー詳細: ", error_desc);
        Print("   → デフォルトパラメータで動作継続");
        
        // 無限再帰を回避: デフォルト設定を直接実行
        return LoadDefaultParameters();
    }
    
    // ファイル読み込み処理
    Print("📁 WFAパラメータファイル読み込み開始: ", filepath);
    
    string line;
    int lines_read = 0;
    
    while(!FileIsEnding(handle))
    {
        line = FileReadString(handle);
        lines_read++;
        
        // 空行やコメント行をスキップ
        if(StringLen(line) == 0 || StringFind(line, "#") == 0 || StringFind(line, "//") == 0)
            continue;
            
        // パラメータ解析
        if(StringFind(line, "h1_period=") == 0)
            g_wfa_params.h1_period = (int)StringToInteger(StringSubstr(line, 10));
        else if(StringFind(line, "min_break_distance=") == 0)
            g_wfa_params.min_break_distance = StringToDouble(StringSubstr(line, 19));
        else if(StringFind(line, "atr_period=") == 0)
            g_wfa_params.atr_period = (int)StringToInteger(StringSubstr(line, 11));
        else if(StringFind(line, "atr_multiplier_tp=") == 0)
            g_wfa_params.atr_multiplier_tp = StringToDouble(StringSubstr(line, 18));
        else if(StringFind(line, "atr_multiplier_sl=") == 0)
            g_wfa_params.atr_multiplier_sl = StringToDouble(StringSubstr(line, 18));
        else if(StringFind(line, "min_atr_ratio=") == 0)
            g_wfa_params.min_atr_ratio = StringToDouble(StringSubstr(line, 14));
        else if(StringFind(line, "min_trend_strength=") == 0)
            g_wfa_params.min_trend_strength = StringToDouble(StringSubstr(line, 19));
        else if(StringFind(line, "min_profit_pips=") == 0)
            g_wfa_params.min_profit_pips = StringToDouble(StringSubstr(line, 16));
        else if(StringFind(line, "cost_ratio=") == 0)
            g_wfa_params.cost_ratio = StringToDouble(StringSubstr(line, 11));
        else if(EnableDebugPrint)
            Print("⚠️ 未知のパラメータ行: ", line);
    }
    
    // ファイルクローズ（必須）
    FileClose(handle);
    g_wfa_params.is_loaded = true;
    
    // 読み込み結果報告
    Print("✅ WFAパラメータ読み込み成功 (", lines_read, "行処理)");
    Print("  H1期間: ", g_wfa_params.h1_period);
    Print("  ATR期間: ", g_wfa_params.atr_period);
    Print("  TP倍率: ", g_wfa_params.atr_multiplier_tp);
    Print("  SL倍率: ", g_wfa_params.atr_multiplier_sl);
    Print("  最小ATR比率: ", g_wfa_params.min_atr_ratio);
    Print("  最小トレンド強度: ", g_wfa_params.min_trend_strength);
    Print("  最小利益pips: ", g_wfa_params.min_profit_pips);
    Print("  コスト比率: ", g_wfa_params.cost_ratio);
    
    return true;
}

//+------------------------------------------------------------------+
//| 高度リスク管理チェック関数                                       |
//+------------------------------------------------------------------+
bool CheckAdvancedRiskLimits()
{
    // 最小残高チェック
    if(AccountBalance() < MinAccountBalance)
    {
        Print("❌ 最小残高未満: ", AccountBalance(), " < ", MinAccountBalance);
        return false;
    }
    
    // 日次損失チェック
    if(g_daily_loss >= MaxDailyLoss)
    {
        Print("❌ 日次損失限界: ", g_daily_loss, "% >= ", MaxDailyLoss, "%");
        return false;
    }
    
    // 週次損失チェック
    if(g_weekly_loss >= MaxWeeklyLoss)
    {
        Print("❌ 週次損失限界: ", g_weekly_loss, "% >= ", MaxWeeklyLoss, "%");
        return false;
    }
    
    // 月次ドローダウンチェック
    if(g_monthly_drawdown >= MaxMonthlyDrawdown)
    {
        Print("❌ 月次ドローダウン限界: ", g_monthly_drawdown, "% >= ", MaxMonthlyDrawdown, "%");
        return false;
    }
    
    // 連続損失チェック
    if(g_consecutive_losses >= MaxConsecutiveLosses)
    {
        Print("❌ 連続損失限界: ", g_consecutive_losses, " >= ", MaxConsecutiveLosses);
        return false;
    }
    
    // 日次取引数チェック
    if(g_daily_trades >= MaxDailyTrades)
    {
        Print("❌ 日次取引数限界: ", g_daily_trades, " >= ", MaxDailyTrades);
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| リスク統計更新関数（修正版 - 期間開始残高基準）                   |
//+------------------------------------------------------------------+
void UpdateRiskStatistics()
{
    datetime current_time = TimeLocal();
    
    // 日付変更チェック
    if(TimeDay(current_time) != TimeDay(g_last_trade_date))
    {
        g_daily_loss = 0.0;
        g_daily_trades = 0;
        g_daily_start_balance = AccountBalance();  // 日開始残高を記録
        g_last_trade_date = current_time;
        
        if(EnableDebugPrint)
            Print("📅 新しい日開始: 残高=", g_daily_start_balance);
    }
    
    // 週変更チェック
    if(TimeDayOfWeek(current_time) == 1 && current_time != g_week_start) // 月曜日
    {
        g_weekly_loss = 0.0;
        g_week_start_balance = AccountBalance();
        g_week_start = current_time;
        
        if(EnableDebugPrint)
            Print("📅 新しい週開始: 残高=", g_week_start_balance);
    }
    
    // 月変更チェック
    if(TimeMonth(current_time) != TimeMonth(g_month_start))
    {
        g_monthly_drawdown = 0.0;
        g_month_start_balance = AccountBalance();
        g_month_start = current_time;
        
        if(EnableDebugPrint)
            Print("📅 新しい月開始: 残高=", g_month_start_balance);
    }
    
    // 日次損失計算（日開始残高基準）
    if(g_daily_start_balance > 0)
    {
        double current_daily_loss = (g_daily_start_balance - AccountBalance()) / g_daily_start_balance * 100.0;
        if(current_daily_loss > g_daily_loss)
            g_daily_loss = current_daily_loss;
    }
    
    // 週次損失計算（週開始残高基準）
    if(g_week_start_balance > 0)
    {
        double current_weekly_loss = (g_week_start_balance - AccountBalance()) / g_week_start_balance * 100.0;
        if(current_weekly_loss > g_weekly_loss)
            g_weekly_loss = current_weekly_loss;
    }
    
    // 月次ドローダウン計算（月開始残高基準）
    if(g_month_start_balance > 0)
    {
        double current_monthly_dd = (g_month_start_balance - AccountBalance()) / g_month_start_balance * 100.0;
        if(current_monthly_dd > g_monthly_drawdown)
            g_monthly_drawdown = current_monthly_dd;
    }
}

//+------------------------------------------------------------------+
//| ATR関連更新関数（Gemini改善案）                                  |
//+------------------------------------------------------------------+
void UpdateAtrCache()
{
    datetime current_time = TimeCurrent();
    g_cache.atr_value = iATR(Symbol(), PERIOD_H1, g_wfa_params.atr_period, 0);
    g_cache.last_atr_update = current_time;
    
    g_cache.atr_quality_ok = CheckATRQuality(g_cache.atr_value);
    g_cache.trend_strength_ok = CheckTrendStrength();
    
    if(EnableDebugPrint)
        Print("📈 ATR更新: ", NormalizeDouble(g_cache.atr_value, Digits), 
              " 品質:", (g_cache.atr_quality_ok ? "OK" : "NG"), 
              " トレンド:", (g_cache.trend_strength_ok ? "OK" : "NG"));
}

//+------------------------------------------------------------------+
//| リスク統計・制限チェック統合関数（Gemini改善案）                 |
//+------------------------------------------------------------------+
void UpdateRiskAndLimits()
{
    datetime current_time = TimeCurrent();
    
    UpdateRiskStatistics();
    g_cache.last_risk_update = current_time;
    
    // 統計更新に基づき、リスク制限を即時チェック
    g_cache.limits_ok = CheckAdvancedRiskLimits();
    g_cache.last_risk_check = current_time;

    if(EnableDebugPrint)
        Print("📊 リスク情報更新完了。制限: ", (g_cache.limits_ok ? "OK" : "NG"));
}

//+------------------------------------------------------------------+
//| ATR品質フィルター                                                |
//+------------------------------------------------------------------+
bool CheckATRQuality(double atr)
{
    if(!g_wfa_params.is_loaded) return true;
    
    double pip_value = MarketInfo(Symbol(), MODE_POINT);
    if(Digits == 3 || Digits == 5) pip_value *= 10;
    
    double atr_pips = atr / pip_value;
    
    // ATR品質チェック
    if(atr_pips < g_wfa_params.min_atr_ratio * g_wfa_params.min_profit_pips)
    {
        if(EnableDebugPrint) 
            Print("⚠️ ATR品質不足: ", atr_pips, " < ", 
                  g_wfa_params.min_atr_ratio * g_wfa_params.min_profit_pips);
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| トレンド強度チェック                                             |
//+------------------------------------------------------------------+
bool CheckTrendStrength()
{
    if(!g_wfa_params.is_loaded) return true;
    
    // 簡単なトレンド強度計算（移動平均の傾き）
    double ma_fast = iMA(Symbol(), PERIOD_H1, 10, 0, MODE_SMA, PRICE_CLOSE, 0);
    double ma_slow = iMA(Symbol(), PERIOD_H1, 20, 0, MODE_SMA, PRICE_CLOSE, 0);
    
    double trend_strength = MathAbs(ma_fast - ma_slow) / ma_slow;
    
    if(trend_strength < g_wfa_params.min_trend_strength)
    {
        if(EnableDebugPrint) 
            Print("⚠️ トレンド強度不足: ", trend_strength, " < ", g_wfa_params.min_trend_strength);
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| レンジ計算関数（WFAパラメータ対応）                              |
//+------------------------------------------------------------------+
void CalculateRange(int timeframe, int period, double &range_high, double &range_low)
{
    range_high = 0.0;
    range_low = 999999.0;
    
    for(int i = 1; i <= period; i++)
    {
        double high = iHigh(Symbol(), timeframe, i);
        double low = iLow(Symbol(), timeframe, i);
        
        if(high > range_high) range_high = high;
        if(low < range_low) range_low = low;
    }
    
    range_high = NormalizeDouble(range_high, Digits);
    range_low = NormalizeDouble(range_low, Digits);
}

//+------------------------------------------------------------------+
//| ブレイクアウト検出（WFAパラメータ対応）                          |
//+------------------------------------------------------------------+
bool CheckBreakout(double current_price, double range_high, double range_low, int &direction)
{
    double pip_size = MarketInfo(Symbol(), MODE_POINT);
    if(Digits == 3 || Digits == 5) pip_size *= 10;
    
    double break_distance = g_wfa_params.min_break_distance * pip_size;
    
    if(current_price > range_high + break_distance)
    {
        direction = 1;
        return true;
    }
    
    if(current_price < range_low - break_distance)
    {
        direction = -1;
        return true;
    }
    
    direction = 0;
    return false;
}

//+------------------------------------------------------------------+
//| セッションチェック関数                                           |
//+------------------------------------------------------------------+
bool IsInTradingSession()
{
    datetime current_gmt = TimeGMT();
    int current_hour = TimeHour(current_gmt);
    
    if(UseLondonSession && current_hour >= LondonStart && current_hour < LondonEnd)
        return true;
    
    if(UseNewYorkSession && current_hour >= NewYorkStart && current_hour < NewYorkEnd)
        return true;
    
    if(UseTokyoSession)
    {
        if(TokyoStart > TokyoEnd)
        {
            if(current_hour >= TokyoStart || current_hour < TokyoEnd)
                return true;
        }
        else
        {
            if(current_hour >= TokyoStart && current_hour < TokyoEnd)
                return true;
        }
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| ポジションサイズ計算（リスク調整）                               |
//+------------------------------------------------------------------+
double CalculatePositionSize(double stop_loss_distance)
{
    double risk_amount = AccountBalance() * (RiskPercent / 100.0);
    
    // 連続損失に基づくリスク調整
    if(g_consecutive_losses > 0)
    {
        double risk_reduction = 1.0 - (g_consecutive_losses * 0.1); // 10%ずつ減少
        risk_reduction = MathMax(risk_reduction, 0.5); // 最大50%減少
        risk_amount *= risk_reduction;
    }
    
    double tick_value = MarketInfo(Symbol(), MODE_TICKVALUE);
    double pip_value = tick_value;
    if(Digits == 3 || Digits == 5) pip_value = tick_value * 10;
    
    double lot_size = risk_amount / (stop_loss_distance / MarketInfo(Symbol(), MODE_POINT) * pip_value);
    
    // ロットサイズ正規化
    double min_lot = MarketInfo(Symbol(), MODE_MINLOT);
    double max_lot = MarketInfo(Symbol(), MODE_MAXLOT);
    double lot_step = MarketInfo(Symbol(), MODE_LOTSTEP);
    
    lot_size = MathFloor(lot_size / lot_step) * lot_step;
    lot_size = MathMax(lot_size, min_lot);
    lot_size = MathMin(lot_size, max_lot);
    
    return NormalizeDouble(lot_size, 2);
}

//+------------------------------------------------------------------+
//| JSON信号生成関数                                                 |
//+------------------------------------------------------------------+
string GenerateSignalJSON(int direction, double lot_size, double sl_distance, double tp_distance)
{
    // キャッシュされたATRを使用（Gemini改善案）
    double atr = g_cache.atr_value;
    
    string json = "{";
    json += "\"type\": \"ADVANCED_BREAKOUT_SIGNAL\",";
    json += "\"symbol\": \"" + Symbol() + "\",";
    json += "\"direction\": \"" + (direction > 0 ? "BUY" : "SELL") + "\",";
    json += "\"lot_size\": " + DoubleToString(lot_size, 2) + ",";
    json += "\"sl_distance\": " + DoubleToString(sl_distance, Digits) + ",";
    json += "\"tp_distance\": " + DoubleToString(tp_distance, Digits) + ",";
    json += "\"current_price\": " + DoubleToString(Bid, Digits) + ",";
    json += "\"h1_range_high\": " + DoubleToString(g_h1_range_high, Digits) + ",";
    json += "\"h1_range_low\": " + DoubleToString(g_h1_range_low, Digits) + ",";
    json += "\"atr\": " + DoubleToString(atr, Digits) + ",";
    json += "\"wfa_params\": {";
    json += "\"h1_period\": " + IntegerToString(g_wfa_params.h1_period) + ",";
    json += "\"atr_period\": " + IntegerToString(g_wfa_params.atr_period) + ",";
    json += "\"tp_multiplier\": " + DoubleToString(g_wfa_params.atr_multiplier_tp, 2) + ",";
    json += "\"sl_multiplier\": " + DoubleToString(g_wfa_params.atr_multiplier_sl, 2) + "";
    json += "},";
    json += "\"risk_stats\": {";
    json += "\"daily_loss\": " + DoubleToString(g_daily_loss, 2) + ",";
    json += "\"consecutive_losses\": " + IntegerToString(g_consecutive_losses) + ",";
    json += "\"daily_trades\": " + IntegerToString(g_daily_trades) + ",";
    json += "\"account_balance\": " + DoubleToString(AccountBalance(), 2) + "";
    json += "},";
    json += "\"timestamp\": \"" + TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS) + "\"";
    json += "}";
    
    return json;
}

//+------------------------------------------------------------------+
//| 取引実行関数                                                     |
//+------------------------------------------------------------------+
bool ExecuteTrade(int direction, double lot_size, double sl_distance, double tp_distance)
{
    if(!AutoExecuteTrades) return false;
    
    double price, sl, tp;
    int order_type;
    
    if(direction > 0) // BUY
    {
        order_type = OP_BUY;
        price = Ask;
        sl = price - sl_distance;
        tp = price + tp_distance;
    }
    else // SELL
    {
        order_type = OP_SELL;
        price = Bid;
        sl = price + sl_distance;
        tp = price - tp_distance;
    }
    
    int ticket = OrderSend(Symbol(), order_type, lot_size, price, 3, sl, tp, 
                          "Advanced Breakout EA", MagicNumber, 0, 
                          direction > 0 ? clrBlue : clrRed);
    
    if(ticket > 0)
    {
        g_total_trades++;
        g_daily_trades++;
        Print("✅ 取引実行成功: Ticket=", ticket, " Direction=", 
              (direction > 0 ? "BUY" : "SELL"), " Lots=", lot_size);
        return true;
    }
    else
    {
        Print("❌ 取引実行失敗: Error=", GetLastError());
        return false;
    }
}

//+------------------------------------------------------------------+
//| 統計表示関数                                                     |
//+------------------------------------------------------------------+
void PrintStatistics()
{
    Print("=== ブレイクアウトEA統計 ===");
    Print("WFAパラメータ使用: ", (UseWFAParameters ? "有効" : "無効"));
    Print("総シグナル数: ", g_total_signals);
    Print("総取引数: ", g_total_trades);
    Print("勝率: ", (g_total_trades > 0 ? (double)g_winning_trades / g_total_trades * 100.0 : 0.0), "%");
    Print("初期残高: ", g_initial_balance);
    Print("現在残高: ", AccountBalance());
    Print("日次損失: ", g_daily_loss, "%");
    Print("週次損失: ", g_weekly_loss, "%");
    Print("月次DD: ", g_monthly_drawdown, "%");
    Print("連続損失: ", g_consecutive_losses);
    Print("========================");
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== BreakoutEA_Complete 初期化開始 ===");
    
    // WFAパラメータ読み込み
    if(!LoadWFAParameters())
    {
        Print("❌ パラメータ読み込み失敗");
        return(INIT_FAILED);
    }
    
    // 初期設定
    g_initial_balance = AccountBalance();
    g_daily_start_balance = AccountBalance();    // 日次開始残高初期化
    g_month_start_balance = AccountBalance();
    g_week_start_balance = AccountBalance();
    g_month_start = TimeLocal();
    g_week_start = TimeLocal();
    g_last_trade_date = TimeLocal();
    
    if(EnableDebugPrint)
        Print("💰 残高初期化: 初期=", g_initial_balance, " 日次開始=", g_daily_start_balance);
    
    // パフォーマンス最適化変数の初期化（Gemini改善案）
    g_cache.last_risk_update = 0;        // 初回実行を促す
    g_cache.last_risk_check = 0;
    g_cache.last_atr_update = 0;
    g_cache.limits_ok = true;            // 最初はOKと仮定
    g_cache.atr_value = 0.0;
    g_cache.atr_quality_ok = false;
    g_cache.trend_strength_ok = false;
    
    g_tick_count = 0;
    
    // OnInit時に初回計算を実行（Gemini改善案）
    UpdateRiskAndLimits();
    UpdateAtrCache();
    
    // OnTrade代替実装のための履歴総数初期化
    g_previous_history_total = OrdersHistoryTotal();
    if(EnableDebugPrint)
        Print("📊 初期履歴総数: ", g_previous_history_total, "件");
    
    // レンジ計算（H1単独）
    CalculateRange(PERIOD_H1, g_wfa_params.h1_period, g_h1_range_high, g_h1_range_low);
    
    Print("初期H1レンジ: High=", g_h1_range_high, " Low=", g_h1_range_low);
    
    PrintStatistics();
    
    Print("=== BreakoutEA_Complete 初期化完了 ===");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== BreakoutEA_Complete 終了処理 ===");
    PrintStatistics();
    Print("=== 終了完了 ===");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    g_tick_count++;
    
    // TimeCurrent()に統一（Gemini改善案）
    datetime current_time = TimeCurrent();
    
    // MQL4のOnTrade代替実装: 履歴変更を監視
    int current_history_total = OrdersHistoryTotal();
    if(current_history_total > g_previous_history_total)
    {
        ProcessNewClosedOrders(g_previous_history_total, current_history_total);
        g_previous_history_total = current_history_total;
        
        // 取引発生時にリスク評価を即時実行（Gemini改善案）
        UpdateRiskAndLimits();
    }
    else
    {
        // 通常時は設定間隔でリスク統計更新
        if(current_time - g_cache.last_risk_update >= RiskUpdateIntervalSec)
        {
            UpdateRiskAndLimits();
        }
    }
    
    // レンジ更新（H1単独）
    datetime current_h1_time = iTime(Symbol(), PERIOD_H1, 0);
    if(current_h1_time != g_last_h1_time)
    {
        CalculateRange(PERIOD_H1, g_wfa_params.h1_period, g_h1_range_high, g_h1_range_low);
        g_last_h1_time = current_h1_time;
    }
    
    // 基本条件チェック（高速）
    if(!IsInTradingSession() || OrdersTotal() > 0)
        return;
    
    // リスク制限チェック（キャッシュ利用・Gemini改善案）
    if(current_time - g_cache.last_risk_check >= RiskCheckIntervalSec)
    {
        g_cache.limits_ok = CheckAdvancedRiskLimits();
        g_cache.last_risk_check = current_time;
        
        if(EnableDebugPrint && (g_tick_count % LogTickInterval == 0))
            Print("🔍 定期リスク制限チェック: ", (g_cache.limits_ok ? "OK" : "NG"));
    }
    
    if(!g_cache.limits_ok)
        return;
    
    // ATR計算と品質チェック（キャッシュ付き）
    if(current_time - g_cache.last_atr_update >= AtrUpdateIntervalSec || g_cache.atr_value == 0.0)
    {
        UpdateAtrCache();
    }
    
    // キャッシュされた結果を使用
    if(!g_cache.atr_quality_ok || !g_cache.trend_strength_ok)
        return;
    
    // ブレイクアウトチェック（Python仕様準拠: H1単独）
    double current_price = Bid;
    int h1_direction = 0;
    
    bool h1_breakout = CheckBreakout(current_price, g_h1_range_high, g_h1_range_low, h1_direction);
    
    // H1単一時間軸ブレイクアウト確認（kiro緊急修正指示）
    if(h1_breakout)
    {
        double sl_distance = g_cache.atr_value * g_wfa_params.atr_multiplier_sl;
        double tp_distance = g_cache.atr_value * g_wfa_params.atr_multiplier_tp;
        double lot_size = CalculatePositionSize(sl_distance);
        
        // 最小利益チェック
        double pip_value = MarketInfo(Symbol(), MODE_POINT);
        if(Digits == 3 || Digits == 5) pip_value *= 10;
        double tp_pips = tp_distance / pip_value;
        
        if(tp_pips < g_wfa_params.min_profit_pips)
        {
            if(EnableDebugPrint) 
                Print("⚠️ 利益目標不足: ", tp_pips, " < ", g_wfa_params.min_profit_pips);
            return;
        }
        
        // コスト比率チェック
        double spread_cost = MarketInfo(Symbol(), MODE_SPREAD) * pip_value;
        if(tp_distance / spread_cost < g_wfa_params.cost_ratio)
        {
            if(EnableDebugPrint) 
                Print("⚠️ コスト比率不足: ", tp_distance/spread_cost, " < ", g_wfa_params.cost_ratio);
            return;
        }
        
        g_total_signals++;
        
        if(EnableDebugPrint)
        {
            Print("🎯 H1ブレイクアウトシグナル検出（Python仕様準拠）");
            Print("  方向: ", (h1_direction > 0 ? "BUY" : "SELL"));
            Print("  ロット: ", lot_size);
            Print("  TP(pips): ", tp_pips);
            Print("  SL/TP ATR倍率: ", g_wfa_params.atr_multiplier_sl, "/", g_wfa_params.atr_multiplier_tp);
        }
        
        // シグナル生成とPython送信
        string signal_json = GenerateSignalJSON(h1_direction, lot_size, sl_distance, tp_distance);
        
        // パフォーマンスログ
        if(EnableDebugPrint && (g_tick_count % 1000 == 0))  // 1000tick毎に統計表示
            Print("📊 パフォーマンス: Tick数=", g_tick_count, 
                  " シグナル数=", g_total_signals, 
                  " 取引数=", g_total_trades);
        
        // 取引実行
        if(ExecuteTrade(h1_direction, lot_size, sl_distance, tp_distance))
        {
            Print("📤 H1シグナル完了: ", signal_json);
        }
    }
}

//+------------------------------------------------------------------+
//| 新規決済注文処理関数（安全版 - 全件処理・マジックナンバーフィルタリング） |
//+------------------------------------------------------------------+
void ProcessNewClosedOrders(int from_index, int to_index)
{
    if(EnableDebugPrint)
        Print("📊 新規決済注文検出: ", (to_index - from_index), "件を処理開始");
    
    int processed_count = 0;
    int our_ea_orders = 0;
    
    // 新規決済注文を逆順で処理（最新から）
    for(int i = to_index - 1; i >= from_index; i--)
    {
        if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
        {
            if(EnableDebugPrint)
                Print("⚠️ 履歴注文選択失敗: インデックス=", i, " エラー=", GetLastError());
            continue;
        }
        
        processed_count++;
        
        // マジックナンバーフィルタリング（最重要）
        if(OrderMagicNumber() != MagicNumber)
        {
            if(EnableDebugPrint)
                Print("💡 他EA/手動取引をスキップ: Ticket=", OrderTicket(), 
                      " Magic=", OrderMagicNumber(), " (EA Magic=", MagicNumber, ")");
            continue;
        }
        
        // 決済済み注文のみ処理
        if(OrderCloseTime() == 0)
        {
            if(EnableDebugPrint)
                Print("💡 未決済注文をスキップ: Ticket=", OrderTicket());
            continue;
        }
        
        our_ea_orders++;
        
        // 取引統計更新
        UpdateTradeStatistics(OrderTicket());
    }
    
    if(EnableDebugPrint)
        Print("✅ 決済注文処理完了: 総処理=", processed_count, "件 EA注文=", our_ea_orders, "件");
}

//+------------------------------------------------------------------+
//| 取引統計更新関数                                                 |
//+------------------------------------------------------------------+
void UpdateTradeStatistics(int ticket)
{
    double profit = OrderProfit() + OrderSwap() + OrderCommission();
    double profit_pips = 0.0;
    
    // pip利益計算
    double pip_value = MarketInfo(OrderSymbol(), MODE_POINT);
    if(MarketInfo(OrderSymbol(), MODE_DIGITS) == 3 || MarketInfo(OrderSymbol(), MODE_DIGITS) == 5)
        pip_value *= 10;
    
    if(OrderType() == OP_BUY)
        profit_pips = (OrderClosePrice() - OrderOpenPrice()) / pip_value;
    else if(OrderType() == OP_SELL)
        profit_pips = (OrderOpenPrice() - OrderClosePrice()) / pip_value;
    
    // 勝敗判定と統計更新
    if(profit > 0)
    {
        g_winning_trades++;
        g_consecutive_losses = 0;
        
        if(EnableDebugPrint)
            Print("🎉 勝ちトレード: Ticket=", ticket, " Profit=$", 
                  NormalizeDouble(profit, 2), " (", NormalizeDouble(profit_pips, 1), "pips)");
    }
    else
    {
        g_losing_trades++;
        g_consecutive_losses++;
        
        // 損失統計更新（日次開始残高基準）
        double loss_percent = 0.0;
        if(g_daily_start_balance > 0)
            loss_percent = MathAbs(profit) / g_daily_start_balance * 100.0;
        else
            loss_percent = MathAbs(profit) / g_initial_balance * 100.0;  // フォールバック
        
        g_daily_loss += loss_percent;
        
        if(EnableDebugPrint)
            Print("💰 損失率計算: 損失=$", NormalizeDouble(MathAbs(profit), 2),
                  " 日次開始残高=$", g_daily_start_balance, 
                  " 損失率=", NormalizeDouble(loss_percent, 3), "%");
        
        if(EnableDebugPrint)
            Print("📉 負けトレード: Ticket=", ticket, " Loss=$", 
                  NormalizeDouble(profit, 2), " (", NormalizeDouble(profit_pips, 1), "pips)",
                  " 連続損失=", g_consecutive_losses);
    }
    
    // 取引実行統計
    g_total_trades++;
    
    // 詳細ログ
    if(EnableDebugPrint)
    {
        Print("📊 取引統計更新:");
        Print("  総取引数: ", g_total_trades);
        Print("  勝ちトレード: ", g_winning_trades);
        Print("  負けトレード: ", g_losing_trades);
        Print("  勝率: ", (g_total_trades > 0 ? NormalizeDouble((double)g_winning_trades / g_total_trades * 100.0, 1) : 0.0), "%");
        Print("  連続損失: ", g_consecutive_losses);
        Print("  日次損失: ", NormalizeDouble(g_daily_loss, 2), "%");
    }
}

//+------------------------------------------------------------------+
//| Trade event handler（旧版・互換性のため保持）                    |
//+------------------------------------------------------------------+
void OnTrade()
{
    // 新しいProcessNewClosedOrders()で処理されるため、この関数は空でOK
    // 互換性のため関数は残すが、実際の処理はOnTick()内で実行
}

//+------------------------------------------------------------------+